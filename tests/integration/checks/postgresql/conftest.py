"""Fixtures for PostgreSQL integration tests (configs, base URL)."""

from typing import TypedDict

# base_postgresql_config fixture is defined in tests/integration/conftest.py


class BasePostgreSQLConfig(TypedDict, total=True):
    """Type for base PostgreSQL config (keys match base_postgresql_config fixture)."""

    host: str
    port: int
    user: str | None
    password: str | None
    database: str | None
