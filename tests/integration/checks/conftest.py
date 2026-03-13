r"""Async fixtures for integration checks that guarantee aclose() in teardown.

Fixtures are function-scoped; they use the session-scoped event loop from
pytest-asyncio (asyncio_default_fixture_loop_scope = "session" in pyproject).
"""

from __future__ import annotations

import asyncio
import socket
import threading
import time
from contextlib import suppress
from typing import TYPE_CHECKING, Any

import pytest
import pytest_asyncio
from uvicorn import Config, Server

from fast_healthchecks.checks.kafka import KafkaHealthCheck
from fast_healthchecks.checks.mongo import MongoHealthCheck
from fast_healthchecks.checks.opensearch import OpenSearchHealthCheck
from fast_healthchecks.checks.rabbitmq import RabbitMQHealthCheck
from fast_healthchecks.checks.redis import RedisHealthCheck
from tests.integration.checks.httpbin_like_app import app as httpbin_like_app

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator


def _free_port() -> int:
    """Bind to port 0 and return the assigned port.

    Returns:
        int: Assigned port number.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _run_uvicorn(server: Server) -> None:
    """Run uvicorn Server in a thread."""
    server.run()


SERVER_NOT_REACHABLE_MSG = "URL test server did not become reachable"


@pytest.fixture(scope="session", name="url_server_base")
def fixture_url_server_base() -> Generator[str, None, None]:
    """Start a local HTTP server (httpbingo-like) and yield its base URL.

    Server runs in a daemon thread. Use for UrlHealthCheck integration tests
    so they do not depend on external services.

    Yields:
        str: Base URL (e.g. http://127.0.0.1:PORT).

    Raises:
        RuntimeError: If the server does not accept connections within the wait window.
    """
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"

    config = Config(
        httpbin_like_app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        ws="none",  # avoid loading websockets (DeprecationWarning breaks under pytest filterwarnings)
    )
    server = Server(config)

    thread = threading.Thread(target=_run_uvicorn, args=(server,), daemon=True)
    thread.start()

    # Wait until the server accepts connections
    for _ in range(50):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.2)
                s.connect(("127.0.0.1", port))
            break
        except OSError:
            time.sleep(0.1)
    else:
        raise RuntimeError(SERVER_NOT_REACHABLE_MSG)

    yield base_url

    server.should_exit = True
    thread.join(timeout=5)


@pytest_asyncio.fixture
async def redis_check(redis_config: dict[str, Any]) -> AsyncGenerator[RedisHealthCheck, None]:
    """RedisHealthCheck with session config; aclose() in teardown.

    Yields:
        RedisHealthCheck: Check instance using redis_config.
    """
    check = RedisHealthCheck(**redis_config)
    try:
        yield check
    finally:
        with suppress(Exception):
            await asyncio.wait_for(check.aclose(), timeout=5.0)
        with suppress(Exception):
            await asyncio.wait_for(asyncio.sleep(0.1), timeout=1.0)


@pytest_asyncio.fixture
async def kafka_check(kafka_config: dict[str, Any]) -> AsyncGenerator[KafkaHealthCheck, None]:
    """KafkaHealthCheck with session config; aclose() in teardown.

    Yields:
        KafkaHealthCheck: Check instance using kafka_config.
    """
    check = KafkaHealthCheck(**kafka_config)
    try:
        yield check
    finally:
        with suppress(Exception):
            await asyncio.wait_for(check.aclose(), timeout=5.0)
        with suppress(Exception):
            await asyncio.wait_for(asyncio.sleep(0.1), timeout=1.0)


@pytest_asyncio.fixture
async def mongo_check(mongo_config: dict[str, Any]) -> AsyncGenerator[MongoHealthCheck, None]:
    """MongoHealthCheck with session config; aclose() in teardown.

    Yields:
        MongoHealthCheck: Check instance using mongo_config.
    """
    check = MongoHealthCheck(**mongo_config)
    try:
        yield check
    finally:
        with suppress(Exception):
            await asyncio.wait_for(check.aclose(), timeout=5.0)
        with suppress(Exception):
            await asyncio.wait_for(asyncio.sleep(0.1), timeout=1.0)


@pytest_asyncio.fixture
async def rabbitmq_check(rabbitmq_config: dict[str, Any]) -> AsyncGenerator[RabbitMQHealthCheck, None]:
    """RabbitMQHealthCheck with session config; aclose() in teardown.

    aclose() is wrapped in wait_for(..., timeout=5) because aio_pika/aiormq can
    leave pending tasks (OneShotCallback, close_writer_task) that block the loop
    indefinitely; we avoid hanging the test run by timing out and continuing.

    Yields:
        RabbitMQHealthCheck: Check instance using rabbitmq_config.
    """
    check = RabbitMQHealthCheck(**rabbitmq_config)
    try:
        yield check
    finally:
        with suppress(Exception):
            await asyncio.wait_for(check.aclose(), timeout=5.0)
        with suppress(Exception):
            await asyncio.wait_for(asyncio.sleep(0.1), timeout=1.0)


@pytest_asyncio.fixture
async def opensearch_check(opensearch_config: dict[str, Any]) -> AsyncGenerator[OpenSearchHealthCheck, None]:
    """OpenSearchHealthCheck with session config; aclose() in teardown.

    Yields:
        OpenSearchHealthCheck: Check instance using opensearch_config.
    """
    check = OpenSearchHealthCheck(**opensearch_config)
    try:
        yield check
    finally:
        with suppress(Exception):
            await asyncio.wait_for(check.aclose(), timeout=5.0)
        with suppress(Exception):
            await asyncio.wait_for(asyncio.sleep(0.1), timeout=1.0)
