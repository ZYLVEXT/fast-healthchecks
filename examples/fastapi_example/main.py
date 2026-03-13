"""Example app for fast-healthchecks."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI, status

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

from examples.probes import (
    custom_handler,
    get_liveness_checks,
    get_readiness_checks,
    get_readiness_checks_fail,
    get_readiness_checks_success,
    get_startup_checks,
)
from fast_healthchecks.integrations.base import Probe, build_probe_route_options
from fast_healthchecks.integrations.fastapi import HealthcheckRouter

router_integration = HealthcheckRouter(
    Probe(
        name="liveness",
        checks=get_liveness_checks(),
    ),
    Probe(
        name="readiness",
        checks=get_readiness_checks(),
    ),
    Probe(
        name="startup",
        checks=get_startup_checks(),
    ),
    options=build_probe_route_options(debug=True, prefix="/health"),
)


@asynccontextmanager
async def lifespan_integration(_app: FastAPI) -> AsyncIterator[None]:
    """Lifespan for integration app: close healthcheck router on shutdown."""
    yield
    await router_integration.close()


app_integration = FastAPI(lifespan=lifespan_integration)
app_integration.include_router(router_integration)

router_success = HealthcheckRouter(
    Probe(
        name="liveness",
        checks=[],
    ),
    Probe(
        name="readiness",
        checks=get_readiness_checks_success(),
    ),
    Probe(
        name="startup",
        checks=[],
    ),
    options=build_probe_route_options(debug=True, prefix="/health"),
)


@asynccontextmanager
async def lifespan_success(_app: FastAPI) -> AsyncIterator[None]:
    """Lifespan for success app: close healthcheck router on shutdown."""
    yield
    await router_success.close()


app_success = FastAPI(lifespan=lifespan_success)
app_success.include_router(router_success)

router_fail = HealthcheckRouter(
    Probe(
        name="liveness",
        checks=[],
    ),
    Probe(
        name="readiness",
        checks=get_readiness_checks_fail(),
    ),
    Probe(
        name="startup",
        checks=[],
    ),
    options=build_probe_route_options(debug=True, prefix="/health"),
)


@asynccontextmanager
async def lifespan_fail(_app: FastAPI) -> AsyncIterator[None]:
    """Lifespan for fail app: close healthcheck router on shutdown."""
    yield
    await router_fail.close()


app_fail = FastAPI(lifespan=lifespan_fail)
app_fail.include_router(router_fail)

router_custom = HealthcheckRouter(
    Probe(
        name="liveness",
        checks=[],
        summary="Check if the application is alive",
    ),
    Probe(
        name="readiness",
        checks=get_readiness_checks_success(),
        summary="Check if the application is ready",
    ),
    Probe(
        name="startup",
        checks=[],
        summary="Check if the application is starting up",
    ),
    options=build_probe_route_options(
        success_handler=custom_handler,
        failure_handler=custom_handler,
        success_status=status.HTTP_200_OK,
        failure_status=status.HTTP_503_SERVICE_UNAVAILABLE,
        debug=True,
        prefix="/custom_health",
    ),
)


@asynccontextmanager
async def lifespan_custom(_app: FastAPI) -> AsyncIterator[None]:
    """Lifespan for custom app: close healthcheck router on shutdown."""
    yield
    await router_custom.close()


app_custom = FastAPI(lifespan=lifespan_custom)
app_custom.include_router(router_custom)
