"""This module provides a health check class for MongoDB.

Classes:
    MongoHealthCheck: A class to perform health checks on MongoDB.

Usage:
    The MongoHealthCheck class can be used to perform health checks on MongoDB by calling it.

Example:
    health_check = MongoHealthCheck(
        hosts=["host1:27017", "host2:27017"],
        # or hosts="localhost",
        port=27017,
        user="myuser",
        password="mypassword",
        database="mydatabase"
    )
    result = await health_check()
    print(result.healthy)
"""

from __future__ import annotations

import asyncio
import contextlib
from traceback import format_exc
from typing import Any, TypedDict, final
from urllib.parse import ParseResult, urlparse

from fast_healthchecks.checks._base import DEFAULT_HC_TIMEOUT, HealthCheckDSN
from fast_healthchecks.compat import MongoDsn
from fast_healthchecks.models import HealthCheckResult
from fast_healthchecks.utils import parse_query_string

IMPORT_ERROR_MSG = "motor is not installed. Install it with `pip install fast-healthchecks[motor]`."

try:
    from motor.motor_asyncio import AsyncIOMotorClient
except ImportError as exc:
    raise ImportError(IMPORT_ERROR_MSG) from exc


class ParseDSNResult(TypedDict, total=True):
    """A dictionary containing the results of parsing a DSN."""

    parse_result: ParseResult
    authSource: str


@final
class MongoHealthCheck(HealthCheckDSN[HealthCheckResult]):
    """A class to perform health checks on MongoDB.

    Attributes:
        _auth_source: The MongoDB authentication source.
        _database: The MongoDB database to use.
        _hosts: The MongoDB host or a list of hosts.
        _name: The name of the health check.
        _password: The MongoDB password.
        _port: The MongoDB port.
        _timeout: The timeout for the health check.
        _user: The MongoDB user.
    """

    __slots__ = (
        "_auth_source",
        "_client",
        "_client_loop",
        "_database",
        "_hosts",
        "_name",
        "_password",
        "_port",
        "_timeout",
        "_user",
    )

    _hosts: str | list[str]
    _port: int | None
    _user: str | None
    _password: str | None
    _database: str | None
    _auth_source: str
    _timeout: float
    _name: str
    _client: AsyncIOMotorClient[dict[str, Any]] | None
    _client_loop: asyncio.AbstractEventLoop | None

    def __init__(  # noqa: PLR0913
        self,
        *,
        hosts: str | list[str] = "localhost",
        port: int | None = 27017,
        user: str | None = None,
        password: str | None = None,
        database: str | None = None,
        auth_source: str = "admin",
        timeout: float = DEFAULT_HC_TIMEOUT,
        name: str = "MongoDB",
    ) -> None:
        """Initialize the MongoHealthCheck.

        Args:
            hosts: The MongoDB host or list of hosts.
            port: The MongoDB port (used when hosts is a single string).
            user: The MongoDB user.
            password: The MongoDB password.
            database: The MongoDB database to use.
            auth_source: The MongoDB authentication source.
            timeout: The timeout for the health check.
            name: The name of the health check.
        """
        self._hosts = hosts
        self._port = port
        self._user = user
        self._password = password
        self._database = database
        self._auth_source = auth_source
        self._timeout = timeout
        self._name = name
        self._client = None
        self._client_loop = None

    async def aclose(self) -> None:
        """Close the cached Motor client if present."""
        if self._client is not None:
            self._client.close()
            self._client = None
            self._client_loop = None

    def _get_client(self) -> AsyncIOMotorClient[dict[str, Any]]:
        if self._client is None:
            try:
                self._client_loop = asyncio.get_running_loop()
            except RuntimeError:
                self._client_loop = None
            self._client = AsyncIOMotorClient(
                host=self._hosts,
                port=self._port,
                username=self._user,
                password=self._password,
                authSource=self._auth_source,
                serverSelectionTimeoutMS=int(self._timeout * 1000),
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
        parse_result: ParseResult = urlparse(dsn)
        query = parse_query_string(parse_result.query)
        return {"parse_result": parse_result, "authSource": query.get("authSource", "admin")}

    @classmethod
    def from_dsn(
        cls,
        dsn: MongoDsn | str,
        *,
        name: str = "MongoDB",
        timeout: float = DEFAULT_HC_TIMEOUT,
    ) -> MongoHealthCheck:
        """Create a MongoHealthCheck from a DSN.

        Args:
            dsn: The DSN for the MongoDB database.
            name: The name of the health check.
            timeout: The timeout for the connection.

        Returns:
            MongoHealthCheck: The configured check instance.
        """
        dsn = cls.validate_dsn(dsn, allowed_schemes=("mongodb", "mongodb+srv"))
        parsed_dsn = cls.parse_dsn(dsn)
        parse_result = parsed_dsn["parse_result"]
        hosts: str | list[str]
        port: int | None
        if "," in parse_result.netloc:
            hosts = parse_result.netloc.split("@")[-1].split(",")
            port = None
        else:
            hosts = parse_result.hostname or "localhost"
            port = parse_result.port or 27017
        return cls(
            hosts=hosts,
            port=port,
            user=parse_result.username,
            password=parse_result.password,
            database=parse_result.path.lstrip("/") or None,
            auth_source=parsed_dsn["authSource"],
            timeout=timeout,
            name=name,
        )

    async def __call__(self) -> HealthCheckResult:
        """Perform the health check on MongoDB.

        Returns:
            HealthCheckResult: The result of the health check.
        """
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if self._client is not None and self._client_loop is not running:
            with contextlib.suppress(Exception):
                self._client.close()
            self._client = None
            self._client_loop = None
        client = self._get_client()
        database = client[self._database] if self._database else client[self._auth_source]
        try:
            res = await database.command("ping")
            ok_raw = res.get("ok")
            ok_value = ok_raw if isinstance(ok_raw, (bool, int, float)) else 0
            return HealthCheckResult(name=self._name, healthy=int(ok_value) == 1)
        except Exception:  # noqa: BLE001
            return HealthCheckResult(name=self._name, healthy=False, error_details=format_exc())

    def to_dict(self) -> dict[str, Any]:
        """Convert the MongoHealthCheck to a dictionary.

        Returns:
            dict: The check attributes as a dictionary.
        """
        return {
            "hosts": self._hosts,
            "port": self._port,
            "user": self._user,
            "password": self._password,
            "database": self._database,
            "auth_source": self._auth_source,
            "timeout": self._timeout,
            "name": self._name,
        }
