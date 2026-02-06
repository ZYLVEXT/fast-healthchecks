import ssl

import pytest

from fast_healthchecks.checks.postgresql.asyncpg import PostgreSQLAsyncPGHealthCheck
from fast_healthchecks.models import HealthCheckResult
from tests.integration.checks.postgresql.conftest import BasePostgreSQLConfig
from tests.integration.test_assertions import (
    CONNECTION_REFUSED_FRAGMENTS,
    DNS_ERROR_FRAGMENTS,
    assert_error_contains_any,
)

pytestmark = pytest.mark.integration


class AsyncPGConfig(BasePostgreSQLConfig, total=True):
    ssl: ssl.SSLContext | None
    direct_tls: bool


@pytest.fixture(scope="session", name="asyncpg_config")
def fixture_asyncpg_config(base_postgresql_config: BasePostgreSQLConfig) -> AsyncPGConfig:
    return {
        "host": base_postgresql_config["host"],
        "port": base_postgresql_config["port"],
        "user": base_postgresql_config["user"],
        "password": base_postgresql_config["password"],
        "database": base_postgresql_config["database"],
        "ssl": None,
        "direct_tls": False,
    }


@pytest.mark.asyncio
async def test_postgresql_asyncpg_check_success(asyncpg_config: AsyncPGConfig) -> None:
    check = PostgreSQLAsyncPGHealthCheck(
        host=asyncpg_config["host"],
        port=asyncpg_config["port"],
        user=asyncpg_config["user"],
        password=asyncpg_config["password"],
        database=asyncpg_config["database"],
        ssl=asyncpg_config["ssl"],
        direct_tls=asyncpg_config["direct_tls"],
    )
    result = await check()
    assert result == HealthCheckResult(name="PostgreSQL", healthy=True, error_details=None)


@pytest.mark.asyncio
async def test_postgresql_asyncpg_check_failure(asyncpg_config: AsyncPGConfig) -> None:
    check = PostgreSQLAsyncPGHealthCheck(
        host="localhost2",
        port=asyncpg_config["port"],
        user=asyncpg_config["user"],
        password=asyncpg_config["password"],
        database=asyncpg_config["database"],
        ssl=asyncpg_config["ssl"],
        direct_tls=asyncpg_config["direct_tls"],
    )
    result = await check()
    assert result.healthy is False
    assert_error_contains_any(result.error_details, DNS_ERROR_FRAGMENTS)


@pytest.mark.asyncio
async def test_postgresql_asyncpg_check_connection_error(asyncpg_config: AsyncPGConfig) -> None:
    check = PostgreSQLAsyncPGHealthCheck(
        host=asyncpg_config["host"],
        port=6432,
        user=asyncpg_config["user"],
        password=asyncpg_config["password"],
        database=asyncpg_config["database"],
        ssl=asyncpg_config["ssl"],
        direct_tls=asyncpg_config["direct_tls"],
    )
    result = await check()
    assert result.healthy is False
    assert_error_contains_any(result.error_details, CONNECTION_REFUSED_FRAGMENTS)
