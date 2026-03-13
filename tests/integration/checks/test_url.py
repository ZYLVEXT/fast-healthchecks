"""Integration tests for UrlHealthCheck (HTTP endpoints)."""

import pytest

from fast_healthchecks.checks.url import UrlHealthCheck
from fast_healthchecks.models import HealthCheckResult

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_url_health_check_success(url_server_base: str) -> None:
    """URL check returns healthy when HTTP request returns 2xx."""
    check = UrlHealthCheck(
        name="test_check",
        url=f"{url_server_base}/status/200",
    )
    try:
        result = await check()
        assert result == HealthCheckResult(name="test_check", healthy=True)
    finally:
        await check.aclose()


@pytest.mark.asyncio
async def test_url_health_check_failure(url_server_base: str) -> None:
    """URL check returns unhealthy when HTTP request returns non-2xx."""
    check = UrlHealthCheck(
        name="test_check",
        url=f"{url_server_base}/status/500",
    )
    try:
        result = await check()
        assert result.healthy is False
        assert "500" in str(result.error_details)
    finally:
        await check.aclose()


@pytest.mark.asyncio
async def test_url_health_check_with_basic_auth_success(url_server_base: str) -> None:
    """URL check with Basic Auth succeeds when credentials accepted."""
    check = UrlHealthCheck(
        name="test_check",
        url=f"{url_server_base}/basic-auth/user/passwd",
        username="user",
        password="passwd",
    )
    try:
        result = await check()
        assert result == HealthCheckResult(name="test_check", healthy=True)
    finally:
        await check.aclose()


@pytest.mark.asyncio
async def test_url_health_check_with_basic_auth_failure(url_server_base: str) -> None:
    """URL check with wrong credentials returns unhealthy."""
    check = UrlHealthCheck(
        name="test_check",
        url=f"{url_server_base}/basic-auth/user/passwd",
        username="user",
        password="wrong_passwd",
    )
    try:
        result = await check()
        assert result.healthy is False
        assert "401" in str(result.error_details)
    finally:
        await check.aclose()


@pytest.mark.asyncio
async def test_url_health_check_with_timeout(url_server_base: str) -> None:
    """URL check respects timeout and returns unhealthy on timeout."""
    check = UrlHealthCheck(
        name="test_check",
        url=f"{url_server_base}/delay/5",
        timeout=1,
    )
    try:
        result = await check()
        assert result.healthy is False
        assert "Timeout" in str(result.error_details)
    finally:
        await check.aclose()
