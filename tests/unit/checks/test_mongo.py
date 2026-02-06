import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from motor.motor_asyncio import AsyncIOMotorClient

from fast_healthchecks.checks.mongo import MongoHealthCheck

pytestmark = pytest.mark.unit

EXPECTED_CLIENT_CREATIONS_AFTER_RECREATE = 2


@pytest.mark.parametrize(
    ("params", "expected", "exception"),
    [
        (
            {},
            {
                "hosts": "localhost",
                "port": 27017,
                "user": None,
                "password": None,
                "database": None,
                "auth_source": "admin",
                "timeout": 5.0,
                "name": "MongoDB",
            },
            None,
        ),
        (
            {
                "hosts": "localhost2",
            },
            {
                "hosts": "localhost2",
                "port": 27017,
                "user": None,
                "password": None,
                "database": None,
                "auth_source": "admin",
                "timeout": 5.0,
                "name": "MongoDB",
            },
            None,
        ),
        (
            {
                "hosts": "localhost2",
                "port": 27018,
            },
            {
                "hosts": "localhost2",
                "port": 27018,
                "user": None,
                "password": None,
                "database": None,
                "auth_source": "admin",
                "timeout": 5.0,
                "name": "MongoDB",
            },
            None,
        ),
        (
            {
                "hosts": "localhost2",
                "port": 27018,
                "user": "user",
            },
            {
                "hosts": "localhost2",
                "port": 27018,
                "user": "user",
                "password": None,
                "database": None,
                "auth_source": "admin",
                "timeout": 5.0,
                "name": "MongoDB",
            },
            None,
        ),
        (
            {
                "hosts": "localhost2",
                "port": 27018,
                "user": "user",
                "password": "pass",
            },
            {
                "hosts": "localhost2",
                "port": 27018,
                "user": "user",
                "password": "pass",
                "database": None,
                "auth_source": "admin",
                "timeout": 5.0,
                "name": "MongoDB",
            },
            None,
        ),
        (
            {
                "hosts": "localhost2",
                "port": 27018,
                "user": "user",
                "password": "pass",
                "database": "test",
            },
            {
                "hosts": "localhost2",
                "port": 27018,
                "user": "user",
                "password": "pass",
                "database": "test",
                "auth_source": "admin",
                "timeout": 5.0,
                "name": "MongoDB",
            },
            None,
        ),
        (
            {
                "hosts": "localhost2",
                "port": 27018,
                "user": "user",
                "password": "pass",
                "database": "test",
                "auth_source": "admin2",
            },
            {
                "hosts": "localhost2",
                "port": 27018,
                "user": "user",
                "password": "pass",
                "database": "test",
                "auth_source": "admin2",
                "timeout": 5.0,
                "name": "MongoDB",
            },
            None,
        ),
        (
            {
                "hosts": "localhost2",
                "port": 27018,
                "user": "user",
                "password": "pass",
                "database": "test",
                "auth_source": "admin2",
                "timeout": 10.0,
            },
            {
                "hosts": "localhost2",
                "port": 27018,
                "user": "user",
                "password": "pass",
                "database": "test",
                "auth_source": "admin2",
                "timeout": 10.0,
                "name": "MongoDB",
            },
            None,
        ),
        (
            {
                "hosts": "localhost2",
                "port": 27018,
                "user": "user",
                "password": "pass",
                "database": "test",
                "auth_source": "admin2",
                "timeout": 10.0,
                "name": "test",
            },
            {
                "hosts": "localhost2",
                "port": 27018,
                "user": "user",
                "password": "pass",
                "database": "test",
                "auth_source": "admin2",
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
            MongoHealthCheck(**params)
    else:
        obj = MongoHealthCheck(**params)
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
            ("mongodb://localhost:27017/",),
            {},
            {
                "hosts": "localhost",
                "port": 27017,
                "user": None,
                "password": None,
                "database": None,
                "auth_source": "admin",
                "timeout": 5.0,
                "name": "MongoDB",
            },
            None,
        ),
        (
            ("mongodb://localhost:27017/test",),
            {},
            {
                "hosts": "localhost",
                "port": 27017,
                "user": None,
                "password": None,
                "database": "test",
                "auth_source": "admin",
                "timeout": 5.0,
                "name": "MongoDB",
            },
            None,
        ),
        (
            ("mongodb://user:pass@localhost:27017/test",),
            {},
            {
                "hosts": "localhost",
                "port": 27017,
                "user": "user",
                "password": "pass",
                "database": "test",
                "auth_source": "admin",
                "timeout": 5.0,
                "name": "MongoDB",
            },
            None,
        ),
        (
            ("mongodb://user:pass@localhost:27017/test?authSource=admin2",),
            {},
            {
                "hosts": "localhost",
                "port": 27017,
                "user": "user",
                "password": "pass",
                "database": "test",
                "auth_source": "admin2",
                "timeout": 5.0,
                "name": "MongoDB",
            },
            None,
        ),
        (
            ("mongodb://user:pass@localhost:27017/test?authSource=admin2",),
            {
                "timeout": 10.0,
                "name": "Test",
            },
            {
                "hosts": "localhost",
                "port": 27017,
                "user": "user",
                "password": "pass",
                "database": "test",
                "auth_source": "admin2",
                "timeout": 10.0,
                "name": "Test",
            },
            None,
        ),
        (
            ("mongodb://user:pass@localhost:27017,localhost2:27018/test?authSource=admin2",),
            {
                "timeout": 10.0,
                "name": "Test",
            },
            {
                "hosts": ["localhost:27017", "localhost2:27018"],
                "port": None,
                "user": "user",
                "password": "pass",
                "database": "test",
                "auth_source": "admin2",
                "timeout": 10.0,
                "name": "Test",
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
            MongoHealthCheck.from_dsn(*args, **kwargs)
    else:
        obj = MongoHealthCheck.from_dsn(*args, **kwargs)
        assert obj.to_dict() == expected


@pytest.mark.asyncio
async def test_AsyncIOMotorClient_args_kwargs() -> None:
    health_check = MongoHealthCheck(
        hosts="localhost2",
        port=27018,
        user="user",
        password="password",
        database="test",
        auth_source="admin2",
        timeout=1.5,
        name="MongoDB",
    )
    with patch("fast_healthchecks.checks.mongo.AsyncIOMotorClient", spec=AsyncIOMotorClient) as mock:
        await health_check()
        mock.assert_called_once_with(
            host="localhost2",
            port=27018,
            username="user",
            password="password",
            authSource="admin2",
            serverSelectionTimeoutMS=1500,
        )

    health_check2 = MongoHealthCheck(
        hosts="localhost:27017,localhost2:27018",
        port=None,
        user="user",
        password="password",
        database="test",
        auth_source="admin2",
        timeout=1.5,
        name="MongoDB",
    )
    with patch("fast_healthchecks.checks.mongo.AsyncIOMotorClient", spec=AsyncIOMotorClient) as mock:
        await health_check2()
        mock.assert_called_once_with(
            host="localhost:27017,localhost2:27018",
            port=None,
            username="user",
            password="password",
            authSource="admin2",
            serverSelectionTimeoutMS=1500,
        )


@pytest.mark.asyncio
async def test_AsyncIOMotorClient_reused_between_calls() -> None:
    health_check = MongoHealthCheck(hosts="localhost", port=27017, database="test")
    mock_client = AsyncMock(spec=AsyncIOMotorClient)
    mock_client["test"].command = AsyncMock(return_value={"ok": 1})
    with patch("fast_healthchecks.checks.mongo.AsyncIOMotorClient", return_value=mock_client) as factory:
        await health_check()
        await health_check()
        factory.assert_called_once_with(
            host="localhost",
            port=27017,
            username=None,
            password=None,
            authSource="admin",
            serverSelectionTimeoutMS=5000,
        )


@pytest.mark.asyncio
async def test__call_success() -> None:
    health_check = MongoHealthCheck(
        hosts="localhost",
        port=27017,
        user="user",
        password="password",
        database="test",
        auth_source="admin",
        timeout=1.5,
        name="MongoDB",
    )
    mock_client = AsyncMock(spec=AsyncIOMotorClient)
    mock_client["test"].command = AsyncMock()
    mock_client["test"].command.side_effect = [{"ok": 1}]
    with patch("fast_healthchecks.checks.mongo.AsyncIOMotorClient", return_value=mock_client):
        result = await health_check()
        assert result.healthy is True
        assert result.name == "MongoDB"
        assert result.error_details is None
        mock_client["test"].command.assert_called_once_with("ping")
        mock_client["test"].command.assert_awaited_once_with("ping")


@pytest.mark.asyncio
async def test__call_failure() -> None:
    health_check = MongoHealthCheck(
        hosts="localhost",
        port=27017,
        user="user",
        password="password",
        database="test",
        auth_source="admin",
        timeout=1.5,
        name="MongoDB",
    )
    mock_client = AsyncMock(spec=AsyncIOMotorClient)
    mock_client["test"].command = AsyncMock()
    mock_client["test"].command.side_effect = Exception("Connection failed")
    with patch("fast_healthchecks.checks.mongo.AsyncIOMotorClient", return_value=mock_client):
        result = await health_check()
        assert result.healthy is False
        assert result.name == "MongoDB"
        assert result.error_details is not None
        mock_client["test"].command.assert_called_once_with("ping")
        mock_client["test"].command.assert_awaited_once_with("ping")


@pytest.mark.asyncio
async def test_aclose_clears_client() -> None:
    health_check = MongoHealthCheck(hosts="localhost", port=27017, auth_source="admin")
    db = MagicMock()
    db.command = AsyncMock(return_value={"ok": 1})
    mock_client = MagicMock()
    mock_client.__getitem__ = MagicMock(return_value=db)
    with patch("fast_healthchecks.checks.mongo.AsyncIOMotorClient", return_value=mock_client) as factory:
        await health_check()
        assert health_check._client is not None
        await health_check.aclose()
        assert health_check._client is None
        assert health_check._client_loop is None
        await health_check()
        assert factory.call_count == EXPECTED_CLIENT_CREATIONS_AFTER_RECREATE


@pytest.mark.asyncio
async def test_aclose_idempotent_when_no_client() -> None:
    health_check = MongoHealthCheck(hosts="localhost", port=27017, auth_source="admin")
    await health_check.aclose()
    assert health_check._client is None


@pytest.mark.asyncio
async def test_loop_invalidation_recreates_client() -> None:
    health_check = MongoHealthCheck(hosts="localhost", port=27017, auth_source="admin")
    real_loop = asyncio.get_running_loop()
    other_loop = object()
    db = MagicMock()
    db.command = AsyncMock(return_value={"ok": 1})
    mock_client = MagicMock()
    mock_client.__getitem__ = MagicMock(return_value=db)
    with (
        patch("fast_healthchecks.checks.mongo.AsyncIOMotorClient", return_value=mock_client) as factory,
        patch(
            "fast_healthchecks.checks.mongo.asyncio.get_running_loop",
            side_effect=[real_loop, real_loop, other_loop, other_loop],
        ),
    ):
        await health_check()
        await health_check()
        assert factory.call_count == EXPECTED_CLIENT_CREATIONS_AFTER_RECREATE


@pytest.mark.asyncio
async def test_get_client_with_no_running_loop() -> None:
    health_check = MongoHealthCheck(hosts="localhost", port=27017, auth_source="admin")
    db = MagicMock()
    db.command = AsyncMock(return_value={"ok": 1})
    mock_client = MagicMock()
    mock_client.__getitem__ = MagicMock(return_value=db)
    with (
        patch("fast_healthchecks.checks.mongo.asyncio.get_running_loop", side_effect=RuntimeError),
        patch("fast_healthchecks.checks.mongo.AsyncIOMotorClient", return_value=mock_client) as factory,
    ):
        result = await health_check()
        assert result.healthy is True
        factory.assert_called_once()
        assert health_check._client_loop is None
