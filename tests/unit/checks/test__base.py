import pytest

from fast_healthchecks.checks.types import HealthCheckDSN
from fast_healthchecks.models import HealthCheckResult

pytestmark = pytest.mark.unit


class DummyCheck(HealthCheckDSN[HealthCheckResult]):
    async def __call__(self) -> HealthCheckResult:
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
    if exception is not None:
        with pytest.raises(exception, match=expected):
            DummyCheck.validate_dsn(dsn, allowed_schemes=allowed_schemes)
    else:
        assert DummyCheck.validate_dsn(dsn, allowed_schemes=allowed_schemes) == expected


def test_validate_dsn_rejects_non_str() -> None:
    with pytest.raises(TypeError, match="DSN must be str"):
        DummyCheck.validate_dsn(None, allowed_schemes=("redis",))  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="got 'bytes'"):
        DummyCheck.validate_dsn(b"redis://host", allowed_schemes=("redis",))  # type: ignore[arg-type]


def test_validate_dsn_rejects_empty_allowed_schemes() -> None:
    with pytest.raises(ValueError, match="allowed_schemes cannot be empty"):
        DummyCheck.validate_dsn("redis://host", allowed_schemes=())


def test_from_dsn_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        DummyCheck.from_dsn("amqp://user:pass@host:10000/vhost")
