"""Unit tests for RabbitMQHealthCheck."""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from fast_healthchecks.checks.rabbitmq import RabbitMQHealthCheck
from tests.utils import assert_check_init

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("params", "expected", "exception"),
    [
        (
            {},
            {
                "host": "localhost",
                "port": 5672,
                "user": "guest",
                "password": "guest",
                "vhost": "/",
                "secure": False,
                "timeout": 5.0,
                "name": "RabbitMQ",
            },
            None,
        ),
        (
            {
                "host": "localhost",
            },
            {
                "host": "localhost",
                "port": 5672,
                "user": "guest",
                "password": "guest",
                "vhost": "/",
                "secure": False,
                "timeout": 5.0,
                "name": "RabbitMQ",
            },
            None,
        ),
        (
            {
                "host": "localhost",
                "user": "user",
            },
            {
                "host": "localhost",
                "port": 5672,
                "user": "user",
                "password": "guest",
                "vhost": "/",
                "secure": False,
                "timeout": 5.0,
                "name": "RabbitMQ",
            },
            None,
        ),
        (
            {
                "host": "localhost",
                "user": "user",
                "password": "password",
            },
            {
                "host": "localhost",
                "user": "user",
                "password": "password",
                "port": 5672,
                "vhost": "/",
                "secure": False,
                "timeout": 5.0,
                "name": "RabbitMQ",
            },
            None,
        ),
        (
            {
                "host": "localhost2",
                "user": "user",
                "password": "password",
                "port": 5673,
            },
            {
                "host": "localhost2",
                "user": "user",
                "password": "password",
                "port": 5673,
                "vhost": "/",
                "secure": False,
                "timeout": 5.0,
                "name": "RabbitMQ",
            },
            None,
        ),
        (
            {
                "host": "localhost2",
                "user": "user",
                "password": "password",
                "port": 5673,
                "vhost": "test",
            },
            {
                "host": "localhost2",
                "user": "user",
                "password": "password",
                "port": 5673,
                "vhost": "test",
                "secure": False,
                "timeout": 5.0,
                "name": "RabbitMQ",
            },
            None,
        ),
        (
            {
                "host": "localhost2",
                "user": "user",
                "password": "password",
                "port": 5673,
                "vhost": "test",
                "secure": True,
            },
            {
                "host": "localhost2",
                "user": "user",
                "password": "password",
                "port": 5673,
                "vhost": "test",
                "secure": True,
                "timeout": 5.0,
                "name": "RabbitMQ",
            },
            None,
        ),
        (
            {
                "host": "localhost2",
                "user": "user",
                "password": "password",
                "port": 5673,
                "vhost": "test",
                "secure": True,
                "timeout": 10.0,
            },
            {
                "host": "localhost2",
                "user": "user",
                "password": "password",
                "port": 5673,
                "vhost": "test",
                "secure": True,
                "timeout": 10.0,
                "name": "RabbitMQ",
            },
            None,
        ),
        (
            {
                "host": "localhost2",
                "user": "user",
                "password": "password",
                "port": 5673,
                "vhost": "test",
                "secure": True,
                "timeout": 10.0,
                "name": "test",
            },
            {
                "host": "localhost2",
                "user": "user",
                "password": "password",
                "port": 5673,
                "vhost": "test",
                "secure": True,
                "timeout": 10.0,
                "name": "test",
            },
            None,
        ),
    ],
)
def test_init(params: dict[str, Any], expected: dict[str, Any], exception: type[BaseException] | None) -> None:
    """RabbitMQHealthCheck.__init__ and to_dict match expected or raise."""
    assert_check_init(lambda: RabbitMQHealthCheck(**params), expected, exception)


