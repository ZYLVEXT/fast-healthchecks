"""Cross-check DSN security contract.

Every ``from_dsn`` implementation must map a secure scheme to a verifying
TLS configuration without extra kwargs, and honor an explicit operator
opt-out. A new backend that silently defaults to unverified TLS fails here.
"""

from collections.abc import Callable
from typing import Any

import pytest

from fast_healthchecks.checks.kafka import KafkaHealthCheck
from fast_healthchecks.checks.mongo import MongoHealthCheck
from fast_healthchecks.checks.opensearch import OpenSearchHealthCheck
from fast_healthchecks.checks.rabbitmq import RabbitMQHealthCheck
from fast_healthchecks.checks.redis import RedisHealthCheck

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("factory", "get_actual", "expected"),
    [
        pytest.param(
            lambda: OpenSearchHealthCheck.from_dsn("https://search.example:9200"),
            lambda check: check._config.verify_certs,
            True,
            id="opensearch-https-verifies-by-default",
        ),
        pytest.param(
            lambda: OpenSearchHealthCheck.from_dsn("https://search.example:9200", verify_certs=False),
            lambda check: check._config.verify_certs,
            False,
            id="opensearch-explicit-opt-out-honored",
        ),
        pytest.param(
            lambda: RedisHealthCheck.from_dsn("rediss://cache.example:6380/0"),
            lambda check: check._config.ssl,
            True,
            id="redis-rediss-enables-tls",
        ),
        pytest.param(
            lambda: RabbitMQHealthCheck.from_dsn("amqps://user:pw@mq.example/"),
            lambda check: check._config.secure,
            True,
            id="rabbitmq-amqps-enables-tls",
        ),
        pytest.param(
            lambda: KafkaHealthCheck.from_dsn("kafkas://broker.example:9092"),
            lambda check: check._config.security_protocol,
            "SSL",
            id="kafka-kafkas-enables-tls",
        ),
        pytest.param(
            lambda: MongoHealthCheck.from_dsn("mongodb+srv://cluster.example/db"),
            lambda check: check._config.tls,
            True,
            id="mongo-srv-enables-tls",
        ),
        pytest.param(
            lambda: MongoHealthCheck.from_dsn("mongodb+srv://cluster.example/db?tls=false"),
            lambda check: check._config.tls,
            False,
            id="mongo-explicit-opt-out-honored",
        ),
    ],
)
def test_secure_scheme_implies_verification(
    factory: Callable[[], Any],
    get_actual: Callable[[Any], object],
    expected: object,
) -> None:
    """A secure scheme configures TLS verification without extra kwargs."""
    assert get_actual(factory()) == expected
