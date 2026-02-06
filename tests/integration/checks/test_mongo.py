from typing import Any, TypedDict

import pytest

from fast_healthchecks.checks.mongo import MongoHealthCheck
from fast_healthchecks.models import HealthCheckResult
from tests.integration.test_assertions import (
    CONNECTION_REFUSED_FRAGMENTS,
    DNS_ERROR_FRAGMENTS,
    assert_error_contains_any,
)

pytestmark = pytest.mark.integration


class MongoConfig(TypedDict, total=True):
    hosts: str | list[str]
    port: int | None
    user: str | None
    password: str | None
    database: str | None
    auth_source: str


@pytest.fixture(scope="session", name="mongo_config")
def fixture_mongo_config(env_config: dict[str, Any]) -> MongoConfig:
    result: MongoConfig = {
        "hosts": "localhost",
        "port": 27017,
        "user": None,
        "password": None,
        "database": None,
        "auth_source": "admin",
    }
    for key in ("hosts", "port", "user", "password", "database", "auth_source"):
        value = env_config.get(f"MONGO_{key.upper()}")
        match key:
            case "port":
                if value is not None:
                    result[key] = int(value)
            case _:
                if value is not None:
                    result[key] = str(value)

    return result


@pytest.mark.asyncio
async def test_mongo_check_success(mongo_config: MongoConfig) -> None:
    check = MongoHealthCheck(
        hosts=mongo_config["hosts"],
        port=mongo_config["port"],
        user=mongo_config["user"],
        password=mongo_config["password"],
        database=mongo_config["database"],
        auth_source=mongo_config["auth_source"],
    )
    try:
        result = await check()
        assert result == HealthCheckResult(name="MongoDB", healthy=True, error_details=None)
    finally:
        await check.aclose()


@pytest.mark.asyncio
async def test_mongo_check_failure(mongo_config: MongoConfig) -> None:
    check = MongoHealthCheck(
        hosts="localhost2",
        port=mongo_config["port"],
        user=mongo_config["user"],
        password=mongo_config["password"],
        database=mongo_config["database"],
        auth_source=mongo_config["auth_source"],
    )
    try:
        result = await check()
        assert result.healthy is False
        assert_error_contains_any(result.error_details, DNS_ERROR_FRAGMENTS)
    finally:
        await check.aclose()


@pytest.mark.asyncio
async def test_mongo_check_connection_error(mongo_config: MongoConfig) -> None:
    check = MongoHealthCheck(
        hosts=mongo_config["hosts"],
        port=27018,
        user=mongo_config["user"],
        password=mongo_config["password"],
        database=mongo_config["database"],
        auth_source=mongo_config["auth_source"],
    )
    try:
        result = await check()
        assert result.healthy is False
        assert_error_contains_any(result.error_details, CONNECTION_REFUSED_FRAGMENTS)
    finally:
        await check.aclose()
