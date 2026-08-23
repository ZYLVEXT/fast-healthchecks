"""Base for FastAPI, FastStream, and Litestar integrations.

Provides Probe, run_probe(), healthcheck_shutdown(), and helpers to build
health routes. Framework-specific routers use these to expose liveness/readiness.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable
from http import HTTPStatus
from typing import Any, NamedTuple, TypeAlias, TypeVar

from fast_healthchecks.execution import (
    Probe,
    ProbeRunner,
    close_probes,
    run_probe,  # ruff: ignore[unused-import] - re-exported for framework integrations
)
from fast_healthchecks.responses import ProbeAsgiResponse, map_report_to_asgi_http_response

HandlerType: TypeAlias = Callable[..., Awaitable[dict[str, Any] | None]]


class ProbeRouteParams(NamedTuple):
    """Parameters for probe route handlers. Used by framework integrations."""

    success_handler: HandlerType
    failure_handler: HandlerType
    success_status: int
    failure_status: int
    debug: bool
    timeout: float | None

    def to_options(self, prefix: str = "/health") -> ProbeRouteOptions:
        """Return ProbeRouteOptions with the given prefix."""
        return ProbeRouteOptions(
            success_handler=self.success_handler,
            failure_handler=self.failure_handler,
            success_status=self.success_status,
            failure_status=self.failure_status,
            debug=self.debug,
            timeout=self.timeout,
            prefix=prefix,
        )


class ProbeRouteOptions(NamedTuple):
    """Options for probe routes. Combines handler params and path prefix."""

    success_handler: HandlerType
    failure_handler: HandlerType
    success_status: int
    failure_status: int
    debug: bool
    timeout: float | None
    prefix: str

    def to_route_params(self) -> ProbeRouteParams:
        """Return ProbeRouteParams for create_probe_route_handler."""
        return ProbeRouteParams(
            success_handler=self.success_handler,
            failure_handler=self.failure_handler,
            success_status=self.success_status,
            failure_status=self.failure_status,
            debug=self.debug,
            timeout=self.timeout,
        )


async def default_handler(response: ProbeAsgiResponse) -> dict[str, Any] | None:  # ruff: ignore[unused-async] - the async signature is part of the handler protocol
    """Default handler for health check route.

    Returns a minimal body ``{"status": "healthy"|"unhealthy"}`` for responses
    that require content (e.g. 503). Returns ``None`` for 204 No Content.

    Args:
        response: The response from the probe.

    Returns:
        Minimal status dict, or None for no response body.
    """
    return {"status": "healthy" if response.healthy else "unhealthy"}


def build_probe_route_options(  # ruff: ignore[too-many-arguments] - explicit options; bundling them would hide the surface
    *,
    success_handler: HandlerType = default_handler,
    failure_handler: HandlerType = default_handler,
    success_status: int = HTTPStatus.NO_CONTENT,
    failure_status: int = HTTPStatus.SERVICE_UNAVAILABLE,
    debug: bool = False,
    prefix: str = "/health",
    timeout: float | None = None,
) -> ProbeRouteOptions:
    """Build ProbeRouteOptions with defaults. Used by health() and _add_probe_route.

    Args:
        success_handler: Handler for healthy responses. Receives ProbeAsgiResponse.
        failure_handler: Handler for unhealthy responses. Same signature.
        success_status: HTTP status for healthy (default 204 No Content).
        failure_status: HTTP status for unhealthy (default 503).
        debug: Include check details in responses.
        prefix: URL prefix for probe routes (e.g. "/health").
        timeout: Max seconds for all checks; on exceed returns failure. None = no limit.

    Returns:
        ProbeRouteOptions for use with HealthcheckRouter or health().
    """
    return ProbeRouteOptions(
        success_handler=success_handler,
        failure_handler=failure_handler,
        success_status=success_status,
        failure_status=failure_status,
        debug=debug,
        timeout=timeout,
        prefix=prefix,
    )


class ProbeAsgi:
    """An ASGI probe.

    Args:
        probe: The probe to run.
        options: Route options (handlers, status codes, debug, timeout).
            When None, defaults from build_probe_route_options() are used.
    """

    __slots__ = (
        "_debug",
        "_exclude_fields",
        "_failure_handler",
        "_failure_status",
        "_probe",
        "_runner",
        "_success_handler",
        "_success_status",
        "_timeout",
    )

    _probe: Probe
    _success_handler: HandlerType
    _failure_handler: HandlerType
    _success_status: int
    _failure_status: int
    _debug: bool
    _exclude_fields: set[str]
    _timeout: float | None

    def __init__(
        self,
        probe: Probe,
        *,
        options: ProbeRouteOptions | None = None,
        runner: ProbeRunner | None = None,
    ) -> None:
        """Initialize the ASGI probe.

        Args:
            probe: The probe to run.
            options: Route options (handlers, status codes, debug, timeout).
                When None, defaults from build_probe_route_options() are used.
            runner: Optional ProbeRunner. When None, uses an internal reporting-mode runner
                with the configured timeout.
        """
        if options is None:
            options = build_probe_route_options()
        params = options.to_route_params()
        self._probe = probe
        self._success_handler = params.success_handler
        self._failure_handler = params.failure_handler
        self._success_status = params.success_status
        self._failure_status = params.failure_status
        self._debug = params.debug
        self._timeout = params.timeout
        self._exclude_fields = {"allow_partial_failure", "error_details"} if not params.debug else set()
        self._runner = runner or _build_default_runner(timeout=params.timeout)

    async def __call__(self) -> tuple[bytes, dict[str, str] | None, int]:
        """Run the probe via run_probe (unified execution and timeout handling).

        Returns:
            A tuple containing the response body, headers, and status code.
        """
        report = await self._runner.run(self._probe)
        return await map_report_to_asgi_http_response(
            report,
            debug=self._debug,
            exclude_fields=self._exclude_fields,
            success_status=self._success_status,
            failure_status=self._failure_status,
            success_handler=self._success_handler,
            failure_handler=self._failure_handler,
        )


def _build_default_runner(timeout: float | None) -> ProbeRunner:
    """Build default ProbeRunner for integrations using reporting timeout mode.

    Returns:
        ProbeRunner configured with reporting mode and mapped probe timeout.
    """
    from fast_healthchecks.execution import (  # ruff: ignore[import-outside-top-level] - lazy: avoids the execution/integrations import cycle
        RunPolicy,
    )

    timeout_ms = None if timeout is None else max(int(timeout * 1000), 1)
    return ProbeRunner(policy=RunPolicy(mode="reporting", probe_timeout_ms=timeout_ms))


def make_probe_asgi(
    probe: Probe,
    *,
    options: ProbeRouteOptions | None = None,
    runner: ProbeRunner | None = None,
) -> Callable[[], Awaitable[tuple[bytes, dict[str, str] | None, int]]]:
    """Create an ASGI probe from a probe.

    Args:
        probe: The probe to create the ASGI probe from.
        options: Route options. When None, defaults from build_probe_route_options().
        runner: Optional ProbeRunner. When None, uses an internal reporting-mode runner.

    Returns:
        An ASGI probe.
    """
    return ProbeAsgi(probe, options=options, runner=runner)


def probe_path_suffix(probe: Probe) -> str:
    """Return the path suffix for a probe (name without leading slash)."""
    return probe.name.removeprefix("/")


def probe_route_path(probe: Probe, prefix: str = "/health") -> str:
    """Return the route path for a probe given a prefix."""
    return f"{prefix.removesuffix('/')}/{probe_path_suffix(probe)}"


_T = TypeVar("_T")


def _build_health_routes(
    probes: Iterable[Probe],
    *,
    add_route: Callable[[Probe, ProbeRouteOptions], _T],
    options: ProbeRouteOptions,
) -> list[_T]:
    """Build health route entries for each probe using the given add_route callback.

    Returns:
        list[_T]: List of route entries produced by add_route for each probe.
    """
    return [add_route(probe, options) for probe in probes]


def build_health_routes(
    probes: Iterable[Probe],
    add_route: Callable[[Probe, ProbeRouteOptions], _T],
    *,
    options: ProbeRouteOptions | None = None,
) -> list[_T]:
    """Build health route entries for framework integrations.

    Used by Litestar and FastStream health() functions. When options is None,
    uses build_probe_route_options() defaults.

    Args:
        probes: Probes to build routes for.
        add_route: Callback (probe, options) -> route entry for the framework.
        options: Route options. When None, defaults from build_probe_route_options().

    Returns:
        List of route entries produced by add_route for each probe.
    """
    if options is None:
        options = build_probe_route_options()
    return _build_health_routes(probes, add_route=add_route, options=options)


def create_probe_route_handler(
    probe: Probe,
    params: ProbeRouteParams,
    *,
    response_factory: Callable[[bytes, dict[str, str], int], _T],
    runner: ProbeRunner | None = None,
) -> Callable[[], Awaitable[_T]]:
    """Create an async handler for a probe route.

    Framework integrations use this with their response_factory to build
    the handler, then register it (FastAPI add_api_route, FastStream/Litestar return).

    Args:
        probe: The probe to run when the route is called.
        params: Route params (handlers, status codes, etc.).
        response_factory: Called with (body, headers, status_code); returns framework response.
        runner: Optional ProbeRunner used for probe execution.

    Returns:
        Async callable that runs the probe and returns the framework response.
    """
    probe_asgi = make_probe_asgi(probe, options=params.to_options(), runner=runner)

    async def handler() -> _T:
        content, headers, status_code = await probe_asgi()
        return response_factory(content, headers or {}, status_code)

    return handler


def healthcheck_shutdown(probes: Iterable[Probe]) -> Callable[[], Awaitable[None]]:
    """Return an async shutdown callback that closes the given probes' checks.

    Use this with framework lifespan/shutdown hooks (e.g. Litestar ``on_shutdown``,
    FastStream shutdown) so that health check resources are closed on app shutdown.

    Args:
        probes: The same probes passed to your health routes.

    Returns:
        An async callable with no arguments that closes all checks with ``aclose()``.
    """

    async def _shutdown() -> None:
        await close_probes(probes)

    return _shutdown
