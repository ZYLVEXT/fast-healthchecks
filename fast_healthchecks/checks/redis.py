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
import contextlib
from traceback import format_exc
from typing import TYPE_CHECKING, Any, TypedDict, final

from fast_healthchecks.checks._base import DEFAULT_HC_TIMEOUT, HealthCheckDSN
from fast_healthchecks.compat import RedisDsn
from fast_healthchecks.models import HealthCheckResult

IMPORT_ERROR_MSG = "redis is not installed. Install it with `pip install fast-healthchecks[redis]`."

try:
    from redis.asyncio import Redis
    from redis.asyncio.connection import parse_url
except ImportError as exc:
    raise ImportError(IMPORT_ERROR_MSG) from exc

if TYPE_CHECKING:
    from redis.asyncio.connection import ConnectKwargs


class ParseDSNResult(TypedDict, total=True):
    """A dictionary containing the results of parsing a DSN."""

    parse_result: ConnectKwargs


@final
class RedisHealthCheck(HealthCheckDSN[HealthCheckResult]):
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

    __slots__ = (
        "_client",
        "_client_loop",
        "_database",
        "_host",
        "_name",
        "_password",
        "_port",
        "_ssl",
        "_ssl_ca_certs",
        "_timeout",
        "_user",
    )

    _host: str
    _port: int
    _database: str | int
    _user: str | None
    _password: str | None
    _timeout: float
    _name: str
    _ssl: bool
    _ssl_ca_certs: str | None
    _client: Redis | None
    _client_loop: asyncio.AbstractEventLoop | None

    def __init__(  # noqa: PLR0913
        self,
        *,
        host: str = "localhost",
        port: int = 6379,
        database: str | int = 0,
        user: str | None = None,
        password: str | None = None,
        ssl: bool = False,
        ssl_ca_certs: str | None = None,
        timeout: float | None = DEFAULT_HC_TIMEOUT,
        name: str = "Redis",
    ) -> None:
        """Initialize the RedisHealthCheck class.

        Args:
            host: The host to connect to.
            port: The port to connect to.
            database: The database to connect to.
            user: The user to authenticate with.
            password: The password to authenticate with.
            ssl: Whether to use SSL.
            ssl_ca_certs: Path to CA certificates for SSL.
            timeout: The timeout for the connection.
            name: The name of the health check.
        """
        self._host = host
        self._port = port
        self._database = database
        self._user = user
        self._password = password
        self._ssl = ssl
        self._ssl_ca_certs = ssl_ca_certs
        self._timeout = DEFAULT_HC_TIMEOUT if timeout is None else timeout
        self._name = name
        self._client = None
        self._client_loop = None

    async def aclose(self) -> None:
        """Close the cached Redis client if present."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            self._client_loop = None

    def _get_client(self) -> Redis:
        if self._client is None:
            try:
                self._client_loop = asyncio.get_running_loop()
            except RuntimeError:
                self._client_loop = None
            self._client = Redis(
                host=self._host,
                port=self._port,
                db=self._database,
                username=self._user,
                password=self._password,
                socket_timeout=self._timeout,
                single_connection_client=True,
                ssl=self._ssl,
                ssl_ca_certs=self._ssl_ca_certs,
            )
        return self._client

    @classmethod
    def parse_dsn(cls, dsn: str) -> ParseDSNResult:
        """Parse the DSN and return the results.

        Args:
            dsn: The DSN to parse.

        Returns:
            ParseDSNResult: The results of parsing the DSN.
        """
        parse_result: ConnectKwargs = parse_url(str(dsn))
        return {"parse_result": parse_result}

    @classmethod
    def from_dsn(
        cls,
        dsn: RedisDsn | str,
        *,
        name: str = "Redis",
        timeout: float = DEFAULT_HC_TIMEOUT,
    ) -> RedisHealthCheck:
        """Create a RedisHealthCheck from a DSN.

        Args:
            dsn: The DSN to connect to.
            name: The name of the health check.
            timeout: The timeout for the connection.

        Returns:
            A RedisHealthCheck instance.
        """
        dsn = cls.validate_dsn(dsn, allowed_schemes=("redis", "rediss"))
        parsed_dsn = cls.parse_dsn(dsn)
        parse_result = parsed_dsn["parse_result"]
        ssl_ca_certs: str | None = parse_result.get("ssl_ca_certs", None)
        ssl = "ssl_ca_certs" in parse_result and bool(ssl_ca_certs)
        return RedisHealthCheck(
            host=parse_result.get("host", "localhost"),
            port=parse_result.get("port", 6379),
            database=parse_result.get("db", 0),
            user=parse_result.get("username"),
            password=parse_result.get("password"),
            ssl=ssl,
            ssl_ca_certs=ssl_ca_certs,
            timeout=timeout,
            name=name,
        )

    async def __call__(self) -> HealthCheckResult:
        """Perform a health check on Redis.

        Returns:
            HealthCheckResult: The result of the health check.
        """
        try:
            try:
                running = asyncio.get_running_loop()
            except RuntimeError:
                running = None
            if self._client is not None and self._client_loop is not running:
                with contextlib.suppress(Exception):
                    await self._client.aclose()
                self._client = None
                self._client_loop = None
            redis = self._get_client()
            healthy_raw = redis.ping()
            healthy = bool(await healthy_raw) if asyncio.iscoroutine(healthy_raw) else bool(healthy_raw)
            return HealthCheckResult(name=self._name, healthy=healthy)
        except Exception:  # noqa: BLE001
            return HealthCheckResult(name=self._name, healthy=False, error_details=format_exc())

    def to_dict(self) -> dict[str, Any]:
        """Convert the RedisHealthCheck to a dictionary.

        Returns:
            dict: The check attributes as a dictionary.
        """
        return {
            "host": self._host,
            "port": self._port,
            "database": self._database,
            "user": self._user,
            "password": self._password,
            "ssl": self._ssl,
            "ssl_ca_certs": self._ssl_ca_certs,
            "timeout": self._timeout,
            "name": self._name,
        }
