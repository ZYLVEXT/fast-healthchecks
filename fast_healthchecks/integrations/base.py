"""Base for FastAPI, FastStream, and Litestar integrations.

Provides Probe, run_probe(), healthcheck_shutdown(), and helpers to build
health routes. Framework-specific routers use these to expose liveness/readiness.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import re
from collections.abc import Awaitable, Callable, Iterable, Sequence
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, NamedTuple, TypeAlias, TypeVar

from fast_healthchecks.checks._base import result_on_error
from fast_healthchecks.checks.types import Check
from fast_healthchecks.errors import PROBE_TIMEOUT, map_exception_to_health_error
from fast_healthchecks.logging import get_probe_logger
from fast_healthchecks.models import (
    HealthCheckReport,
    HealthCheckResult,
    HealthCheckTimeoutError,
)
from fast_healthchecks.responses import ProbeAsgiResponse, map_report_to_asgi_http_response

if TYPE_CHECKING:
    from fast_healthchecks.execution import ProbeRunner

HandlerType: TypeAlias = Callable[..., Awaitable[dict[str, Any] | None]]

OnCheckStart: TypeAlias = Callable[[Check, int], Awaitable[None]]
OnCheckEnd: TypeAlias = Callable[[Check, int, HealthCheckResult], Awaitable[None]]


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


class Probe(NamedTuple):
    """A probe is a collection of health checks that can be run together.

    Attributes:
        name: The name of the probe.
        checks: A sequence of health checks to run.
        summary: A summary of the probe. If not provided, a default summary will be generated.
        default_check_timeout_ms: Default per-check timeout (ms) when check timeout is not set.
    """

    name: str
    checks: Sequence[Check]
    summary: str | None = None
    default_check_timeout_ms: int | None = None

    @property
    def endpoint_summary(self) -> str:
        """Return a summary for the endpoint.

        If a summary is provided, it will be used. Otherwise, a default summary will be generated.
        """
        if self.summary:
            return self.summary
        title = re.sub(
            pattern=r"[^a-z0-9]+",
            repl=" ",
            string=self.name.lower().capitalize(),
            flags=re.IGNORECASE,
        )
        return f"{title} probe"


async def default_handler(response: ProbeAsgiResponse) -> dict[str, Any] | None:
    """Default handler for health check route.

    Returns a minimal body ``{"status": "healthy"|"unhealthy"}`` for responses
    that require content (e.g. 503). Returns ``None`` for 204 No Content.

    Args:
        response: The response from the probe.

    Returns:
        Minimal status dict, or None for no response body.
    """
    await asyncio.sleep(0)
    return {"status": "healthy" if response.healthy else "unhealthy"}


def build_probe_route_options(  # noqa: PLR0913
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


def _get_check_name(check: Check, index: int) -> str:
    return getattr(check, "name", None) or getattr(check, "_name", f"Check-{index}")


async def _run_check_safe(check: Check, index: int) -> HealthCheckResult:
    """Run a single check; wrap failures in HealthCheckResult.

    CancelledError, SystemExit, and KeyboardInterrupt are re-raised and never
    wrapped. All other exceptions produce a failed HealthCheckResult.

    Returns:
        HealthCheckResult from the check, or a failed result on exception.

    Raises:
        asyncio.CancelledError: If the check is cancelled.
        SystemExit: If the check raises SystemExit.
        KeyboardInterrupt: If the check raises KeyboardInterrupt.
    """
    name = _get_check_name(check, index)
    get_probe_logger().log(logging.DEBUG, "check_start", check_name=name, index=index)
    try:
        result = await check()
        get_probe_logger().log(
            logging.DEBUG,
            "check_end",
            check_name=result.name,
            index=index,
            healthy=result.healthy,
        )
        return result  # noqa: TRY300
    except (asyncio.CancelledError, SystemExit, KeyboardInterrupt):
        raise
    except Exception as exc:  # noqa: BLE001
        result = result_on_error(name, exc)
        get_probe_logger().log(
            logging.DEBUG,
            "check_end",
            check_name=name,
            index=index,
            healthy=False,
        )
        return result


async def _gather_check_results(
    probe: Probe,
    timeout: float | None = None,
    *,
    on_timeout_return_failure: bool = False,
) -> list[HealthCheckResult]:
    """Run all probe checks in parallel, optionally with timeout.

    Args:
        probe: The probe whose checks to run.
        timeout: Max seconds. When exceeded, raises HealthCheckTimeoutError unless
            on_timeout_return_failure is True.
        on_timeout_return_failure: If True, return failure results instead of raising.

    Returns:
        List of HealthCheckResult from each check.

    Raises:
        HealthCheckTimeoutError: When timeout is exceeded and on_timeout_return_failure is False.
    """
    tasks = [_run_check_safe(check, i) for i, check in enumerate(probe.checks)]
    if timeout is not None:
        try:
            return list(
                await asyncio.wait_for(asyncio.gather(*tasks), timeout=timeout),
            )
        except asyncio.TimeoutError:
            if on_timeout_return_failure:
                return [
                    HealthCheckResult(
                        name=_get_check_name(check, i),
                        healthy=False,
                        error=map_exception_to_health_error(
                            HealthCheckTimeoutError("Probe timed out"),
                            code=PROBE_TIMEOUT,
                        ),
                    )
                    for i, check in enumerate(probe.checks)
                ]
            raise HealthCheckTimeoutError(code=PROBE_TIMEOUT) from None
    return list(await asyncio.gather(*tasks))


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
    from fast_healthchecks.execution import ProbeRunner, RunPolicy  # noqa: PLC0415

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


async def run_probe(
    probe: Probe,
    *,
    timeout: float | None = None,
    on_check_start: OnCheckStart | None = None,
    on_check_end: OnCheckEnd | None = None,
    on_timeout_return_failure: bool = False,
) -> HealthCheckReport:
    """Run a probe and return the health check report.

    Can be used without ASGI (CLI, cron, tests). ProbeAsgi uses this with
    on_timeout_return_failure=True so timeout behavior is unified.

    When ``on_check_start`` or ``on_check_end`` are provided, checks run
    sequentially (for ordering guarantees). Otherwise they run in parallel.

    **Cleanup and cancellation:** On cancellation or timeout, run_probe does not
    close cached clients (checks with ``aclose``). The caller must call
    ``healthcheck_shutdown(probes)`` or ``close_probes(probes)`` to close them.
    There are no dangling background tasks after run_probe returns or raises.
    See lifecycle and run-probe docs for cleanup paths X and Y.

    **Timeout semantics (probe-level only):** When ``timeout`` is exceeded,
    all pending checks are cancelled. Mode A (on_timeout_return_failure=False):
    raise TimeoutError, no report. Mode B (on_timeout_return_failure=True):
    return HealthCheckReport with failed results for timed-out checks.
    ProbeAsgi uses Mode B. See docs run-probe.md for full semantics.

    Args:
        probe: The probe to run.
        timeout: Maximum seconds for all checks. Raises asyncio.TimeoutError if exceeded
            unless on_timeout_return_failure is True.
        on_check_start: Optional callback before each check runs. Receives (check, index).
        on_check_end: Optional callback after each check completes. Receives (check, index, result).
        on_timeout_return_failure: If True, on timeout return a report with failed results
            instead of raising TimeoutError.

    Returns:
        HealthCheckReport with results from all checks.

    Raises:
        HealthCheckTimeoutError: When timeout is exceeded and on_timeout_return_failure is False.
            (Subclass of asyncio.TimeoutError; existing ``except TimeoutError`` still works.)
    """
    get_probe_logger().log(
        logging.INFO,
        "probe_start",
        probe=probe.name,
        checks_count=len(probe.checks),
    )
    try:
        if on_check_start is None and on_check_end is None:
            results = await _gather_check_results(
                probe,
                timeout=timeout,
                on_timeout_return_failure=on_timeout_return_failure,
            )
        else:

            async def _run_with_hooks() -> list[HealthCheckResult]:
                out: list[HealthCheckResult] = []
                for i, check in enumerate(probe.checks):
                    if on_check_start is not None:
                        await on_check_start(check, i)
                    result = await _run_check_safe(check, i)
                    if on_check_end is not None:
                        await on_check_end(check, i, result)
                    out.append(result)
                return out

            try:
                if timeout is not None:
                    results = await asyncio.wait_for(_run_with_hooks(), timeout=timeout)
                else:
                    results = await _run_with_hooks()
            except asyncio.TimeoutError:
                if on_timeout_return_failure:
                    results = [
                        HealthCheckResult(
                            name=_get_check_name(check, i),
                            healthy=False,
                            error=map_exception_to_health_error(
                                HealthCheckTimeoutError("Probe timed out"),
                                code=PROBE_TIMEOUT,
                            ),
                        )
                        for i, check in enumerate(probe.checks)
                    ]
                else:
                    raise HealthCheckTimeoutError(code=PROBE_TIMEOUT) from None

        report = HealthCheckReport(
            results=results,
        )
        get_probe_logger().log(
            logging.INFO,
            "probe_end",
            probe=probe.name,
            healthy=report.healthy,
            results_summary=[(r.name, r.healthy) for r in results],
        )
        return report
    finally:
        # Cleanup of cached clients is not done here; caller must call
        # healthcheck_shutdown(probes) or close_probes(probes). See lifecycle docs.
        pass


async def close_probes(probes: Iterable[Probe]) -> None:
    """Close resources owned by checks in the given probes.

    Calls ``aclose()`` on each check that has it (e.g. checks with cached
    clients). Ignores exceptions so one failure does not block others.
    After closing, yields to the event loop a few times so that any
    transport/socket cleanup callbacks (e.g. from aiohttp connector) can run
    before the caller's context is torn down (avoids unclosed-resource
    warnings in tests).

    Args:
        probes: Probes whose checks should be closed.
    """
    for probe in probes:
        for check in probe.checks:
            aclose = getattr(check, "aclose", None)
            if callable(aclose):
                with contextlib.suppress(Exception):
                    maybe_awaitable = aclose()
                    if isinstance(maybe_awaitable, Awaitable):
                        await maybe_awaitable
    # aiohttp (opensearch-py) may schedule cleanup across multiple loop turns.
    # Yield a few times so transport/socket finalizers run before teardown.
    await asyncio.sleep(0.1)


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
