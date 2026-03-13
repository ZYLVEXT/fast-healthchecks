"""Tests for execution-layer policy models."""

import asyncio
from collections.abc import Callable
from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from fast_healthchecks.checks.function import FunctionHealthCheck
from fast_healthchecks.errors import PROBE_TIMEOUT
from fast_healthchecks.execution import (
    ExecutionMode,
    HealthEvaluationMode,
    ProbeRunner,
    RunMode,
    RunPolicy,
)
from fast_healthchecks.integrations.base import Probe
from fast_healthchecks.models import HealthCheckReport, HealthCheckTimeoutError
from tests.unit.integrations.helpers import CheckWithAclose

pytestmark = pytest.mark.unit

MIN_PARALLEL_CONCURRENCY = 2


def test_run_policy_defaults() -> None:
    """RunPolicy has expected v1 defaults."""
    policy = RunPolicy()
    assert policy.mode == "strict"
    assert policy.execution == "parallel"
    assert policy.probe_timeout_ms is None
    assert policy.health_evaluation == "all_required"


def test_run_policy_is_immutable() -> None:
    """RunPolicy is frozen and disallows mutation."""
    policy = RunPolicy()
    with pytest.raises(FrozenInstanceError):
        policy.mode = "reporting"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("factory", "expected_message"),
    [
        (
            lambda: RunPolicy(mode=cast("RunMode", "invalid")),
            "Invalid run mode",
        ),
        (
            lambda: RunPolicy(execution=cast("ExecutionMode", "invalid")),
            "Invalid execution mode",
        ),
        (
            lambda: RunPolicy(health_evaluation=cast("HealthEvaluationMode", "invalid")),
            "Invalid health evaluation mode",
        ),
        (lambda: RunPolicy(probe_timeout_ms=0), "probe_timeout_ms must be > 0 when provided"),
        (lambda: RunPolicy(probe_timeout_ms=-1), "probe_timeout_ms must be > 0 when provided"),
    ],
)
def test_run_policy_validation(factory: Callable[[], RunPolicy], expected_message: str) -> None:
    """RunPolicy validates enum-like fields and timeout constraints."""
    with pytest.raises(ValueError, match=expected_message):
        factory()


@pytest.mark.asyncio
async def test_probe_runner_run_returns_health_check_report() -> None:
    """ProbeRunner.run executes in parallel and preserves input result order."""
    running = 0
    max_running = 0

    async def _slow() -> bool:
        nonlocal running, max_running
        running += 1
        max_running = max(max_running, running)
        await asyncio.sleep(0.03)
        running -= 1
        return True

    async def _fast() -> bool:
        nonlocal running, max_running
        running += 1
        max_running = max(max_running, running)
        await asyncio.sleep(0.005)
        running -= 1
        return True

    probe = Probe(
        name="ready",
        checks=[
            FunctionHealthCheck(func=_slow, name="Slow"),
            FunctionHealthCheck(func=_fast, name="Fast"),
        ],
    )
    runner = ProbeRunner(policy=RunPolicy())

    report = await runner.run(probe)

    assert isinstance(report, HealthCheckReport)
    assert [result.name for result in report.results] == ["Slow", "Fast"]
    assert max_running >= MIN_PARALLEL_CONCURRENCY


@pytest.mark.asyncio
async def test_probe_runner_accepts_run_policy_in_constructor() -> None:
    """ProbeRunner stores constructor policy and applies timeout mode."""

    async def _slow() -> bool:
        await asyncio.sleep(0.05)
        return True

    probe = Probe(
        name="ready",
        checks=[FunctionHealthCheck(func=_slow, name="Slow")],
    )
    policy = RunPolicy(mode="reporting", probe_timeout_ms=1)
    runner = ProbeRunner(policy=policy)

    report = await runner.run(probe)

    assert runner.policy == policy
    assert report.healthy is False
    assert report.results[0].error is not None
    assert report.results[0].error.code == "PROBE_TIMEOUT"


@pytest.mark.asyncio
async def test_probe_runner_strict_timeout_raises_probe_timeout_exception() -> None:
    """Strict mode raises timeout exception with PROBE_TIMEOUT code."""

    async def _slow() -> bool:
        await asyncio.sleep(0.05)
        return True

    probe = Probe(
        name="ready",
        checks=[FunctionHealthCheck(func=_slow, name="Slow")],
    )
    runner = ProbeRunner(policy=RunPolicy(mode="strict", probe_timeout_ms=1))

    with pytest.raises(HealthCheckTimeoutError, match="Probe timed out") as exc_info:
        await runner.run(probe)

    assert exc_info.value.code == PROBE_TIMEOUT


@pytest.mark.asyncio
async def test_probe_runner_partial_allowed_policy_changes_report_health() -> None:
    """ProbeRunner applies health evaluation policy to report result."""

    def _ok() -> bool:
        return True

    def _fail() -> bool:
        msg = "failed"
        raise ValueError(msg)

    probe = Probe(
        name="ready",
        checks=[
            FunctionHealthCheck(func=_ok, name="Check 1"),
            FunctionHealthCheck(func=_fail, name="Check 2"),
        ],
    )
    runner = ProbeRunner(policy=RunPolicy(health_evaluation="partial_allowed"))

    report = await runner.run(probe)

    assert report.healthy is True


def test_probe_runner_is_immutable() -> None:
    """ProbeRunner is frozen and disallows mutation."""
    runner = ProbeRunner()
    with pytest.raises(FrozenInstanceError):
        runner.policy = RunPolicy(mode="reporting")  # type: ignore[misc]


@pytest.mark.asyncio
async def test_probe_runner_close_closes_aclose_compatible_checks() -> None:
    """ProbeRunner.close closes checks from probes it has run."""
    check = CheckWithAclose(name="A")
    probe = Probe(name="ready", checks=[check])
    runner = ProbeRunner()

    await runner.run(probe)
    await runner.close()

    check._aclose_mock.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_probe_runner_async_context_closes_on_exception() -> None:
    """Async context manager closes checks even when an exception is raised."""
    check = CheckWithAclose(name="A")
    probe = Probe(name="ready", checks=[check])

    async def _run_and_raise() -> None:
        async with ProbeRunner() as runner:
            await runner.run(probe)
            msg = "boom"
            raise RuntimeError(msg)

    with pytest.raises(RuntimeError, match="boom"):
        await _run_and_raise()

    check._aclose_mock.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_probe_runner_sequential_execution() -> None:
    """Sequential mode runs checks one at a time in input order."""

    async def _first() -> bool:
        await asyncio.sleep(0)
        return True

    async def _second() -> bool:
        await asyncio.sleep(0)
        return True

    probe = Probe(
        name="ready",
        checks=[
            FunctionHealthCheck(func=_first, name="First"),
            FunctionHealthCheck(func=_second, name="Second"),
        ],
    )
    runner = ProbeRunner(policy=RunPolicy(execution="sequential"))

    report = await runner.run(probe)

    assert [result.name for result in report.results] == ["First", "Second"]
    assert all(result.healthy for result in report.results)
