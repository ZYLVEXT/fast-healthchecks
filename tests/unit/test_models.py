"""Tests for HealthCheckResult and HealthCheckReport."""

from dataclasses import asdict

import pytest

from fast_healthchecks.models import HealthCheckReport, HealthCheckResult, HealthError

pytestmark = pytest.mark.unit


def test_healthcheck_result() -> None:
    """HealthCheckResult has name, healthy, error and correct str()."""
    hcr1 = HealthCheckResult(
        name="test",
        healthy=True,
    )
    assert str(hcr1) == "test: healthy"

    error = HealthError(
        code="CHECK_EXCEPTION",
        message="error",
        duration_ms=10,
        timeout_ms=100,
        meta={"service": "db"},
    )
    hcr2 = HealthCheckResult(
        name="test",
        healthy=False,
        error=error,
    )
    assert str(hcr2) == "test: unhealthy"
    assert hcr2.error is not None
    assert hcr2.error == error
    assert hcr2.error.message == "error"


def test_healthcheck_result_asdict_and_eq() -> None:
    """HealthCheckResult serializes and compares by structured error."""
    result = HealthCheckResult(
        name="redis",
        healthy=False,
        error=HealthError(code="CHECK_TIMEOUT", message="timed out", timeout_ms=500),
    )
    assert asdict(result) == {
        "name": "redis",
        "healthy": False,
        "error": {
            "code": "CHECK_TIMEOUT",
            "message": "timed out",
            "duration_ms": 0,
            "timeout_ms": 500,
            "meta": {},
        },
    }

    assert result == HealthCheckResult(
        name="redis",
        healthy=False,
        error=HealthError(code="CHECK_TIMEOUT", message="timed out", timeout_ms=500),
    )


def test_healthcheck_report() -> None:
    """HealthCheckReport.healthy is True when all results healthy (or partial allowed)."""
    hcr = HealthCheckReport(
        results=[
            HealthCheckResult(
                name="test1",
                healthy=True,
            ),
            HealthCheckResult(
                name="test2",
                healthy=False,
                error=HealthError(code="CHECK_EXCEPTION", message="error"),
            ),
        ],
    )
    assert str(hcr) == "test1: healthy\ntest2: unhealthy"
    assert hcr.healthy is False

    hcr = HealthCheckReport(
        results=[
            HealthCheckResult(
                name="test1",
                healthy=True,
            ),
            HealthCheckResult(
                name="test2",
                healthy=False,
                error=HealthError(code="CHECK_EXCEPTION", message="error"),
            ),
        ],
        allow_partial_failure=True,
    )
    assert hcr.healthy is True

    hcr = HealthCheckReport(
        results=[
            HealthCheckResult(name="a", healthy=False),
            HealthCheckResult(name="b", healthy=False),
        ],
        allow_partial_failure=True,
    )
    assert hcr.healthy is False


def test_healthcheck_result_error_details_backward_compatible() -> None:
    """HealthCheckResult supports legacy error_details via property accessor."""
    error = HealthError(code="CHECK_EXCEPTION", message="legacy error")
    result = HealthCheckResult(name="test", healthy=False, error=error)
    assert result.error_details == "legacy error"


def test_healthcheck_result_error_details_none_when_no_error() -> None:
    """error_details property returns None when error is None."""
    result = HealthCheckResult(name="test", healthy=True)
    assert result.error_details is None


def test_healthcheck_result_error_details_from_legacy_string() -> None:
    """HealthCheckResult accepts legacy error_details string and converts to HealthError."""
    result = HealthCheckReport(
        results=[
            HealthCheckResult(
                name="test",
                healthy=False,
                error_details="legacy failure message",
            ),
        ],
    )
    assert result.results[0].error is not None
    assert result.results[0].error.code == "CHECK_EXCEPTION"
    assert result.results[0].error.message == "legacy failure message"


def test_healthcheck_result_rejects_both_error_and_error_details() -> None:
    """HealthCheckResult raises ValueError when both error and error_details provided."""
    error = HealthError(code="CHECK_EXCEPTION", message="new format")
    with pytest.raises(ValueError, match="Provide either error or error_details, not both"):
        HealthCheckResult(
            name="test",
            healthy=False,
            error=error,
            error_details="legacy format",
        )
