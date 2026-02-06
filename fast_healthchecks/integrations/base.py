"""Base classes for integrations."""

from __future__ import annotations

import asyncio
import contextlib
import json
import re
from collections.abc import Awaitable, Callable, Iterable, Sequence
from dataclasses import asdict
from http import HTTPStatus
from traceback import format_exc
from typing import Any, NamedTuple, TypeAlias

from fast_healthchecks.checks.types import Check
from fast_healthchecks.models import HealthCheckReport, HealthCheckResult

HandlerType: TypeAlias = Callable[..., Awaitable[dict[str, Any] | None]]

OnCheckStart: TypeAlias = Callable[[Check, int], Awaitable[None]]
OnCheckEnd: TypeAlias = Callable[[Check, int, HealthCheckResult], Awaitable[None]]


class Probe(NamedTuple):
    """A probe is a collection of health checks that can be run together.

    Args:
        name: The name of the probe.
        checks: A sequence of health checks to run.
        summary: A summary of the probe. If not provided, a default summary will be generated.
        allow_partial_failure: If True, probe is healthy when at least one check passes.
    """

    name: str
    checks: Sequence[Check]
    summary: str | None = None
    allow_partial_failure: bool = False

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


class ProbeAsgiResponse(NamedTuple):
    """A response from an ASGI probe.

    Args:
        data: The response data (healthcheck results).
        healthy: Whether all healthchecks passed.
    """

    data: dict[str, Any]
    healthy: bool


async def default_handler(response: ProbeAsgiResponse) -> dict[str, Any] | None:
    """Default handler for health check route.

    Args:
        response: The response from the probe.

    Returns:
        The response data, or None for no response body.
    """
    _ = response
    await asyncio.sleep(0)
    return None


def _get_check_name(check: Check, index: int) -> str:
    return getattr(check, "_name", f"Check-{index}")


async def _run_check_safe(check: Check, index: int) -> HealthCheckResult:
    try:
        return await check()
    except Exception:  # noqa: BLE001
        return HealthCheckResult(name=_get_check_name(check, index), healthy=False, error_details=format_exc())


class ProbeAsgi:
    """An ASGI probe.

    Args:
        probe: The probe to run.
        success_handler: The handler to use for successful responses.
        failure_handler: The handler to use for failed responses.
        success_status: The status code to use for successful responses.
        failure_status: The status code to use for failed responses.
        debug: Whether to include debug information in the response.
    """

    __slots__ = (
        "_debug",
        "_exclude_fields",
        "_failure_handler",
        "_failure_status",
        "_map_handler",
        "_map_status",
        "_probe",
        "_success_handler",
        "_success_status",
    )

    _probe: Probe
    _success_handler: HandlerType
    _failure_handler: HandlerType
    _success_status: int
    _failure_status: int
    _debug: bool
    _exclude_fields: set[str]
    _map_status: dict[bool, int]
    _map_handler: dict[bool, HandlerType]

    def __init__(  # noqa: PLR0913
        self,
        probe: Probe,
        *,
        success_handler: HandlerType = default_handler,
        failure_handler: HandlerType = default_handler,
        success_status: int = HTTPStatus.NO_CONTENT,
        failure_status: int = HTTPStatus.SERVICE_UNAVAILABLE,
        debug: bool = False,
    ) -> None:
        """Initialize the ASGI probe."""
        self._probe = probe
        self._success_handler = success_handler
        self._failure_handler = failure_handler
        self._success_status = success_status
        self._failure_status = failure_status
        self._debug = debug
        self._exclude_fields = {"allow_partial_failure", "error_details"} if not debug else set()
        self._map_status = {True: success_status, False: failure_status}
        self._map_handler = {True: success_handler, False: failure_handler}

    async def __call__(self) -> tuple[bytes, dict[str, str] | None, int]:
        """Run the probe.

        Returns:
            A tuple containing the response body, headers, and status code.
        """
        tasks = [_run_check_safe(check, i) for i, check in enumerate(self._probe.checks)]
        results = list(await asyncio.gather(*tasks))
        report = HealthCheckReport(
            results=results,
            allow_partial_failure=self._probe.allow_partial_failure,
        )
        response = ProbeAsgiResponse(
            data=asdict(
                report,
                dict_factory=lambda x: {k: v for (k, v) in x if k not in self._exclude_fields},
            ),
            healthy=report.healthy,
        )

        actual_status = self._map_status[response.healthy]
        content_needed = actual_status not in {
            HTTPStatus.NO_CONTENT,
            HTTPStatus.NOT_MODIFIED,
        } and not (response.healthy and actual_status < HTTPStatus.OK)

        content = b""
        headers = None
        if content_needed:
            handler = self._map_handler[response.healthy]
            content_ = await handler(response)
            if content_ is not None:
                content = json.dumps(
                    content_,
                    ensure_ascii=False,
                    allow_nan=False,
                    indent=None,
                    separators=(",", ":"),
                ).encode("utf-8")
                headers = {
                    "content-type": "application/json",
                    "content-length": str(len(content)),
                }

        return content, headers, self._map_status[response.healthy]


