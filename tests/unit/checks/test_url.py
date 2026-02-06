import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient, Response

from fast_healthchecks.checks.url import UrlHealthCheck
from fast_healthchecks.models import HealthCheckResult

pytestmark = pytest.mark.unit

EXPECTED_CLIENT_CREATIONS_AFTER_RECREATE = 2


@pytest.mark.vcr
@pytest.mark.asyncio
async def test_url_health_check_success() -> None:
    check = UrlHealthCheck(
        name="test_check",
        url="https://httpbingo.org/status/200",
    )
    result = await check()
    assert result == HealthCheckResult(name="test_check", healthy=True)


@pytest.mark.vcr
@pytest.mark.asyncio
async def test_url_health_check_failure() -> None:
    check = UrlHealthCheck(
        name="test_check",
        url="https://httpbingo.org/status/500",
    )
    result = await check()
    assert result.healthy is False
    assert "500 Internal Server Error" in str(result.error_details)


@pytest.mark.vcr
@pytest.mark.asyncio
async def test_url_health_check_with_basic_auth_success() -> None:
    check = UrlHealthCheck(
        name="test_check",
        url="https://httpbingo.org/basic-auth/user/passwd",
        username="user",
        password="passwd",
    )
    result = await check()
    assert result == HealthCheckResult(name="test_check", healthy=True)


@pytest.mark.vcr
@pytest.mark.asyncio
async def test_url_health_check_with_basic_auth_failure() -> None:
    check = UrlHealthCheck(
        name="test_check",
        url="https://httpbingo.org/basic-auth/user/passwd",
        username="user",
        password="wrong_passwd",
    )
    result = await check()
    assert result.healthy is False
    assert "401 Unauthorized" in str(result.error_details)


@pytest.mark.vcr
@pytest.mark.asyncio
async def test_url_health_check_with_timeout() -> None:
    check = UrlHealthCheck(
        name="test_check",
        url="https://httpbingo.org/delay/5",
        timeout=0.1,
    )
    result = await check()
    assert result.healthy is False
    error_details = str(result.error_details)
    assert any(fragment in error_details for fragment in ("Timeout", "ConnectError", "nodename nor servname"))


@pytest.mark.vcr
@pytest.mark.asyncio
async def test_AsyncClient_args_kwargs() -> None:
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
        patched_async_client.assert_called_once_with(
            auth=health_check._auth,
            timeout=1.0,
            transport=health_check._transport,
            follow_redirects=False,
        )
        async_client_mock.get.assert_called_once_with("https://httpbingo.org/status/200")


@pytest.mark.asyncio
async def test_AsyncClient_reused_between_calls() -> None:
    health_check = UrlHealthCheck(name="Test", url="https://httpbingo.org/status/200")
    response = Response(status_code=200, content=b"", request=MagicMock(), history=[])
    async_client_mock = MagicMock(spec=AsyncClient)
    async_client_mock.get = AsyncMock(side_effect=[response, response])
    with patch("fast_healthchecks.checks.url.AsyncClient", return_value=async_client_mock) as patched_async_client:
        await health_check()
        await health_check()
        patched_async_client.assert_called_once_with(
            auth=health_check._auth,
            timeout=5.0,
            transport=health_check._transport,
            follow_redirects=True,
        )


@pytest.mark.asyncio
async def test_aclose_clears_client() -> None:
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
    health_check = UrlHealthCheck(name="Test", url="https://example.com/")
    await health_check.aclose()
    assert health_check._client is None


@pytest.mark.asyncio
async def test_loop_invalidation_recreates_client() -> None:
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
            "fast_healthchecks.checks.url.asyncio.get_running_loop",
            side_effect=[real_loop, real_loop, other_loop, other_loop],
        ),
    ):
        await health_check()
        await health_check()
        assert factory.call_count == EXPECTED_CLIENT_CREATIONS_AFTER_RECREATE


def test_to_dict() -> None:
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
    }


@pytest.mark.asyncio
async def test_get_client_with_no_running_loop() -> None:
    health_check = UrlHealthCheck(name="Test", url="https://example.com/")
    response = Response(status_code=200, content=b"", request=MagicMock(), history=[])
    async_client_mock = MagicMock(spec=AsyncClient)
    async_client_mock.get = AsyncMock(return_value=response)
    with (
        patch("fast_healthchecks.checks.url.asyncio.get_running_loop", side_effect=RuntimeError),
        patch("fast_healthchecks.checks.url.AsyncClient", return_value=async_client_mock) as factory,
    ):
        result = await health_check()
        assert result.healthy is True
        factory.assert_called_once()
        assert health_check._client_loop is None
