"""Tests for run_probe function."""

import asyncio
import json

import pytest

from fast_healthchecks.checks.function import FunctionHealthCheck
from fast_healthchecks.integrations.base import (
    Probe,
    ProbeAsgi,
    build_probe_route_options,
    healthcheck_shutdown,
    run_probe,
)
from fast_healthchecks.models import HealthCheckReport, HealthCheckResult, HealthError
from tests.unit.integrations.helpers import CheckWithAclose

pytestmark = pytest.mark.unit

EXPECTED_RESULTS_COUNT = 2
UNHEALTHY_STATUS_CODE = 503


def _success_check() -> bool:
    """Return True for success tests.

    Returns:
        True.
    """
    return True


def _failure_check() -> bool:
    """Raise ValueError for failure tests.

    Raises:
        ValueError: Always.
    """
    msg = "Failed"
    raise ValueError(msg) from None


class _RaisingCheck:
    """Check that raises directly (no internal exception handling)."""

    _ERROR_MSG = "Check failed"

    def __init__(self, name: str = "Raising") -> None:
        """Store name for the raising check."""
        self._name = name

    async def __call__(self) -> HealthCheckResult:
        """Raise RuntimeError.

        Raises:
            RuntimeError: Always.
        """
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
    assert report.results[1].error is not None


@pytest.mark.asyncio
async def test_run_probe_is_unhealthy_when_any_check_fails() -> None:
    """run_probe marks report unhealthy when any check fails."""
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


@pytest.mark.asyncio
async def test_run_probe_with_hooks() -> None:
    """Test run_probe with on_check_start and on_check_end hooks."""
    started: list[tuple[int, str]] = []
    ended: list[tuple[int, str, bool]] = []

    async def on_start(check: object, index: int) -> None:
        """Callback invoked before each check runs."""
        await asyncio.sleep(0)
        started.append((index, getattr(check, "_name", str(check))))

    async def on_end(_check: object, index: int, result: HealthCheckResult) -> None:
        """Callback invoked after each check completes."""
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
        """No-op callback before check."""
        await asyncio.sleep(0)

    async def noop_end(_c: object, _i: int, _r: HealthCheckResult) -> None:
        """No-op callback after check."""
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
async def test_run_probe_with_hooks_timeout_returns_failure_when_requested() -> None:
    """run_probe with hooks and timeout returns report with failures when on_timeout_return_failure=True."""

    async def slow_start(_c: object, _i: int) -> None:
        await asyncio.sleep(10)

    probe = Probe(
        name="test",
        checks=[
            FunctionHealthCheck(func=_success_check, name="A"),
        ],
    )
    report = await run_probe(
        probe,
        timeout=0.05,
        on_check_start=slow_start,
        on_timeout_return_failure=True,
    )
    assert report.healthy is False
    assert len(report.results) == 1
    assert report.results[0].healthy is False
    assert report.results[0].error is not None
    assert "timed out" in report.results[0].error.message.lower()


@pytest.mark.asyncio
async def test_run_probe_with_hooks_timeout_raises_when_not_requested() -> None:
    """run_probe with hooks and timeout raises TimeoutError when on_timeout_return_failure=False."""

    async def slow_start(_c: object, _i: int) -> None:
        await asyncio.sleep(10)

    probe = Probe(
        name="test",
        checks=[
            FunctionHealthCheck(func=_success_check, name="A"),
        ],
    )
    with pytest.raises(asyncio.TimeoutError):
        await run_probe(
            probe,
            timeout=0.05,
            on_check_start=slow_start,
            on_timeout_return_failure=False,
        )


@pytest.mark.asyncio
async def test_run_probe_hook_exception_handling() -> None:
    """Test run_probe when a check raises (hooks path, exception handling)."""

    async def noop_end(_c: object, _i: int, _r: HealthCheckResult) -> None:
        """No-op callback after check."""
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
    assert report.results[0].error is not None
    assert "RuntimeError" in report.results[0].error.message


@pytest.mark.asyncio
async def test_run_probe_parallel_exception_handling() -> None:
    """run_probe catches per-check exceptions and returns failed result for that check."""
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
    assert report.results[0].error is not None
    assert "RuntimeError" in report.results[0].error.message


@pytest.mark.asyncio
async def test_probe_asgi_exception_handling() -> None:
    """ProbeAsgi catches check exceptions and returns failure response."""
    probe = Probe(
        name="test",
        checks=[
            _RaisingCheck(name="Failing"),
        ],
    )
    asgi_probe = ProbeAsgi(probe)
    content, headers, status = await asgi_probe()
    assert content == b'{"status":"unhealthy"}'
    assert headers is not None
    assert headers.get("content-type") == "application/json"
    assert status == UNHEALTHY_STATUS_CODE


