"""Integration tests for KafkaHealthCheck against real broker."""

from typing import Any

import pytest

from fast_healthchecks.checks.kafka import KafkaHealthCheck
from fast_healthchecks.models import HealthCheckResult

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_kafka_check_success(kafka_check: KafkaHealthCheck) -> None:
    """Kafka check returns healthy against real broker."""
    result = await kafka_check()
    assert result == HealthCheckResult(name="Kafka", healthy=True, error_details=None)


@pytest.mark.asyncio
async def test_kafka_check_failure(kafka_config: dict[str, Any]) -> None:
    """Kafka check returns unhealthy when broker unreachable."""
    config: dict[str, Any] = {
        **kafka_config,
        "bootstrap_servers": "localhost2:9093",
    }
    check = KafkaHealthCheck(**config)
    try:
        result = await check()
        assert result.healthy is False
        assert result.error_details is not None
        assert "Unable to bootstrap from" in result.error_details
    finally:
        await check.aclose()


@pytest.mark.asyncio
async def test_kafka_check_connection_error(kafka_config: dict[str, Any]) -> None:
    """Kafka check returns unhealthy with error_details on connection error."""
    # Use closed port to guarantee connection refused (not a running broker)
    config: dict[str, Any] = {
        **kafka_config,
        "bootstrap_servers": "localhost:19092",
    }
    check = KafkaHealthCheck(**config)
    try:
        result = await check()
        assert result.healthy is False
        assert result.error_details is not None
        assert "Unable to bootstrap from" in result.error_details
    finally:
        await check.aclose()
