"""Integration tests for FastStream health() with real backends."""

import asyncio
import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from http import HTTPStatus
from typing import cast

import httpx
import pytest
from faststream import TestApp
from faststream.asgi import AsgiFastStream
from faststream.kafka import KafkaBroker, TestKafkaBroker

from examples.faststream_example.main import app_custom, app_fail, app_integration
from examples.faststream_example.main import broker as example_broker
from fast_healthchecks.checks.function import FunctionHealthCheck
from fast_healthchecks.execution import ProbeRunner, RunPolicy
from fast_healthchecks.integrations.base import Probe, build_probe_route_options
from fast_healthchecks.integrations.faststream import health
from fast_healthchecks.models import HealthCheckResult

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@asynccontextmanager
async def _faststream_client(app: AsgiFastStream) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Run the app and its test broker in the current event loop.

    Yields:
        httpx.AsyncClient: Client bound to the ASGI app.
    """
    kafka_broker = cast("KafkaBroker", app.broker)
    async with (
        TestKafkaBroker(kafka_broker, connect_only=True),
        TestApp(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client,
    ):
        yield client


async def test_liveness_probe() -> None:
    """Liveness probe returns success when checks pass."""
    async with _faststream_client(app_integration) as client:
        response = await client.get("/health/liveness")
        assert response.status_code == HTTPStatus.NO_CONTENT
        assert response.content == b""


async def test_readiness_probe() -> None:
    """Readiness probe returns success when all checks pass."""
    async with _faststream_client(app_integration) as client:
        response = await client.get("/health/readiness")
        assert response.status_code == HTTPStatus.NO_CONTENT, (
            f"readiness returned {response.status_code}; body={response.text!r}"
        )
        assert response.content == b""


async def test_startup_probe() -> None:
    """Startup probe returns success when checks pass."""
    async with _faststream_client(app_integration) as client:
        response = await client.get("/health/startup")
        assert response.status_code == HTTPStatus.NO_CONTENT
        assert response.content == b""


async def test_readiness_probe_fail() -> None:
    """Readiness probe returns failure when a check fails."""
    async with _faststream_client(app_fail) as client:
        response = await client.get("/health/readiness")
        assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
        data = response.json()
        # With debug=True the body is the full report (results, allow_partial_failure); otherwise minimal {"status": "unhealthy"}
        assert data.get("status") == "unhealthy" or (
            "results" in data and any(not r.get("healthy", True) for r in data["results"])
        )


async def test_custom_handler() -> None:
    """Custom handler is used for probe response."""
    async with _faststream_client(app_custom) as client:
        response = await client.get("/custom_health/readiness")
    assert response.status_code == HTTPStatus.OK
    assert response.content == json.dumps(
        {"results": [{"name": "Async dummy", "healthy": True, "error": None}], "allow_partial_failure": False},
        ensure_ascii=False,
        allow_nan=False,
        indent=None,
        separators=(",", ":"),
    ).encode("utf-8")


async def test_reporting_timeout_returns_failed_report_with_injected_runner() -> None:
    """Reporting mode timeout returns unhealthy HTTP response (no exception)."""

    async def _slow_check() -> HealthCheckResult:
        await asyncio.sleep(0.05)
        return HealthCheckResult(name="slow", healthy=True)

    app = AsgiFastStream(
        example_broker,
        asgi_routes=list(
            health(
                Probe(name="readiness", checks=[_slow_check]),
                options=build_probe_route_options(prefix="/health"),
                runner=ProbeRunner(policy=RunPolicy(mode="reporting", probe_timeout_ms=1)),
            ),
        ),
    )

    async with _faststream_client(app) as client:
        response = await client.get("/health/readiness")

    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert response.json() == {"status": "unhealthy"}


async def test_strict_timeout_returns_http_500_with_injected_runner() -> None:
    """Strict mode timeout is surfaced as HTTP 500 in integration endpoint."""

    async def _slow_check() -> HealthCheckResult:
        await asyncio.sleep(0.05)
        return HealthCheckResult(name="slow", healthy=True)

    app = AsgiFastStream(
        example_broker,
        asgi_routes=list(
            health(
                Probe(name="readiness", checks=[_slow_check]),
                options=build_probe_route_options(prefix="/health"),
                runner=ProbeRunner(policy=RunPolicy(mode="strict", probe_timeout_ms=1)),
            ),
        ),
    )

    async with _faststream_client(app) as client:
        response = await client.get("/health/readiness")

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


async def test_debug_payload_contains_structured_error_object() -> None:
    """Debug failure response uses structured `error` payload."""

    async def _failing_check() -> bool:
        await asyncio.sleep(0)
        message = "boom"
        raise ValueError(message)

    app = AsgiFastStream(
        example_broker,
        asgi_routes=list(
            health(
                Probe(name="readiness", checks=[FunctionHealthCheck(func=_failing_check, name="failing")]),
                options=build_probe_route_options(debug=True, prefix="/health"),
            ),
        ),
    )

    async with _faststream_client(app) as client:
        response = await client.get("/health/readiness")

    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    data = response.json()
    assert "results" in data
    assert "error_details" not in data["results"][0]
    assert data["results"][0]["error"]["code"] == "CHECK_EXCEPTION"
    assert "ValueError: boom" in data["results"][0]["error"]["message"]