@pytest.mark.parametrize(
    ("args", "kwargs", "expected", "exception"),
    [
        (
            (),
            {},
            "missing 1 required positional argument: 'dsn'",
            TypeError,
        ),
        (
            ("amqp://user:password@localhost/",),
            {},
            {
                "host": "localhost",
                "user": "user",
                "password": "password",
                "port": 5672,
                "vhost": "/",
                "secure": False,
                "timeout": 5.0,
                "name": "RabbitMQ",
            },
            None,
        ),
        (
            ("amqp://user:password@localhost/test",),
            {},
            {
                "host": "localhost",
                "user": "user",
                "password": "password",
                "port": 5672,
                "vhost": "test",
                "secure": False,
                "timeout": 5.0,
                "name": "RabbitMQ",
            },
            None,
        ),
        (
            ("amqp://user:password@localhost:5673/test",),
            {},
            {
                "host": "localhost",
                "user": "user",
                "password": "password",
                "port": 5673,
                "vhost": "test",
                "secure": False,
                "timeout": 5.0,
                "name": "RabbitMQ",
            },
            None,
        ),
        (
            ("amqps://user:password@localhost:5673/test",),
            {},
            {
                "host": "localhost",
                "user": "user",
                "password": "password",
                "port": 5673,
                "vhost": "test",
                "secure": True,
                "timeout": 5.0,
                "name": "RabbitMQ",
            },
            None,
        ),
        (
            ("amqps://user:password@localhost:5673/test",),
            {
                "timeout": 10.0,
            },
            {
                "host": "localhost",
                "user": "user",
                "password": "password",
                "port": 5673,
                "vhost": "test",
                "secure": True,
                "timeout": 10.0,
                "name": "RabbitMQ",
            },
            None,
        ),
        (
            ("amqps://user:password@localhost:5673/test",),
            {
                "timeout": 10.0,
                "name": "test",
            },
            {
                "host": "localhost",
                "user": "user",
                "password": "password",
                "port": 5673,
                "vhost": "test",
                "secure": True,
                "timeout": 10.0,
                "name": "test",
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
    assert_check_init(lambda: RabbitMQHealthCheck.from_dsn(*args, **kwargs), expected, exception)


@pytest.mark.asyncio
async def test_call_success() -> None:
    """Check returns healthy when connection and channel open succeed."""
    health_check = RabbitMQHealthCheck(
        host="localhost2",
        user="user",
        password="password",
        port=5673,
        vhost="test",
        secure=True,
        timeout=10.0,
    )
    with patch("aio_pika.connect_robust", new_callable=AsyncMock) as mock_connect:
        mock_connect.return_value.__aenter__.return_value = AsyncMock()
        result = await health_check()
        assert result.healthy is True
        assert result.name == "RabbitMQ"
        mock_connect.assert_called_once_with(
            host="localhost2",
            port=5673,
            login="user",
            password="password",
            ssl=True,
            virtualhost="test",
            timeout=10.0,
        )
        mock_connect.assert_awaited_once_with(
            host="localhost2",
            port=5673,
            login="user",
            password="password",
            ssl=True,
            virtualhost="test",
            timeout=10.0,
        )


@pytest.mark.asyncio
async def test_call_failure() -> None:
    """Check returns unhealthy when connection fails."""
    health_check = RabbitMQHealthCheck(
        host="localhost",
        user="user",
        password="password",
    )
    with patch("aio_pika.connect_robust", new_callable=AsyncMock) as mock_connect:
        mock_connect.side_effect = Exception("Connection failed")
        result = await health_check()
        assert result.healthy is False
        assert result.name == "RabbitMQ"
        assert result.error is not None
        assert "Connection failed" in result.error.message
        mock_connect.assert_called_once_with(
            host="localhost",
            port=5672,
            login="user",
            password="password",
            ssl=False,
            virtualhost="/",
            timeout=5.0,
        )
        mock_connect.assert_awaited_once_with(
            host="localhost",
            port=5672,
            login="user",
            password="password",
            ssl=False,
            virtualhost="/",
            timeout=5.0,
        )


@pytest.mark.asyncio
async def test_aclose_clears_client() -> None:
    """aclose() closes and clears cached client (covers _close_rabbitmq_client)."""
    health_check = RabbitMQHealthCheck(
        host="localhost",
        user="user",
        password="password",
    )
    with patch("aio_pika.connect_robust", new_callable=AsyncMock) as mock_connect:
        mock_conn = AsyncMock()
        mock_conn.close = AsyncMock()
        mock_connect.return_value = mock_conn
        await health_check()
        assert health_check._client is not None
        await health_check.aclose()
        assert health_check._client is None
        assert health_check._client_loop is None
        mock_conn.close.assert_called_once_with()


@pytest.mark.asyncio
async def test_aclose_idempotent_when_no_client() -> None:
    """aclose() when no client is safe and idempotent."""
    health_check = RabbitMQHealthCheck(
        host="localhost",
        user="user",
        password="password",
    )
    await health_check.aclose()
    assert health_check._client is None
