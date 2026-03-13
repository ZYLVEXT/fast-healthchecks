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

import contextlib
from typing import TYPE_CHECKING, Any, cast, final
from urllib.parse import unquote, urlsplit

from fast_healthchecks.checks._base import (
    _CLIENT_CACHING_SLOTS,
    DEFAULT_HC_TIMEOUT,
    ClientCachingMixin,
    HealthCheckDSN,
    healthcheck_safe,
)
from fast_healthchecks.checks._imports import raise_optional_import_error
from fast_healthchecks.checks.configs import KafkaConfig
from fast_healthchecks.checks.dsn_parsing import KafkaParseDsnResult
from fast_healthchecks.models import HealthCheckResult

if TYPE_CHECKING:
    import asyncio
    import ssl
    from collections.abc import Awaitable, Callable

    from fast_healthchecks.checks.configs import SaslMechanism, SecurityProtocol

try:
    from aiokafka.admin import AIOKafkaAdminClient
except ImportError as exc:
    raise_optional_import_error("aiokafka", "aiokafka", exc)


def _close_kafka_client(client: AIOKafkaAdminClient) -> Awaitable[None]:
    return client.close()


@final
class KafkaHealthCheck(
    ClientCachingMixin["AIOKafkaAdminClient"],
    HealthCheckDSN[HealthCheckResult, KafkaParseDsnResult],
):
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

    __slots__ = (*_CLIENT_CACHING_SLOTS, "_config", "_name")

    _config: KafkaConfig
    _name: str
    _client: AIOKafkaAdminClient | None
    _client_loop: asyncio.AbstractEventLoop | None

    def __init__(
        self,
        *,
        config: KafkaConfig | None = None,
        name: str = "Kafka",
        close_client_fn: Callable[[AIOKafkaAdminClient], Awaitable[None]] = _close_kafka_client,
        **kwargs: Any,  # noqa: ANN401
    ) -> None:
        """Initialize the KafkaHealthCheck.

        Args:
            config: Connection config. If None, built from kwargs (bootstrap_servers, etc.).
            name: The name of the health check.
            close_client_fn: Callable to close the cached client.
            **kwargs: Passed to KafkaConfig when config is None.
        """
        if config is None:
            config = KafkaConfig(**kwargs)
        self._config = config
        self._name = name
        super().__init__(close_client_fn=close_client_fn)

    def _create_client(self) -> AIOKafkaAdminClient:
        c = self._config
        return AIOKafkaAdminClient(
            bootstrap_servers=c.bootstrap_servers,
            client_id="fast_healthchecks",
            request_timeout_ms=int(c.timeout * 1000),
            ssl_context=c.ssl_context,
            security_protocol=c.security_protocol,
            sasl_mechanism=c.sasl_mechanism,
            sasl_plain_username=c.sasl_plain_username,
            sasl_plain_password=c.sasl_plain_password,
        )

    @classmethod
    def _allowed_schemes(cls) -> tuple[str, ...]:
        return ("kafka", "kafkas")

    @classmethod
    def _default_name(cls) -> str:
        return "Kafka"

    @classmethod
    def parse_dsn(cls, dsn: str) -> KafkaParseDsnResult:
        """Parse the Kafka DSN and return the results.

        Scheme ``kafkas`` implies SSL (SASL_SSL when credentials present).
        Scheme ``kafka`` implies PLAINTEXT (SASL_PLAINTEXT when credentials present).
        Kwargs to from_dsn override DSN-derived values.

        Args:
            dsn: The DSN to parse.

        Returns:
            KafkaParseDsnResult: The results of parsing the DSN.

        Raises:
            ValueError: If bootstrap servers are missing.
        """
        parsed = urlsplit(dsn)
        scheme = (parsed.scheme or "kafka").lower()
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

        if scheme == "kafkas":
            security_protocol = "SASL_SSL" if (sasl_plain_username or sasl_plain_password) else "SSL"
        else:
            security_protocol = "SASL_PLAINTEXT" if (sasl_plain_username or sasl_plain_password) else "PLAINTEXT"

        return {
            "bootstrap_servers": bootstrap_servers,
            "sasl_plain_username": sasl_plain_username,
            "sasl_plain_password": sasl_plain_password,
            "security_protocol": security_protocol,
        }

    @classmethod
    def _from_parsed_dsn(
        cls,
        parsed: KafkaParseDsnResult,
        *,
        name: str = "Kafka",
        timeout: float = DEFAULT_HC_TIMEOUT,
        **kwargs: object,
    ) -> KafkaHealthCheck:
        config = KafkaConfig(
            bootstrap_servers=parsed["bootstrap_servers"],
            ssl_context=cast("ssl.SSLContext | None", kwargs.get("ssl_context")),
            security_protocol=cast(
                "SecurityProtocol",
                kwargs.get("security_protocol", parsed["security_protocol"]) or "PLAINTEXT",
            ),
            sasl_mechanism=cast("SaslMechanism", kwargs.get("sasl_mechanism", "PLAIN")),
            sasl_plain_username=parsed["sasl_plain_username"],
            sasl_plain_password=parsed["sasl_plain_password"],
            timeout=timeout,
        )
        return cls(config=config, name=name)

    @healthcheck_safe(invalidate_on_error=True)
    async def __call__(self) -> HealthCheckResult:
        """Perform the health check on Kafka.

        Returns:
            HealthCheckResult: The result of the health check.
        """
        client = await self._ensure_client()
        if not getattr(client, "_started", False):  # pragma: no branch
            await client.start()
            with contextlib.suppress(AttributeError):
                client._started = True  # noqa: SLF001
        await client.list_topics()
        return HealthCheckResult(name=self._name, healthy=True)
