"""Probe and check factory helpers for example apps."""

import asyncio
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from fast_healthchecks.checks.function import FunctionHealthCheck
from fast_healthchecks.checks.kafka import KafkaHealthCheck
from fast_healthchecks.checks.mongo import MongoHealthCheck
from fast_healthchecks.checks.opensearch import OpenSearchHealthCheck
from fast_healthchecks.checks.postgresql.asyncpg import PostgreSQLAsyncPGHealthCheck
from fast_healthchecks.checks.postgresql.psycopg import PostgreSQLPsycopgHealthCheck
from fast_healthchecks.checks.rabbitmq import RabbitMQHealthCheck
from fast_healthchecks.checks.redis import RedisHealthCheck
from fast_healthchecks.checks.types import Check
from fast_healthchecks.checks.url import UrlHealthCheck
from fast_healthchecks.integrations.base import ProbeAsgiResponse

_ = load_dotenv(Path(__file__).parent.parent / ".env")


def sync_dummy_check() -> bool:
    """Run a synchronous dummy check that sleeps briefly and returns True.

    Returns:
        True.
    """
    time.sleep(0.1)
    return True


async def async_dummy_check() -> bool:
    """Run an async dummy check that sleeps briefly and returns True.

    Returns:
        True.
    """
    await asyncio.sleep(0.1)
    return True


async def async_dummy_check_fail() -> bool:
    """Run an async dummy check that raises ValueError.

    Raises:
        ValueError: Always.
    """
    await asyncio.sleep(0)
    msg = "Failed"
    raise ValueError(msg) from None


def get_liveness_checks() -> list[Check]:
    """Return new check instances (one set per app to avoid shared clients across event loops)."""
    return [
        FunctionHealthCheck(func=sync_dummy_check, name="Sync dummy"),
    ]


def get_readiness_checks() -> list[Check]:
    """Return new check instances (one set per app to avoid shared clients across event loops)."""
    return [
        KafkaHealthCheck(
            bootstrap_servers=os.environ["KAFKA_BOOTSTRAP_SERVERS"],
            name="Kafka",
        ),
        MongoHealthCheck.from_dsn(os.environ["MONGO_DSN"], name="Mongo"),
        OpenSearchHealthCheck(hosts=os.environ["OPENSEARCH_HOSTS"].split(","), name="OpenSearch"),
        PostgreSQLAsyncPGHealthCheck.from_dsn(os.environ["POSTGRES_DSN"], name="PostgreSQL asyncpg"),
        PostgreSQLPsycopgHealthCheck.from_dsn(os.environ["POSTGRES_DSN"], name="PostgreSQL psycopg"),
        RabbitMQHealthCheck.from_dsn(os.environ["RABBITMQ_DSN"], name="RabbitMQ"),
        RedisHealthCheck.from_dsn(os.environ["REDIS_DSN"], name="Redis"),
        UrlHealthCheck(url="https://httpbingo.org/status/200", name="URL 200"),
    ]


def get_startup_checks() -> list[Check]:
    """Return new check instances (one set per app to avoid shared clients across event loops)."""
    return [
        FunctionHealthCheck(func=async_dummy_check, name="Async dummy"),
    ]


def get_readiness_checks_success() -> list[Check]:
    """Return new check instances for success-path tests."""
    return [
        FunctionHealthCheck(func=async_dummy_check, name="Async dummy"),
    ]


def get_readiness_checks_fail() -> list[Check]:
    """Return new check instances for failure-path tests."""
    return [
        FunctionHealthCheck(func=async_dummy_check_fail, name="Async dummy fail"),
    ]


LIVENESS_CHECKS: list[Check] = get_liveness_checks()
READINESS_CHECKS: list[Check] = get_readiness_checks()
STARTUP_CHECKS: list[Check] = get_startup_checks()
READINESS_CHECKS_SUCCESS: list[Check] = get_readiness_checks_success()
READINESS_CHECKS_FAIL: list[Check] = get_readiness_checks_fail()


async def custom_handler(response: ProbeAsgiResponse) -> dict[str, Any] | None:
    """Custom handler for probes.

    Returns:
        Any: Probe response payload.
    """
    await asyncio.sleep(0)
    return response.data
