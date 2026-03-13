"""Unit tests for UrlHealthCheck."""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from httpx import AsyncClient, Response

from fast_healthchecks.checks.url import UrlHealthCheck
from fast_healthchecks.errors import DEPENDENCY_UNHEALTHY
from fast_healthchecks.models import HealthCheckResult
from tests.utils import assert_check_init

pytestmark = pytest.mark.unit

EXPECTED_CLIENT_CREATIONS_AFTER_RECREATE = 2


@pytest.mark.parametrize(
    ("params", "expected", "exception"),
    [
        (
            {"url": "https://example.com/"},
            {
                "url": "https://example.com/",
                "username": None,
                "password": None,
                "verify_ssl": True,
                "follow_redirects": True,
                "timeout": 5.0,
                "name": "HTTP",
                "block_private_hosts": False,
            },
            None,
        ),
        (
            {
                "url": "https://example.com/",
                "username": "user",
                "password": "pass",
                "verify_ssl": False,
                "follow_redirects": False,
                "timeout": 1.5,
                "name": "HTTP Test",
            },
            {
                "url": "https://example.com/",
                "username": "user",
                "password": "pass",
                "verify_ssl": False,
                "follow_redirects": False,
                "timeout": 1.5,
                "name": "HTTP Test",
                "block_private_hosts": False,
            },
            None,
        ),
        (
            {"url": "https://example.com/", "name": "Custom"},
            {
                "url": "https://example.com/",
                "username": None,
                "password": None,
                "verify_ssl": True,
                "follow_redirects": True,
                "timeout": 5.0,
                "name": "Custom",
                "block_private_hosts": False,
            },
            None,
        ),
        (
            {"url": "file:///etc/passwd"},
            r"URL scheme must be one of",
            ValueError,
        ),
        (
            {"url": "http://localhost/", "block_private_hosts": True},
            r"must not be localhost",
            ValueError,
        ),
    ],
)
def test_init(params: dict[str, Any], expected: dict[str, Any] | str, exception: type[BaseException] | None) -> None:
    """UrlHealthCheck.__init__ and to_dict match expected or raise."""
    assert_check_init(lambda: UrlHealthCheck(**params), expected, exception)


@pytest.mark.asyncio
async def test_url_health_check_success() -> None:
    """Check returns healthy when HTTP request returns 2xx."""
    check = UrlHealthCheck(name="test_check", url="https://example.com/status/200")
    response = Response(status_code=200, content=b"", request=MagicMock(), history=[])
    async_client_mock = MagicMock(spec=AsyncClient)
    async_client_mock.get = AsyncMock(return_value=response)
    with patch("fast_healthchecks.checks.url.AsyncClient", return_value=async_client_mock):
        result = await check()
    assert result == HealthCheckResult(name="test_check", healthy=True)


@pytest.mark.asyncio
async def test_url_health_check_failure() -> None:
    """Check returns unhealthy when HTTP request returns non-2xx."""
    check = UrlHealthCheck(name="test_check", url="https://example.com/status/404")
    response = Response(status_code=404, content=b"", request=MagicMock(), history=[])
    async_client_mock = MagicMock(spec=AsyncClient)
    async_client_mock.get = AsyncMock(return_value=response)
    with patch("fast_healthchecks.checks.url.AsyncClient", return_value=async_client_mock):
        result = await check()
    assert result.healthy is False
    assert result.error is not None
    assert result.error.code == DEPENDENCY_UNHEALTHY
    assert "404" in result.error.message


@pytest.mark.asyncio
async def test_url_health_check_with_basic_auth_success() -> None:
    """Check with Basic Auth succeeds when credentials are accepted."""
    check = UrlHealthCheck(
        name="test_check",
        url="https://example.com/basic-auth",
        username="user",
        password="passwd",
    )
    response = Response(status_code=200, content=b"", request=MagicMock(), history=[])
    async_client_mock = MagicMock(spec=AsyncClient)
    async_client_mock.get = AsyncMock(return_value=response)
    with patch("fast_healthchecks.checks.url.AsyncClient", return_value=async_client_mock):
        result = await check()
    assert result == HealthCheckResult(name="test_check", healthy=True)


