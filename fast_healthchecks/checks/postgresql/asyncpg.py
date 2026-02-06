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

from traceback import format_exc
from typing import TYPE_CHECKING, Any

from fast_healthchecks.checks._base import DEFAULT_HC_TIMEOUT
from fast_healthchecks.checks.postgresql.base import BasePostgreSQLHealthCheck
from fast_healthchecks.compat import PostgresDsn
from fast_healthchecks.models import HealthCheckResult

IMPORT_ERROR_MSG = "asyncpg is not installed. Install it with `pip install fast-healthchecks[asyncpg]`."

try:
    import asyncpg
except ImportError as exc:
    raise ImportError(IMPORT_ERROR_MSG) from exc

if TYPE_CHECKING:
    import ssl

    from asyncpg.connection import Connection


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

    __slots__ = (
        "_database",
        "_direct_tls",
        "_host",
        "_name",
        "_password",
        "_port",
        "_ssl",
        "_timeout",
        "_user",
    )

    _host: str
    _port: int
    _user: str | None
    _password: str | None
    _database: str | None
    _ssl: ssl.SSLContext | None
    _direct_tls: bool
    _timeout: float
    _name: str

    def __init__(  # noqa: PLR0913
        self,
        *,
        host: str,
        port: int,
        user: str | None = None,
        password: str | None = None,
        database: str | None = None,
        ssl: ssl.SSLContext | None = None,
        direct_tls: bool = False,
        timeout: float = DEFAULT_HC_TIMEOUT,
        name: str = "PostgreSQL",
    ) -> None:
        """Initialize the PostgreSQLAsyncPGHealthCheck.

        Args:
            host: The hostname of the PostgreSQL server.
            port: The port number of the PostgreSQL server.
            user: The username for authentication.
            password: The password for authentication.
            database: The database name.
            ssl: The SSL context for secure connections.
            direct_tls: Whether to use direct TLS.
            timeout: The timeout for the connection.
            name: The name of the health check.
        """
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._database = database
        self._ssl = ssl
        self._direct_tls = direct_tls
        self._timeout = timeout
        self._name = name

    @classmethod
    def from_dsn(
        cls,
        dsn: PostgresDsn | str,
        *,
        name: str = "PostgreSQL",
        timeout: float = DEFAULT_HC_TIMEOUT,
    ) -> PostgreSQLAsyncPGHealthCheck:
        """Create a PostgreSQLAsyncPGHealthCheck from a DSN.

        Args:
            dsn: The DSN for the PostgreSQL database.
            name: The name of the health check.
            timeout: The timeout for the connection.

        Returns:
            PostgreSQLAsyncPGHealthCheck: The configured check instance.
        """
        dsn = cls.validate_dsn(dsn, allowed_schemes=("postgresql", "postgres"))
        parsed_dsn = cls.parse_dsn(dsn)
        parse_result = parsed_dsn["parse_result"]
        sslctx = parsed_dsn["sslctx"]
        return cls(
            host=parse_result.hostname or "localhost",
            port=parse_result.port or 5432,
            user=parse_result.username,
            password=parse_result.password,
            database=parse_result.path.lstrip("/"),
            ssl=sslctx,
            timeout=timeout,
            name=name,
        )

    async def __call__(self) -> HealthCheckResult:
        """Perform the health check.

        Returns:
            HealthCheckResult: The result of the health check.
        """
        connection: Connection | None = None
        try:
            connection = await asyncpg.connect(
                host=self._host,
                port=self._port,
                user=self._user,
                password=self._password,
                database=self._database,
                timeout=self._timeout,
                ssl=self._ssl,
                direct_tls=self._direct_tls,
            )
            async with connection.transaction(readonly=True):
                healthy: bool = bool(await connection.fetchval("SELECT 1"))
                return HealthCheckResult(name=self._name, healthy=healthy)
        except Exception:  # noqa: BLE001
            return HealthCheckResult(name=self._name, healthy=False, error_details=format_exc())
        finally:
            if connection is not None and not connection.is_closed():
                await connection.close(timeout=self._timeout)

    def to_dict(self) -> dict[str, Any]:
        """Convert the PostgreSQLAsyncPGHealthCheck to a dictionary.

        Returns:
            dict: The check attributes as a dictionary.
        """
        return {
            "host": self._host,
            "port": self._port,
            "user": self._user,
            "password": self._password,
            "database": self._database,
            "ssl": self._ssl,
            "direct_tls": self._direct_tls,
            "timeout": self._timeout,
            "name": self._name,
        }
