"""Litestar integration for health checks."""

from __future__ import annotations

from collections.abc import Iterable
from http import HTTPStatus

from litestar import Response, get
from litestar.handlers.http_handlers import HTTPRouteHandler

from fast_healthchecks.integrations.base import (
    HandlerType,
    Probe,
    default_handler,
    healthcheck_shutdown,
    make_probe_asgi,
)

__all__ = ["health", "healthcheck_shutdown"]


def _add_probe_route(  # noqa: PLR0913
    probe: Probe,
    *,
    success_handler: HandlerType = default_handler,
    failure_handler: HandlerType = default_handler,
    success_status: int = HTTPStatus.NO_CONTENT,
    failure_status: int = HTTPStatus.SERVICE_UNAVAILABLE,
    debug: bool = False,
    prefix: str = "/health",
) -> HTTPRouteHandler:
    probe_handler = make_probe_asgi(
        probe,
        success_handler=success_handler,
        failure_handler=failure_handler,
        success_status=success_status,
        failure_status=failure_status,
        debug=debug,
    )

    @get(
        path=f"{prefix.removesuffix('/')}/{probe.name.removeprefix('/')}",
        name=probe.name,
        operation_id=f"health:{probe.name}",
        summary=probe.endpoint_summary,
        include_in_schema=debug,
    )
    async def handle_request() -> Response[bytes]:
        content, headers, status_code = await probe_handler()
        return Response(content, headers=headers, status_code=status_code)

    return handle_request


def health(  # noqa: PLR0913
    *probes: Probe,
    success_handler: HandlerType = default_handler,
    failure_handler: HandlerType = default_handler,
    success_status: int = HTTPStatus.NO_CONTENT,
    failure_status: int = HTTPStatus.SERVICE_UNAVAILABLE,
    debug: bool = False,
    prefix: str = "/health",
) -> Iterable[HTTPRouteHandler]:
    """Make list of routes for healthchecks.

    Returns:
        Iterable[HTTPRouteHandler]: Generated healthcheck route handlers.

    To close health check resources on app shutdown, pass the same probes
    to ``healthcheck_shutdown(probes)`` and add the returned callback to
    Litestar's ``on_shutdown`` list.
    """
    return [
        _add_probe_route(
            probe,
            success_handler=success_handler,
            failure_handler=failure_handler,
            success_status=success_status,
            failure_status=failure_status,
            debug=debug,
            prefix=prefix,
        )
        for probe in probes
    ]
