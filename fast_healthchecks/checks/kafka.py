"""This module provides a health check class for Kafka.

Classes:
    KafkaHealthCheck: A class to perform health checks on Kafka.

Usage:
    The KafkaHealthCheck class can be used to perform health checks on Kafka by calling it.

Example:
    health_check = KafkaHealthCheck(
        bootstrap_servers="localhost:9092",
        security_protocol="PLAINTEXT",
    )
    result = await health_check()
    print(result.healthy)
"""

from __future__ import annotations

import asyncio
import contextlib
from traceback import format_exc
from typing import TYPE_CHECKING, Any, Literal, TypeAlias, final
from urllib.parse import unquote, urlsplit

from fast_healthchecks.checks._base import DEFAULT_HC_TIMEOUT, HealthCheck
from fast_healthchecks.models import HealthCheckResult

if TYPE_CHECKING:
    import ssl

    from fast_healthchecks.compat import KafkaDsn

IMPORT_ERROR_MSG = "aiokafka is not installed. Install it with `pip install fast-healthchecks[aiokafka]`."

try:
    from aiokafka.admin import AIOKafkaAdminClient
except ImportError as exc:
    raise ImportError(IMPORT_ERROR_MSG) from exc

SecurityProtocol: TypeAlias = Literal["SSL", "PLAINTEXT", "SASL_PLAINTEXT", "SASL_SSL"]
SaslMechanism: TypeAlias = Literal["PLAIN", "GSSAPI", "SCRAM-SHA-256", "SCRAM-SHA-512", "OAUTHBEARER"]


