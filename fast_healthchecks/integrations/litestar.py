"""Litestar integration for health checks."""

from __future__ import annotations

from typing import TYPE_CHECKING

from litestar import Response, get

from fast_healthchecks.integrations.base import (
    Probe,
    ProbeRouteOptions,
    build_health_routes,
    create_probe_route_handler,
    healthcheck_shutdown,
    probe_route_path,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from litestar.handlers.http_handlers import HTTPRouteHandler

    from fast_healthchecks.execution import ProbeRunner

__all__ = ["health", "healthcheck_shutdown"]


def _add_probe_route(
    probe: Probe,
    options: ProbeRouteOptions,
    *,
    runner: ProbeRunner | None = None,
) -> HTTPRouteHandler:
    params = options.to_route_params()
    handle_request = create_probe_route_handler(
        probe,
        params,
        response_factory=lambda c, h, s: Response(content=c, headers=h, status_code=s),
        runner=runner,
    )

    @get(
        path=probe_route_path(probe, options.prefix),
        name=probe.name,
        operation_id=f"health:{probe.name}",
        summary=probe.endpoint_summary,
        include_in_schema=options.debug,
    )
    async def route_handler() -> Response[bytes]:
        return await handle_request()

    return route_handler


def health(
    *probes: Probe,
    options: ProbeRouteOptions | None = None,
    runner: ProbeRunner | None = None,
) -> Iterable[HTTPRouteHandler]:
    """Make list of routes for healthchecks.

    Returns:
        Iterable[HTTPRouteHandler]: Generated healthcheck route handlers.

    To close health check resources on app shutdown, pass the same probes
    to ``healthcheck_shutdown(probes)`` and add the returned callback to
    Litestar's ``on_shutdown`` list.
    """
    return build_health_routes(
        probes,
        add_route=lambda probe, route_options: _add_probe_route(probe, route_options, runner=runner),
        options=options,
    )
