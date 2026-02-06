from typing import Any, TypedDict

import pytest

from fast_healthchecks.checks.kafka import KafkaHealthCheck
from fast_healthchecks.models import HealthCheckResult

pytestmark = pytest.mark.integration


class KafkaConfig(TypedDict, total=True):
    bootstrap_servers: str


@pytest.fixture(scope="session", name="kafka_config")
def fixture_kafka_config(env_config: dict[str, Any]) -> KafkaConfig:
    result: KafkaConfig = {
        "bootstrap_servers": "localhost:9092",
    }
    for key in ("bootstrap_servers",):
        value = env_config.get(f"KAFKA_{key.upper()}")
        match key:
            case _:
                if value is not None:
                    result[key] = str(value)

    return result


@pytest.mark.asyncio
async def test_kafka_check_success(kafka_config: KafkaConfig) -> None:
    check = KafkaHealthCheck(**kafka_config)
    result = await check()
    assert result == HealthCheckResult(name="Kafka", healthy=True, error_details=None)


@pytest.mark.asyncio
async def test_kafka_check_failure(kafka_config: KafkaConfig) -> None:
    config: KafkaConfig = {
        **kafka_config,
        "bootstrap_servers": "localhost2:9093",
    }
    check = KafkaHealthCheck(**config)
    result = await check()
    assert result.healthy is False
    assert result.error_details is not None
    assert "Unable to bootstrap from" in result.error_details


@pytest.mark.asyncio
async def test_kafka_check_connection_error(kafka_config: KafkaConfig) -> None:
    config: KafkaConfig = {
        **kafka_config,
        "bootstrap_servers": "localhost:9092",
    }
    check = KafkaHealthCheck(**config)
    result = await check()
    assert result.healthy is False
    assert result.error_details is not None
    assert "Unable to bootstrap from" in result.error_details
