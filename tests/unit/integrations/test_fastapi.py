"""Unit tests for FastAPI HealthcheckRouter and probes."""

import asyncio
import json

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from examples.fastapi_example.main import app_custom, app_fail, app_success
from examples.probes import READINESS_CHECKS_SUCCESS
from fast_healthchecks.execution import ProbeRunner, RunPolicy
from fast_healthchecks.integrations.base import Probe, build_probe_route_options, default_handler
from fast_healthchecks.integrations.fastapi import HealthcheckRouter
from fast_healthchecks.models import HealthCheckResult

from .helpers import CheckWithAclose

pytestmark = pytest.mark.unit


def _success_check() -> bool:
    """Return True for probe tests.

    Returns:
        True.
    """
    return True


def test_liveness_probe() -> None:
    """Liveness probe returns success status when checks pass."""
    with TestClient(app_success) as client:
        response = client.get("/health/liveness")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""


def test_readiness_probe() -> None:
    """Readiness probe returns success when all checks pass."""
    with TestClient(app_success) as client:
        response = client.get("/health/readiness")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""


def test_startup_probe() -> None:
    """Startup probe returns success when checks pass."""
    with TestClient(app_success) as client:
        response = client.get("/health/startup")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""


def test_readiness_probe_fail() -> None:
    """Readiness probe returns failure status when a check fails."""
    with TestClient(app_fail) as client:
        response = client.get("/health/readiness")
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    data = response.json()
    # With debug=True the body is the full report (results, allow_partial_failure); otherwise minimal {"status": "unhealthy"}
    assert data.get("status") == "unhealthy" or (
        "results" in data and any(not r.get("healthy", True) for r in data["results"])
    )


def test_custom_handler() -> None:
    """Custom success/failure handlers receive probe response and are invoked correctly."""
    with TestClient(app_custom) as client:
        response = client.get("/custom_health/readiness")
    assert response.status_code == status.HTTP_200_OK
    assert response.content == json.dumps(
        {"results": [{"name": "Async dummy", "healthy": True, "error": None}], "allow_partial_failure": False},
        ensure_ascii=False,
        allow_nan=False,
        indent=None,
        separators=(",", ":"),
    ).encode("utf-8")


def test_default_handler_returns_minimal_body() -> None:
    """Test that default_handler returns minimal status body."""
    app = FastAPI()
    app.include_router(
        HealthcheckRouter(
            Probe(name="readiness", checks=READINESS_CHECKS_SUCCESS),
            options=build_probe_route_options(
                success_handler=default_handler,
                failure_handler=default_handler,
                success_status=status.HTTP_200_OK,
                failure_status=status.HTTP_503_SERVICE_UNAVAILABLE,
                debug=True,
                prefix="/health",
            ),
        ),
    )
    with TestClient(app) as client_default:
        response = client_default.get("/health/readiness")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "healthy"}


def test_router_without_options_uses_defaults() -> None:
    """HealthcheckRouter(probe) without options uses build_probe_route_options() defaults."""
    app = FastAPI()
    app.include_router(HealthcheckRouter(Probe(name="readiness", checks=READINESS_CHECKS_SUCCESS)))
    with TestClient(app) as client_default:
        response = client_default.get("/health/readiness")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""


def test_router_uses_injected_runner() -> None:
    """HealthcheckRouter uses injected runner when provided."""

    async def _slow_check() -> HealthCheckResult:
        await asyncio.sleep(0.05)
        return HealthCheckResult(name="slow", healthy=True)

    app = FastAPI()
    runner = ProbeRunner(policy=RunPolicy(mode="reporting", probe_timeout_ms=1))
    app.include_router(
        HealthcheckRouter(
            Probe(name="readiness", checks=[_slow_check]),
            options=build_probe_route_options(prefix="/health"),
            runner=runner,
        ),
    )
    with TestClient(app) as client_default:
        response = client_default.get("/health/readiness")
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json() == {"status": "unhealthy"}


def test_router_without_runner_uses_safe_default_reporting_mode() -> None:
    """Default internal runner returns failure response on timeout (no exception leak)."""

    async def _slow_check() -> HealthCheckResult:
        await asyncio.sleep(0.05)
        return HealthCheckResult(name="slow", healthy=True)

    app = FastAPI()
    app.include_router(
        HealthcheckRouter(
            Probe(name="readiness", checks=[_slow_check]),
            options=build_probe_route_options(prefix="/health", timeout=0.001),
        ),
    )
    with TestClient(app) as client_default:
        response = client_default.get("/health/readiness")
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json() == {"status": "unhealthy"}


@pytest.mark.asyncio
async def test_router_close_closes_probe_checks() -> None:
    """HealthcheckRouter.close() calls aclose() on checks that have it."""
    check = CheckWithAclose(name="A")
    probe = Probe(name="readiness", checks=[check])
    router = HealthcheckRouter(probe, options=build_probe_route_options(prefix="/health"))
    await router.close()
    check._aclose_mock.assert_awaited_once_with()
