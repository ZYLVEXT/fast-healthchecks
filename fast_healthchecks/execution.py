"""Framework-neutral probe execution and lifecycle primitives."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import re
from collections.abc import Awaitable, Callable, Iterable, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal, NamedTuple, TypeAlias

from fast_healthchecks.checks._base import result_on_error
from fast_healthchecks.checks.types import Check
from fast_healthchecks.errors import PROBE_TIMEOUT, map_exception_to_health_error
from fast_healthchecks.logging import get_probe_logger, is_probe_logging_enabled
from fast_healthchecks.models import (
    HealthCheckReport,
    HealthCheckResult,
    HealthCheckTimeoutError,
)

if TYPE_CHECKING:
    from types import TracebackType

RunMode: TypeAlias = Literal["strict", "reporting"]
ExecutionMode: TypeAlias = Literal["parallel", "sequential"]
HealthEvaluationMode: TypeAlias = Literal["all_required", "partial_allowed"]
OnCheckStart: TypeAlias = Callable[[Check, int], Awaitable[None]]
OnCheckEnd: TypeAlias = Callable[[Check, int, HealthCheckResult], Awaitable[None]]

_VALID_RUN_MODES: frozenset[str] = frozenset({"strict", "reporting"})
_VALID_EXECUTION_MODES: frozenset[str] = frozenset({"parallel", "sequential"})
_VALID_HEALTH_EVALUATIONS: frozenset[str] = frozenset({"all_required", "partial_allowed"})

DEFAULT_MAX_CONCURRENCY: int = 8


class Probe(NamedTuple):
    """A named sequence of health checks executed as one probe."""

    name: str
    checks: Sequence[Check]
    summary: str | None = None
    default_check_timeout_ms: int | None = None

    @property
    def endpoint_summary(self) -> str:
        """The explicit summary or a readable summary derived from the route."""
        if self.summary:
            return self.summary
        title = re.sub(
            pattern=r"[^a-z0-9]+",
            repl=" ",
            string=self.name.lower().capitalize(),
            flags=re.IGNORECASE,
        )
        return f"{title} probe"


def _get_check_name(check: Check, index: int) -> str:
    return getattr(check, "name", None) or getattr(check, "_name", f"Check-{index}")


async def _run_check_safe(check: Check, index: int) -> HealthCheckResult:
    """Run one check and convert ordinary failures to a result.

    Returns:
        The check result or a structured failure result.

    Raises:
        asyncio.CancelledError: If the caller cancels execution.
        KeyboardInterrupt: If the process receives an interrupt.
        SystemExit: If the check requests process termination.
    """
    name = _get_check_name(check, index)
    logging_enabled = is_probe_logging_enabled()
    logger = get_probe_logger() if logging_enabled else None
    if logger is not None:
        logger.log(logging.DEBUG, "check_start", check_name=name, index=index)
    try:
        result = await check()
        if logger is not None:
            logger.log(
                logging.DEBUG,
                "check_end",
                check_name=result.name,
                index=index,
                healthy=result.healthy,
                error=result.error_details,
            )
        return result  # ruff: ignore[try-consider-else] - the success path stays next to the call it describes
    except (asyncio.CancelledError, SystemExit, KeyboardInterrupt):
        raise
    except Exception as exc:  # ruff: ignore[blind-except] - any failure becomes a structured result
        result = result_on_error(name, exc)
        if logger is not None:
            logger.log(
                logging.DEBUG,
                "check_end",
                check_name=name,
                index=index,
                healthy=False,
                error=result.error_details,
            )
        return result


def _timeout_results(probe: Probe) -> list[HealthCheckResult]:
    return [
        HealthCheckResult(
            name=_get_check_name(check, index),
            healthy=False,
            error=map_exception_to_health_error(
                HealthCheckTimeoutError("Probe timed out"),
                code=PROBE_TIMEOUT,
            ),
        )
        for index, check in enumerate(probe.checks)
    ]


async def _run_parallel(probe: Probe, *, max_concurrency: int | None = None) -> list[HealthCheckResult]:
    if len(probe.checks) == 1:
        return [await _run_check_safe(probe.checks[0], 0)]
    if max_concurrency is None:
        return list(
            await asyncio.gather(
                *(_run_check_safe(check, index) for index, check in enumerate(probe.checks)),
            ),
        )
    semaphore = asyncio.Semaphore(max_concurrency)

    async def run_limited(check: Check, index: int) -> HealthCheckResult:
        async with semaphore:
            return await _run_check_safe(check, index)

    return list(
        await asyncio.gather(
            *(run_limited(check, index) for index, check in enumerate(probe.checks)),
        ),
    )


async def _run_sequential(
    probe: Probe,
    *,
    on_check_start: OnCheckStart | None,
    on_check_end: OnCheckEnd | None,
) -> list[HealthCheckResult]:
    results: list[HealthCheckResult] = []
    for index, check in enumerate(probe.checks):
        if on_check_start is not None:
            await on_check_start(check, index)
        result = await _run_check_safe(check, index)
        if on_check_end is not None:
            await on_check_end(check, index, result)
        results.append(result)
    return results


async def run_probe(  # ruff: ignore[too-many-arguments] - explicit options; bundling them would hide the surface
    probe: Probe,
    *,
    timeout: float | None = None,
    execution: ExecutionMode = "parallel",
    max_concurrency: int | None = DEFAULT_MAX_CONCURRENCY,
    on_check_start: OnCheckStart | None = None,
    on_check_end: OnCheckEnd | None = None,
    on_timeout_return_failure: bool = False,
) -> HealthCheckReport:
    """Run a probe without importing an HTTP or framework integration.

    ``max_concurrency`` caps how many checks run at once in parallel mode
    (default 8); ``None`` removes the cap. Sequential mode ignores it.

    Returns:
        A report containing results in input order.

    Raises:
        HealthCheckTimeoutError: If the probe times out in strict mode.
    """
    logging_enabled = is_probe_logging_enabled()
    logger = get_probe_logger() if logging_enabled else None
    if logger is not None:
        logger.log(logging.INFO, "probe_start", probe=probe.name, checks_count=len(probe.checks))

    sequential = execution == "sequential" or on_check_start is not None or on_check_end is not None
    execution_awaitable = (
        _run_sequential(probe, on_check_start=on_check_start, on_check_end=on_check_end)
        if sequential
        else _run_parallel(probe, max_concurrency=max_concurrency)
    )
    try:
        results = (
            await asyncio.wait_for(execution_awaitable, timeout=timeout)
            if timeout is not None
            else await execution_awaitable
        )
    except asyncio.TimeoutError:
        if on_timeout_return_failure:
            results = _timeout_results(probe)
        else:
            raise HealthCheckTimeoutError(code=PROBE_TIMEOUT) from None

    report = HealthCheckReport(results=results)
    if logger is not None:
        logger.log(
            logging.INFO,
            "probe_end",
            probe=probe.name,
            healthy=report.healthy,
            results_summary=[(result.name, result.healthy) for result in results],
        )
    return report


async def _close_checks(checks: Iterable[object]) -> bool:
    closed_ids: set[int] = set()
    closed_resource = False
    for check in checks:
        check_id = id(check)
        if check_id in closed_ids:
            continue
        closed_ids.add(check_id)
        aclose = getattr(check, "aclose", None)
        if callable(aclose):
            closed_resource = True
            with contextlib.suppress(Exception):
                await aclose()
    return closed_resource


async def close_probes(probes: Iterable[Probe]) -> None:
    """Close unique check resources and give transports one cleanup grace period."""
    if await _close_checks(check for probe in probes for check in probe.checks):
        await asyncio.sleep(0.1)


@dataclass(frozen=True)
class RunPolicy:
    """Immutable policy controlling probe execution behavior.

    ``max_concurrency`` caps how many checks run at once in parallel mode
    (default 8); ``None`` removes the cap.
    """

    mode: RunMode = "strict"
    execution: ExecutionMode = "parallel"
    probe_timeout_ms: int | None = None
    health_evaluation: HealthEvaluationMode = "all_required"
    max_concurrency: int | None = DEFAULT_MAX_CONCURRENCY

    def __post_init__(self) -> None:
        """Validate policy values.

        Raises:
            ValueError: If a mode is unknown, the timeout is not positive, or
                max_concurrency is not positive.
        """
        if self.mode not in _VALID_RUN_MODES:
            msg = f"Invalid run mode: {self.mode}"
            raise ValueError(msg)
        if self.execution not in _VALID_EXECUTION_MODES:
            msg = f"Invalid execution mode: {self.execution}"
            raise ValueError(msg)
        if self.health_evaluation not in _VALID_HEALTH_EVALUATIONS:
            msg = f"Invalid health evaluation mode: {self.health_evaluation}"
            raise ValueError(msg)
        if self.probe_timeout_ms is not None and self.probe_timeout_ms <= 0:
            msg = "probe_timeout_ms must be > 0 when provided"
            raise ValueError(msg)
        if self.max_concurrency is not None and self.max_concurrency <= 0:
            msg = "max_concurrency must be > 0 when provided"
            raise ValueError(msg)


@dataclass(frozen=True)
class ProbeRunner:
    """Execute probes and close only resource-owning checks seen by the runner.

    The runner owns the lifecycle of resource checks it has seen: ``close()``
    and resource tracking are serialized by an internal lock so a concurrent
    ``close()`` cannot race registration. Probe execution itself is not
    locked; concurrent ``run()`` calls proceed in parallel.
    """

    policy: RunPolicy = field(default_factory=RunPolicy)
    _resource_checks: list[object] = field(default_factory=list, init=False, repr=False, compare=False)
    _resource_check_ids: set[int] = field(default_factory=set, init=False, repr=False, compare=False)
    _resources_lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False, compare=False)

    async def __aenter__(self) -> ProbeRunner:  # ruff: ignore[non-self-return-type] - returns the concrete subclass by design
        """Return self for async context-manager usage."""
        return self

    async def __aexit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _tb: TracebackType | None,
    ) -> None:
        """Always close managed checks on context exit."""
        await self.close()

    def _track_resources(self, probe: Probe) -> None:
        for check in probe.checks:
            check_id = id(check)
            if check_id in self._resource_check_ids or not callable(getattr(check, "aclose", None)):
                continue
            self._resource_check_ids.add(check_id)
            self._resource_checks.append(check)

    async def run(self, probe: Probe) -> HealthCheckReport:
        """Run probe checks and return a report.

        Returns:
            The evaluated health-check report.
        """
        async with self._resources_lock:
            self._track_resources(probe)
        timeout = None if self.policy.probe_timeout_ms is None else self.policy.probe_timeout_ms / 1000
        report = await run_probe(
            probe,
            timeout=timeout,
            execution=self.policy.execution,
            max_concurrency=self.policy.max_concurrency,
            on_timeout_return_failure=self.policy.mode == "reporting",
        )
        if self.policy.health_evaluation == "partial_allowed":
            return HealthCheckReport(results=report.results, allow_partial_failure=True)
        return report

    async def close(self) -> None:
        """Close resource-owning checks observed by this runner."""
        async with self._resources_lock:
            if await _close_checks(self._resource_checks):
                await asyncio.sleep(0.1)
            self._resource_checks.clear()
            self._resource_check_ids.clear()


__all__ = (
    "DEFAULT_MAX_CONCURRENCY",
    "ExecutionMode",
    "HealthEvaluationMode",
    "Probe",
    "ProbeRunner",
    "RunMode",
    "RunPolicy",
    "close_probes",
    "run_probe",
)
