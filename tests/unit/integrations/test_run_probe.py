"""Tests for run_probe function."""

import asyncio

import pytest

from fast_healthchecks.checks.function import FunctionHealthCheck
from fast_healthchecks.integrations.base import Probe, ProbeAsgi, run_probe
from fast_healthchecks.models import HealthCheckReport, HealthCheckResult

pytestmark = pytest.mark.unit

EXPECTED_RESULTS_COUNT = 2
UNHEALTHY_STATUS_CODE = 503


def _success_check() -> bool:
    return True


def _failure_check() -> bool:
    msg = "Failed"
    raise ValueError(msg) from None


class _RaisingCheck:
    """Check that raises directly (no internal exception handling)."""

    _ERROR_MSG = "Check failed"

    def __init__(self, name: str = "Raising") -> None:
        self._name = name

    async def __call__(self) -> HealthCheckResult:
        raise RuntimeError(self._ERROR_MSG)


@pytest.mark.asyncio
async def test_run_probe_success() -> None:
    """Test run_probe with all checks passing."""
    probe = Probe(
        name="test",
        checks=[
            FunctionHealthCheck(func=_success_check, name="Check 1"),
            FunctionHealthCheck(func=_success_check, name="Check 2"),
        ],
    )
    report = await run_probe(probe)
    assert isinstance(report, HealthCheckReport)
    assert report.healthy is True
    assert len(report.results) == EXPECTED_RESULTS_COUNT
    assert all(r.healthy for r in report.results)


@pytest.mark.asyncio
async def test_run_probe_failure() -> None:
    """Test run_probe with one check failing."""
    probe = Probe(
        name="test",
        checks=[
            FunctionHealthCheck(func=_success_check, name="Check 1"),
            FunctionHealthCheck(func=_failure_check, name="Check 2"),
        ],
    )
    report = await run_probe(probe)
    assert report.healthy is False
    assert report.results[0].healthy is True
    assert report.results[1].healthy is False
    assert report.results[1].error_details is not None


@pytest.mark.asyncio
async def test_run_probe_allow_partial_failure() -> None:
    """Test run_probe with allow_partial_failure=True."""
    probe = Probe(
        name="test",
        checks=[
            FunctionHealthCheck(func=_success_check, name="Check 1"),
            FunctionHealthCheck(func=_failure_check, name="Check 2"),
        ],
        allow_partial_failure=True,
    )
    report = await run_probe(probe)
    assert report.healthy is True
    assert report.results[0].healthy is True
    assert report.results[1].healthy is False


@pytest.mark.asyncio
async def test_run_probe_with_hooks() -> None:
    """Test run_probe with on_check_start and on_check_end hooks."""
    started: list[tuple[int, str]] = []
    ended: list[tuple[int, str, bool]] = []

    async def on_start(check: object, index: int) -> None:
        await asyncio.sleep(0)
        started.append((index, getattr(check, "_name", str(check))))

    async def on_end(_check: object, index: int, result: HealthCheckResult) -> None:
        await asyncio.sleep(0)
        ended.append((index, result.name, result.healthy))

    probe = Probe(
        name="test",
        checks=[
            FunctionHealthCheck(func=_success_check, name="A"),
            FunctionHealthCheck(func=_failure_check, name="B"),
        ],
    )
    report = await run_probe(probe, on_check_start=on_start, on_check_end=on_end)

    assert started == [(0, "A"), (1, "B")]
    assert ended == [(0, "A", True), (1, "B", False)]
    assert report.healthy is False


@pytest.mark.asyncio
async def test_run_probe_with_timeout() -> None:
    """Test run_probe with timeout parameter."""
    probe = Probe(
        name="test",
        checks=[
            FunctionHealthCheck(func=_success_check, name="Check 1"),
            FunctionHealthCheck(func=_success_check, name="Check 2"),
        ],
    )
    report = await run_probe(probe, timeout=10.0)
    assert report.healthy is True
    assert len(report.results) == EXPECTED_RESULTS_COUNT


@pytest.mark.asyncio
async def test_run_probe_with_hooks_and_timeout() -> None:
    """Test run_probe with hooks and timeout."""

    async def noop_start(_c: object, _i: int) -> None:
        await asyncio.sleep(0)

    async def noop_end(_c: object, _i: int, _r: HealthCheckResult) -> None:
        await asyncio.sleep(0)

    probe = Probe(
        name="test",
        checks=[
            FunctionHealthCheck(func=_success_check, name="A"),
        ],
    )
    report = await run_probe(
        probe,
        timeout=5.0,
        on_check_start=noop_start,
        on_check_end=noop_end,
    )
    assert report.healthy is True


@pytest.mark.asyncio
async def test_run_probe_hook_exception_handling() -> None:
    """Test run_probe when a check raises (hooks path, exception handling)."""

    async def noop_end(_c: object, _i: int, _r: HealthCheckResult) -> None:
        await asyncio.sleep(0)

    probe = Probe(
        name="test",
        checks=[
            _RaisingCheck(name="Failing"),
        ],
    )
    report = await run_probe(probe, on_check_end=noop_end)
    assert report.healthy is False
    assert len(report.results) == 1
    assert report.results[0].healthy is False
    assert "RuntimeError" in (report.results[0].error_details or "")


@pytest.mark.asyncio
async def test_run_probe_parallel_exception_handling() -> None:
    probe = Probe(
        name="test",
        checks=[
            _RaisingCheck(name="Failing"),
        ],
    )
    report = await run_probe(probe)
    assert report.healthy is False
    assert len(report.results) == 1
    assert report.results[0].name == "Failing"
    assert report.results[0].healthy is False
    assert "RuntimeError" in (report.results[0].error_details or "")


@pytest.mark.asyncio
async def test_probe_asgi_exception_handling() -> None:
    probe = Probe(
        name="test",
        checks=[
            _RaisingCheck(name="Failing"),
        ],
    )
    asgi_probe = ProbeAsgi(probe)
    content, headers, status = await asgi_probe()
    assert content == b""
    assert headers is None
    assert status == UNHEALTHY_STATUS_CODE
