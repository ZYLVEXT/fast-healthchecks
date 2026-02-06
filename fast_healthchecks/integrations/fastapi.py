"""FastAPI integration for health checks."""

from __future__ import annotations

from fastapi import APIRouter, status
from fastapi.responses import Response

from fast_healthchecks.integrations.base import (
    HandlerType,
    Probe,
    close_probes,
    default_handler,
    healthcheck_shutdown,
    make_probe_asgi,
)

__all__ = ["HealthcheckRouter", "healthcheck_shutdown"]


class HealthcheckRouter(APIRouter):
    """A router for health checks.

    Args:
        probes: An iterable of probes to run.
        debug: Whether to include the probes in the schema. Defaults to False.

    To close health check resources (e.g. cached clients) on app shutdown,
    call ``await router.close()`` from your FastAPI lifespan, or use
    ``healthcheck_shutdown(probes)`` and call the returned callback.
    """

    def __init__(  # noqa: PLR0913
        self,
        *probes: Probe,
        success_handler: HandlerType = default_handler,
        failure_handler: HandlerType = default_handler,
        success_status: int = status.HTTP_204_NO_CONTENT,
        failure_status: int = status.HTTP_503_SERVICE_UNAVAILABLE,
        debug: bool = False,
        prefix: str = "/health",
    ) -> None:
        """Initialize the router."""
        super().__init__(prefix=prefix, tags=["Healthchecks"])
        self._healthcheck_probes: list[Probe] = list(probes)
        for probe in probes:
            self._add_probe_route(
                probe,
                success_handler=success_handler,
                failure_handler=failure_handler,
                success_status=success_status,
                failure_status=failure_status,
                debug=debug,
            )

    def _add_probe_route(  # noqa: PLR0913
        self,
        probe: Probe,
        *,
        success_handler: HandlerType = default_handler,
        failure_handler: HandlerType = default_handler,
        success_status: int = status.HTTP_204_NO_CONTENT,
        failure_status: int = status.HTTP_503_SERVICE_UNAVAILABLE,
        debug: bool = False,
    ) -> None:
        probe_handler = make_probe_asgi(
            probe,
            success_handler=success_handler,
            failure_handler=failure_handler,
            success_status=success_status,
            failure_status=failure_status,
            debug=debug,
        )

        async def handle_request() -> Response:
            content, headers, status_code = await probe_handler()
            return Response(content=content, status_code=status_code, headers=headers)

        self.add_api_route(
            path=f"/{probe.name}",
            endpoint=handle_request,
            status_code=success_status,
            summary=probe.endpoint_summary,
            include_in_schema=debug,
        )

    async def close(self) -> None:
        """Close resources owned by this router's health check probes.

        Call this from your FastAPI lifespan shutdown (e.g. after ``yield``
        in an ``@asynccontextmanager`` lifespan) so cached clients are closed.
        """
        await close_probes(self._healthcheck_probes)
