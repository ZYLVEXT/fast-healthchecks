import pytest

from fast_healthchecks.utils import parse_query_string

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("", {}),
        ("sslmode=disable", {"sslmode": "disable"}),
        ("sslcert=%2Ftmp%2Fclient.crt", {"sslcert": "/tmp/client.crt"}),
        ("key=value=value2", {"key": "value=value2"}),
        ("a=1&b=2", {"a": "1", "b": "2"}),
        ("a=1&b", {"a": "1", "b": ""}),
    ],
)
def test_parse_query_string(query: str, expected: dict[str, str]) -> None:
    assert parse_query_string(query) == expected