@pytest.mark.asyncio
async def test_probe_asgi_timeout() -> None:
    """ProbeAsgi with timeout returns failure when checks exceed timeout."""

    async def slow_check() -> bool:
        """Sleep and return True.

        Returns:
            True.
        """
        await asyncio.sleep(2.0)
        return True

    probe = Probe(
        name="test",
        checks=[FunctionHealthCheck(func=slow_check, name="Slow")],
    )
    asgi_probe = ProbeAsgi(probe, options=build_probe_route_options(timeout=0.1))
    _content, _headers, status = await asgi_probe()
    assert status == UNHEALTHY_STATUS_CODE


@pytest.mark.asyncio
async def test_probe_asgi_debug_redacts_error_meta_secrets() -> None:
    """ProbeAsgi redacts nested secrets from error.meta in debug JSON payload."""

    class _FailedCheck:
        _name = "Failed"

        async def __call__(self) -> HealthCheckResult:
            return HealthCheckResult(
                name=self._name,
                healthy=False,
                error=HealthError(
                    code="CHECK_EXCEPTION",
                    message="boom",
                    meta={
                        "password": "secret",
                        "user": "alice",
                        "token": "abc123",
                        "safe": "ok",
                    },
                ),
            )

    probe = Probe(name="test", checks=[_FailedCheck()])
    asgi_probe = ProbeAsgi(probe, options=build_probe_route_options(debug=True))
    content, _headers, status = await asgi_probe()

    assert status == UNHEALTHY_STATUS_CODE
    payload = json.loads(content.decode("utf-8"))
    meta = payload["results"][0]["error"]["meta"]
    assert meta["password"] == "***"
    assert meta["user"] == "***"
    assert meta["token"] == "***"
    assert meta["safe"] == "ok"


@pytest.mark.asyncio
async def test_run_probe_timeout_raises() -> None:
    """run_probe raises TimeoutError when timeout is exceeded and no on_check hooks."""

    async def slow_check() -> bool:
        """Sleep and return True.

        Returns:
            True.
        """
        await asyncio.sleep(10.0)
        return True

    probe = Probe(
        name="test",
        checks=[FunctionHealthCheck(func=slow_check, name="Slow")],
    )
    with pytest.raises(asyncio.TimeoutError):
        await run_probe(probe, timeout=0.01)


@pytest.mark.asyncio
async def test_run_probe_cancelled_error_propagates() -> None:
    """_run_check_safe re-raises CancelledError; never wraps in HealthCheckResult (CF-1)."""

    class CancelledCheck:
        _name = "Cancelled"

        async def __call__(self) -> HealthCheckResult:
            raise asyncio.CancelledError

    probe = Probe(name="test", checks=[CancelledCheck()])
    with pytest.raises(asyncio.CancelledError):
        await run_probe(probe)


@pytest.mark.asyncio
async def test_run_probe_probe_level_cancel_raises_no_deadlock() -> None:
    """On probe-level cancel, run_probe raises CancelledError and completes (no deadlock)."""

    class SlowCheck:
        _name = "Slow"

        async def __call__(self) -> HealthCheckResult:
            await asyncio.sleep(60)
            return HealthCheckResult(name=self._name, healthy=True)

    probe = Probe(name="test", checks=[SlowCheck()])

    task = asyncio.create_task(run_probe(probe, timeout=30.0))
    await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    # If we get here without hanging, no deadlock (bounded completion).


@pytest.mark.asyncio
async def test_run_probe_cancel_does_not_close_cached_clients() -> None:
    """On cancel, run_probe does not call aclose; only healthcheck_shutdown does (CF-2)."""

    class SlowCheck:
        _name = "Slow"

        async def __call__(self) -> HealthCheckResult:
            await asyncio.sleep(10)
            return HealthCheckResult(name=self._name, healthy=True)

    check_with_aclose = CheckWithAclose(name="C")
    probe = Probe(name="test", checks=[SlowCheck(), check_with_aclose])

    task = asyncio.create_task(run_probe(probe, timeout=20.0))
    await asyncio.sleep(0.02)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert check_with_aclose._aclose_mock.await_count == 0
    await healthcheck_shutdown([probe])()
    check_with_aclose._aclose_mock.assert_awaited_once()
