"""FastAPI integration for health checks."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter
from fastapi.responses import Response

from fast_healthchecks.integrations.base import (
    Probe,
    ProbeRouteOptions,
    build_probe_route_options,
    close_probes,
    create_probe_route_handler,
    healthcheck_shutdown,
    probe_path_suffix,
)

if TYPE_CHECKING:
    from fast_healthchecks.execution import ProbeRunner

__all__ = ["HealthcheckRouter", "healthcheck_shutdown"]


class HealthcheckRouter(APIRouter):
    """A router for health checks.

    Args:
        *probes: Probes to run (e.g. liveness, readiness, startup).
        options: Route options. When None, uses build_probe_route_options() defaults.

    To close health check resources (e.g. cached clients) on app shutdown,
    call ``await router.close()`` from your FastAPI lifespan, or use
    ``healthcheck_shutdown(probes)`` and call the returned callback.
    """

    def __init__(
        self,
        *probes: Probe,
        options: ProbeRouteOptions | None = None,
        runner: ProbeRunner | None = None,
    ) -> None:
        """Initialize the router."""
        if options is None:
            options = build_probe_route_options()
        super().__init__(prefix=options.prefix.removesuffix("/"), tags=["Healthchecks"])
        self._healthcheck_probes: list[Probe] = list(probes)
        self._runner = runner
        for probe in probes:
            self._add_probe_route(probe, options=options)

    def _add_probe_route(self, probe: Probe, *, options: ProbeRouteOptions) -> None:
        params = options.to_route_params()
        handle_request = create_probe_route_handler(
            probe,
            params,
            response_factory=lambda c, h, s: Response(content=c, status_code=s, headers=h),
            runner=self._runner,
        )

        self.add_api_route(
            path=f"/{probe_path_suffix(probe)}",
            endpoint=handle_request,
            status_code=options.success_status,
            summary=probe.endpoint_summary,
            include_in_schema=options.debug,
            response_model=None,
            response_class=Response,
        )

    async def close(self) -> None:
        """Close resources owned by this router's health check probes.

        Call this from your FastAPI lifespan shutdown (e.g. after ``yield``
        in an ``@asynccontextmanager`` lifespan) so cached clients are closed.
        """
        await close_probes(self._healthcheck_probes)
