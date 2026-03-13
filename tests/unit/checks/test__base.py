"""Tests for HealthCheckDSN (validate_dsn, from_dsn, DummyCheck) and healthcheck_safe."""

import asyncio
from typing import cast

import pytest

from fast_healthchecks.checks._base import healthcheck_safe, result_on_error  # noqa: PLC2701
from fast_healthchecks.checks.kafka import KafkaHealthCheck
from fast_healthchecks.checks.mongo import MongoHealthCheck
from fast_healthchecks.checks.opensearch import OpenSearchHealthCheck
from fast_healthchecks.checks.postgresql.asyncpg import PostgreSQLAsyncPGHealthCheck
from fast_healthchecks.checks.postgresql.psycopg import PostgreSQLPsycopgHealthCheck
from fast_healthchecks.checks.rabbitmq import RabbitMQHealthCheck
from fast_healthchecks.checks.redis import RedisHealthCheck
from fast_healthchecks.checks.types import HealthCheckDSN
from fast_healthchecks.models import HealthCheckResult

pytestmark = pytest.mark.unit

_DSN_CHECK_FROM_DSN_REJECTS_NON_STR = [
    (RedisHealthCheck, "Redis", b"redis://localhost"),
    (KafkaHealthCheck, "Kafka", b"kafka://localhost:9092"),
    (MongoHealthCheck, "MongoDB", b"mongodb://localhost"),
    (RabbitMQHealthCheck, "RabbitMQ", b"amqp://user:pass@host:5672/vhost"),
    (OpenSearchHealthCheck, "OpenSearch", b"http://localhost:9200"),
    (PostgreSQLAsyncPGHealthCheck, "PostgreSQL", b"postgresql://localhost/db"),
    (PostgreSQLPsycopgHealthCheck, "PostgreSQL", b"postgresql://localhost/db"),
]


class DummyCheck(HealthCheckDSN[HealthCheckResult, object]):
    """Minimal HealthCheckDSN for testing validate_dsn/from_dsn."""

    async def __call__(self) -> HealthCheckResult:
        """Return a healthy dummy result.

        Returns:
            HealthCheckResult with name dummy and healthy True.
        """
        return HealthCheckResult(name="dummy", healthy=True)


@pytest.mark.parametrize(
    ("dsn", "allowed_schemes", "expected", "exception"),
    [
        ("redis://localhost:6379", ("redis", "rediss"), "redis://localhost:6379", None),
        ("rediss://localhost:6379", ("redis", "rediss"), "rediss://localhost:6379", None),
        (
            "postgresql://user:pass@host:5432/db",
            ("postgresql", "postgres"),
            "postgresql://user:pass@host:5432/db",
            None,
        ),
        ("postgres://user:pass@host:5432/db", ("postgresql", "postgres"), "postgres://user:pass@host:5432/db", None),
        ("mongodb://user:pass@host:27017/db", ("mongodb", "mongodb+srv"), "mongodb://user:pass@host:27017/db", None),
        ("mongodb+srv://cluster/db", ("mongodb", "mongodb+srv"), "mongodb+srv://cluster/db", None),
        ("amqp://user:pass@host:5672/vhost", ("amqp", "amqps"), "amqp://user:pass@host:5672/vhost", None),
        ("amqps://user:pass@host:5671/vhost", ("amqp", "amqps"), "amqps://user:pass@host:5671/vhost", None),
        ("postgresql+asyncpg://user@host/db", ("postgresql", "postgres"), "postgresql+asyncpg://user@host/db", None),
        ("postgresql+psycopg://user@host/db", ("postgresql", "postgres"), "postgresql+psycopg://user@host/db", None),
        ("  redis://localhost  ", ("redis",), "redis://localhost", None),
        ("REDIS://host", ("redis",), "REDIS://host", None),
        (
            "http://localhost",
            ("redis", "rediss"),
            r"DSN scheme must be one of redis, rediss",
            ValueError,
        ),
        ("", ("redis", "rediss"), "DSN cannot be empty", ValueError),
        ("   ", ("redis", "rediss"), "DSN cannot be empty", ValueError),
        ("\t\n", ("redis",), "DSN cannot be empty", ValueError),
    ],
)
def test_validate_dsn(
    dsn: str,
    allowed_schemes: tuple[str, ...],
    expected: str,
    exception: type[BaseException] | None,
) -> None:
    """Test validate_dsn with various inputs."""
    if exception is not None:
        with pytest.raises(exception, match=expected):
            DummyCheck.validate_dsn(dsn, allowed_schemes=allowed_schemes)
    else:
        assert DummyCheck.validate_dsn(dsn, allowed_schemes=allowed_schemes) == expected


