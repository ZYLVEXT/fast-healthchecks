import json
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from examples.fastapi_example.main import app_custom, app_fail, app_success
from examples.probes import READINESS_CHECKS_SUCCESS
from fast_healthchecks.checks.function import FunctionHealthCheck
from fast_healthchecks.integrations.base import Probe, default_handler
from fast_healthchecks.integrations.fastapi import HealthcheckRouter

pytestmark = pytest.mark.unit

client = TestClient(app_success)


def _success_check() -> bool:
    return True


def test_liveness_probe() -> None:
    response = client.get("/health/liveness")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""


def test_readiness_probe() -> None:
    response = client.get("/health/readiness")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""


def test_startup_probe() -> None:
    response = client.get("/health/startup")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""


def test_readiness_probe_fail() -> None:
    client_fail = TestClient(app_fail)
    response = client_fail.get("/health/readiness")
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.content == b""


def test_custom_handler() -> None:
    client_custom = TestClient(app_custom)
    response = client_custom.get("/custom_health/readiness")
    assert response.status_code == status.HTTP_200_OK
    assert response.content == json.dumps(
        {"results": [{"name": "Async dummy", "healthy": True, "error_details": None}], "allow_partial_failure": False},
        ensure_ascii=False,
        allow_nan=False,
        indent=None,
        separators=(",", ":"),
    ).encode("utf-8")


def test_default_handler_returns_empty_body() -> None:
    """Test that default_handler returns None, resulting in empty response body."""
    app = FastAPI()
    app.include_router(
        HealthcheckRouter(
            Probe(name="readiness", checks=READINESS_CHECKS_SUCCESS),
            success_handler=default_handler,
            failure_handler=default_handler,
            success_status=status.HTTP_200_OK,
            failure_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            debug=True,
            prefix="/health",
        ),
    )
    client_default = TestClient(app)
    response = client_default.get("/health/readiness")
    assert response.status_code == status.HTTP_200_OK
    assert response.content == b""


@pytest.mark.asyncio
async def test_router_close_closes_probe_checks() -> None:
    """HealthcheckRouter.close() calls aclose() on checks that have it."""
    check = FunctionHealthCheck(func=_success_check, name="A")
    check.aclose = AsyncMock()  # type: ignore[method-assign]
    probe = Probe(name="readiness", checks=[check])
    router = HealthcheckRouter(probe, prefix="/health")
    await router.close()
    check.aclose.assert_awaited_once_with()  # type: ignore[attr-defined]
