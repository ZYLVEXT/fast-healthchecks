def assert_error_contains_any(error_details: str | None, expected_fragments: tuple[str, ...]) -> None:
    assert error_details is not None
    text = error_details.lower()
    assert any(fragment.lower() in text for fragment in expected_fragments)


DNS_ERROR_FRAGMENTS = (
    "nodename nor servname provided, or not known",
    "name or service not known",
    "getaddrinfo failed",
    "no address associated with hostname",
)


CONNECTION_REFUSED_FRAGMENTS = (
    "connect call failed",
    "connection refused",
    "connection failed",
    "multiple exceptions",
    "errno 61",
    "errno 111",
)