@pytest.mark.asyncio
async def test_url_health_check_with_basic_auth_failure() -> None:
    """Check with wrong credentials returns unhealthy."""
    check = UrlHealthCheck(
        name="test_check",
        url="https://example.com/basic-auth",
        username="user",
        password="wrong_passwd",
    )
    response = Response(status_code=401, content=b"", request=MagicMock(), history=[])
    async_client_mock = MagicMock(spec=AsyncClient)
    async_client_mock.get = AsyncMock(return_value=response)
    with patch("fast_healthchecks.checks.url.AsyncClient", return_value=async_client_mock):
        result = await check()
    assert result.healthy is False
    assert result.error is not None
    assert "401" in result.error.message


@pytest.mark.asyncio
async def test_url_health_check_with_timeout() -> None:
    """Check respects timeout and returns unhealthy on timeout."""
    check = UrlHealthCheck(name="test_check", url="https://example.com/", timeout=0.1)
    async_client_mock = MagicMock(spec=AsyncClient)
    async_client_mock.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
    with patch("fast_healthchecks.checks.url.AsyncClient", return_value=async_client_mock):
        result = await check()
    assert result.healthy is False
    assert result.error is not None
    assert "timed out" in result.error.message


@pytest.mark.asyncio
async def test_AsyncClient_args_kwargs() -> None:
    """Constructor args/kwargs are passed through to httpx AsyncClient."""
    health_check = UrlHealthCheck(
        name="Test",
        url="https://httpbingo.org/status/200",
        username="user",
        password="passwd",
        follow_redirects=False,
        timeout=1.0,
    )
    response = Response(
        status_code=200,
        content=b"",
        request=MagicMock(),
        history=[],
    )
    async_client_mock = MagicMock(spec=AsyncClient)
    async_client_mock.get = AsyncMock(side_effect=[response])
    with patch("fast_healthchecks.checks.url.AsyncClient", return_value=async_client_mock) as patched_async_client:
        result = await health_check()
        assert result == HealthCheckResult(name="Test", healthy=True)
        call_kw = patched_async_client.call_args[1]
        assert call_kw["timeout"] == pytest.approx(1.0)
        assert call_kw["follow_redirects"] is False
        assert call_kw["auth"] is not None
        assert call_kw["transport"] is not None
        async_client_mock.get.assert_called_once_with("https://httpbingo.org/status/200")


@pytest.mark.asyncio
async def test_AsyncClient_reused_between_calls() -> None:
    """Same AsyncClient instance is reused across __call__ invocations."""
    health_check = UrlHealthCheck(name="Test", url="https://httpbingo.org/status/200")
    response = Response(status_code=200, content=b"", request=MagicMock(), history=[])
    async_client_mock = MagicMock(spec=AsyncClient)
    async_client_mock.get = AsyncMock(side_effect=[response, response])
    with patch("fast_healthchecks.checks.url.AsyncClient", return_value=async_client_mock) as patched_async_client:
        await health_check()
        await health_check()
        call_kw = patched_async_client.call_args[1]
        assert call_kw["timeout"] == pytest.approx(5.0)  # default timeout
        assert call_kw["follow_redirects"] is True
        assert call_kw["auth"] is None
        assert call_kw["transport"] is not None


@pytest.mark.asyncio
async def test_aclose_clears_client() -> None:
    """aclose() closes and clears cached client."""
    health_check = UrlHealthCheck(name="Test", url="https://example.com/")
    response = Response(status_code=200, content=b"", request=MagicMock(), history=[])
    async_client_mock = MagicMock(spec=AsyncClient)
    async_client_mock.get = AsyncMock(return_value=response)
    async_client_mock.aclose = AsyncMock()
    with patch("fast_healthchecks.checks.url.AsyncClient", return_value=async_client_mock) as factory:
        await health_check()
        assert health_check._client is not None
        await health_check.aclose()
        assert health_check._client is None
        assert health_check._client_loop is None
        await health_check()
        assert factory.call_count == EXPECTED_CLIENT_CREATIONS_AFTER_RECREATE


@pytest.mark.asyncio
async def test_aclose_idempotent_when_no_client() -> None:
    """aclose() when no client is safe and idempotent."""
    health_check = UrlHealthCheck(name="Test", url="https://example.com/")
    await health_check.aclose()
    assert health_check._client is None


