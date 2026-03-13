"""Unit tests for test helpers (assert_check_init, create_temp_files, redact, validate_url_ssrf)."""

import asyncio
import socket
from unittest.mock import AsyncMock, patch

import pytest

from fast_healthchecks.utils import (
    maybe_redact,
    parse_query_string,
    redact_secrets_in_dict,
    validate_host_ssrf_async,
    validate_url_ssrf,
)

pytestmark = pytest.mark.unit


def test_redact_secrets_in_dict() -> None:
    """redact_secrets_in_dict replaces known secret keys with placeholder."""
    data = {
        "host": "x",
        "password": "secret",
        "user": "u",
        "username": "admin",
        "sasl_plain_password": "pwd",
        "meta": {
            "token": "abc",
            "nested": {"password": "nested-secret"},
            "items": [{"user": "alice"}, {"safe": "ok"}],
        },
    }
    result = redact_secrets_in_dict(data)
    assert result["host"] == "x"
    assert result["user"] == "***"
    assert result["username"] == "***"
    assert result["password"] == "***"
    assert result["sasl_plain_password"] == "***"
    assert result["meta"]["token"] == "***"
    assert result["meta"]["nested"]["password"] == "***"
    assert result["meta"]["items"][0]["user"] == "***"
    assert result["meta"]["items"][1]["safe"] == "ok"


def test_redact_secrets_in_dict_with_set() -> None:
    """redact_secrets_in_dict handles set values recursively."""
    data = {
        "items": [{"password": "secret1"}, {"token": "secret2"}],
        "other": {1, 2, 3},
    }
    result = redact_secrets_in_dict(data)
    assert result["items"][0]["password"] == "***"
    assert result["items"][1]["token"] == "***"
    assert result["other"] == {1, 2, 3}


def test_maybe_redact_with_redaction() -> None:
    """maybe_redact with redact_secrets=True redacts secret keys."""
    data = {"user": "u", "password": "p"}
    result = maybe_redact(data, redact_secrets=True)
    assert result["user"] == "***"
    assert result["password"] == "***"


def test_maybe_redact_without_redaction() -> None:
    """maybe_redact with redact_secrets=False returns dict unchanged."""
    data = {"user": "u", "password": "p"}
    result = maybe_redact(data, redact_secrets=False)
    assert result == data


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("", {}),
        ("sslmode=disable", {"sslmode": "disable"}),
        ("sslcert=%2Ftmp%2Fclient.crt", {"sslcert": "/tmp/client.crt"}),
        ("key%20name=value", {"key name": "value"}),
        ("key=value=value2", {"key": "value=value2"}),
        ("a=1&b=2", {"a": "1", "b": "2"}),
        ("a=1&b", {"a": "1", "b": ""}),
    ],
)
def test_parse_query_string(query: str, expected: dict[str, str]) -> None:
    """parse_query_string parses key=value pairs and unquotes keys/values."""
    assert parse_query_string(query) == expected


def test_validate_url_ssrf_allows_http_https() -> None:
    """validate_url_ssrf allows http and https schemes by default."""
    validate_url_ssrf("https://example.com/")
    validate_url_ssrf("http://example.com/path")
    validate_url_ssrf("HTTPS://example.com/")


def test_validate_url_ssrf_rejects_bad_scheme() -> None:
    """validate_url_ssrf raises ValueError for disallowed scheme."""
    with pytest.raises(ValueError, match=r"URL scheme must be one of"):
        validate_url_ssrf("file:///etc/passwd")
    with pytest.raises(ValueError, match=r"URL scheme must be one of"):
        validate_url_ssrf("gopher://localhost/")


def test_validate_url_ssrf_block_private_rejects_localhost() -> None:
    """validate_url_ssrf with block_private_hosts rejects localhost host."""
    with pytest.raises(ValueError, match=r"must not be localhost"):
        validate_url_ssrf("http://localhost/", block_private_hosts=True)
    with pytest.raises(ValueError, match=r"must not be localhost"):
        validate_url_ssrf("http://localhost:8080/", block_private_hosts=True)


def test_validate_url_ssrf_block_private_rejects_loopback_ip() -> None:
    """validate_url_ssrf with block_private_hosts rejects loopback IP."""
    with pytest.raises(ValueError, match=r"must not be loopback"):
        validate_url_ssrf("http://127.0.0.1/", block_private_hosts=True)
    with pytest.raises(ValueError, match=r"must not be loopback"):
        validate_url_ssrf("http://[::1]/", block_private_hosts=True)


def test_validate_url_ssrf_block_private_rejects_private_ip() -> None:
    """validate_url_ssrf with block_private_hosts rejects private IP."""
    with pytest.raises(ValueError, match=r"must not be loopback"):
        validate_url_ssrf("http://192.168.1.1/", block_private_hosts=True)
    with pytest.raises(ValueError, match=r"must not be loopback"):
        validate_url_ssrf("http://10.0.0.1/", block_private_hosts=True)


