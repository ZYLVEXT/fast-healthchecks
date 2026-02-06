"""This module provides a health check class for RabbitMQ.

Classes:
    RabbitMQHealthCheck: A class to perform health checks on RabbitMQ.

Usage:
    The RabbitMQHealthCheck class can be used to perform health checks on RabbitMQ by calling it.

Example:
    health_check = RabbitMQHealthCheck(
        host="localhost",
        port=5672,
        username="guest",
        password="guest",
    )
    result = await health_check()
    print(result.healthy)
"""

from __future__ import annotations

from traceback import format_exc
from typing import Any, TypedDict, final
from urllib.parse import ParseResult, urlparse

from fast_healthchecks.checks._base import DEFAULT_HC_TIMEOUT, HealthCheckDSN
from fast_healthchecks.compat import AmqpDsn
from fast_healthchecks.models import HealthCheckResult

IMPORT_ERROR_MSG = "aio-pika is not installed. Install it with `pip install fast-healthchecks[aio-pika]`."

try:
    import aio_pika
except ImportError as exc:
    raise ImportError(IMPORT_ERROR_MSG) from exc


class ParseDSNResult(TypedDict, total=True):
    """A dictionary containing the results of parsing a DSN."""

    parse_result: ParseResult


@final
class RabbitMQHealthCheck(HealthCheckDSN[HealthCheckResult]):
    """A class to perform health checks on RabbitMQ.

    Attributes:
        _host: The RabbitMQ host.
        _name: The name of the health check.
        _password: The RabbitMQ password.
        _port: The RabbitMQ port.
        _secure: Whether to use a secure connection.
        _timeout: The timeout for the health check.
        _user: The RabbitMQ user.
        _vhost: The RabbitMQ virtual host.
    """

    __slots__ = ("_host", "_name", "_password", "_port", "_secure", "_timeout", "_user", "_vhost")

    _host: str
    _port: int
    _secure: bool
    _user: str
    _vhost: str
    _password: str
    _timeout: float
    _name: str

    def __init__(  # noqa: PLR0913
        self,
        *,
        host: str,
        user: str,
        password: str,
        port: int = 5672,
        vhost: str = "/",
        secure: bool = False,
        timeout: float = DEFAULT_HC_TIMEOUT,
        name: str = "RabbitMQ",
    ) -> None:
        """Initialize the RabbitMQHealthCheck.

        Args:
            host: The RabbitMQ host.
            user: The RabbitMQ user
            password: The RabbitMQ password
            port: The RabbitMQ port
            vhost: The RabbitMQ virtual host
            secure: Whether to use a secure connection
            timeout: The timeout for the health check
            name: The name of the health check
        """
        self._host = host
        self._user = user
        self._password = password
        self._port = port
        self._vhost = vhost
        self._secure = secure
        self._timeout = timeout
        self._name = name

    @classmethod
    def parse_dsn(cls, dsn: str) -> ParseDSNResult:
        """Parse the DSN and return the results.

        Args:
            dsn: The DSN to parse.

        Returns:
            ParseDSNResult: The results of parsing the DSN.
        """
        parse_result: ParseResult = urlparse(dsn)
        return {"parse_result": parse_result}

    @classmethod
    def from_dsn(
        cls,
        dsn: AmqpDsn | str,
        *,
        name: str = "RabbitMQ",
        timeout: float = DEFAULT_HC_TIMEOUT,
    ) -> RabbitMQHealthCheck:
        """Create a RabbitMQHealthCheck from a DSN.

        Args:
            dsn: The DSN for the RabbitMQ connection.
            name: The name of the health check.
            timeout: The timeout for the health check.

        Returns:
            RabbitMQHealthCheck: The configured check instance.
        """
        dsn = cls.validate_dsn(dsn, allowed_schemes=("amqp", "amqps"))
        parsed_dsn = cls.parse_dsn(dsn)
        parse_result = parsed_dsn["parse_result"]
        return RabbitMQHealthCheck(
            host=parse_result.hostname or "localhost",
            user=parse_result.username or "guest",
            password=parse_result.password or "guest",
            port=parse_result.port or 5672,
            vhost=parse_result.path.lstrip("/") or "/",
            secure=parse_result.scheme == "amqps",
            timeout=timeout,
            name=name,
        )

    async def __call__(self) -> HealthCheckResult:
        """Perform the health check on RabbitMQ.

        Returns:
            HealthCheckResult: The result of the health check.
        """
        try:
            async with await aio_pika.connect_robust(
                host=self._host,
                port=self._port,
                login=self._user,
                password=self._password,
                ssl=self._secure,
                virtualhost=self._vhost,
                timeout=self._timeout,
            ):
                return HealthCheckResult(name=self._name, healthy=True)
        except Exception:  # noqa: BLE001
            return HealthCheckResult(name=self._name, healthy=False, error_details=format_exc())

    def to_dict(self) -> dict[str, Any]:
        """Convert the RabbitMQHealthCheck to a dictionary.

        Returns:
            dict: The check attributes as a dictionary.
        """
        return {
            "host": self._host,
            "user": self._user,
            "password": self._password,
            "port": self._port,
            "vhost": self._vhost,
            "secure": self._secure,
            "timeout": self._timeout,
            "name": self._name,
        }
