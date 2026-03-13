"""Integration tests for MongoHealthCheck against real MongoDB."""

from typing import Any

import pytest

from fast_healthchecks.checks.mongo import MongoHealthCheck
from fast_healthchecks.models import HealthCheckResult
from tests.integration.test_assertions import (
    CONNECTION_REFUSED_FRAGMENTS,
    DNS_ERROR_FRAGMENTS,
    assert_error_contains_any,
)

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_mongo_check_success(mongo_check: MongoHealthCheck) -> None:
    """Mongo check returns healthy against real MongoDB."""
    result = await mongo_check()
    assert result == HealthCheckResult(name="MongoDB", healthy=True, error_details=None)


@pytest.mark.asyncio
async def test_mongo_check_failure(mongo_config: dict[str, Any]) -> None:
    """Mongo check returns unhealthy when cluster unreachable."""
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
async def test_mongo_check_connection_error(mongo_config: dict[str, Any]) -> None:
    """Mongo check returns unhealthy with error_details on connection error."""
    check = MongoHealthCheck(
        hosts=mongo_config["hosts"],
        port=27018,
        user=mongo_config["user"],
        password=mongo_config["password"],
        database=mongo_config["database"],
        auth_source=mongo_config["auth_source"],
        timeout=1.0,
    )
    try:
        result = await check()
        assert result.healthy is False
        assert_error_contains_any(result.error_details, CONNECTION_REFUSED_FRAGMENTS)
    finally:
        await check.aclose()
