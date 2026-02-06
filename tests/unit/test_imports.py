import pytest

pytestmark = pytest.mark.imports


def test_import_error_PostgreSQLAsyncPGHealthCheck() -> None:
    with pytest.raises(
        ImportError,
        match=r"asyncpg is not installed. Install it with `pip install fast-healthchecks\[asyncpg\]`.",
    ):
        from fast_healthchecks.checks.postgresql.asyncpg import PostgreSQLAsyncPGHealthCheck  # noqa: F401, PLC0415


def test_import_error_PostgreSQLPsycopgHealthCheck() -> None:
    with pytest.raises(
        ImportError,
        match=r"psycopg is not installed. Install it with `pip install fast-healthchecks\[psycopg\]`.",
    ):
        from fast_healthchecks.checks.postgresql.psycopg import PostgreSQLPsycopgHealthCheck  # noqa: F401, PLC0415


def test_import_error_KafkaHealthCheck() -> None:
    with pytest.raises(
        ImportError,
        match=r"aiokafka is not installed. Install it with `pip install fast-healthchecks\[aiokafka\]`.",
    ):
        from fast_healthchecks.checks.kafka import KafkaHealthCheck  # noqa: F401, PLC0415


def test_import_error_MongoHealthCheck() -> None:
    with pytest.raises(
        ImportError,
        match=r"motor is not installed. Install it with `pip install fast-healthchecks\[motor\]`.",
    ):
        from fast_healthchecks.checks.mongo import MongoHealthCheck  # noqa: F401, PLC0415


def test_import_error_OpenSearchHealthCheck() -> None:
    with pytest.raises(
        ImportError,
        match=r"opensearch-py is not installed. Install it with `pip install fast-healthchecks\[opensearch\]`.",
    ):
        from fast_healthchecks.checks.opensearch import OpenSearchHealthCheck  # noqa: F401, PLC0415


def test_import_error_RabbitMQHealthCheck() -> None:
    with pytest.raises(
        ImportError,
        match=r"aio-pika is not installed. Install it with `pip install fast-healthchecks\[aio-pika\]`.",
    ):
        from fast_healthchecks.checks.rabbitmq import RabbitMQHealthCheck  # noqa: F401, PLC0415


def test_import_error_RedisHealthCheck() -> None:
    with pytest.raises(
        ImportError,
        match=r"redis is not installed. Install it with `pip install fast-healthchecks\[redis\]`.",
    ):
        from fast_healthchecks.checks.redis import RedisHealthCheck  # noqa: F401, PLC0415


def test_import_error_UrlHealthCheck() -> None:
    with pytest.raises(
        ImportError,
        match=r"httpx is not installed. Install it with `pip install fast-healthchecks\[httpx\]`.",
    ):
        from fast_healthchecks.checks.url import UrlHealthCheck  # noqa: F401, PLC0415
