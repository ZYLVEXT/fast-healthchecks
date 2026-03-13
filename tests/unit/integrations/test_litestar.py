"""Unit tests for Litestar health() and probes."""

import asyncio
import json

import pytest
from litestar import Litestar
from litestar.status_codes import HTTP_200_OK, HTTP_204_NO_CONTENT, HTTP_503_SERVICE_UNAVAILABLE
from litestar.testing import TestClient

from examples.litestar_example.main import app_custom, app_fail, app_success
from fast_healthchecks.execution import ProbeRunner, RunPolicy
from fast_healthchecks.integrations.base import Probe, build_probe_route_options
from fast_healthchecks.integrations.litestar import health
from fast_healthchecks.models import HealthCheckResult

pytestmark = pytest.mark.unit


def test_liveness_probe() -> None:
    """Liveness probe returns success when checks pass."""
    with TestClient(app=app_success) as client:
        response = client.get("/health/liveness")
        assert response.status_code == HTTP_204_NO_CONTENT
        assert response.content == b""


def test_readiness_probe() -> None:
    """Readiness probe returns success when all checks pass."""
    with TestClient(app=app_success) as client:
        response = client.get("/health/readiness")
        assert response.status_code == HTTP_204_NO_CONTENT
        assert response.content == b""


def test_startup_probe() -> None:
    """Startup probe returns success when checks pass."""
    with TestClient(app=app_success) as client:
        response = client.get("/health/startup")
        assert response.status_code == HTTP_204_NO_CONTENT
        assert response.content == b""


def test_readiness_probe_fail() -> None:
    """Readiness probe returns failure when a check fails."""
    with TestClient(app=app_fail) as client:
        response = client.get("/health/readiness")
        assert response.status_code == HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        # With debug=True the body is the full report (results, allow_partial_failure); otherwise minimal {"status": "unhealthy"}
        assert data.get("status") == "unhealthy" or (
            "results" in data and any(not r.get("healthy", True) for r in data["results"])
        )


def test_custom_handler() -> None:
    """Custom handler is used for probe response."""
    with TestClient(app=app_custom) as client:
        response = client.get("/custom_health/readiness")
        assert response.status_code == HTTP_200_OK
    assert response.content == json.dumps(
        {"results": [{"name": "Async dummy", "healthy": True, "error": None}], "allow_partial_failure": False},
        ensure_ascii=False,
        allow_nan=False,
        indent=None,
        separators=(",", ":"),
    ).encode("utf-8")


def test_health_uses_injected_runner() -> None:
    """health() uses injected runner when provided."""

    async def _slow_check() -> HealthCheckResult:
        await asyncio.sleep(0.05)
        return HealthCheckResult(name="slow", healthy=True)

    app = Litestar(
        route_handlers=list(
            health(
                Probe(name="readiness", checks=[_slow_check]),
                runner=ProbeRunner(policy=RunPolicy(mode="reporting", probe_timeout_ms=1)),
            ),
        ),
    )

    with TestClient(app=app) as client:
        response = client.get("/health/readiness")

    assert response.status_code == HTTP_503_SERVICE_UNAVAILABLE
    assert response.json() == {"status": "unhealthy"}


def test_health_without_runner_uses_safe_default_reporting_mode() -> None:
    """Default internal runner returns failure response on timeout."""

    async def _slow_check() -> HealthCheckResult:
        await asyncio.sleep(0.05)
        return HealthCheckResult(name="slow", healthy=True)

    app = Litestar(
        route_handlers=list(
            health(
                Probe(name="readiness", checks=[_slow_check]),
                options=build_probe_route_options(timeout=0.001),
            ),
        ),
    )

    with TestClient(app=app) as client:
        response = client.get("/health/readiness")

    assert response.status_code == HTTP_503_SERVICE_UNAVAILABLE
    assert response.json() == {"status": "unhealthy"}
