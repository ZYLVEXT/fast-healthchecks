"""Unit tests for RedisHealthCheck."""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from redis.asyncio import Redis

from fast_healthchecks.checks.redis import RedisHealthCheck
from fast_healthchecks.errors import DEPENDENCY_UNHEALTHY
from tests.utils import assert_check_init

pytestmark = pytest.mark.unit

EXPECTED_CLIENT_CREATIONS_AFTER_RECREATE = 2


@pytest.mark.parametrize(
    ("params", "expected", "exception"),
    [
        (
            {},
            {
                "host": "localhost",
                "port": 6379,
                "database": 0,
                "user": None,
                "password": None,
                "ssl": False,
                "ssl_ca_certs": None,
                "timeout": 5.0,
                "name": "Redis",
            },
            None,
        ),
        (
            {
                "host": "localhost2",
            },
            {
                "host": "localhost2",
                "port": 6379,
                "database": 0,
                "user": None,
                "password": None,
                "ssl": False,
                "ssl_ca_certs": None,
                "timeout": 5.0,
                "name": "Redis",
            },
            None,
        ),
        (
            {
                "host": "localhost2",
                "port": 6380,
            },
            {
                "host": "localhost2",
                "port": 6380,
                "database": 0,
                "user": None,
                "password": None,
                "ssl": False,
                "ssl_ca_certs": None,
                "timeout": 5.0,
                "name": "Redis",
            },
            None,
        ),
        (
            {
                "host": "localhost2",
                "port": 6380,
                "database": 1,
            },
            {
                "host": "localhost2",
                "port": 6380,
                "database": 1,
                "user": None,
                "password": None,
                "ssl": False,
                "ssl_ca_certs": None,
                "timeout": 5.0,
                "name": "Redis",
            },
            None,
        ),
        (
            {
                "host": "localhost2",
                "port": 6380,
                "database": "test",
            },
            {
                "host": "localhost2",
                "port": 6380,
                "database": "test",
                "user": None,
                "password": None,
                "ssl": False,
                "ssl_ca_certs": None,
                "timeout": 5.0,
                "name": "Redis",
            },
            None,
        ),
        (
            {
                "host": "localhost2",
                "port": 6380,
                "database": "test",
                "user": "user",
            },
            {
                "host": "localhost2",
                "port": 6380,
                "database": "test",
                "user": "user",
                "password": None,
                "ssl": False,
                "ssl_ca_certs": None,
                "timeout": 5.0,
                "name": "Redis",
            },
            None,
        ),
        (
            {
                "host": "localhost2",
                "port": 6380,
                "database": "test",
                "user": "user",
                "password": "pass",
            },
            {
                "host": "localhost2",
                "port": 6380,
                "database": "test",
                "user": "user",
                "password": "pass",
                "ssl": False,
                "ssl_ca_certs": None,
                "timeout": 5.0,
                "name": "Redis",
            },
            None,
        ),
        (
            {
                "host": "localhost2",
                "port": 6380,
                "database": "test",
                "user": "user",
                "password": "pass",
                "timeout": 10.0,
            },
            {
                "host": "localhost2",
                "port": 6380,
                "database": "test",
                "user": "user",
                "password": "pass",
                "ssl": False,
                "ssl_ca_certs": None,
                "timeout": 10.0,
                "name": "Redis",
            },
            None,
        ),
        (
            {
                "host": "localhost2",
                "port": 6380,
                "database": "test",
                "user": "user",
                "password": "pass",
                "timeout": 10.0,
                "name": "test",
            },
            {
                "host": "localhost2",
                "port": 6380,
                "database": "test",
                "user": "user",
                "password": "pass",
                "ssl": False,
                "ssl_ca_certs": None,
                "timeout": 10.0,
                "name": "test",
            },
            None,
        ),
    ],
)
def test_init(params: dict[str, Any], expected: dict[str, Any], exception: type[BaseException] | None) -> None:
    """RedisHealthCheck.__init__ and to_dict match expected or raise."""
    assert_check_init(lambda: RedisHealthCheck(**params), expected, exception)


