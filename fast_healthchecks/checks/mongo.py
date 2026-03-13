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
from fast_healthchecks.checks.configs import MongoConfig
from fast_healthchecks.checks.dsn_parsing import MongoParseDsnResult
from fast_healthchecks.models import HealthCheckResult
from fast_healthchecks.utils import parse_query_string

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

try:
    from motor.motor_asyncio import AsyncIOMotorClient
except ImportError as exc:
    raise_optional_import_error("motor", "motor", exc)


def _close_mongo_client(
    client: AsyncIOMotorClient[dict[str, Any]],
) -> Awaitable[None]:
    result = client.close()
    if asyncio.iscoroutine(result):
        return result

    async def _noop() -> None:
        pass

    return _noop()


@final
class MongoHealthCheck(
    ClientCachingMixin["AsyncIOMotorClient[dict[str, Any]]"],
    HealthCheckDSN[HealthCheckResult, MongoParseDsnResult],
):
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

    __slots__ = (*_CLIENT_CACHING_SLOTS, "_config", "_name")

    _config: MongoConfig
    _name: str
    _client: AsyncIOMotorClient[dict[str, Any]] | None
    _client_loop: asyncio.AbstractEventLoop | None

    def __init__(
        self,
        *,
        config: MongoConfig | None = None,
        name: str = "MongoDB",
        close_client_fn: Callable[
            [AsyncIOMotorClient[dict[str, Any]]],
            Awaitable[None],
        ] = _close_mongo_client,
        **kwargs: Any,  # noqa: ANN401
    ) -> None:
        """Initialize the MongoHealthCheck.

        Args:
            config: Connection config. If None, built from kwargs (hosts, port, etc.).
            name: The name of the health check.
            close_client_fn: Callable to close the cached client.
            **kwargs: Passed to MongoConfig when config is None.
        """
        if config is None:
            config = MongoConfig(**kwargs)
        self._config = config
        self._name = name
        super().__init__(close_client_fn=close_client_fn)

    def _create_client(self) -> AsyncIOMotorClient[dict[str, Any]]:
        c = self._config
        return AsyncIOMotorClient(
            host=c.hosts,
            port=c.port,
            username=c.user,
            password=c.password,
            authSource=c.auth_source,
            serverSelectionTimeoutMS=int(c.timeout * 1000),
        )

    @classmethod
    def _allowed_schemes(cls) -> tuple[str, ...]:
        return ("mongodb", "mongodb+srv")

    @classmethod
    def _default_name(cls) -> str:
        return "MongoDB"

    @classmethod
    def parse_dsn(cls, dsn: str) -> MongoParseDsnResult:
        """Parse the DSN and return the results.

        Args:
            dsn: The DSN to parse.

        Returns:
            MongoParseDsnResult: The results of parsing the DSN.
        """
        parse_result = urlsplit(dsn)
        query = parse_query_string(parse_result.query)
        return {"parse_result": parse_result, "authSource": query.get("authSource", "admin")}

    @classmethod
    def _from_parsed_dsn(
        cls,
        parsed: MongoParseDsnResult,
        *,
        name: str = "MongoDB",
        timeout: float = DEFAULT_HC_TIMEOUT,
        **_kwargs: object,
    ) -> MongoHealthCheck:
        parse_result = parsed["parse_result"]
        hosts: str | list[str]
        port: int | None
        if "," in parse_result.netloc:
            hosts = parse_result.netloc.split("@")[-1].split(",")
            port = None
        else:
            hosts = parse_result.hostname or "localhost"
            port = parse_result.port or 27017
        config = MongoConfig(
            hosts=hosts,
            port=port,
            user=parse_result.username,
            password=parse_result.password,
            database=parse_result.path.lstrip("/") or None,
            auth_source=parsed["authSource"],
            timeout=timeout,
        )
        return cls(config=config, name=name)

    @healthcheck_safe(invalidate_on_error=True)
    async def __call__(self) -> HealthCheckResult:
        """Perform the health check on MongoDB.

        Returns:
            HealthCheckResult: The result of the health check.
        """
        client = await self._ensure_client()
        database = client[self._config.database] if self._config.database else client[self._config.auth_source]
        res = await database.command("ping")
        ok_raw = res.get("ok")
        ok_value = ok_raw if isinstance(ok_raw, (bool, int, float)) else 0
        if int(ok_value) == 1:
            return HealthCheckResult(name=self._name, healthy=True)
        return result_unhealthy_dependency(
            name=self._name,
            message="MongoDB ping returned unhealthy status",
            meta={"ok": ok_raw if isinstance(ok_raw, (bool, int, float, str)) else str(ok_raw)},
        )
