"""Integration tests for RabbitMQHealthCheck against real broker."""

import asyncio
from typing import Any

import pytest

from fast_healthchecks.checks.rabbitmq import RabbitMQHealthCheck
from fast_healthchecks.models import HealthCheckResult
from tests.integration.test_assertions import (
    CONNECTION_REFUSED_FRAGMENTS,
    DNS_ERROR_FRAGMENTS,
    assert_error_contains_any,
)

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_rabbitmq_check_success(rabbitmq_check: RabbitMQHealthCheck) -> None:
    """RabbitMQ check returns healthy against real broker."""
    result = await rabbitmq_check()
    assert result == HealthCheckResult(name="RabbitMQ", healthy=True, error_details=None)


@pytest.mark.asyncio
async def test_rabbitmq_check_failure(rabbitmq_config: dict[str, Any]) -> None:
    """RabbitMQ check returns unhealthy when broker unreachable."""
    check = RabbitMQHealthCheck(
        host="localhost2",
        port=rabbitmq_config["port"],
        user=rabbitmq_config["user"],
        password=rabbitmq_config["password"],
        vhost=rabbitmq_config["vhost"],
    )
    try:
        result = await check()
        assert result.healthy is False
        assert_error_contains_any(result.error_details, DNS_ERROR_FRAGMENTS)
    finally:
        await check.aclose()
        await asyncio.sleep(0.1)


@pytest.mark.asyncio
async def test_rabbitmq_check_connection_error(rabbitmq_config: dict[str, Any]) -> None:
    """RabbitMQ check returns unhealthy with error_details on connection error."""
    check = RabbitMQHealthCheck(
        host=rabbitmq_config["host"],
        port=5673,
        user=rabbitmq_config["user"],
        password=rabbitmq_config["password"],
        vhost=rabbitmq_config["vhost"],
    )
    try:
        result = await check()
        assert result.healthy is False
        assert_error_contains_any(result.error_details, CONNECTION_REFUSED_FRAGMENTS)
    finally:
        await check.aclose()
        await asyncio.sleep(0.1)
