"""Pytest fixtures and helpers for integration tests (Docker, configs, apps)."""

from __future__ import annotations

import asyncio
import os
import sys
import warnings
from typing import Any

import pytest
from dotenv import dotenv_values


def pytest_configure(config: pytest.Config) -> None:
    """Register warning filters for this test directory only.

    Unclosed transport/socket (aiohttp / opensearch-py): cleanup runs on the
    next loop iteration; TestClient stops the loop after our shutdown returns,
    so PytestUnraisableExceptionWarning can appear at session cleanup.
    Suppress only in integration tests; production is unaffected.
    """
    # Message starts with "Exception ignored in" for unclosed resource warnings
    config.addinivalue_line(
        "filterwarnings",
        "ignore:Exception ignored in:pytest.PytestUnraisableExceptionWarning",
    )


# Set Windows event loop policy at import so it applies before any test runs.
# TestClient runs the ASGI app in a background thread; that thread creates an
# event loop using the process default policy. Sync integration tests do not
# request the event_loop_policy fixture, so without this, Windows would use
# ProactorEventLoop and psycopg async would raise (readiness probe 503).
# set_event_loop_policy is deprecated in 3.14 (removed in 3.16); the recommended
# approach is asyncio.Runner(loop_factory=...), but we do not control the loop
# creation—TestClient/Starlette do. Suppress only here until 3.16 or framework support.
if sys.platform == "win32" and sys.version_info < (3, 16):
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=".*(?:set_event_loop_policy|WindowsSelectorEventLoopPolicy).*deprecated",
            category=DeprecationWarning,
        )
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def _asyncio_policy_for_tests() -> asyncio.AbstractEventLoopPolicy | None:
    """Return event loop policy for pytest-asyncio; use deprecated APIs only where needed.

    Windows needs SelectorEventLoop for psycopg etc.; policy APIs are deprecated in 3.14
    (removed in 3.16). We suppress only at use site—pytest-asyncio controls loop creation.
    """
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=".*(?:DefaultEventLoopPolicy|WindowsSelectorEventLoopPolicy).*deprecated",
            category=DeprecationWarning,
        )
        if sys.platform == "win32" and sys.version_info < (3, 16):
            return asyncio.WindowsSelectorEventLoopPolicy()
        if sys.version_info >= (3, 14):
            return None
        return asyncio.DefaultEventLoopPolicy()


@pytest.fixture(scope="session")
def event_loop_policy() -> asyncio.AbstractEventLoopPolicy | None:
    """Use SelectorEventLoop on Windows so psycopg (and other libs) work in async mode.

    Windows defaults to ProactorEventLoop, which psycopg cannot use for async I/O.
    Use WindowsSelectorEventLoopPolicy on Windows for Python < 3.16 (deprecated in 3.14,
    removed in 3.16). On non-Windows 3.14+, return None so pytest-asyncio uses default.

    Returns:
        Event loop policy, or None on Python 3.14+ (non-Windows) to avoid deprecated APIs.
    """
    return _asyncio_policy_for_tests()


