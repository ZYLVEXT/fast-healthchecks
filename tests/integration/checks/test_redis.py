from typing import Any, TypedDict

import pytest

from fast_healthchecks.checks.redis import RedisHealthCheck
from fast_healthchecks.models import HealthCheckResult
from tests.integration.test_assertions import (
    CONNECTION_REFUSED_FRAGMENTS,
    DNS_ERROR_FRAGMENTS,
    assert_error_contains_any,
)

pytestmark = pytest.mark.integration


class RedisConfig(TypedDict, total=True):
    host: str
    port: int
    user: str | None
    password: str | None
    database: str | int


@pytest.fixture(scope="session", name="redis_config")
def fixture_redis_config(env_config: dict[str, Any]) -> RedisConfig:
    result: RedisConfig = {
        "host": "localhost",
        "port": 6379,
        "user": None,
        "password": None,
        "database": 0,
    }
    for key in ("host", "port", "user", "password", "database"):
        value = env_config.get(f"REDIS_{key.upper()}")
        match key:
            case "port":
                if value is not None:
                    result[key] = int(value)
            case _:
                if value is not None:
                    result[key] = str(value)

    return result


@pytest.mark.asyncio
async def test_redis_check_success(redis_config: RedisConfig) -> None:
    check = RedisHealthCheck(
        host=redis_config["host"],
        port=redis_config["port"],
        user=redis_config["user"],
        password=redis_config["password"],
        database=redis_config["database"],
    )
    try:
        result = await check()
        assert result == HealthCheckResult(name="Redis", healthy=True, error_details=None)
    finally:
        await check.aclose()


@pytest.mark.asyncio
async def test_redis_check_failure(redis_config: RedisConfig) -> None:
    check = RedisHealthCheck(
        host="localhost2",
        port=redis_config["port"],
        user=redis_config["user"],
        password=redis_config["password"],
        database=redis_config["database"],
    )
    try:
        result = await check()
        assert result.healthy is False
        assert_error_contains_any(result.error_details, DNS_ERROR_FRAGMENTS)
    finally:
        await check.aclose()


@pytest.mark.asyncio
async def test_redis_check_connection_error(redis_config: RedisConfig) -> None:
    check = RedisHealthCheck(
        host=redis_config["host"],
        port=6380,
        user=redis_config["user"],
        password=redis_config["password"],
        database=redis_config["database"],
    )
    try:
        result = await check()
        assert result.healthy is False
        assert_error_contains_any(result.error_details, CONNECTION_REFUSED_FRAGMENTS)
    finally:
        await check.aclose()
