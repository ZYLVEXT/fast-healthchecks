"""FastStream integration for health checks."""

from __future__ import annotations

from collections.abc import Iterable
from http import HTTPStatus
from typing import TYPE_CHECKING

from faststream.asgi.handlers import get
from faststream.asgi.response import AsgiResponse
from faststream.asgi.types import Scope
from faststream.specification.schema.extra.tag import Tag

from fast_healthchecks.integrations.base import (
    HandlerType,
    Probe,
    default_handler,
    healthcheck_shutdown,
    make_probe_asgi,
)

if TYPE_CHECKING:
    from faststream.asgi.types import ASGIApp

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
) -> tuple[str, ASGIApp]:
    probe_handler = make_probe_asgi(
        probe,
        success_handler=success_handler,
        failure_handler=failure_handler,
        success_status=success_status,
        failure_status=failure_status,
        debug=debug,
    )

    @get(
        include_in_schema=debug,
        description=probe.endpoint_summary,
        tags=[Tag(name="Healthchecks")] if debug else None,
        unique_id=f"health:{probe.name}",
    )
    async def handle_request(_scope: Scope) -> AsgiResponse:
        content, headers, status_code = await probe_handler()
        return AsgiResponse(content, status_code=status_code, headers=headers)

    return f"{prefix.removesuffix('/')}/{probe.name.removeprefix('/')}", handle_request


def health(  # noqa: PLR0913
    *probes: Probe,
    success_handler: HandlerType = default_handler,
    failure_handler: HandlerType = default_handler,
    success_status: int = HTTPStatus.NO_CONTENT,
    failure_status: int = HTTPStatus.SERVICE_UNAVAILABLE,
    debug: bool = False,
    prefix: str = "/health",
) -> Iterable[tuple[str, ASGIApp]]:
    """Make list of routes for healthchecks.

    Returns:
        Iterable[tuple[str, ASGIApp]]: Generated healthcheck routes.

    To close health check resources on app shutdown, pass the same probes
    to ``healthcheck_shutdown(probes)`` and register the returned callback
    with your FastStream app's shutdown hooks (e.g. ``@app.on_shutdown``).
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
