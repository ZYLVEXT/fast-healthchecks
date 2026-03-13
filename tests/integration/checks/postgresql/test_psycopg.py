"""Integration tests for PostgreSQLPsycopgHealthCheck against real PostgreSQL."""

import pytest

from fast_healthchecks.checks.dsn_parsing import SslMode
from fast_healthchecks.checks.postgresql.psycopg import PostgreSQLPsycopgHealthCheck
from fast_healthchecks.models import HealthCheckResult
from tests.integration.checks.postgresql.conftest import BasePostgreSQLConfig
from tests.integration.test_assertions import (
    CONNECTION_REFUSED_FRAGMENTS,
    DNS_ERROR_FRAGMENTS,
    assert_error_contains_any,
)

pytestmark = pytest.mark.integration


class PsycopgConfig(BasePostgreSQLConfig, total=True):
    """Psycopg-specific config with sslmode and sslrootcert."""

    sslmode: SslMode | None
    sslrootcert: str | None


@pytest.fixture(scope="session", name="psycopg_config")
def fixture_psycopg_config(base_postgresql_config: BasePostgreSQLConfig) -> PsycopgConfig:
    """Build PsycopgConfig from base config.

    Returns:
        PsycopgConfig for integration tests.
    """
    return {
        "host": base_postgresql_config["host"],
        "port": base_postgresql_config["port"],
        "user": base_postgresql_config["user"],
        "password": base_postgresql_config["password"],
        "database": base_postgresql_config["database"],
        "sslmode": None,
        "sslrootcert": None,
    }


@pytest.mark.asyncio
async def test_postgresql_psycopg_check_success(psycopg_config: PsycopgConfig) -> None:
    """Psycopg check returns healthy against real PostgreSQL."""
    check = PostgreSQLPsycopgHealthCheck(
        host=psycopg_config["host"],
        port=psycopg_config["port"],
        user=psycopg_config["user"],
        password=psycopg_config["password"],
        database=psycopg_config["database"],
        sslmode=psycopg_config["sslmode"],
        sslrootcert=psycopg_config["sslrootcert"],
    )
    result = await check()
    assert result == HealthCheckResult(name="PostgreSQL", healthy=True, error_details=None)


@pytest.mark.asyncio
async def test_postgresql_psycopg_check_failure(psycopg_config: PsycopgConfig) -> None:
    """Psycopg check returns unhealthy when DB is unreachable (wrong port)."""
    check = PostgreSQLPsycopgHealthCheck(
        host="localhost2",
        port=psycopg_config["port"],
        user=psycopg_config["user"],
        password=psycopg_config["password"],
        database=psycopg_config["database"],
        sslmode=psycopg_config["sslmode"],
        sslrootcert=psycopg_config["sslrootcert"],
    )
    result = await check()
    assert result.healthy is False
    assert_error_contains_any(result.error_details, DNS_ERROR_FRAGMENTS)


@pytest.mark.asyncio
async def test_postgresql_psycopg_check_connection_error(psycopg_config: PsycopgConfig) -> None:
    """Psycopg check returns unhealthy with error_details on connection error."""
    check = PostgreSQLPsycopgHealthCheck(
        host=psycopg_config["host"],
        port=6432,
        user=psycopg_config["user"],
        password=psycopg_config["password"],
        database=psycopg_config["database"],
        sslmode=psycopg_config["sslmode"],
        sslrootcert=psycopg_config["sslrootcert"],
    )
    result = await check()
    assert result.healthy is False
    assert_error_contains_any(result.error_details, CONNECTION_REFUSED_FRAGMENTS)
