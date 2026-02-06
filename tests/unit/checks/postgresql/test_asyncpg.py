import ssl
from typing import Any
from unittest.mock import MagicMock, patch
from urllib.parse import ParseResult, unquote, urlparse

import pytest
from asyncpg import Connection

from fast_healthchecks.checks.postgresql.asyncpg import PostgreSQLAsyncPGHealthCheck
from fast_healthchecks.checks.postgresql.base import create_ssl_context
from fast_healthchecks.utils import parse_query_string
from tests.utils import (
    TEST_SSLCERT,
    TEST_SSLKEY,
    TEST_SSLROOTCERT,
    create_temp_files,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("params", "expected", "exception"),
    [
        (
            {},
            "missing 2 required keyword-only arguments: 'host' and 'port'",
            TypeError,
        ),
        (
            {
                "host": "localhost",
            },
            "missing 1 required keyword-only argument: 'port'",
            TypeError,
        ),
        (
            {
                "host": "localhost",
                "port": 5432,
            },
            {
                "host": "localhost",
                "port": 5432,
                "user": None,
                "password": None,
                "database": None,
                "ssl": None,
                "direct_tls": False,
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            {
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
            },
            {
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": None,
                "database": None,
                "ssl": None,
                "direct_tls": False,
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            {
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "pass",
            },
            {
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "pass",
                "database": None,
                "ssl": None,
                "direct_tls": False,
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            {
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "pass",
                "database": "db",
            },
            {
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "pass",
                "database": "db",
                "ssl": None,
                "direct_tls": False,
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            {
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "pass",
                "database": "db",
                "ssl": ("verify-full", TEST_SSLCERT, TEST_SSLKEY, TEST_SSLROOTCERT),
            },
            {
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "pass",
                "database": "db",
                "ssl": ("verify-full", TEST_SSLCERT, TEST_SSLKEY, TEST_SSLROOTCERT),
                "direct_tls": False,
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            {
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "pass",
                "database": "db",
                "ssl": ("verify-full", TEST_SSLCERT, TEST_SSLKEY, TEST_SSLROOTCERT),
                "direct_tls": True,
            },
            {
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "pass",
                "database": "db",
                "ssl": ("verify-full", TEST_SSLCERT, TEST_SSLKEY, TEST_SSLROOTCERT),
                "direct_tls": True,
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            {
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "pass",
                "database": "db",
                "ssl": ("verify-full", TEST_SSLCERT, TEST_SSLKEY, TEST_SSLROOTCERT),
                "direct_tls": True,
                "timeout": 10.0,
            },
            {
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "pass",
                "database": "db",
                "ssl": ("verify-full", TEST_SSLCERT, TEST_SSLKEY, TEST_SSLROOTCERT),
                "direct_tls": True,
                "timeout": 10.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            {
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "pass",
                "database": "db",
                "ssl": ("verify-full", TEST_SSLCERT, TEST_SSLKEY, TEST_SSLROOTCERT),
                "direct_tls": True,
                "timeout": 10.0,
                "name": "test",
            },
            {
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "pass",
                "database": "db",
                "ssl": ("verify-full", TEST_SSLCERT, TEST_SSLKEY, TEST_SSLROOTCERT),
                "direct_tls": True,
                "timeout": 10.0,
                "name": "test",
            },
            None,
        ),
    ],
)
def test__init(params: dict[str, Any], expected: dict[str, Any] | str, exception: type[BaseException] | None) -> None:
    files_1 = list(params.get("ssl", ()) or ())
    files_2 = list(expected.get("ssl", ()) or ()) if isinstance(expected, dict) else []
    files = []
    files += files_1[1:] if files_1 else []
    files += files_2[1:] if files_2 else []
    files = list(set(files))
    with create_temp_files(files):
        if "ssl" in params and params["ssl"] is not None:
            params["ssl"] = create_ssl_context(*params["ssl"])
        if isinstance(expected, dict) and "ssl" in expected and expected["ssl"] is not None:
            expected["ssl"] = create_ssl_context(*expected["ssl"])
        if exception is not None and isinstance(expected, str):
            with pytest.raises(exception, match=expected):
                PostgreSQLAsyncPGHealthCheck(**params)
        else:
            obj = PostgreSQLAsyncPGHealthCheck(**params)
            assert obj.to_dict() == expected


@pytest.mark.parametrize(
    ("args", "kwargs", "expected", "exception"),
    [
        (
            ("postgresql+asyncpg://postgres:pass@localhost:5432/db?sslmode=broken",),
            {},
            "Invalid sslmode: broken",
            ValueError,
        ),
        (
            ("postgresql+asyncpg://postgres:pass@localhost:5432/db?sslmode=disable",),
            {},
            {
                "database": "db",
                "direct_tls": False,
                "host": "localhost",
                "password": "pass",
                "port": 5432,
                "ssl": None,
                "user": "postgres",
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            (f"postgresql+asyncpg://postgres:pass@localhost:5432/db?sslmode=disable&sslcert={TEST_SSLCERT}",),
            {},
            {
                "database": "db",
                "direct_tls": False,
                "host": "localhost",
                "password": "pass",
                "port": 5432,
                "ssl": None,
                "user": "postgres",
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            (
                f"postgresql+asyncpg://postgres:pass@localhost:5432/db?sslmode=disable&sslcert={TEST_SSLCERT}&sslkey={TEST_SSLKEY}",
            ),
            {},
            {
                "database": "db",
                "direct_tls": False,
                "host": "localhost",
                "password": "pass",
                "port": 5432,
                "ssl": None,
                "user": "postgres",
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            (
                f"postgresql+asyncpg://postgres:pass@localhost:5432/db?sslmode=disable&sslcert={TEST_SSLCERT}&sslkey={TEST_SSLKEY}&sslrootcert={TEST_SSLROOTCERT}",
            ),
            {},
            {
                "database": "db",
                "direct_tls": False,
                "host": "localhost",
                "password": "pass",
                "port": 5432,
                "ssl": None,
                "user": "postgres",
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            ("postgresql+asyncpg://postgres:pass@localhost:5432/db?sslmode=allow",),
            {},
            {
                "database": "db",
                "direct_tls": False,
                "host": "localhost",
                "password": "pass",
                "port": 5432,
                "ssl": None,
                "user": "postgres",
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            (f"postgresql+asyncpg://postgres:pass@localhost:5432/db?sslmode=allow&sslcert={TEST_SSLCERT}",),
            {},
            {
                "database": "db",
                "direct_tls": False,
                "host": "localhost",
                "password": "pass",
                "port": 5432,
                "ssl": None,
                "user": "postgres",
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            (
                f"postgresql+asyncpg://postgres:pass@localhost:5432/db?sslmode=allow&sslcert={TEST_SSLCERT}&sslkey={TEST_SSLKEY}",
            ),
            {},
            {
                "database": "db",
                "direct_tls": False,
                "host": "localhost",
                "password": "pass",
                "port": 5432,
                "ssl": None,
                "user": "postgres",
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            (
                f"postgresql+asyncpg://postgres:pass@localhost:5432/db?sslmode=allow&sslcert={TEST_SSLCERT}&sslkey={TEST_SSLKEY}&sslrootcert={TEST_SSLROOTCERT}",
            ),
            {},
            {
                "database": "db",
                "direct_tls": False,
                "host": "localhost",
                "password": "pass",
                "port": 5432,
                "ssl": None,
                "user": "postgres",
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            ("postgresql+asyncpg://postgres:pass@localhost:5432/db?sslmode=prefer",),
            {},
            {
                "database": "db",
                "direct_tls": False,
                "host": "localhost",
                "password": "pass",
                "port": 5432,
                "ssl": ("prefer", None, None, None),
                "user": "postgres",
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            (f"postgresql+asyncpg://postgres:pass@localhost:5432/db?sslmode=prefer&sslcert={TEST_SSLCERT}",),
            {},
            {
                "database": "db",
                "direct_tls": False,
                "host": "localhost",
                "password": "pass",
                "port": 5432,
                "ssl": ("prefer", TEST_SSLCERT, None, None),
                "user": "postgres",
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            (
                f"postgresql+asyncpg://postgres:pass@localhost:5432/db?sslmode=prefer&sslcert={TEST_SSLCERT}&sslkey={TEST_SSLKEY}",
            ),
            {},
            {
                "database": "db",
                "direct_tls": False,
                "host": "localhost",
                "password": "pass",
                "port": 5432,
                "ssl": ("prefer", TEST_SSLCERT, TEST_SSLKEY, None),
                "user": "postgres",
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            (
                f"postgresql+asyncpg://postgres:pass@localhost:5432/db?sslmode=prefer&sslcert={TEST_SSLCERT}&sslkey={TEST_SSLKEY}&sslrootcert={TEST_SSLROOTCERT}",
            ),
            {},
            {
                "database": "db",
                "direct_tls": False,
                "host": "localhost",
                "password": "pass",
                "port": 5432,
                "ssl": ("prefer", TEST_SSLCERT, TEST_SSLKEY, TEST_SSLROOTCERT),
                "user": "postgres",
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            ("postgresql+asyncpg://postgres:pass@localhost:5432/db?sslmode=require",),
            {},
            {
                "database": "db",
                "direct_tls": False,
                "host": "localhost",
                "password": "pass",
                "port": 5432,
                "ssl": ("require", None, None, None),
                "user": "postgres",
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            (f"postgresql+asyncpg://postgres:pass@localhost:5432/db?sslmode=require&sslcert={TEST_SSLCERT}",),
            {},
            {
                "database": "db",
                "direct_tls": False,
                "host": "localhost",
                "password": "pass",
                "port": 5432,
                "ssl": ("require", TEST_SSLCERT, None, None),
                "user": "postgres",
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            (
                f"postgresql+asyncpg://postgres:pass@localhost:5432/db?sslmode=require&sslcert={TEST_SSLCERT}&sslkey={TEST_SSLKEY}",
            ),
            {},
            {
                "database": "db",
                "direct_tls": False,
                "host": "localhost",
                "password": "pass",
                "port": 5432,
                "ssl": ("require", TEST_SSLCERT, TEST_SSLKEY, None),
                "user": "postgres",
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            (
                f"postgresql+asyncpg://postgres:pass@localhost:5432/db?sslmode=require&sslcert={TEST_SSLCERT}&sslkey={TEST_SSLKEY}&sslrootcert={TEST_SSLROOTCERT}",
            ),
            {},
            {
                "database": "db",
                "direct_tls": False,
                "host": "localhost",
                "password": "pass",
                "port": 5432,
                "ssl": ("require", TEST_SSLCERT, TEST_SSLKEY, TEST_SSLROOTCERT),
                "user": "postgres",
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            ("postgresql+asyncpg://postgres:pass@localhost:5432/db?sslmode=verify-ca",),
            {},
            {
                "database": "db",
                "direct_tls": False,
                "host": "localhost",
                "password": "pass",
                "port": 5432,
                "ssl": ("verify-ca", None, None, None),
                "user": "postgres",
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            (f"postgresql+asyncpg://postgres:pass@localhost:5432/db?sslmode=verify-ca&sslcert={TEST_SSLCERT}",),
            {},
            {
                "database": "db",
                "direct_tls": False,
                "host": "localhost",
                "password": "pass",
                "port": 5432,
                "ssl": ("verify-ca", TEST_SSLCERT, None, None),
                "user": "postgres",
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            (
                f"postgresql+asyncpg://postgres:pass@localhost:5432/db?sslmode=verify-ca&sslcert={TEST_SSLCERT}&sslkey={TEST_SSLKEY}",
            ),
            {},
            {
                "database": "db",
                "direct_tls": False,
                "host": "localhost",
                "password": "pass",
                "port": 5432,
                "ssl": ("verify-ca", TEST_SSLCERT, TEST_SSLKEY, None),
                "user": "postgres",
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            (
                f"postgresql+asyncpg://postgres:pass@localhost:5432/db?sslmode=verify-ca&sslcert={TEST_SSLCERT}&sslkey={TEST_SSLKEY}&sslrootcert={TEST_SSLROOTCERT}",
            ),
            {},
            {
                "database": "db",
                "direct_tls": False,
                "host": "localhost",
                "password": "pass",
                "port": 5432,
                "ssl": ("verify-ca", TEST_SSLCERT, TEST_SSLKEY, TEST_SSLROOTCERT),
                "user": "postgres",
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            ("postgresql+asyncpg://postgres:pass@localhost:5432/db?sslmode=verify-full",),
            {},
            "sslcert is required for verify-full",
            ValueError,
        ),
        (
            (f"postgresql+asyncpg://postgres:pass@localhost:5432/db?sslmode=verify-full&sslcert={TEST_SSLCERT}",),
            {},
            "\\[SSL\\] PEM lib \\(_ssl.c:\\d+\\)",
            ssl.SSLError,
        ),
        (
            (
                f"postgresql+asyncpg://postgres:pass@localhost:5432/db?sslmode=verify-full&sslcert={TEST_SSLCERT}&sslkey={TEST_SSLKEY}",
            ),
            {},
            {
                "database": "db",
                "direct_tls": False,
                "host": "localhost",
                "password": "pass",
                "port": 5432,
                "ssl": ("verify-full", unquote(TEST_SSLCERT), unquote(TEST_SSLKEY), None),
                "user": "postgres",
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            (
                f"postgresql+asyncpg://postgres:pass@localhost:5432/db?sslmode=verify-full&sslcert={TEST_SSLCERT}&sslkey={TEST_SSLKEY}&sslrootcert={TEST_SSLROOTCERT}",
            ),
            {},
            {
                "database": "db",
                "direct_tls": False,
                "host": "localhost",
                "password": "pass",
                "port": 5432,
                "ssl": ("verify-full", unquote(TEST_SSLCERT), unquote(TEST_SSLKEY), unquote(TEST_SSLROOTCERT)),
                "user": "postgres",
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            (
                f"postgresql+asyncpg://postgres:pass@localhost:5432/db?sslmode=verify-full&sslcert={TEST_SSLCERT}&sslkey={TEST_SSLKEY}&sslrootcert={TEST_SSLROOTCERT}",
            ),
            {
                "timeout": 10.0,
            },
            {
                "database": "db",
                "direct_tls": False,
                "host": "localhost",
                "password": "pass",
                "port": 5432,
                "ssl": ("verify-full", unquote(TEST_SSLCERT), unquote(TEST_SSLKEY), unquote(TEST_SSLROOTCERT)),
                "user": "postgres",
                "timeout": 10.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            (
                f"postgresql+asyncpg://postgres:pass@localhost:5432/db?sslmode=verify-full&sslcert={TEST_SSLCERT}&sslkey={TEST_SSLKEY}&sslrootcert={TEST_SSLROOTCERT}",
            ),
            {
                "timeout": 10.0,
                "name": "test",
            },
            {
                "database": "db",
                "direct_tls": False,
                "host": "localhost",
                "password": "pass",
                "port": 5432,
                "ssl": ("verify-full", unquote(TEST_SSLCERT), unquote(TEST_SSLKEY), unquote(TEST_SSLROOTCERT)),
                "user": "postgres",
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
    parse_result: ParseResult = urlparse(args[0])
    query = parse_query_string(parse_result.query)
    files = [y for x, y in query.items() if x in {"sslcert", "sslkey", "sslrootcert"}]

    if exception is not None and isinstance(expected, str):
        with pytest.raises(exception, match=expected), create_temp_files(files):
            PostgreSQLAsyncPGHealthCheck.from_dsn(*args, **kwargs)
    else:
        with create_temp_files(files):
            check = PostgreSQLAsyncPGHealthCheck.from_dsn(*args, **kwargs)
            if isinstance(expected, dict) and "ssl" in expected and expected["ssl"] is not None:
                expected["ssl"] = create_ssl_context(*expected["ssl"])
            assert check.to_dict() == expected


@pytest.mark.asyncio
async def test_asyncpg_connect_args_kwargs() -> None:
    with create_temp_files([TEST_SSLCERT, TEST_SSLKEY, TEST_SSLROOTCERT]):
        test_ssl_context = create_ssl_context("verify-full", TEST_SSLCERT, TEST_SSLKEY, TEST_SSLROOTCERT)
        health_check = PostgreSQLAsyncPGHealthCheck(
            host="localhost2",
            port=6432,
            user="user",
            password="password",
            database="db",
            ssl=test_ssl_context,
            direct_tls=True,
            timeout=1.5,
            name="test",
        )
        Connection_mock = MagicMock(spec=Connection)
        Connection_mock.is_closed.return_value = False
        with patch(
            "fast_healthchecks.checks.postgresql.asyncpg.asyncpg.connect",
            return_value=Connection_mock,
        ) as asyncpg_connect_mock:
            await health_check()
            asyncpg_connect_mock.assert_called_once_with(
                host="localhost2",
                port=6432,
                user="user",
                password="password",
                database="db",
                timeout=1.5,
                ssl=test_ssl_context,
                direct_tls=True,
            )
            asyncpg_connect_mock.assert_awaited_once_with(
                host="localhost2",
                port=6432,
                user="user",
                password="password",
                database="db",
                timeout=1.5,
                ssl=test_ssl_context,
                direct_tls=True,
            )
            Connection_mock.transaction.assert_called_once_with(readonly=True)
            Connection_mock.fetchval.assert_called_once_with("SELECT 1")
            Connection_mock.fetchval.assert_awaited_once_with("SELECT 1")
            Connection_mock.is_closed.assert_called_once_with()
            Connection_mock.close.assert_called_once_with(timeout=1.5)
            Connection_mock.close.assert_awaited_once_with(timeout=1.5)


@pytest.mark.asyncio
async def test__call_success() -> None:
    with create_temp_files([TEST_SSLCERT, TEST_SSLKEY, TEST_SSLROOTCERT]):
        test_ssl_context = create_ssl_context("verify-full", TEST_SSLCERT, TEST_SSLKEY, TEST_SSLROOTCERT)
        health_check = PostgreSQLAsyncPGHealthCheck(
            host="localhost2",
            port=6432,
            user="user",
            password="password",
            database="db",
            ssl=test_ssl_context,
            direct_tls=True,
            timeout=1.5,
            name="test",
        )
        Connection_mock = MagicMock(spec=Connection)
        Connection_mock.is_closed.return_value = False
        Connection_mock.fetchval.return_value = 1
        with patch(
            "fast_healthchecks.checks.postgresql.asyncpg.asyncpg.connect",
            return_value=Connection_mock,
        ) as asyncpg_connect_mock:
            result = await health_check()
            assert result.healthy is True
            assert result.name == "test"
            asyncpg_connect_mock.assert_called_once_with(
                host="localhost2",
                port=6432,
                user="user",
                password="password",
                database="db",
                timeout=1.5,
                ssl=test_ssl_context,
                direct_tls=True,
            )
            Connection_mock.transaction.assert_called_once_with(readonly=True)
            Connection_mock.fetchval.assert_called_once_with("SELECT 1")
            Connection_mock.is_closed.assert_called_once_with()
            Connection_mock.close.assert_called_once_with(timeout=1.5)


@pytest.mark.asyncio
async def test__call_failure() -> None:
    with create_temp_files([TEST_SSLCERT, TEST_SSLKEY, TEST_SSLROOTCERT]):
        test_ssl_context = create_ssl_context("verify-full", TEST_SSLCERT, TEST_SSLKEY, TEST_SSLROOTCERT)
        health_check = PostgreSQLAsyncPGHealthCheck(
            host="localhost2",
            port=6432,
            user="user",
            password="password",
            database="db",
            ssl=test_ssl_context,
            direct_tls=True,
            timeout=1.5,
            name="test",
        )
        Connection_mock = MagicMock(spec=Connection)
        Connection_mock.is_closed.return_value = False
        Connection_mock.fetchval.side_effect = Exception("Database error")
        with patch(
            "fast_healthchecks.checks.postgresql.asyncpg.asyncpg.connect",
            return_value=Connection_mock,
        ) as asyncpg_connect_mock:
            result = await health_check()
            assert result.healthy is False
            assert result.name == "test"
            assert "Database error" in str(result.error_details)
            asyncpg_connect_mock.assert_called_once_with(
                host="localhost2",
                port=6432,
                user="user",
                password="password",
                database="db",
                timeout=1.5,
                ssl=test_ssl_context,
                direct_tls=True,
            )
            Connection_mock.transaction.assert_called_once_with(readonly=True)
            Connection_mock.fetchval.assert_called_once_with("SELECT 1")
            Connection_mock.is_closed.assert_called_once_with()
            Connection_mock.close.assert_called_once_with(timeout=1.5)
