"""This module provides a health check for PostgreSQL using psycopg.

Classes:
    PostgreSQLPsycopgHealthCheck: A class for health checking PostgreSQL using psycopg.

Usage:
    The PostgreSQLPsycopgHealthCheck class can be used to perform health checks on a PostgreSQL database by
    connecting to the database and executing a simple query.

Example:
    health_check = PostgreSQLPsycopgHealthCheck(
        host="localhost",
        port=5432,
        user="username",
        password="password",
        database="dbname"
    )
    # or
    health_check = PostgreSQLPsycopgHealthCheck.from_dsn(
        "postgresql://username:password@localhost:5432/dbname",
    )
    result = await health_check()
    print(result.healthy)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fast_healthchecks.checks._base import DEFAULT_HC_TIMEOUT, healthcheck_safe, result_unhealthy_dependency
from fast_healthchecks.checks._imports import raise_optional_import_error
from fast_healthchecks.checks.configs import PostgresPsycopgConfig
from fast_healthchecks.checks.postgresql.base import BasePostgreSQLHealthCheck
from fast_healthchecks.models import HealthCheckResult

try:
    import psycopg
except ImportError as exc:
    raise_optional_import_error("psycopg", "psycopg", exc)

if TYPE_CHECKING:
    from psycopg import AsyncConnection

    from fast_healthchecks.checks.dsn_parsing import PostgresParseDsnResult


class PostgreSQLPsycopgHealthCheck(BasePostgreSQLHealthCheck[HealthCheckResult]):
    """Health check class for PostgreSQL using psycopg.

    Attributes:
        _name: The name of the health check.
        _host: The hostname of the PostgreSQL server.
        _port: The port number of the PostgreSQL server.
        _user: The username for authentication.
        _password: The password for authentication.
        _database: The database name.
        _sslmode: The SSL mode to use for the connection.
        _sslcert: The path to the SSL certificate file.
        _sslkey: The path to the SSL key file.
        _sslrootcert: The path to the SSL root certificate file.
        _timeout: The timeout for the health check.
    """

    __slots__ = ("_config", "_name")

    _config: PostgresPsycopgConfig
    _name: str

    def __init__(
        self,
        *,
        config: PostgresPsycopgConfig | None = None,
        name: str = "PostgreSQL",
        **kwargs: Any,  # noqa: ANN401
    ) -> None:
        """Initialize the PostgreSQLPsycopgHealthCheck.

        Args:
            config: Connection config. If None, built from kwargs (host, port, user, etc.).
            name: The name of the health check.
            **kwargs: Passed to PostgresPsycopgConfig when config is None.
        """
        if config is None:
            config = PostgresPsycopgConfig(**kwargs)
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
    ) -> PostgreSQLPsycopgHealthCheck:
        parse_result = parsed["parse_result"]
        config = PostgresPsycopgConfig(
            host=parse_result.hostname or "localhost",
            port=parse_result.port or 5432,
            user=parse_result.username,
            password=parse_result.password,
            database=parse_result.path.lstrip("/"),
            sslmode=parsed["sslmode"],
            sslcert=parsed["sslcert"],
            sslkey=parsed["sslkey"],
            sslrootcert=parsed["sslrootcert"],
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
        connection: AsyncConnection | None = None
        try:
            connection = await psycopg.AsyncConnection.connect(
                host=c.host,
                port=c.port,
                user=c.user,
                password=c.password,
                dbname=c.database,
                sslmode=c.sslmode,
                sslcert=c.sslcert,
                sslkey=c.sslkey,
                sslrootcert=c.sslrootcert,
                connect_timeout=int(c.timeout),
            )
            async with connection.cursor() as cursor:
                await cursor.execute("SELECT 1")
                healthy: bool = bool(await cursor.fetchone())
                if healthy:
                    return HealthCheckResult(name=self._name, healthy=True)
                return result_unhealthy_dependency(
                    name=self._name,
                    message="PostgreSQL check query returned unhealthy status",
                )
        finally:
            if connection is not None and not connection.closed:
                await connection.cancel_safe(timeout=c.timeout)
                await connection.close()