@final
class KafkaHealthCheck(HealthCheck[HealthCheckResult]):
    """A class to perform health checks on Kafka.

    Attributes:
        _bootstrap_servers: The Kafka bootstrap servers.
        _name: The name of the health check.
        _sasl_mechanism: The SASL mechanism to use.
        _sasl_plain_password: The SASL plain password.
        _sasl_plain_username: The SASL plain username.
        _security_protocol: The security protocol to use.
        _ssl_context: The SSL context to use.
        _timeout: The timeout for the health check.
    """

    __slots__ = (
        "_bootstrap_servers",
        "_client",
        "_client_loop",
        "_name",
        "_sasl_mechanism",
        "_sasl_plain_password",
        "_sasl_plain_username",
        "_security_protocol",
        "_ssl_context",
        "_timeout",
    )

    _bootstrap_servers: str
    _ssl_context: ssl.SSLContext | None
    _security_protocol: SecurityProtocol
    _sasl_mechanism: SaslMechanism
    _sasl_plain_username: str | None
    _sasl_plain_password: str | None
    _timeout: float
    _name: str
    _client: AIOKafkaAdminClient | None
    _client_loop: asyncio.AbstractEventLoop | None

    def __init__(  # noqa: PLR0913
        self,
        *,
        bootstrap_servers: str,
        ssl_context: ssl.SSLContext | None = None,
        security_protocol: SecurityProtocol = "PLAINTEXT",
        sasl_mechanism: SaslMechanism = "PLAIN",
        sasl_plain_username: str | None = None,
        sasl_plain_password: str | None = None,
        timeout: float = DEFAULT_HC_TIMEOUT,
        name: str = "Kafka",
    ) -> None:
        """Initialize the KafkaHealthCheck.

        Args:
            bootstrap_servers: The Kafka bootstrap servers.
            ssl_context: The SSL context to use.
            security_protocol: The security protocol to use.
            sasl_mechanism: The SASL mechanism to use.
            sasl_plain_username: The SASL plain username.
            sasl_plain_password: The SASL plain password.
            timeout: The timeout for the health check.
            name: The name of the health check.

        Raises:
            ValueError: If the security protocol or SASL mechanism is invalid.
        """
        self._bootstrap_servers = bootstrap_servers
        self._ssl_context = ssl_context
        if security_protocol not in {"SSL", "PLAINTEXT", "SASL_PLAINTEXT", "SASL_SSL"}:
            msg = f"Invalid security protocol: {security_protocol}"
            raise ValueError(msg) from None
        self._security_protocol = security_protocol
        if sasl_mechanism not in {"PLAIN", "GSSAPI", "SCRAM-SHA-256", "SCRAM-SHA-512", "OAUTHBEARER"}:
            msg = f"Invalid SASL mechanism: {sasl_mechanism}"
            raise ValueError(msg) from None
        self._sasl_mechanism = sasl_mechanism
        self._sasl_plain_username = sasl_plain_username
        self._sasl_plain_password = sasl_plain_password
        self._timeout = timeout
        self._name = name
        self._client = None
        self._client_loop = None

    async def aclose(self) -> None:
        """Close the cached Kafka admin client if present."""
        if self._client is not None:
            await self._client.close()
            self._client = None
            self._client_loop = None

    def _get_client(self) -> AIOKafkaAdminClient:
        if self._client is None:
            try:
                self._client_loop = asyncio.get_running_loop()
            except RuntimeError:
                self._client_loop = None
            self._client = AIOKafkaAdminClient(
                bootstrap_servers=self._bootstrap_servers,
                client_id="fast_healthchecks",
                request_timeout_ms=int(self._timeout * 1000),
                ssl_context=self._ssl_context,
                security_protocol=self._security_protocol,
                sasl_mechanism=self._sasl_mechanism,
                sasl_plain_username=self._sasl_plain_username,
                sasl_plain_password=self._sasl_plain_password,
            )
        return self._client

    @classmethod
    def from_dsn(  # noqa: PLR0913
        cls,
        dsn: KafkaDsn | str,
        *,
        ssl_context: ssl.SSLContext | None = None,
        security_protocol: SecurityProtocol = "PLAINTEXT",
        sasl_mechanism: SaslMechanism = "PLAIN",
        timeout: float = DEFAULT_HC_TIMEOUT,
        name: str = "Kafka",
    ) -> KafkaHealthCheck:
        """Create a KafkaHealthCheck from a DSN.

        Returns:
            KafkaHealthCheck: The configured check instance.

        Raises:
            ValueError: If DSN scheme is invalid or bootstrap servers are missing.
        """
        parsed = urlsplit(str(dsn))
        if parsed.scheme != "kafka":
            msg = "Kafka DSN must start with kafka://"
            raise ValueError(msg) from None

        netloc = parsed.netloc
        sasl_plain_username: str | None = None
        sasl_plain_password: str | None = None
        if "@" in netloc:
            userinfo, hosts = netloc.rsplit("@", 1)
            netloc = hosts
            if ":" in userinfo:
                username, password = userinfo.split(":", 1)
                sasl_plain_username = unquote(username) or None
                sasl_plain_password = unquote(password) or None
            else:
                sasl_plain_username = unquote(userinfo) or None

        bootstrap_servers = netloc or parsed.path.lstrip("/")
        if not bootstrap_servers:
            msg = "Kafka DSN must include bootstrap servers"
            raise ValueError(msg) from None

        return cls(
            bootstrap_servers=bootstrap_servers,
            ssl_context=ssl_context,
            security_protocol=security_protocol,
            sasl_mechanism=sasl_mechanism,
            sasl_plain_username=sasl_plain_username,
            sasl_plain_password=sasl_plain_password,
            timeout=timeout,
            name=name,
        )

    async def __call__(self) -> HealthCheckResult:
        """Perform the health check on Kafka.

        Returns:
            HealthCheckResult: The result of the health check.
        """
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if self._client is not None and self._client_loop is not running:
            with contextlib.suppress(Exception):
                await self._client.close()
            self._client = None
            self._client_loop = None
        client = self._get_client()
        try:
            await client.start()
            await client.list_topics()
            return HealthCheckResult(name=self._name, healthy=True)
        except Exception:  # noqa: BLE001
            with contextlib.suppress(Exception):
                await client.close()
            self._client = None
            self._client_loop = None
            return HealthCheckResult(name=self._name, healthy=False, error_details=format_exc())

    def to_dict(self) -> dict[str, Any]:
        """Convert the KafkaHealthCheck to a dictionary.

        Returns:
            dict: The check attributes as a dictionary.
        """
        return {
            "bootstrap_servers": self._bootstrap_servers,
            "ssl_context": self._ssl_context,
            "security_protocol": self._security_protocol,
            "sasl_mechanism": self._sasl_mechanism,
            "sasl_plain_username": self._sasl_plain_username,
            "sasl_plain_password": self._sasl_plain_password,
            "timeout": self._timeout,
            "name": self._name,
        }