def test_validate_url_ssrf_block_private_allows_public() -> None:
    """validate_url_ssrf with block_private_hosts allows public host (e.g. example.com)."""
    validate_url_ssrf("https://example.com/", block_private_hosts=True)


def test_validate_url_ssrf_block_private_empty_host_skips_check() -> None:
    """validate_url_ssrf with empty host does not apply block_private check."""
    validate_url_ssrf("https:///", block_private_hosts=True)


@pytest.mark.asyncio
async def test_validate_host_ssrf_async_rejects_localhost() -> None:
    """validate_host_ssrf_async rejects localhost (resolves to 127.0.0.1)."""
    with pytest.raises(ValueError, match=r"must not be localhost"):
        await validate_host_ssrf_async("localhost")


@pytest.mark.asyncio
async def test_validate_host_ssrf_async_rejects_loopback_ip() -> None:
    """validate_host_ssrf_async rejects IP that resolves to loopback (e.g. via /etc/hosts)."""
    with pytest.raises(ValueError, match=r"must not resolve to loopback"):
        await validate_host_ssrf_async("127.0.0.1")


@pytest.mark.asyncio
async def test_validate_host_ssrf_async_empty_host_ok() -> None:
    """validate_host_ssrf_async does nothing for empty host."""
    await validate_host_ssrf_async("")


@pytest.mark.asyncio
async def test_validate_host_ssrf_async_oserror_returns_early() -> None:
    """validate_host_ssrf_async returns without raising when getaddrinfo raises OSError."""
    loop = asyncio.get_running_loop()
    with patch.object(loop, "run_in_executor", AsyncMock(side_effect=OSError("resolve failed"))):
        await validate_host_ssrf_async("unknown.invalid.example")


@pytest.mark.asyncio
async def test_validate_host_ssrf_async_skips_empty_sockaddr() -> None:
    """validate_host_ssrf_async skips entries with empty sockaddr."""

    # getaddrinfo returns (family, type, proto, canonname, sockaddr); empty sockaddr is skipped
    def fake_getaddrinfo(host: str, port: str | int | None) -> list:
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ()),
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 80)),
        ]

    loop = asyncio.get_running_loop()
    with patch.object(loop, "run_in_executor", AsyncMock(return_value=fake_getaddrinfo("example.com", None))):
        # Second entry is public IP so no raise; first has empty sockaddr and is skipped
        await validate_host_ssrf_async("example.com")


@pytest.mark.asyncio
async def test_validate_host_ssrf_async_skips_falsy_ip_str() -> None:
    """validate_host_ssrf_async skips entries where sockaddr yields a falsy ip string."""

    # Covers "if not ip_str: continue" (e.g. sockaddr is ("", port))
    def fake_getaddrinfo(host: str, port: str | int | None) -> list:
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("", 80)),
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 443)),
        ]

    loop = asyncio.get_running_loop()
    with patch.object(loop, "run_in_executor", AsyncMock(return_value=fake_getaddrinfo("example.com", None))):
        await validate_host_ssrf_async("example.com")


@pytest.mark.asyncio
async def test_validate_host_ssrf_async_skips_invalid_ip_valueerror() -> None:
    """validate_host_ssrf_async skips addresses that raise ValueError in ip_address."""

    def fake_getaddrinfo(host: str, port: str | int | None) -> list:
        # First entry has non-parseable "address"; second is valid public IP
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("not-an-ip", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 80)),
        ]

    loop = asyncio.get_running_loop()
    with patch.object(loop, "run_in_executor", AsyncMock(return_value=fake_getaddrinfo("example.com", None))):
        await validate_host_ssrf_async("example.com")


@pytest.mark.asyncio
async def test_validate_host_ssrf_async_rejects_resolved_private_ip() -> None:
    """validate_host_ssrf_async raises when getaddrinfo returns a private IP."""

    # Resolved private IP triggers the loop body and ValueError (covers try/ip_address/raise path)
    def fake_getaddrinfo(host: str, port: str | int | None) -> list:
        return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("10.0.0.1", 443))]

    loop = asyncio.get_running_loop()
    with (
        patch.object(loop, "run_in_executor", AsyncMock(return_value=fake_getaddrinfo("internal.example", None))),
        pytest.raises(ValueError, match=r"must not resolve to loopback or private"),
    ):
        await validate_host_ssrf_async("internal.example")


@pytest.mark.asyncio
async def test_validate_host_ssrf_async_sockaddr_with_host_attr() -> None:
    """validate_host_ssrf_async uses getattr(sockaddr, 'host', None) for non-tuple sockaddr."""

    # Some getaddrinfo implementations return objects with .host; cover that branch and try block
    class SockaddrHost:
        host = "192.168.1.1"

    def fake_getaddrinfo(host: str, port: str | int | None) -> list:
        return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", SockaddrHost())]

    loop = asyncio.get_running_loop()
    with (
        patch.object(loop, "run_in_executor", AsyncMock(return_value=fake_getaddrinfo("lan.example", None))),
        pytest.raises(ValueError, match=r"must not resolve to loopback or private"),
    ):
        await validate_host_ssrf_async("lan.example")