def _service_config_from_env(
    env_config: dict[str, Any],
    service: str,
    defaults: dict[str, Any],
    *,
    int_keys: frozenset[str] = frozenset(),
    list_keys: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    """Merge env overrides onto defaults for service config fixtures.

    Returns:
        Config dict with env values overriding defaults for specified keys.
    """
    result = dict(defaults)
    for key in defaults:
        val = env_config.get(f"{service}_{key}".upper())
        if val is not None:
            if key in int_keys:
                result[key] = int(val)
            elif key in list_keys:
                result[key] = [v.strip() for v in str(val).split(",")]
            else:
                result[key] = str(val)
    return result


@pytest.fixture(scope="session", name="env_config")
def fixture_env_config() -> dict[str, Any]:
    """Load .env and os.environ into a single dict for integration test config.

    Returns:
        dict[str, Any]: Env vars from .env and os.environ.
    """
    return {
        **dotenv_values(".env"),  # load shared default test environment variables
        **os.environ,  # override loaded values with environment variables
    }


# --- Service config fixtures (env-based, reused across integration checks) ---

REDIS_DEFAULTS: dict[str, Any] = {
    "host": "localhost",
    "port": 6379,
    "user": None,
    "password": None,
    "database": 0,
}


@pytest.fixture(scope="session", name="redis_config")
def fixture_redis_config(env_config: dict[str, Any]) -> dict[str, Any]:
    """Redis connection config from env (host, port, user, password, database).

    Returns:
        dict[str, Any]: Redis config for integration tests.
    """
    return _service_config_from_env(
        env_config,
        "REDIS",
        REDIS_DEFAULTS,
        int_keys=frozenset({"port", "database"}),
    )


KAFKA_DEFAULTS: dict[str, Any] = {"bootstrap_servers": "localhost:9092"}


@pytest.fixture(scope="session", name="kafka_config")
def fixture_kafka_config(env_config: dict[str, Any]) -> dict[str, Any]:
    """Kafka connection config from env (bootstrap_servers).

    Returns:
        dict[str, Any]: Kafka config for integration tests.
    """
    return _service_config_from_env(env_config, "KAFKA", KAFKA_DEFAULTS)


MONGO_DEFAULTS: dict[str, Any] = {
    "hosts": "localhost",
    "port": 27017,
    "user": None,
    "password": None,
    "database": None,
    "auth_source": "admin",
}


@pytest.fixture(scope="session", name="mongo_config")
def fixture_mongo_config(env_config: dict[str, Any]) -> dict[str, Any]:
    """MongoDB connection config from env (hosts, port, user, password, database, auth_source).

    Returns:
        dict[str, Any]: MongoDB config for integration tests.
    """
    return _service_config_from_env(env_config, "MONGO", MONGO_DEFAULTS, int_keys=frozenset({"port"}))


RABBITMQ_DEFAULTS: dict[str, Any] = {
    "host": "localhost",
    "port": 5672,
    "user": "guest",
    "password": "guest",
    "vhost": "/",
}


@pytest.fixture(scope="session", name="rabbitmq_config")
def fixture_rabbitmq_config(env_config: dict[str, Any]) -> dict[str, Any]:
    """RabbitMQ connection config from env (host, port, user, password, vhost).

    Returns:
        dict[str, Any]: RabbitMQ config for integration tests.
    """
    return _service_config_from_env(env_config, "RABBITMQ", RABBITMQ_DEFAULTS, int_keys=frozenset({"port"}))


OPENSEARCH_DEFAULTS: dict[str, Any] = {"hosts": ["localhost:9200"]}


@pytest.fixture(scope="session", name="opensearch_config")
def fixture_opensearch_config(env_config: dict[str, Any]) -> dict[str, Any]:
    """OpenSearch connection config from env (hosts list).

    Returns:
        dict[str, Any]: OpenSearch config for integration tests.
    """
    result = dict(OPENSEARCH_DEFAULTS)
    val = env_config.get("OPENSEARCH_HOSTS")
    if val is not None:
        result["hosts"] = [v.strip() for v in str(val).split(",")]
    return result


POSTGRES_DEFAULTS: dict[str, Any] = {
    "host": "localhost",
    "port": 5432,
    "user": None,
    "password": None,
    "database": None,
}


@pytest.fixture(scope="session", name="base_postgresql_config")
def fixture_base_postgresql_config(env_config: dict[str, Any]) -> dict[str, Any]:
    """PostgreSQL connection config from env (host, port, user, password, database).

    Returns:
        dict[str, Any]: PostgreSQL config for integration tests.
    """
    return _service_config_from_env(env_config, "POSTGRES", POSTGRES_DEFAULTS, int_keys=frozenset({"port"}))
