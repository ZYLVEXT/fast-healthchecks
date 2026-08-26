"""Cross-check behavior contract for all built-in health checks.

Every check must expose its public ``name`` and keep configured secrets out
of ``to_dict(redact_secrets=True)``. A new check type is added to the table
below; failing to redact or to expose ``name`` fails here.
"""

from collections.abc import Callable, Iterator
from typing import Any

import pytest

from fast_healthchecks.checks.function import FunctionHealthCheck
from fast_healthchecks.checks.kafka import KafkaHealthCheck
from fast_healthchecks.checks.mongo import MongoHealthCheck
from fast_healthchecks.checks.opensearch import OpenSearchHealthCheck
from fast_healthchecks.checks.postgresql.asyncpg import PostgreSQLAsyncPGHealthCheck
from fast_healthchecks.checks.postgresql.psycopg import PostgreSQLPsycopgHealthCheck
from fast_healthchecks.checks.rabbitmq import RabbitMQHealthCheck
from fast_healthchecks.checks.redis import RedisHealthCheck
from fast_healthchecks.checks.url import UrlHealthCheck

pytestmark = pytest.mark.unit

SECRET = "s3cr3t-value"
CHECK_NAME = "Contract"

CHECK_FACTORIES: list[Any] = [
    pytest.param(lambda: FunctionHealthCheck(func=lambda: True, name=CHECK_NAME), False, id="function"),
    pytest.param(lambda: RedisHealthCheck(host="db.example", password=SECRET, name=CHECK_NAME), True, id="redis"),
    pytest.param(
        lambda: RabbitMQHealthCheck(host="mq.example", user="svc", password=SECRET, name=CHECK_NAME),
        True,
        id="rabbitmq",
    ),
    pytest.param(
        lambda: KafkaHealthCheck(bootstrap_servers="k.example:9092", sasl_plain_password=SECRET, name=CHECK_NAME),
        True,
        id="kafka",
    ),
    pytest.param(
        lambda: MongoHealthCheck(hosts="db.example", user="svc", password=SECRET, name=CHECK_NAME),
        True,
        id="mongo",
    ),
    pytest.param(
        lambda: OpenSearchHealthCheck(hosts=["s.example:9200"], http_auth=("svc", SECRET), name=CHECK_NAME),
        True,
        id="opensearch",
    ),
    pytest.param(
        lambda: UrlHealthCheck(url="https://x.example/", username="svc", password=SECRET, name=CHECK_NAME),
        True,
        id="url",
    ),
    pytest.param(
        lambda: PostgreSQLAsyncPGHealthCheck(host="db.example", user="svc", password=SECRET, name=CHECK_NAME),
        True,
        id="postgres-asyncpg",
    ),
    pytest.param(
        lambda: PostgreSQLPsycopgHealthCheck(host="db.example", user="svc", password=SECRET, name=CHECK_NAME),
        True,
        id="postgres-psycopg",
    ),
]


def _flat_values(obj: object) -> Iterator[object]:
    if isinstance(obj, dict):
        for value in obj.values():
            yield from _flat_values(value)
    elif isinstance(obj, (list, tuple, set)):
        for value in obj:
            yield from _flat_values(value)
    else:
        yield obj


@pytest.mark.parametrize(("factory", "has_secret"), CHECK_FACTORIES)
def test_check_exposes_public_name(factory: Callable[[], Any], *, has_secret: bool) -> None:
    """Every check exposes the configured name via the public property."""
    assert factory().name == CHECK_NAME


@pytest.mark.parametrize(("factory", "has_secret"), CHECK_FACTORIES)
def test_redacted_to_dict_never_leaks_secret(factory: Callable[[], Any], *, has_secret: bool) -> None:
    """to_dict(redact_secrets=True) contains no configured secret value."""
    data = factory().to_dict(redact_secrets=True)
    values = list(_flat_values(data))
    assert SECRET not in values
    if has_secret:
        assert "***" in values
