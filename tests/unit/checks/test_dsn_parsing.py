"""Unit tests for checks/dsn_parsing.py."""

from urllib.parse import urlsplit

import pytest

from fast_healthchecks.checks.dsn_parsing import (
    VALID_SSLMODES,
    KafkaParseDsnResult,
    MongoParseDsnResult,
    OpenSearchParseDsnResult,
    ParsedUrl,
    PostgresParseDsnResult,
    RabbitMQParseDsnResult,
)

pytestmark = pytest.mark.unit


def test_valid_sslmodes() -> None:
    """VALID_SSLMODES contains expected PostgreSQL sslmode values."""
    assert (
        frozenset(
            {"disable", "allow", "prefer", "require", "verify-ca", "verify-full"},
        )
        == VALID_SSLMODES
    )


def test_parsed_url_type_alias() -> None:
    """ParsedUrl type alias accepts ParseResult and SplitResult."""
    result = urlsplit("postgresql://localhost/db")
    assert isinstance(result, ParsedUrl)


def test_typed_dict_structures() -> None:
    """Verify TypedDict shapes are usable."""
    kafka: KafkaParseDsnResult = {
        "bootstrap_servers": "localhost:9092",
        "sasl_plain_username": None,
        "sasl_plain_password": None,
        "security_protocol": "PLAINTEXT",
    }
    assert kafka["bootstrap_servers"] == "localhost:9092"

    mongo: MongoParseDsnResult = {
        "parse_result": urlsplit("mongodb://localhost"),
        "authSource": "admin",
    }
    assert mongo["authSource"] == "admin"

    opensearch: OpenSearchParseDsnResult = {"hosts": ["localhost:9200"], "http_auth": None, "use_ssl": False}
    assert opensearch["hosts"] == ["localhost:9200"]

    rabbitmq: RabbitMQParseDsnResult = {"parse_result": urlsplit("amqp://localhost")}
    assert "parse_result" in rabbitmq

    postgres: PostgresParseDsnResult = {
        "parse_result": urlsplit("postgresql://localhost"),
        "sslmode": "disable",
        "sslcert": None,
        "sslkey": None,
        "sslrootcert": None,
        "sslctx": None,
        "direct_tls": False,
    }
    assert postgres["sslmode"] == "disable"
