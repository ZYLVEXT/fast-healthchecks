"""This module provides a health check class for Redis.

Classes:
    RedisHealthCheck: A class to perform health checks on Redis.

Usage:
    The RedisHealthCheck class can be used to perform health checks on Redis by calling it.

Example:
    health_check = RedisHealthCheck(
        host="localhost",
        port=6379,
    )
    result = await health_check()
    print(result.healthy)
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, final
from urllib.parse import urlsplit

from fast_healthchecks.checks._base import (
    _CLIENT_CACHING_SLOTS,
    DEFAULT_HC_TIMEOUT,
    ClientCachingMixin,
    HealthCheckDSN,
    healthcheck_safe,
    result_unhealthy_dependency,
)
from fast_healthchecks.checks._imports import raise_optional_import_error
from fast_healthchecks.checks.configs import RedisConfig
from fast_healthchecks.models import HealthCheckResult

try:
    from redis.asyncio import Redis
    from redis.asyncio.connection import parse_url
except ImportError as exc:
    raise_optional_import_error("redis", "redis", exc)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from redis.asyncio.connection import ConnectKwargs

from fast_healthchecks.checks.dsn_parsing import RedisParseDsnResult

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from redis.asyncio.connection import ConnectKwargs


def _close_redis_client(client: Redis) -> Awaitable[None]:
    return client.aclose()


@final
class RedisHealthCheck(ClientCachingMixin["Redis"], HealthCheckDSN[HealthCheckResult, RedisParseDsnResult]):
    """A class to perform health checks on Redis.

    Attributes:
        _database: The database to connect to.
        _host: The host to connect to.
        _name: The name of the health check.
        _password: The password to authenticate with.
        _port: The port to connect to.
        _timeout: The timeout for the connection.
        _user: The user to authenticate with.
        _ssl: Whether to use SSL or not.
        _ssl_ca_certs: The path to the CA certificate.
    """

    __slots__ = (*_CLIENT_CACHING_SLOTS, "_config", "_name")

    _config: RedisConfig
    _name: str
    _client: Redis | None
    _client_loop: asyncio.AbstractEventLoop | None

    def __init__(
        self,
        *,
        config: RedisConfig | None = None,
        name: str = "Redis",
        close_client_fn: Callable[[Redis], Awaitable[None]] = _close_redis_client,
        **kwargs: Any,  # noqa: ANN401
    ) -> None:
        """Initialize the RedisHealthCheck class.

        Args:
            config: Connection config. If None, built from kwargs (host, port, database, etc.).
            name: The name of the health check.
            close_client_fn: Callable to close the cached client. Defaults to the
                standard Redis aclose.
            **kwargs: Passed to RedisConfig when config is None (host, port, database,
                user, password, ssl, ssl_ca_certs, timeout).
        """
        if config is None:
            config = RedisConfig(**kwargs)
        self._config = config
        self._name = name
        super().__init__(close_client_fn=close_client_fn)

    def _create_client(self) -> Redis:
        c = self._config
        return Redis(
            host=c.host,
            port=c.port,
            db=c.database,
            username=c.user,
            password=c.password,
            socket_timeout=c.timeout,
            single_connection_client=True,
            ssl=c.ssl,
            ssl_ca_certs=c.ssl_ca_certs,
        )

    @classmethod
    def _allowed_schemes(cls) -> tuple[str, ...]:
        return ("redis", "rediss")

    @classmethod
    def _default_name(cls) -> str:
        return "Redis"

    @classmethod
    def parse_dsn(cls, dsn: str) -> RedisParseDsnResult:
        """Parse the DSN and return the results.

        Args:
            dsn: The DSN to parse.

        Returns:
            RedisParseDsnResult: The results of parsing the DSN.
        """
        parse_result: ConnectKwargs = parse_url(str(dsn))
        scheme = urlsplit(dsn).scheme.lower()
        return {"parse_result": parse_result, "scheme": scheme}

    @classmethod
    def _from_parsed_dsn(
        cls,
        parsed: RedisParseDsnResult,
        *,
        name: str = "Redis",
        timeout: float = DEFAULT_HC_TIMEOUT,
        **_kwargs: object,
    ) -> RedisHealthCheck:
        parse_result = parsed["parse_result"]
        scheme = parsed.get("scheme", "")
        ssl_ca_certs: str | None = parse_result.get("ssl_ca_certs")
        ssl = parse_result.get("ssl", False) or bool(ssl_ca_certs) or (scheme == "rediss")
        config = RedisConfig(
            host=parse_result.get("host", "localhost"),
            port=parse_result.get("port", 6379),
            database=parse_result.get("db", 0),
            user=parse_result.get("username"),
            password=parse_result.get("password"),
            ssl=ssl,
            ssl_ca_certs=ssl_ca_certs,
            timeout=timeout,
        )
        return cls(config=config, name=name)

    @healthcheck_safe(invalidate_on_error=True)
    async def __call__(self) -> HealthCheckResult:
        """Perform a health check on Redis.

        Returns:
            HealthCheckResult: The result of the health check.
        """
        redis = await self._ensure_client()
        ping_result = redis.ping()
        healthy = bool(await ping_result) if asyncio.iscoroutine(ping_result) else bool(ping_result)
        if healthy:
            return HealthCheckResult(name=self._name, healthy=True)
        return result_unhealthy_dependency(name=self._name, message="Redis ping returned unhealthy status")
