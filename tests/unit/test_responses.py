"""Tests for response mapping."""

from enum import IntEnum

import pytest

from fast_healthchecks.models import HealthCheckReport, HealthCheckResult
from fast_healthchecks.responses import ProbeAsgiResponse, map_report_to_asgi_http_response


class _StatusCode(IntEnum):
    OK = 200
    NO_CONTENT = 204
    SERVICE_UNAVAILABLE = 503


pytestmark = pytest.mark.unit


async def _handler_that_returns_none(_response: ProbeAsgiResponse) -> dict | None:  # noqa: RUF029
    """Handler that returns None to trigger no-content response.

    Returns:
        None to indicate no content.
    """
    return None


async def _healthy_handler(_response: ProbeAsgiResponse) -> dict:  # type: ignore[empty-body]
    """Handler that returns dict for healthy response.

    Returns:
        Dict with status: healthy.
    """


async def _unhealthy_handler(_response: ProbeAsgiResponse) -> dict:  # type: ignore[empty-body]
    """Handler that returns dict for unhealthy response.

    Returns:
        Dict with status: unhealthy.
    """


@pytest.mark.asyncio
async def test_map_report_to_asgi_http_response_handler_returns_none() -> None:
    """When handler returns None, response body is empty."""
    report = HealthCheckReport(
        results=[HealthCheckResult(name="test", healthy=True)],
    )
    body, headers, status = await map_report_to_asgi_http_response(
        report,
        debug=False,
        exclude_fields=set(),
        success_status=200,
        failure_status=503,
        success_handler=_handler_that_returns_none,
        failure_handler=_handler_that_returns_none,
    )
    assert body == b""
    assert headers is None
    assert status == _StatusCode.OK


@pytest.mark.asyncio
async def test_map_report_to_asgi_http_response_debug_unhealthy_includes_data() -> None:
    """When debug=True and unhealthy, full data is included."""
    report = HealthCheckReport(
        results=[HealthCheckResult(name="test", healthy=False, error=None)],
    )
    body, _headers, status = await map_report_to_asgi_http_response(
        report,
        debug=True,
        exclude_fields=set(),
        success_status=200,
        failure_status=503,
        success_handler=_healthy_handler,
        failure_handler=_unhealthy_handler,
    )
    assert b"test" in body
    assert status == _StatusCode.SERVICE_UNAVAILABLE


@pytest.mark.asyncio
async def test_map_report_to_asgi_http_response_no_content_status() -> None:
    """When status is NO_CONTENT (204), no body is returned regardless of handler."""
    report = HealthCheckReport(
        results=[HealthCheckResult(name="test", healthy=True)],
    )
    body, headers, status = await map_report_to_asgi_http_response(
        report,
        debug=False,
        exclude_fields=set(),
        success_status=204,
        failure_status=503,
        success_handler=_healthy_handler,
        failure_handler=_unhealthy_handler,
    )
    assert body == b""
    assert headers is None
    assert status == _StatusCode.NO_CONTENT