@pytest.mark.parametrize(
    ("args", "kwargs", "expected", "exception"),
    [
        (
            ("redis://localhost:6379/",),
            {},
            {
                "host": "localhost",
                "port": 6379,
                "database": 0,
                "user": None,
                "password": None,
                "ssl": False,
                "ssl_ca_certs": None,
                "timeout": 5.0,
                "name": "Redis",
            },
            None,
        ),
        (
            ("redis://localhost:6379/1",),
            {},
            {
                "host": "localhost",
                "port": 6379,
                "database": 1,
                "user": None,
                "password": None,
                "ssl": False,
                "ssl_ca_certs": None,
                "timeout": 5.0,
                "name": "Redis",
            },
            None,
        ),
        (
            ("redis://user@localhost:6379/1",),
            {},
            {
                "host": "localhost",
                "port": 6379,
                "database": 1,
                "user": "user",
                "password": None,
                "ssl": False,
                "ssl_ca_certs": None,
                "timeout": 5.0,
                "name": "Redis",
            },
            None,
        ),
        (
            ("redis://user:pass@localhost:6379/1",),
            {},
            {
                "host": "localhost",
                "port": 6379,
                "database": 1,
                "user": "user",
                "password": "pass",
                "ssl": False,
                "ssl_ca_certs": None,
                "timeout": 5.0,
                "name": "Redis",
            },
            None,
        ),
        (
            ("redis://user:pass@localhost:6379/1",),
            {
                "timeout": 10.0,
            },
            {
                "host": "localhost",
                "port": 6379,
                "database": 1,
                "user": "user",
                "password": "pass",
                "ssl": False,
                "ssl_ca_certs": None,
                "timeout": 10.0,
                "name": "Redis",
            },
            None,
        ),
        (
            ("redis://user:pass@localhost:6379/1",),
            {
                "timeout": 10.0,
                "name": "test",
            },
            {
                "host": "localhost",
                "port": 6379,
                "database": 1,
                "user": "user",
                "password": "pass",
                "ssl": False,
                "ssl_ca_certs": None,
                "timeout": 10.0,
                "name": "test",
            },
            None,
        ),
        (
            ("redis://user:pass@localhost:6379/1?ssl_ca_certs=/root.crt",),
            {
                "timeout": 10.0,
                "name": "test",
            },
            {
                "host": "localhost",
                "port": 6379,
                "database": 1,
                "user": "user",
                "password": "pass",
                "ssl": True,
                "ssl_ca_certs": "/root.crt",
                "timeout": 10.0,
                "name": "test",
            },
            None,
        ),
        (
            ("rediss://localhost:6379/",),
            {},
            {
                "host": "localhost",
                "port": 6379,
                "database": 0,
                "user": None,
                "password": None,
                "ssl": True,
                "ssl_ca_certs": None,
                "timeout": 5.0,
                "name": "Redis",
            },
            None,
        ),
    ],
)
def test_from_dsn(
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    expected: dict[str, Any] | str,
    exception: type[BaseException] | None,
) -> None:
    """Test from_dsn with various DSN options."""
    assert_check_init(lambda: RedisHealthCheck.from_dsn(*args, **kwargs), expected, exception)


@pytest.mark.asyncio
async def test_call_success() -> None:
    """Check returns healthy when Redis ping succeeds."""
    health_check = RedisHealthCheck(
        host="localhost2",
        port=6380,
        database="test",
        user="user",
        password="pass",
        timeout=10.0,
        name="Test",
    )
    redis_mock = MagicMock(spec=Redis)
    redis_mock.ping = AsyncMock(return_value=True)
    with patch("fast_healthchecks.checks.redis.Redis", return_value=redis_mock) as patched_Redis:
        result = await health_check()
        assert result.healthy is True
        assert result.name == "Test"
        patched_Redis.assert_called_once_with(
            host="localhost2",
            port=6380,
            db="test",
            username="user",
            password="pass",
            ssl=False,
            ssl_ca_certs=None,
            socket_timeout=10.0,
            single_connection_client=True,
        )


@pytest.mark.asyncio
async def test_call_reuses_client() -> None:
    """Multiple __call__ reuse the same cached client."""
    health_check = RedisHealthCheck(host="localhost")
    redis_mock = MagicMock(spec=Redis)
    redis_mock.ping = AsyncMock(side_effect=[True, True])
    with patch("fast_healthchecks.checks.redis.Redis", return_value=redis_mock) as patched_Redis:
        await health_check()
        await health_check()
        patched_Redis.assert_called_once_with(
            host="localhost",
            port=6379,
            db=0,
            username=None,
            password=None,
            ssl=False,
            ssl_ca_certs=None,
            socket_timeout=5.0,
            single_connection_client=True,
        )


