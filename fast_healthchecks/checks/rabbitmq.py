"""This module provides a health check class for RabbitMQ.

Classes:
    RabbitMQHealthCheck: A class to perform health checks on RabbitMQ.

**Security:** When using DSN or config without a password (or with default
credentials), the library falls back to ``user="guest"`` and ``password="guest"``.
These defaults are for local development only; do not use them in production or
on non-local brokers. See SECURITY.md and :class:`RabbitMQConfig` docstring.

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

from typing import TYPE_CHECKING, Any, final
from urllib.parse import urlsplit

from fast_healthchecks.checks._base import (
    _CLIENT_CACHING_SLOTS,
    DEFAULT_HC_TIMEOUT,
    ClientCachingMixin,
    HealthCheckDSN,
    healthcheck_safe,
)
from fast_healthchecks.checks._imports import raise_optional_import_error
from fast_healthchecks.checks.configs import RabbitMQConfig
from fast_healthchecks.checks.dsn_parsing import RabbitMQParseDsnResult
from fast_healthchecks.models import HealthCheckResult

if TYPE_CHECKING:
    import asyncio
    from collections.abc import Awaitable, Callable

    from aio_pika.abc import AbstractRobustConnection

try:
    import aio_pika
except ImportError as exc:
    raise_optional_import_error("aio-pika", "aio-pika", exc)


def _close_rabbitmq_client(client: AbstractRobustConnection) -> Awaitable[None]:
    return client.close()


@final
class RabbitMQHealthCheck(
    ClientCachingMixin["AbstractRobustConnection"],
    HealthCheckDSN[HealthCheckResult, RabbitMQParseDsnResult],
):
    """A class to perform health checks on RabbitMQ.

    Uses ClientCachingMixin to reuse a single connection instead of opening
    a new one on every check.

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

    __slots__ = (*_CLIENT_CACHING_SLOTS, "_config", "_name")

    _config: RabbitMQConfig
    _name: str
    _client: AbstractRobustConnection | None
    _client_loop: asyncio.AbstractEventLoop | None

    def __init__(
        self,
        *,
        config: RabbitMQConfig | None = None,
        name: str = "RabbitMQ",
        close_client_fn: Callable[[AbstractRobustConnection], Awaitable[None]] = _close_rabbitmq_client,
        **kwargs: Any,  # noqa: ANN401
    ) -> None:
        """Initialize the RabbitMQHealthCheck.

        Args:
            config: Connection config. If None, built from kwargs (host, user, password, etc.).
            name: The name of the health check.
            close_client_fn: Callable to close the cached connection.
            **kwargs: Passed to RabbitMQConfig when config is None.
        """
        if config is None:
            config = RabbitMQConfig(**kwargs)
        self._config = config
        self._name = name
        super().__init__(close_client_fn=close_client_fn)

    def _create_client(self) -> Awaitable[AbstractRobustConnection]:
        c = self._config
        return aio_pika.connect_robust(
            host=c.host,
            port=c.port,
            login=c.user,
            password=c.password,
            ssl=c.secure,
            virtualhost=c.vhost,
            timeout=c.timeout,
        )

    @classmethod
    def _allowed_schemes(cls) -> tuple[str, ...]:
        return ("amqp", "amqps")

    @classmethod
    def _default_name(cls) -> str:
        return "RabbitMQ"

    @classmethod
    def parse_dsn(cls, dsn: str) -> RabbitMQParseDsnResult:
        """Parse the DSN and return the results.

        Args:
            dsn: The DSN to parse.

        Returns:
            RabbitMQParseDsnResult: The results of parsing the DSN.
        """
        parse_result = urlsplit(dsn)
        return {"parse_result": parse_result}

    @classmethod
    def _from_parsed_dsn(
        cls,
        parsed: RabbitMQParseDsnResult,
        *,
        name: str = "RabbitMQ",
        timeout: float = DEFAULT_HC_TIMEOUT,
        **_kwargs: object,
    ) -> RabbitMQHealthCheck:
        parse_result = parsed["parse_result"]
        # Default "guest"/"guest" is development-only; see SECURITY.md and RabbitMQConfig.
        config = RabbitMQConfig(
            host=parse_result.hostname or "localhost",
            user=parse_result.username or "guest",
            password=parse_result.password or "guest",
            port=parse_result.port or 5672,
            vhost=parse_result.path.lstrip("/") or "/",
            secure=parse_result.scheme == "amqps",
            timeout=timeout,
        )
        return cls(config=config, name=name)

    @healthcheck_safe(invalidate_on_error=True)
    async def __call__(self) -> HealthCheckResult:
        """Perform the health check on RabbitMQ.

        ClientCachingMixin handles connection persistence; _ensure_client
        validates the connection via aio-pika's robust logic.

        Returns:
            HealthCheckResult: The result of the health check.
        """
        _ = await self._ensure_client()
        return HealthCheckResult(name=self._name, healthy=True)