@pytest.mark.asyncio
async def test_loop_invalidation_recreates_client() -> None:
    """Client from different event loop is recreated on next __call__."""
    health_check = UrlHealthCheck(name="Test", url="https://example.com/")
    real_loop = asyncio.get_running_loop()
    other_loop = object()
    response = Response(status_code=200, content=b"", request=MagicMock(), history=[])
    async_client_mock = MagicMock(spec=AsyncClient)
    async_client_mock.get = AsyncMock(return_value=response)
    async_client_mock.aclose = AsyncMock()
    with (
        patch("fast_healthchecks.checks.url.AsyncClient", return_value=async_client_mock) as factory,
        patch(
            "fast_healthchecks.checks._base.asyncio.get_running_loop",
            side_effect=[real_loop, real_loop, other_loop, other_loop],
        ),
    ):
        await health_check()
        await health_check()
        assert factory.call_count == EXPECTED_CLIENT_CREATIONS_AFTER_RECREATE


def test_to_dict() -> None:
    """to_dict returns expected keys; secrets redacted when requested."""
    check = UrlHealthCheck(
        url="https://example.com/",
        username="user",
        password="pass",
        verify_ssl=False,
        follow_redirects=False,
        timeout=1.5,
        name="HTTP Test",
    )
    assert check.to_dict() == {
        "url": "https://example.com/",
        "username": "user",
        "password": "pass",
        "verify_ssl": False,
        "follow_redirects": False,
        "timeout": 1.5,
        "name": "HTTP Test",
        "block_private_hosts": False,
    }


def test_url_health_check_rejects_file_scheme() -> None:
    """UrlHealthCheck rejects file:// scheme (validate_url_ssrf)."""
    with pytest.raises(ValueError, match=r"URL scheme must be one of"):
        UrlHealthCheck(url="file:///etc/passwd")


def test_url_health_check_block_private_rejects_localhost() -> None:
    """With block_private_hosts=True, localhost host raises ValueError."""
    with pytest.raises(ValueError, match=r"must not be localhost"):
        UrlHealthCheck(url="http://localhost/", block_private_hosts=True)


def test_url_health_check_block_private_allows_localhost_by_default() -> None:
    """With block_private_hosts=False (default), localhost is allowed."""
    check = UrlHealthCheck(url="http://localhost:8080/")
    assert check._block_private_hosts is False


def test_url_health_check_properties_auth_and_transport() -> None:
    """_auth and _transport properties return expected values."""
    check_with_auth = UrlHealthCheck(
        url="https://example.com/",
        username="u",
        password="p",
    )
    assert check_with_auth._auth is not None
    assert check_with_auth._transport is not None
    check_no_auth = UrlHealthCheck(url="https://example.com/")
    assert check_no_auth._auth is None
    assert check_no_auth._transport is not None


@pytest.mark.asyncio
async def test_url_check_with_block_private_hosts_calls_validate_async() -> None:
    """When block_private_hosts=True, __call__ runs validate_host_ssrf_async before request."""
    check = UrlHealthCheck(
        url="https://example.com/",
        block_private_hosts=True,
        name="Test",
    )
    response = Response(status_code=200, content=b"", request=MagicMock(), history=[])
    async_client_mock = MagicMock(spec=AsyncClient)
    async_client_mock.get = AsyncMock(return_value=response)
    with (
        patch("fast_healthchecks.checks.url.validate_host_ssrf_async", new_callable=AsyncMock) as mock_validate,
        patch("fast_healthchecks.checks.url.AsyncClient", return_value=async_client_mock),
    ):
        result = await check()
        assert result.healthy is True
        mock_validate.assert_called_once_with("example.com")


@pytest.mark.asyncio
async def test_get_client_with_no_running_loop() -> None:
    """_ensure_client works when get_running_loop raises."""
    health_check = UrlHealthCheck(name="Test", url="https://example.com/")
    response = Response(status_code=200, content=b"", request=MagicMock(), history=[])
    async_client_mock = MagicMock(spec=AsyncClient)
    async_client_mock.get = AsyncMock(return_value=response)
    with (
        patch("fast_healthchecks.checks._base.asyncio.get_running_loop", side_effect=RuntimeError),
        patch("fast_healthchecks.checks.url.AsyncClient", return_value=async_client_mock) as factory,
    ):
        result = await health_check()
        assert result.healthy is True
        factory.assert_called_once()
        assert health_check._client_loop is None