def make_probe_asgi(  # noqa: PLR0913
    probe: Probe,
    *,
    success_handler: HandlerType = default_handler,
    failure_handler: HandlerType = default_handler,
    success_status: int = HTTPStatus.NO_CONTENT,
    failure_status: int = HTTPStatus.SERVICE_UNAVAILABLE,
    debug: bool = False,
) -> Callable[[], Awaitable[tuple[bytes, dict[str, str] | None, int]]]:
    """Create an ASGI probe from a probe.

    Args:
        probe: The probe to create the ASGI probe from.
        success_handler: The handler to use for successful responses.
        failure_handler: The handler to use for failed responses.
        success_status: The status code to use for successful responses.
        failure_status: The status code to use for failed responses.
        debug: Whether to include debug information in the response.

    Returns:
        An ASGI probe.
    """
    return ProbeAsgi(
        probe,
        success_handler=success_handler,
        failure_handler=failure_handler,
        success_status=success_status,
        failure_status=failure_status,
        debug=debug,
    )


async def run_probe(
    probe: Probe,
    *,
    timeout: float | None = None,
    on_check_start: OnCheckStart | None = None,
    on_check_end: OnCheckEnd | None = None,
) -> HealthCheckReport:
    """Run a probe and return the health check report.

    Can be used without ASGI (CLI, cron, tests).

    Args:
        probe: The probe to run.
        timeout: Maximum seconds for all checks. Raises asyncio.TimeoutError if exceeded.
        on_check_start: Optional callback before each check runs. Receives (check, index).
        on_check_end: Optional callback after each check completes. Receives (check, index, result).

    Returns:
        HealthCheckReport with results from all checks.
    """
    if on_check_start is None and on_check_end is None:
        tasks = [_run_check_safe(check, i) for i, check in enumerate(probe.checks)]
        if timeout is not None:
            results: list[HealthCheckResult] = await asyncio.wait_for(
                asyncio.gather(*tasks),
                timeout=timeout,
            )
        else:
            results = await asyncio.gather(*tasks)
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

        if timeout is not None:
            results = await asyncio.wait_for(_run_with_hooks(), timeout=timeout)
        else:
            results = await _run_with_hooks()

    return HealthCheckReport(
        results=list(results),
        allow_partial_failure=probe.allow_partial_failure,
    )


async def close_probes(probes: Iterable[Probe]) -> None:
    """Close resources owned by checks in the given probes.

    Calls ``aclose()`` on each check that has it (e.g. checks with cached
    clients). Ignores exceptions so one failure does not block others.

    Args:
        probes: Probes whose checks should be closed.
    """
    for probe in probes:
        for check in probe.checks:
            aclose = getattr(check, "aclose", None)
            if callable(aclose):
                with contextlib.suppress(Exception):
                    await aclose()


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
