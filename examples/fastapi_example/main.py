from fastapi import FastAPI, status

from examples.probes import (
    custom_handler,
    get_liveness_checks,
    get_readiness_checks,
    get_readiness_checks_fail,
    get_readiness_checks_success,
    get_startup_checks,
)
from fast_healthchecks.integrations.base import Probe
from fast_healthchecks.integrations.fastapi import HealthcheckRouter

app_integration = FastAPI()
app_integration.include_router(
    HealthcheckRouter(
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
        debug=True,
        prefix="/health",
    ),
)

app_success = FastAPI()
app_success.include_router(
    HealthcheckRouter(
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
        debug=True,
        prefix="/health",
    ),
)

app_fail = FastAPI()
app_fail.include_router(
    HealthcheckRouter(
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
        debug=True,
        prefix="/health",
    ),
)

app_custom = FastAPI()
app_custom.include_router(
    HealthcheckRouter(
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
        success_handler=custom_handler,
        failure_handler=custom_handler,
        success_status=status.HTTP_200_OK,
        failure_status=status.HTTP_503_SERVICE_UNAVAILABLE,
        debug=True,
        prefix="/custom_health",
    ),
)
