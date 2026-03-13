"""Unit tests for PostgreSQLPsycopgHealthCheck."""

import ssl
from typing import Any
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch
from urllib.parse import ParseResult, unquote, urlparse

import pytest
from psycopg.connection_async import AsyncConnection, AsyncCursor

from fast_healthchecks.checks.postgresql.base import create_ssl_context
from fast_healthchecks.checks.postgresql.psycopg import PostgreSQLPsycopgHealthCheck
from fast_healthchecks.errors import DEPENDENCY_UNHEALTHY
from fast_healthchecks.utils import parse_query_string
from tests.utils import (
    TEST_SSLCERT,
    TEST_SSLKEY,
    TEST_SSLROOTCERT,
    assert_check_init,
    create_temp_files,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("params", "expected", "exception"),
    [
        (
            {},
            {
                "host": "localhost",
                "port": 5432,
                "user": None,
                "password": None,
                "database": None,
                "sslmode": None,
                "sslcert": None,
                "sslkey": None,
                "sslrootcert": None,
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            {
                "host": "localhost",
            },
            {
                "host": "localhost",
                "port": 5432,
                "user": None,
                "password": None,
                "database": None,
                "sslmode": None,
                "sslcert": None,
                "sslkey": None,
                "sslrootcert": None,
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
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
                "sslmode": None,
                "sslcert": None,
                "sslkey": None,
                "sslrootcert": None,
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
                "sslmode": None,
                "sslcert": None,
                "sslkey": None,
                "sslrootcert": None,
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
                "sslmode": None,
                "sslcert": None,
                "sslkey": None,
                "sslrootcert": None,
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
                "sslmode": None,
                "sslcert": None,
                "sslkey": None,
                "sslrootcert": None,
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
                "sslmode": "disable",
            },
            {
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "pass",
                "database": "db",
                "sslmode": "disable",
                "sslcert": None,
                "sslkey": None,
                "sslrootcert": None,
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
                "sslmode": "disable",
                "sslcert": TEST_SSLCERT,
            },
            {
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "pass",
                "database": "db",
                "sslmode": "disable",
                "sslcert": TEST_SSLCERT,
                "sslkey": None,
                "sslrootcert": None,
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
                "sslmode": "disable",
                "sslcert": TEST_SSLCERT,
                "sslkey": TEST_SSLKEY,
            },
            {
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "pass",
                "database": "db",
                "sslmode": "disable",
                "sslcert": TEST_SSLCERT,
                "sslkey": TEST_SSLKEY,
                "sslrootcert": None,
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
                "sslmode": "disable",
                "sslcert": TEST_SSLCERT,
                "sslkey": TEST_SSLKEY,
                "sslrootcert": TEST_SSLROOTCERT,
            },
            {
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "pass",
                "database": "db",
                "sslmode": "disable",
                "sslcert": TEST_SSLCERT,
                "sslkey": TEST_SSLKEY,
                "sslrootcert": TEST_SSLROOTCERT,
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
                "sslmode": "allow",
            },
            {
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "pass",
                "database": "db",
                "sslmode": "allow",
                "sslcert": None,
                "sslkey": None,
                "sslrootcert": None,
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
                "sslmode": "allow",
                "sslcert": TEST_SSLCERT,
            },
            {
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "pass",
                "database": "db",
                "sslmode": "allow",
                "sslcert": TEST_SSLCERT,
                "sslkey": None,
                "sslrootcert": None,
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
                "sslmode": "allow",
                "sslcert": TEST_SSLCERT,
                "sslkey": TEST_SSLKEY,
            },
            {
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "pass",
                "database": "db",
                "sslmode": "allow",
                "sslcert": TEST_SSLCERT,
                "sslkey": TEST_SSLKEY,
                "sslrootcert": None,
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
                "sslmode": "allow",
                "sslcert": TEST_SSLCERT,
                "sslkey": TEST_SSLKEY,
                "sslrootcert": TEST_SSLROOTCERT,
            },
            {
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "pass",
                "database": "db",
                "sslmode": "allow",
                "sslcert": TEST_SSLCERT,
                "sslkey": TEST_SSLKEY,
                "sslrootcert": TEST_SSLROOTCERT,
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
                "sslmode": "prefer",
            },
            {
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "pass",
                "database": "db",
                "sslmode": "prefer",
                "sslcert": None,
                "sslkey": None,
                "sslrootcert": None,
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
                "sslmode": "prefer",
                "sslcert": TEST_SSLCERT,
            },
            {
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "pass",
                "database": "db",
                "sslmode": "prefer",
                "sslcert": TEST_SSLCERT,
                "sslkey": None,
                "sslrootcert": None,
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
                "sslmode": "prefer",
                "sslcert": TEST_SSLCERT,
                "sslkey": TEST_SSLKEY,
            },
            {
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "pass",
                "database": "db",
                "sslmode": "prefer",
                "sslcert": TEST_SSLCERT,
                "sslkey": TEST_SSLKEY,
                "sslrootcert": None,
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
                "sslmode": "prefer",
                "sslcert": TEST_SSLCERT,
                "sslkey": TEST_SSLKEY,
                "sslrootcert": TEST_SSLROOTCERT,
            },
            {
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "pass",
                "database": "db",
                "sslmode": "prefer",
                "sslcert": TEST_SSLCERT,
                "sslkey": TEST_SSLKEY,
                "sslrootcert": TEST_SSLROOTCERT,
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
                "sslmode": "require",
            },
            {
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "pass",
                "database": "db",
                "sslmode": "require",
                "sslcert": None,
                "sslkey": None,
                "sslrootcert": None,
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
                "sslmode": "require",
                "sslcert": TEST_SSLCERT,
            },
            {
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "pass",
                "database": "db",
                "sslmode": "require",
                "sslcert": TEST_SSLCERT,
                "sslkey": None,
                "sslrootcert": None,
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
                "sslmode": "require",
                "sslcert": TEST_SSLCERT,
                "sslkey": TEST_SSLKEY,
            },
            {
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "pass",
                "database": "db",
                "sslmode": "require",
                "sslcert": TEST_SSLCERT,
                "sslkey": TEST_SSLKEY,
                "sslrootcert": None,
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
                "sslmode": "require",
                "sslcert": TEST_SSLCERT,
                "sslkey": TEST_SSLKEY,
                "sslrootcert": TEST_SSLROOTCERT,
            },
            {
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "pass",
                "database": "db",
                "sslmode": "require",
                "sslcert": TEST_SSLCERT,
                "sslkey": TEST_SSLKEY,
                "sslrootcert": TEST_SSLROOTCERT,
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
                "sslmode": "verify-ca",
            },
            {
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "pass",
                "database": "db",
                "sslmode": "verify-ca",
                "sslcert": None,
                "sslkey": None,
                "sslrootcert": None,
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
                "sslmode": "verify-ca",
                "sslcert": TEST_SSLCERT,
            },
            {
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "pass",
                "database": "db",
                "sslmode": "verify-ca",
                "sslcert": TEST_SSLCERT,
                "sslkey": None,
                "sslrootcert": None,
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
                "sslmode": "verify-ca",
                "sslcert": TEST_SSLCERT,
                "sslkey": TEST_SSLKEY,
            },
            {
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "pass",
                "database": "db",
                "sslmode": "verify-ca",
                "sslcert": TEST_SSLCERT,
                "sslkey": TEST_SSLKEY,
                "sslrootcert": None,
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
                "sslmode": "verify-ca",
                "sslcert": TEST_SSLCERT,
                "sslkey": TEST_SSLKEY,
                "sslrootcert": TEST_SSLROOTCERT,
            },
            {
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "pass",
                "database": "db",
                "sslmode": "verify-ca",
                "sslcert": TEST_SSLCERT,
                "sslkey": TEST_SSLKEY,
                "sslrootcert": TEST_SSLROOTCERT,
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
                "sslmode": "verify-full",
            },
            {
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "pass",
                "database": "db",
                "sslmode": "verify-full",
                "sslcert": None,
                "sslkey": None,
                "sslrootcert": None,
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
                "sslmode": "verify-full",
                "sslcert": TEST_SSLCERT,
            },
            {
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "pass",
                "database": "db",
                "sslmode": "verify-full",
                "sslcert": TEST_SSLCERT,
                "sslkey": None,
                "sslrootcert": None,
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
                "sslmode": "verify-full",
                "sslcert": TEST_SSLCERT,
                "sslkey": TEST_SSLKEY,
            },
            {
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "pass",
                "database": "db",
                "sslmode": "verify-full",
                "sslcert": TEST_SSLCERT,
                "sslkey": TEST_SSLKEY,
                "sslrootcert": None,
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
                "sslmode": "verify-full",
                "sslcert": TEST_SSLCERT,
                "sslkey": TEST_SSLKEY,
                "sslrootcert": TEST_SSLROOTCERT,
            },
            {
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "pass",
                "database": "db",
                "sslmode": "verify-full",
                "sslcert": TEST_SSLCERT,
                "sslkey": TEST_SSLKEY,
                "sslrootcert": TEST_SSLROOTCERT,
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
                "sslmode": "verify-full",
                "sslcert": TEST_SSLCERT,
                "sslkey": TEST_SSLKEY,
                "sslrootcert": TEST_SSLROOTCERT,
                "timeout": 10.0,
            },
            {
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "pass",
                "database": "db",
                "sslmode": "verify-full",
                "sslcert": TEST_SSLCERT,
                "sslkey": TEST_SSLKEY,
                "sslrootcert": TEST_SSLROOTCERT,
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
                "sslmode": "verify-full",
                "sslcert": TEST_SSLCERT,
                "sslkey": TEST_SSLKEY,
                "sslrootcert": TEST_SSLROOTCERT,
                "timeout": 10.0,
                "name": "test",
            },
            {
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "pass",
                "database": "db",
                "sslmode": "verify-full",
                "sslcert": TEST_SSLCERT,
                "sslkey": TEST_SSLKEY,
                "sslrootcert": TEST_SSLROOTCERT,
                "timeout": 10.0,
                "name": "test",
            },
            None,
        ),
    ],
)
def test__init(params: dict[str, Any], expected: dict[str, Any] | str, exception: type[BaseException] | None) -> None:
    """PostgreSQLPsycopgHealthCheck.__init__ and to_dict match expected or raise."""
    assert_check_init(lambda: PostgreSQLPsycopgHealthCheck(**params), expected, exception)


@pytest.mark.parametrize(
    ("args", "kwargs", "expected", "exception"),
    [
        (
            ("postgresql+psycopg://postgres:pass@localhost:5432/db?sslmode=broken",),
            {},
            "Invalid sslmode: broken",
            ValueError,
        ),
        (
            ("postgresql+psycopg://postgres:pass@localhost:5432/db?sslmode=disable",),
            {},
            {
                "database": "db",
                "host": "localhost",
                "password": "pass",
                "port": 5432,
                "sslcert": None,
                "sslkey": None,
                "sslmode": "disable",
                "sslrootcert": None,
                "user": "postgres",
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            (f"postgresql+psycopg://postgres:pass@localhost:5432/db?sslmode=disable&sslcert={TEST_SSLCERT}",),
            {},
            {
                "database": "db",
                "host": "localhost",
                "password": "pass",
                "port": 5432,
                "sslcert": unquote(TEST_SSLCERT),
                "sslkey": None,
                "sslmode": "disable",
                "sslrootcert": None,
                "user": "postgres",
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            (
                f"postgresql+psycopg://postgres:pass@localhost:5432/db?sslmode=disable&sslcert={TEST_SSLCERT}&sslkey={TEST_SSLKEY}",
            ),
            {},
            {
                "database": "db",
                "host": "localhost",
                "password": "pass",
                "port": 5432,
                "sslcert": unquote(TEST_SSLCERT),
                "sslkey": unquote(TEST_SSLKEY),
                "sslmode": "disable",
                "sslrootcert": None,
                "user": "postgres",
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            (
                f"postgresql+psycopg://postgres:pass@localhost:5432/db?sslmode=disable&sslcert={TEST_SSLCERT}&sslkey={TEST_SSLKEY}&sslrootcert={TEST_SSLROOTCERT}",
            ),
            {},
            {
                "database": "db",
                "host": "localhost",
                "password": "pass",
                "port": 5432,
                "sslcert": unquote(TEST_SSLCERT),
                "sslkey": unquote(TEST_SSLKEY),
                "sslmode": "disable",
                "sslrootcert": unquote(TEST_SSLROOTCERT),
                "user": "postgres",
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            ("postgresql+psycopg://postgres:pass@localhost:5432/db?sslmode=allow",),
            {},
            {
                "database": "db",
                "host": "localhost",
                "password": "pass",
                "port": 5432,
                "sslcert": None,
                "sslkey": None,
                "sslmode": "allow",
                "sslrootcert": None,
                "user": "postgres",
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            (f"postgresql+psycopg://postgres:pass@localhost:5432/db?sslmode=allow&sslcert={TEST_SSLCERT}",),
            {},
            {
                "database": "db",
                "host": "localhost",
                "password": "pass",
                "port": 5432,
                "sslcert": unquote(TEST_SSLCERT),
                "sslkey": None,
                "sslmode": "allow",
                "sslrootcert": None,
                "user": "postgres",
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            (
                f"postgresql+psycopg://postgres:pass@localhost:5432/db?sslmode=allow&sslcert={TEST_SSLCERT}&sslkey={TEST_SSLKEY}",
            ),
            {},
            {
                "database": "db",
                "host": "localhost",
                "password": "pass",
                "port": 5432,
                "sslcert": unquote(TEST_SSLCERT),
                "sslkey": unquote(TEST_SSLKEY),
                "sslmode": "allow",
                "sslrootcert": None,
                "user": "postgres",
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            (
                f"postgresql+psycopg://postgres:pass@localhost:5432/db?sslmode=allow&sslcert={TEST_SSLCERT}&sslkey={TEST_SSLKEY}&sslrootcert={TEST_SSLROOTCERT}",
            ),
            {},
            {
                "database": "db",
                "host": "localhost",
                "password": "pass",
                "port": 5432,
                "sslcert": unquote(TEST_SSLCERT),
                "sslkey": unquote(TEST_SSLKEY),
                "sslmode": "allow",
                "sslrootcert": unquote(TEST_SSLROOTCERT),
                "user": "postgres",
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            ("postgresql+psycopg://postgres:pass@localhost:5432/db?sslmode=prefer",),
            {},
            {
                "database": "db",
                "host": "localhost",
                "password": "pass",
                "port": 5432,
                "sslcert": None,
                "sslkey": None,
                "sslmode": "prefer",
                "sslrootcert": None,
                "user": "postgres",
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            (f"postgresql+psycopg://postgres:pass@localhost:5432/db?sslmode=prefer&sslcert={TEST_SSLCERT}",),
            {},
            {
                "database": "db",
                "host": "localhost",
                "password": "pass",
                "port": 5432,
                "sslcert": unquote(TEST_SSLCERT),
                "sslkey": None,
                "sslmode": "prefer",
                "sslrootcert": None,
                "user": "postgres",
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            (
                f"postgresql+psycopg://postgres:pass@localhost:5432/db?sslmode=prefer&sslcert={TEST_SSLCERT}&sslkey={TEST_SSLKEY}",
            ),
            {},
            {
                "database": "db",
                "host": "localhost",
                "password": "pass",
                "port": 5432,
                "sslcert": unquote(TEST_SSLCERT),
                "sslkey": unquote(TEST_SSLKEY),
                "sslmode": "prefer",
                "sslrootcert": None,
                "user": "postgres",
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            (
                f"postgresql+psycopg://postgres:pass@localhost:5432/db?sslmode=prefer&sslcert={TEST_SSLCERT}&sslkey={TEST_SSLKEY}&sslrootcert={TEST_SSLROOTCERT}",
            ),
            {},
            {
                "database": "db",
                "host": "localhost",
                "password": "pass",
                "port": 5432,
                "sslcert": unquote(TEST_SSLCERT),
                "sslkey": unquote(TEST_SSLKEY),
                "sslmode": "prefer",
                "sslrootcert": unquote(TEST_SSLROOTCERT),
                "user": "postgres",
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            ("postgresql+psycopg://postgres:pass@localhost:5432/db?sslmode=verify-full",),
            {},
            "sslcert is required for verify-full",
            ValueError,
        ),
        (
            (f"postgresql+psycopg://postgres:pass@localhost:5432/db?sslmode=verify-full&sslcert={TEST_SSLCERT}",),
            {},
            "\\[SSL\\] PEM lib \\(_ssl.c:\\d+\\)",
            ssl.SSLError,
        ),
        (
            (
                f"postgresql+psycopg://postgres:pass@localhost:5432/db?sslmode=verify-full&sslcert={TEST_SSLCERT}&sslkey={TEST_SSLKEY}",
            ),
            {},
            {
                "database": "db",
                "host": "localhost",
                "password": "pass",
                "port": 5432,
                "sslcert": unquote(TEST_SSLCERT),
                "sslkey": unquote(TEST_SSLKEY),
                "sslmode": "verify-full",
                "sslrootcert": None,
                "user": "postgres",
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            (
                f"postgresql+psycopg://postgres:pass@localhost:5432/db?sslmode=verify-full&sslcert={TEST_SSLCERT}&sslkey={TEST_SSLKEY}&sslrootcert={TEST_SSLROOTCERT}",
            ),
            {},
            {
                "database": "db",
                "host": "localhost",
                "password": "pass",
                "port": 5432,
                "sslcert": unquote(TEST_SSLCERT),
                "sslkey": unquote(TEST_SSLKEY),
                "sslmode": "verify-full",
                "sslrootcert": unquote(TEST_SSLROOTCERT),
                "user": "postgres",
                "timeout": 5.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            (
                f"postgresql+psycopg://postgres:pass@localhost:5432/db?sslmode=verify-full&sslcert={TEST_SSLCERT}&sslkey={TEST_SSLKEY}&sslrootcert={TEST_SSLROOTCERT}",
            ),
            {
                "timeout": 10.0,
            },
            {
                "database": "db",
                "host": "localhost",
                "password": "pass",
                "port": 5432,
                "sslcert": unquote(TEST_SSLCERT),
                "sslkey": unquote(TEST_SSLKEY),
                "sslmode": "verify-full",
                "sslrootcert": unquote(TEST_SSLROOTCERT),
                "user": "postgres",
                "timeout": 10.0,
                "name": "PostgreSQL",
            },
            None,
        ),
        (
            (
                f"postgresql+psycopg://postgres:pass@localhost:5432/db?sslmode=verify-full&sslcert={TEST_SSLCERT}&sslkey={TEST_SSLKEY}&sslrootcert={TEST_SSLROOTCERT}",
            ),
            {
                "timeout": 10.0,
                "name": "test",
            },
            {
                "database": "db",
                "host": "localhost",
                "password": "pass",
                "port": 5432,
                "sslcert": unquote(TEST_SSLCERT),
                "sslkey": unquote(TEST_SSLKEY),
                "sslmode": "verify-full",
                "sslrootcert": unquote(TEST_SSLROOTCERT),
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
    """Test from_dsn with various DSN and SSL options."""
    parse_result: ParseResult = urlparse(args[0])
    query = parse_query_string(parse_result.query)
    files = [y for x, y in query.items() if x in {"sslcert", "sslkey", "sslrootcert"}]
    with create_temp_files(files):
        if exception is None and isinstance(expected, dict) and "ssl" in expected and expected["ssl"] is not None:
            expected["ssl"] = create_ssl_context(*expected["ssl"])
        assert_check_init(lambda: PostgreSQLPsycopgHealthCheck.from_dsn(*args, **kwargs), expected, exception)


@pytest.mark.asyncio
async def test_psycopg_AsyncConnection_connect_args_kwargs() -> None:
    """Constructor and SSL args are passed through to psycopg connect."""
    with create_temp_files([unquote(TEST_SSLCERT), unquote(TEST_SSLKEY), unquote(TEST_SSLROOTCERT)]):
        health_check = PostgreSQLPsycopgHealthCheck(
            host="localhost2",
            port=6432,
            user="user",
            password="password",
            database="db",
            sslmode="verify-full",
            sslcert=unquote(TEST_SSLCERT),
            sslkey=unquote(TEST_SSLKEY),
            sslrootcert=unquote(TEST_SSLROOTCERT),
            timeout=1.5,
            name="test",
        )
        AsyncConnection_mock = MagicMock(spec=AsyncConnection)
        closed = PropertyMock(return_value=False)
        type(AsyncConnection_mock).closed = closed
        AsyncCursor_mock = MagicMock(spec=AsyncCursor)
        AsyncConnection_mock.cursor.return_value = AsyncCursor_mock
        AsyncCursor_mock.__aenter__.return_value = AsyncCursor_mock
        with patch(
            "fast_healthchecks.checks.postgresql.psycopg.psycopg.AsyncConnection.connect",
            return_value=AsyncConnection_mock,
        ) as asyncpg_connect_mock:
            await health_check()
            asyncpg_connect_mock.assert_called_once_with(
                host="localhost2",
                port=6432,
                user="user",
                password="password",
                dbname="db",
                sslmode="verify-full",
                sslcert=unquote(TEST_SSLCERT),
                sslkey=unquote(TEST_SSLKEY),
                sslrootcert=unquote(TEST_SSLROOTCERT),
                connect_timeout=1,
            )
            asyncpg_connect_mock.assert_awaited_once_with(
                host="localhost2",
                port=6432,
                user="user",
                password="password",
                dbname="db",
                sslmode="verify-full",
                sslcert=unquote(TEST_SSLCERT),
                sslkey=unquote(TEST_SSLKEY),
                sslrootcert=unquote(TEST_SSLROOTCERT),
                connect_timeout=1,
            )
            AsyncConnection_mock.cursor.assert_called_once_with()
            AsyncCursor_mock.execute.assert_called_once_with("SELECT 1")
            AsyncCursor_mock.execute.assert_awaited_once_with("SELECT 1")
            AsyncCursor_mock.fetchone.assert_called_once_with()
            AsyncCursor_mock.fetchone.assert_awaited_once_with()
            closed.assert_called_once_with()
            AsyncConnection_mock.cancel_safe.assert_called_once_with(timeout=1.5)
            AsyncConnection_mock.cancel_safe.assert_awaited_once_with(timeout=1.5)
            AsyncConnection_mock.close.assert_called_once_with()
            AsyncConnection_mock.close.assert_awaited_once_with()


@pytest.mark.asyncio
async def test__call_success() -> None:
    """Check returns healthy when connection and ping succeed."""
    with create_temp_files([unquote(TEST_SSLCERT), unquote(TEST_SSLKEY), unquote(TEST_SSLROOTCERT)]):
        health_check = PostgreSQLPsycopgHealthCheck(
            host="localhost",
            port=5432,
            user="user",
            password="password",
            database="db",
            sslmode="verify-full",
            sslcert=unquote(TEST_SSLCERT),
            sslkey=unquote(TEST_SSLKEY),
            sslrootcert=unquote(TEST_SSLROOTCERT),
            timeout=1.5,
            name="test",
        )
        AsyncConnection_mock = AsyncMock(spec=AsyncConnection)
        AsyncCursor_mock = AsyncMock(spec=AsyncCursor)
        AsyncConnection_mock.cursor.return_value.__aenter__.return_value = AsyncCursor_mock
        AsyncCursor_mock.execute.return_value = None
        AsyncCursor_mock.fetchone.return_value = (1,)

        with patch("psycopg.AsyncConnection.connect", return_value=AsyncConnection_mock):
            result = await health_check()
            assert result.healthy is True
            assert result.name == "test"
            assert result.error is None


@pytest.mark.asyncio
async def test__call_failure() -> None:
    """Check returns unhealthy when connection fails."""
    with create_temp_files([unquote(TEST_SSLCERT), unquote(TEST_SSLKEY), unquote(TEST_SSLROOTCERT)]):
        health_check = PostgreSQLPsycopgHealthCheck(
            host="localhost",
            port=5432,
            user="user",
            password="password",
            database="db",
            sslmode="verify-full",
            sslcert=unquote(TEST_SSLCERT),
            sslkey=unquote(TEST_SSLKEY),
            sslrootcert=unquote(TEST_SSLROOTCERT),
            timeout=1.5,
            name="test",
        )
        AsyncConnection_mock = AsyncMock(spec=AsyncConnection)
        AsyncCursor_mock = AsyncMock(spec=AsyncCursor)
        AsyncConnection_mock.cursor.return_value.__aenter__.return_value = AsyncCursor_mock
        AsyncCursor_mock.execute.side_effect = Exception("Database error")

        with patch("psycopg.AsyncConnection.connect", return_value=AsyncConnection_mock):
            result = await health_check()
            assert result.healthy is False
            assert result.name == "test"
            assert result.error is not None
            assert "Database error" in result.error.message


@pytest.mark.asyncio
async def test__call_query_returns_false_dependency_unhealthy() -> None:
    """SELECT result that evaluates to False produces DEPENDENCY_UNHEALTHY."""
    health_check = PostgreSQLPsycopgHealthCheck(
        host="localhost",
        port=5432,
        user="user",
        password="password",
        database="db",
        sslmode="disable",
        sslcert=None,
        sslkey=None,
        sslrootcert=None,
        timeout=1.5,
        name="test",
    )
    async_connection_mock = AsyncMock(spec=AsyncConnection)
    async_cursor_mock = AsyncMock(spec=AsyncCursor)
    async_connection_mock.cursor.return_value.__aenter__.return_value = async_cursor_mock
    async_cursor_mock.execute.return_value = None
    async_cursor_mock.fetchone.return_value = None

    with patch("psycopg.AsyncConnection.connect", return_value=async_connection_mock):
        result = await health_check()
        assert result.healthy is False
        assert result.error is not None
        assert result.error.code == DEPENDENCY_UNHEALTHY
