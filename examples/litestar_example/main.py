"""Example app for fast-healthchecks."""

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
from fast_healthchecks.integrations.base import Probe, build_probe_route_options
from fast_healthchecks.integrations.litestar import health, healthcheck_shutdown

_probes_integration = [
    Probe(name="liveness", checks=get_liveness_checks()),
    Probe(name="readiness", checks=get_readiness_checks()),
    Probe(name="startup", checks=get_startup_checks()),
]
app_integration = Litestar(
    route_handlers=[
        *health(
            *_probes_integration,
            options=build_probe_route_options(debug=False, prefix="/health"),
        ),
    ],
    on_shutdown=[healthcheck_shutdown(_probes_integration)],
)
app_integration.debug = True  # for integration tests (verbose errors/schema)

_probes_success = [
    Probe(name="liveness", checks=[]),
    Probe(name="readiness", checks=get_readiness_checks_success()),
    Probe(name="startup", checks=[]),
]
app_success = Litestar(
    route_handlers=[
        *health(
            *_probes_success,
            options=build_probe_route_options(debug=False, prefix="/health"),
        ),
    ],
    on_shutdown=[healthcheck_shutdown(_probes_success)],
)
app_success.debug = True  # for unit/integration tests (verbose errors/schema)

_probes_fail = [
    Probe(name="liveness", checks=[]),
    Probe(name="readiness", checks=get_readiness_checks_fail()),
    Probe(name="startup", checks=[]),
]
app_fail = Litestar(
    route_handlers=[
        *health(
            *_probes_fail,
            options=build_probe_route_options(debug=False, prefix="/health"),
        ),
    ],
    on_shutdown=[healthcheck_shutdown(_probes_fail)],
)

_probes_custom = [
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
]
app_custom = Litestar(
    route_handlers=[
        *health(
            *_probes_custom,
            options=build_probe_route_options(
                success_handler=custom_handler,
                failure_handler=custom_handler,
                success_status=HTTP_200_OK,
                failure_status=HTTP_503_SERVICE_UNAVAILABLE,
                debug=True,
                prefix="/custom_health",
            ),
        ),
    ],
    on_shutdown=[healthcheck_shutdown(_probes_custom)],
)
