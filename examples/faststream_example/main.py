"""Example app for fast-healthchecks."""

import os
from http import HTTPStatus

from faststream.asgi import AsgiFastStream
from faststream.kafka import KafkaBroker

from examples.probes import (
    LIVENESS_CHECKS,
    READINESS_CHECKS,
    READINESS_CHECKS_FAIL,
    READINESS_CHECKS_SUCCESS,
    STARTUP_CHECKS,
    custom_handler,
)
from fast_healthchecks.integrations.base import Probe, build_probe_route_options
from fast_healthchecks.integrations.faststream import health, healthcheck_shutdown

broker = KafkaBroker(
    os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9094,localhost:9095").split(","),
)

_probes_integration = (
    Probe(name="liveness", checks=LIVENESS_CHECKS),
    Probe(name="readiness", checks=READINESS_CHECKS),
    Probe(name="startup", checks=STARTUP_CHECKS),
)
app_integration = AsgiFastStream(
    broker,
    asgi_routes=[
        *health(
            *_probes_integration,
            options=build_probe_route_options(debug=False, prefix="/health"),
        ),
    ],
    on_shutdown=[healthcheck_shutdown(_probes_integration)],
)

_probes_success = (
    Probe(name="liveness", checks=[]),
    Probe(name="readiness", checks=READINESS_CHECKS_SUCCESS),
    Probe(name="startup", checks=[]),
)
app_success = AsgiFastStream(
    broker,
    asgi_routes=[
        *health(
            *_probes_success,
            options=build_probe_route_options(debug=False, prefix="/health"),
        ),
    ],
    on_shutdown=[healthcheck_shutdown(_probes_success)],
)

_probes_fail = (
    Probe(name="liveness", checks=[]),
    Probe(name="readiness", checks=READINESS_CHECKS_FAIL),
    Probe(name="startup", checks=[]),
)
app_fail = AsgiFastStream(
    broker,
    asgi_routes=[
        *health(
            *_probes_fail,
            options=build_probe_route_options(debug=False, prefix="/health"),
        ),
    ],
    on_shutdown=[healthcheck_shutdown(_probes_fail)],
)

_probes_custom = (
    Probe(
        name="liveness",
        checks=[],
        summary="Check if the application is alive",
    ),
    Probe(
        name="readiness",
        checks=READINESS_CHECKS_SUCCESS,
        summary="Check if the application is ready",
    ),
    Probe(
        name="startup",
        checks=[],
        summary="Check if the application is starting up",
    ),
)
app_custom = AsgiFastStream(
    broker,
    asgi_routes=[
        *health(
            *_probes_custom,
            options=build_probe_route_options(
                success_handler=custom_handler,
                failure_handler=custom_handler,
                success_status=HTTPStatus.OK,
                failure_status=HTTPStatus.SERVICE_UNAVAILABLE,
                debug=True,
                prefix="/custom_health",
            ),
        ),
    ],
    on_shutdown=[healthcheck_shutdown(_probes_custom)],
)
