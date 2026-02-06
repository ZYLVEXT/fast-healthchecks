import pytest

from fast_healthchecks import compat

pytestmark = pytest.mark.unit


def test_public_exports() -> None:
    assert "AmqpDsn" in compat.__all__
    assert "KafkaDsn" in compat.__all__
    assert "MongoDsn" in compat.__all__
    assert "PostgresDsn" in compat.__all__
    assert "RedisDsn" in compat.__all__
    assert "SupportedDsns" in compat.__all__


def test_dsn_aliases_are_string_type() -> None:
    assert compat.MongoDsn is str
    assert compat.AmqpDsn is str
    assert compat.KafkaDsn is str
    assert compat.PostgresDsn is str
    assert compat.RedisDsn is str
