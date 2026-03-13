"""This module provides a health check class for PostgreSQL using asyncpg.

Classes:
    PostgreSQLAsyncPGHealthCheck: A class to perform health checks on a PostgreSQL database using asyncpg.

Usage:
    The PostgreSQLAsyncPGHealthCheck class can be used to perform health checks on a PostgreSQL database by
    connecting to the database and executing a simple query.

Example:
    health_check = PostgreSQLAsyncPGHealthCheck(
        host="localhost",
        port=5432,
        user="username",
        password="password",
        database="dbname"
    )
    # or
    health_check = PostgreSQLAsyncPGHealthCheck.from_dsn(
        "postgresql://username:password@localhost:5432/dbname",
    )
    result = await health_check()
    print(result.healthy)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fast_healthchecks.checks._base import DEFAULT_HC_TIMEOUT, healthcheck_safe, result_unhealthy_dependency
from fast_healthchecks.checks._imports import raise_optional_import_error
from fast_healthchecks.checks.configs import PostgresAsyncPGConfig
from fast_healthchecks.checks.postgresql.base import BasePostgreSQLHealthCheck
from fast_healthchecks.models import HealthCheckResult

try:
    import asyncpg
except ImportError as exc:
    raise_optional_import_error("asyncpg", "asyncpg", exc)

if TYPE_CHECKING:
    from asyncpg.connection import Connection

    from fast_healthchecks.checks.dsn_parsing import PostgresParseDsnResult


class PostgreSQLAsyncPGHealthCheck(BasePostgreSQLHealthCheck[HealthCheckResult]):
    """Health check class for PostgreSQL using asyncpg.

    Attributes:
        _name: The name of the health check.
        _host: The hostname of the PostgreSQL server.
        _port: The port number of the PostgreSQL server.
        _user: The username for authentication.
        _password: The password for authentication.
        _database: The database name.
        _ssl: The SSL context for secure connections.
        _direct_tls: Whether to use direct TLS.
        _timeout: The timeout for the connection.
    """

    __slots__ = ("_config", "_name")

    _config: PostgresAsyncPGConfig
    _name: str

    def __init__(
        self,
        *,
        config: PostgresAsyncPGConfig | None = None,
        name: str = "PostgreSQL",
        **kwargs: Any,  # noqa: ANN401
    ) -> None:
        """Initialize the PostgreSQLAsyncPGHealthCheck.

        Args:
            config: Connection config. If None, built from kwargs (host, port, user, etc.).
            name: The name of the health check.
            **kwargs: Passed to PostgresAsyncPGConfig when config is None.
        """
        if config is None:
            config = PostgresAsyncPGConfig(**kwargs)
        self._config = config
        self._name = name

    @classmethod
    def _from_parsed_dsn(
        cls,
        parsed: "PostgresParseDsnResult",  # noqa: UP037
        *,
        name: str = "PostgreSQL",
        timeout: float = DEFAULT_HC_TIMEOUT,
        **_kwargs: object,
    ) -> PostgreSQLAsyncPGHealthCheck:
        parse_result = parsed["parse_result"]
        sslctx = parsed["sslctx"]
        config = PostgresAsyncPGConfig(
            host=parse_result.hostname or "localhost",
            port=parse_result.port or 5432,
            user=parse_result.username,
            password=parse_result.password,
            database=parse_result.path.lstrip("/"),
            ssl=sslctx,
            direct_tls=parsed["direct_tls"],
            timeout=timeout,
        )
        return cls(config=config, name=name)

    @healthcheck_safe(invalidate_on_error=False)
    async def __call__(self) -> HealthCheckResult:
        """Perform the health check.

        Returns:
            HealthCheckResult: The result of the health check.
        """
        c = self._config
        connection: Connection | None = None
        try:
            connection = await asyncpg.connect(
                host=c.host,
                port=c.port,
                user=c.user,
                password=c.password,
                database=c.database,
                timeout=c.timeout,
                ssl=c.ssl,
                direct_tls=c.direct_tls,
            )
            async with connection.transaction(readonly=True):
                healthy: bool = bool(await connection.fetchval("SELECT 1"))
                if healthy:
                    return HealthCheckResult(name=self._name, healthy=True)
                return result_unhealthy_dependency(
                    name=self._name,
                    message="PostgreSQL check query returned unhealthy status",
                )
        finally:
            if connection is not None and not connection.is_closed():
                await connection.close(timeout=c.timeout)
