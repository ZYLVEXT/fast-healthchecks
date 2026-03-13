"""Unit tests for MongoHealthCheck."""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from motor.motor_asyncio import AsyncIOMotorClient

from fast_healthchecks.checks.mongo import MongoHealthCheck
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
    """MongoHealthCheck.__init__ and to_dict match expected or raise."""
    assert_check_init(lambda: MongoHealthCheck(**params), expected, exception)


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
        (
            ("mongodb://host1:27017",),
            {},
            {
                "hosts": "host1",
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
            ("mongodb://user:pass@host1:27017,host2:27018",),
            {},
            {
                "hosts": ["host1:27017", "host2:27018"],
                "port": None,
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
            ("mongodb+srv://cluster.mongodb.net/mydb",),
            {},
            {
                "hosts": "cluster.mongodb.net",
                "port": 27017,
                "user": None,
                "password": None,
                "database": "mydb",
                "auth_source": "admin",
                "timeout": 5.0,
                "name": "MongoDB",
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
    assert_check_init(lambda: MongoHealthCheck.from_dsn(*args, **kwargs), expected, exception)


@pytest.mark.asyncio
async def test_AsyncIOMotorClient_args_kwargs() -> None:
    """Constructor args/kwargs are passed through to AsyncIOMotorClient."""
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
    """Same client instance is reused across __call__ invocations."""
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
    """Check returns healthy when ping succeeds."""
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
        assert result.error is None
        mock_client["test"].command.assert_called_once_with("ping")
        mock_client["test"].command.assert_awaited_once_with("ping")


@pytest.mark.asyncio
async def test__call_failure() -> None:
    """Check returns unhealthy when ping fails."""
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
        assert result.error is not None
        mock_client["test"].command.assert_called_once_with("ping")
        mock_client["test"].command.assert_awaited_once_with("ping")


@pytest.mark.asyncio
async def test__call_ping_false_returns_dependency_unhealthy() -> None:
    """Mongo ping with ok=0 returns structured DEPENDENCY_UNHEALTHY error."""
    health_check = MongoHealthCheck(hosts="localhost", port=27017, database="test", name="MongoDB")
    mock_client = AsyncMock(spec=AsyncIOMotorClient)
    mock_client["test"].command = AsyncMock(return_value={"ok": 0})
    with patch("fast_healthchecks.checks.mongo.AsyncIOMotorClient", return_value=mock_client):
        result = await health_check()
        assert result.healthy is False
        assert result.error is not None
        assert result.error.code == DEPENDENCY_UNHEALTHY


@pytest.mark.asyncio
async def test_aclose_clears_client() -> None:
    """aclose() closes and clears cached client."""
    health_check = MongoHealthCheck(hosts="localhost", port=27017, auth_source="admin")
    db = MagicMock()
    db.command = AsyncMock(return_value={"ok": 1})
    mock_client = MagicMock()
    mock_client.__getitem__ = MagicMock(return_value=db)
    mock_client.close = AsyncMock()
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
    """aclose() when no client is safe and idempotent."""
    health_check = MongoHealthCheck(hosts="localhost", port=27017, auth_source="admin")
    await health_check.aclose()
    assert health_check._client is None


@pytest.mark.asyncio
async def test_loop_invalidation_recreates_client() -> None:
    """Client from different event loop is recreated on next __call__."""
    health_check = MongoHealthCheck(hosts="localhost", port=27017, auth_source="admin")
    real_loop = asyncio.get_running_loop()
    other_loop = object()
    db = MagicMock()
    db.command = AsyncMock(return_value={"ok": 1})
    mock_client = MagicMock()
    mock_client.__getitem__ = MagicMock(return_value=db)
    mock_client.close = AsyncMock()
    with (
        patch("fast_healthchecks.checks.mongo.AsyncIOMotorClient", return_value=mock_client) as factory,
        patch(
            "fast_healthchecks.checks._base.asyncio.get_running_loop",
            side_effect=[real_loop, real_loop, other_loop, other_loop],
        ),
    ):
        await health_check()
        await health_check()
        assert factory.call_count == EXPECTED_CLIENT_CREATIONS_AFTER_RECREATE


@pytest.mark.asyncio
async def test_get_client_with_no_running_loop() -> None:
    """_ensure_client works when get_running_loop raises."""
    health_check = MongoHealthCheck(hosts="localhost", port=27017, auth_source="admin")
    db = MagicMock()
    db.command = AsyncMock(return_value={"ok": 1})
    mock_client = MagicMock()
    mock_client.__getitem__ = MagicMock(return_value=db)
    mock_client.close = AsyncMock()
    with (
        patch("fast_healthchecks.checks._base.asyncio.get_running_loop", side_effect=RuntimeError),
        patch("fast_healthchecks.checks.mongo.AsyncIOMotorClient", return_value=mock_client) as factory,
    ):
        result = await health_check()
        assert result.healthy is True
        factory.assert_called_once()
        assert health_check._client_loop is None
