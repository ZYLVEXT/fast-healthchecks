"""Shared integration-test assertions (e.g. assert_error_contains_any)."""


def assert_error_contains_any(error_details: str | None, expected_fragments: tuple[str, ...]) -> None:
    """Assert that error_details contains at least one of the expected substrings."""
    assert error_details is not None
    text = error_details.lower()
    assert any(fragment.lower() in text for fragment in expected_fragments)


DNS_ERROR_FRAGMENTS = (
    "nodename nor servname provided, or not known",
    "name or service not known",
    "getaddrinfo failed",
    "no address associated with hostname",
    "temporary failure in name resolution",  # Linux (glibc)
    "failed to resolve host",  # psycopg, asyncpg, etc. on Linux
    # opensearch-py can wrap DNS/unreachable host as ConnectionTimeout/TimeoutError
    "connectiontimeout",
    "timeouterror",
)


CONNECTION_REFUSED_FRAGMENTS = (
    "connect call failed",
    "connection refused",
    "connection failed",
    "multiple exceptions",
    "errno 61",
    "errno 111",
    # Windows
    "actively refused",
    "refused the network connection",
    # Timeout when connecting to wrong port (e.g. WSL/Docker)
    "timeout",
    "connection timeout",
)