@pytest.mark.asyncio
async def test_call_failure_invalidates_client_then_succeeds() -> None:
    """After check failure with invalidate_on_error, next call creates new client."""
    health_check = RedisHealthCheck(host="localhost", port=6379, name="Redis")
    with patch("fast_healthchecks.checks.redis.Redis") as patched_Redis:
        mock_instance = MagicMock(spec=Redis)
        mock_instance.ping = AsyncMock(side_effect=[Exception("Connection error"), True])
        mock_instance.aclose = AsyncMock()
        patched_Redis.return_value = mock_instance

        result1 = await health_check()
        assert result1.healthy is False
        assert result1.error is not None
        assert "Connection error" in result1.error.message

        result2 = await health_check()
        assert result2.healthy is True

        assert patched_Redis.call_count == EXPECTED_CLIENT_CREATIONS_AFTER_RECREATE


@pytest.mark.asyncio
async def test_call_ping_false_returns_dependency_unhealthy() -> None:
    """False Redis ping is normalized to structured DEPENDENCY_UNHEALTHY error."""
    health_check = RedisHealthCheck(host="localhost", port=6379, name="Redis")
    with patch("fast_healthchecks.checks.redis.Redis") as patched_redis:
        patched_redis.return_value.ping = AsyncMock(return_value=False)
        result = await health_check()
        assert result.healthy is False
        assert result.error is not None
        assert result.error.code == DEPENDENCY_UNHEALTHY


@pytest.mark.asyncio
async def test_call_exception() -> None:
    """Check returns unhealthy result when Redis raises."""
    health_check = RedisHealthCheck(
        host="localhost",
        port=6379,
        database=0,
        user=None,
        password=None,
        timeout=5.0,
        name="Redis",
    )
    with patch("fast_healthchecks.checks.redis.Redis") as patched_Redis:
        patched_Redis.return_value.ping.side_effect = Exception("Connection error")
        result = await health_check()
        assert result.name == "Redis"
        assert result.healthy is False
        assert result.error is not None
        assert "Connection error" in result.error.message
        patched_Redis.assert_called_once_with(
            host="localhost",
            port=6379,
            db=0,
            username=None,
            password=None,
            ssl=False,
            ssl_ca_certs=None,
            socket_timeout=5.0,
            single_connection_client=True,
        )


@pytest.mark.asyncio
async def test_aclose_clears_client() -> None:
    """aclose() closes cached client and clears it."""
    health_check = RedisHealthCheck(host="localhost", port=6379)
    with patch("fast_healthchecks.checks.redis.Redis") as patched_redis:
        patched_redis.return_value.ping = AsyncMock(return_value=True)
        patched_redis.return_value.aclose = AsyncMock()
        await health_check()
        assert health_check._client is not None
        await health_check.aclose()
        assert health_check._client is None
        assert health_check._client_loop is None
        await health_check()
        assert patched_redis.call_count == EXPECTED_CLIENT_CREATIONS_AFTER_RECREATE


@pytest.mark.asyncio
async def test_aclose_idempotent_when_no_client() -> None:
    """aclose() when no client is safe and idempotent."""
    health_check = RedisHealthCheck(host="localhost", port=6379)
    await health_check.aclose()
    assert health_check._client is None


@pytest.mark.asyncio
async def test_loop_invalidation_recreates_client() -> None:
    """Client from different event loop is recreated on next __call__."""
    health_check = RedisHealthCheck(host="localhost", port=6379)
    real_loop = asyncio.get_running_loop()
    other_loop = object()
    with (
        patch("fast_healthchecks.checks.redis.Redis") as patched_redis,
        patch(
            "fast_healthchecks.checks._base.asyncio.get_running_loop",
            side_effect=[real_loop, real_loop, other_loop, other_loop],
        ),
    ):
        patched_redis.return_value.ping = AsyncMock(return_value=True)
        await health_check()
        await health_check()
        assert patched_redis.call_count == EXPECTED_CLIENT_CREATIONS_AFTER_RECREATE


@pytest.mark.asyncio
async def test_get_client_with_no_running_loop() -> None:
    """_ensure_client works when get_running_loop raises (e.g. outside async)."""
    health_check = RedisHealthCheck(host="localhost", port=6379)
    with (
        patch("fast_healthchecks.checks._base.asyncio.get_running_loop", side_effect=RuntimeError),
        patch("fast_healthchecks.checks.redis.Redis") as patched_redis,
    ):
        patched_redis.return_value.ping = AsyncMock(return_value=True)
        result = await health_check()
        assert result.healthy is True
        patched_redis.assert_called_once()
        assert health_check._client_loop is None
