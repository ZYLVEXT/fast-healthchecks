from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from fast_healthchecks.checks.rabbitmq import RabbitMQHealthCheck

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("params", "expected", "exception"),
    [
        (
            {},
            "missing 3 required keyword-only arguments: 'host', 'user', and 'password'",
            TypeError,
        ),
        (
            {
                "host": "localhost",
            },
            "missing 2 required keyword-only arguments: 'user' and 'password'",
            TypeError,
        ),
        (
            {
                "host": "localhost",
                "user": "user",
            },
            "missing 1 required keyword-only argument: 'password'",
            TypeError,
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
    if exception is not None:
        with pytest.raises(exception, match=str(expected)):
            RabbitMQHealthCheck(**params)
    else:
        obj = RabbitMQHealthCheck(**params)
        assert obj.to_dict() == expected


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
    if exception is not None and isinstance(expected, str):
        with pytest.raises(exception, match=expected):
            RabbitMQHealthCheck.from_dsn(*args, **kwargs)
    else:
        obj = RabbitMQHealthCheck.from_dsn(*args, **kwargs)
        assert obj.to_dict() == expected


@pytest.mark.asyncio
async def test_call_success() -> None:
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
        assert "Connection failed" in str(result.error_details)
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
