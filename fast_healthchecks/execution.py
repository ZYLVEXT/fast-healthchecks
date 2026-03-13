"""Execution primitives and policy models for healthchecks."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal, TypeAlias

from fast_healthchecks.integrations.base import close_probes, run_probe
from fast_healthchecks.models import HealthCheckReport

if TYPE_CHECKING:
    from types import TracebackType

    from fast_healthchecks.integrations.base import Probe

RunMode: TypeAlias = Literal["strict", "reporting"]
ExecutionMode: TypeAlias = Literal["parallel", "sequential"]
HealthEvaluationMode: TypeAlias = Literal["all_required", "partial_allowed"]

_VALID_RUN_MODES: frozenset[str] = frozenset({"strict", "reporting"})
_VALID_EXECUTION_MODES: frozenset[str] = frozenset({"parallel", "sequential"})
_VALID_HEALTH_EVALUATIONS: frozenset[str] = frozenset({"all_required", "partial_allowed"})


async def _noop_on_check_start(_check: object, _index: int) -> None:
    await asyncio.sleep(0)


@dataclass(frozen=True)
class RunPolicy:
    """Immutable policy controlling probe execution behavior.

    Attributes:
        mode: Controls how probe failures affect overall health status.
            - "strict": Any failure marks the health check as failed
            - "reporting": Failures are reported but don't fail the check
        execution: Controls how probes are executed.
            - "parallel": All probes run concurrently
            - "sequential": Probes run one at a time
        probe_timeout_ms: Optional timeout in milliseconds for each probe.
            If None, probes use their default timeout.
        health_evaluation: Controls evaluation strategy.
            - "all_required": All probes must pass for overall health
            - "partial_allowed": Some probes can fail without failing overall
    """

    mode: RunMode = "strict"
    execution: ExecutionMode = "parallel"
    probe_timeout_ms: int | None = None
    health_evaluation: HealthEvaluationMode = "all_required"

    def __post_init__(self) -> None:
        """Validate policy values.

        Raises:
            ValueError: If mode/execution/health_evaluation is invalid or timeout is non-positive.
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


@dataclass(frozen=True)
class ProbeRunner:
    """Immutable runner that executes probes according to RunPolicy.

    Use as an async context manager to ensure proper resource cleanup:

        async with ProbeRunner(policy) as runner:
            report = await runner.run(probe)

    Attributes:
        policy: RunPolicy instance controlling execution behavior.
        _probes: Internal list of probes that have been registered with this runner.
        _probe_ids: Internal set of probe object IDs for deduplication.
    """

    policy: RunPolicy = field(default_factory=RunPolicy)
    _probes: list[Probe] = field(default_factory=list, init=False, repr=False, compare=False)
    _probe_ids: set[int] = field(default_factory=set, init=False, repr=False, compare=False)

    async def __aenter__(self) -> ProbeRunner:  # noqa: PYI034
        """Return self for async context-manager usage."""
        return self

    async def __aexit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _tb: TracebackType | None,
    ) -> None:
        """Always close managed probes on context exit."""
        await self.close()

    async def run(self, probe: Probe) -> HealthCheckReport:
        """Run probe checks and return a report.

        Args:
            probe: Probe with checks to execute.

        Returns:
            HealthCheckReport for the probe run.
        """
        probe_id = id(probe)
        if probe_id not in self._probe_ids:
            self._probe_ids.add(probe_id)
            self._probes.append(probe)

        timeout = None
        if self.policy.probe_timeout_ms is not None:
            timeout = self.policy.probe_timeout_ms / 1000

        on_check_start = _noop_on_check_start if self.policy.execution == "sequential" else None

        report = await run_probe(
            probe,
            timeout=timeout,
            on_check_start=on_check_start,
            on_timeout_return_failure=self.policy.mode == "reporting",
        )

        if self.policy.health_evaluation == "partial_allowed":
            return HealthCheckReport(results=report.results, allow_partial_failure=True)
        return report

    async def close(self) -> None:
        """Close resources for probes executed by this runner."""
        await close_probes(self._probes)


__all__ = (
    "ExecutionMode",
    "HealthEvaluationMode",
    "ProbeRunner",
    "RunMode",
    "RunPolicy",
)