def _validate_dsn_arg(dsn: object, allowed_schemes: tuple[str, ...]) -> str:
    """Call validate_dsn with arbitrary dsn type for testing.

    Returns:
        Validated DSN string, or raise.
    """
    return DummyCheck.validate_dsn(cast("str", dsn), allowed_schemes=allowed_schemes)


def test_validate_dsn_rejects_non_str() -> None:
    """validate_dsn raises TypeError for non-str (e.g. None, bytes)."""
    with pytest.raises(TypeError, match="DSN must be str"):
        _validate_dsn_arg(None, ("redis",))
    with pytest.raises(TypeError, match="got 'bytes'"):
        _validate_dsn_arg(b"redis://host", ("redis",))


def _from_dsn_arg(
    check_class: type[HealthCheckDSN[HealthCheckResult, object]],
    dsn: object,
    name: str,
) -> HealthCheckDSN[HealthCheckResult, object]:
    """Call from_dsn with arbitrary dsn type for testing.

    Returns:
        HealthCheckDSN instance from check_class.
    """
    return check_class.from_dsn(cast("str", dsn), name=name)


@pytest.mark.parametrize(
    ("check_class", "default_name", "sample_dsn_bytes"),
    _DSN_CHECK_FROM_DSN_REJECTS_NON_STR,
)
def test_from_dsn_rejects_non_str(
    check_class: type[HealthCheckDSN[HealthCheckResult, object]],
    default_name: str,
    sample_dsn_bytes: bytes,
) -> None:
    """Test that from_dsn rejects non-str dsn."""
    with pytest.raises(TypeError, match="DSN must be str"):
        _from_dsn_arg(check_class, None, default_name)
    with pytest.raises(TypeError, match="got 'bytes'"):
        _from_dsn_arg(check_class, sample_dsn_bytes, default_name)


def test_validate_dsn_rejects_empty_allowed_schemes() -> None:
    """validate_dsn raises ValueError when allowed_schemes is empty."""
    with pytest.raises(ValueError, match="allowed_schemes cannot be empty"):
        DummyCheck.validate_dsn("redis://host", allowed_schemes=())


def test_from_dsn_not_implemented() -> None:
    """DummyCheck.from_dsn raises NotImplementedError (no parse_dsn implementation)."""
    with pytest.raises(NotImplementedError):
        DummyCheck.from_dsn("amqp://user:pass@host:10000/vhost")


# --- healthcheck_safe: exception re-raise vs wrap (CF-1) ---


class _CheckWithName:
    """Minimal check-like object with _name for healthcheck_safe tests."""

    _name = "SafeCheck"


@pytest.mark.asyncio
async def test_healthcheck_safe_cancelled_error_propagates() -> None:
    """healthcheck_safe re-raises CancelledError; never wraps in HealthCheckResult."""

    @healthcheck_safe()
    async def raises_cancelled(self: _CheckWithName) -> HealthCheckResult:
        await asyncio.sleep(0)
        raise asyncio.CancelledError

    obj = _CheckWithName()
    with pytest.raises(asyncio.CancelledError):
        await raises_cancelled(obj)


@pytest.mark.asyncio
async def test_healthcheck_safe_exception_returns_result() -> None:
    """healthcheck_safe wraps Exception in failed HealthCheckResult (existing behavior)."""
    msg = "expected failure"

    @healthcheck_safe()
    async def raises_value_error(self: _CheckWithName) -> HealthCheckResult:
        await asyncio.sleep(0)
        raise ValueError(msg)

    obj = _CheckWithName()
    result = await raises_value_error(obj)
    assert result.healthy is False
    assert result.name == "SafeCheck"
    assert result.error is not None
    assert "ValueError" in result.error.message


def test_result_on_error_with_exception() -> None:
    """result_on_error wraps provided exception in HealthCheckResult."""
    exc = ValueError("test error")
    result = result_on_error("TestCheck", exc)
    assert result.name == "TestCheck"
    assert result.healthy is False
    assert result.error is not None
    assert result.error.code == "CHECK_EXCEPTION"
    assert "test error" in result.error.message


def test_result_on_error_without_exception() -> None:
    """result_on_error captures current exception when exc is None."""

    def _raise_error() -> None:
        raise ValueError("captured error")  # noqa: TRY003, EM101

    result = HealthCheckResult(name="", healthy=True)
    try:
        _raise_error()
    except ValueError:
        result = result_on_error("TestCheck")
    assert result.name == "TestCheck"
    assert result.name == "TestCheck"
    assert result.healthy is False
    assert result.error is not None
    assert result.error.code == "CHECK_EXCEPTION"
    assert result.error.message == "Check failed with exception"
