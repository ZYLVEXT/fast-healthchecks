from litestar import Litestar
from litestar.status_codes import HTTP_200_OK, HTTP_503_SERVICE_UNAVAILABLE

from examples.probes import (
    custom_handler,
    get_liveness_checks,
    get_readiness_checks,
    get_readiness_checks_fail,
    get_readiness_checks_success,
    get_startup_checks,
)
from fast_healthchecks.integrations.base import Probe
from fast_healthchecks.integrations.litestar import health

app_integration = Litestar(
    route_handlers=[
        *health(
            Probe(name="liveness", checks=get_liveness_checks()),
            Probe(name="readiness", checks=get_readiness_checks()),
            Probe(name="startup", checks=get_startup_checks()),
            debug=False,
            prefix="/health",
        ),
    ],
)

app_success = Litestar(
    route_handlers=[
        *health(
            Probe(name="liveness", checks=[]),
            Probe(name="readiness", checks=get_readiness_checks_success()),
            Probe(name="startup", checks=[]),
            debug=False,
            prefix="/health",
        ),
    ],
)

app_fail = Litestar(
    route_handlers=[
        *health(
            Probe(name="liveness", checks=[]),
            Probe(name="readiness", checks=get_readiness_checks_fail()),
            Probe(name="startup", checks=[]),
            debug=False,
            prefix="/health",
        ),
    ],
)

app_custom = Litestar(
    route_handlers=[
        *health(
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
            success_status=HTTP_200_OK,
            failure_status=HTTP_503_SERVICE_UNAVAILABLE,
            debug=True,
            prefix="/custom_health",
        ),
    ],
)
