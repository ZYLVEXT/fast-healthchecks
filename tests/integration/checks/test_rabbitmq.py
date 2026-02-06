from typing import Any, TypedDict

import pytest

from fast_healthchecks.checks.rabbitmq import RabbitMQHealthCheck
from fast_healthchecks.models import HealthCheckResult
from tests.integration.test_assertions import (
    CONNECTION_REFUSED_FRAGMENTS,
    DNS_ERROR_FRAGMENTS,
    assert_error_contains_any,
)

pytestmark = pytest.mark.integration


class RabbitMqConfig(TypedDict, total=True):
    host: str
    user: str
    password: str
    port: int
    vhost: str


@pytest.fixture(scope="session", name="rabbitmq_config")
def fixture_rabbitmq_config(env_config: dict[str, Any]) -> RabbitMqConfig:
    result: RabbitMqConfig = {
        "host": "localhost",
        "port": 5672,
        "user": "guest",
        "password": "guest",
        "vhost": "/",
    }
    for key in ("host", "port", "user", "password", "vhost"):
        value = env_config.get(f"RABBITMQ_{key.upper()}")
        match key:
            case "port":
                if value is not None:
                    result[key] = int(value)
            case _:
                if value is not None:
                    result[key] = str(value)

    return result


@pytest.mark.asyncio
async def test_rabbitmq_check_success(rabbitmq_config: RabbitMqConfig) -> None:
    check = RabbitMQHealthCheck(
        host=rabbitmq_config["host"],
        port=rabbitmq_config["port"],
        user=rabbitmq_config["user"],
        password=rabbitmq_config["password"],
        vhost=rabbitmq_config["vhost"],
    )
    result = await check()
    assert result == HealthCheckResult(name="RabbitMQ", healthy=True, error_details=None)


@pytest.mark.asyncio
async def test_rabbitmq_check_failure(rabbitmq_config: RabbitMqConfig) -> None:
    check = RabbitMQHealthCheck(
        host="localhost2",
        port=rabbitmq_config["port"],
        user=rabbitmq_config["user"],
        password=rabbitmq_config["password"],
        vhost=rabbitmq_config["vhost"],
    )
    result = await check()
    assert result.healthy is False
    assert_error_contains_any(result.error_details, DNS_ERROR_FRAGMENTS)


@pytest.mark.asyncio
async def test_rabbitmq_check_connection_error(rabbitmq_config: RabbitMqConfig) -> None:
    check = RabbitMQHealthCheck(
        host=rabbitmq_config["host"],
        port=5673,
        user=rabbitmq_config["user"],
        password=rabbitmq_config["password"],
        vhost=rabbitmq_config["vhost"],
    )
    result = await check()
    assert result.healthy is False
    assert_error_contains_any(result.error_details, CONNECTION_REFUSED_FRAGMENTS)
