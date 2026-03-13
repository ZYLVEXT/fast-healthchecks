"""Tests for dsn module (NewTypes and SupportedDsns)."""

import pytest

from fast_healthchecks import dsn

pytestmark = pytest.mark.unit


def test_public_exports() -> None:
    """Dsn module exports all DSN NewTypes and SupportedDsns."""
    assert "AmqpDsn" in dsn.__all__
    assert "KafkaDsn" in dsn.__all__
    assert "MongoDsn" in dsn.__all__
    assert "OpenSearchDsn" in dsn.__all__
    assert "PostgresDsn" in dsn.__all__
    assert "RedisDsn" in dsn.__all__
    assert "SupportedDsns" in dsn.__all__


def test_dsn_types_accept_str_and_return_str() -> None:
    """DSN NewTypes accept a str and return str at runtime."""
    assert isinstance(dsn.MongoDsn("mongodb://localhost"), str)
    assert isinstance(dsn.AmqpDsn("amqp://localhost"), str)
    assert isinstance(dsn.KafkaDsn("kafka://localhost"), str)
    assert isinstance(dsn.OpenSearchDsn("https://localhost:9200"), str)
    assert isinstance(dsn.PostgresDsn("postgresql://localhost"), str)
    assert isinstance(dsn.RedisDsn("redis://localhost"), str)
