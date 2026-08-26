"""Tests for error mapping helpers."""

import asyncio

import pytest

from fast_healthchecks.errors import CHECK_EXCEPTION, CHECK_TIMEOUT, PROBE_TIMEOUT, map_exception_to_health_error

pytestmark = pytest.mark.unit


def test_map_exception_to_health_error_unknown_exception_code() -> None:
    """Unknown exceptions are mapped to CHECK_EXCEPTION."""
    error = map_exception_to_health_error(RuntimeError("boom"))
    assert error.code == CHECK_EXCEPTION
    assert "RuntimeError" in error.message


def test_message_has_no_traceback_even_when_traceback_present() -> None:
    """A raised exception maps to '<Type>: <message>' without traceback frames."""  # ruff: ignore[docstring-missing-exception] - the raise never escapes the test
    try:
        msg = "boom"
        raise RuntimeError(msg)  # ruff: ignore[raise-within-try] - the raise builds a real traceback for the assertion
    except RuntimeError as exc:
        error = map_exception_to_health_error(exc)
    assert error.message == "RuntimeError: boom"
    assert "Traceback" not in error.message
    assert "File" not in error.message


def test_map_exception_to_health_error_timeout_code() -> None:
    """Timeout exceptions are mapped to CHECK_TIMEOUT by default."""
    error = map_exception_to_health_error(asyncio.TimeoutError("timed out"))
    assert error.code == CHECK_TIMEOUT
    assert "timed out" in error.message.lower()


def test_map_exception_to_health_error_supports_explicit_code() -> None:
    """Code override is respected for probe-level timeout mapping."""
    error = map_exception_to_health_error(asyncio.TimeoutError("timed out"), code=PROBE_TIMEOUT)
    assert error.code == PROBE_TIMEOUT
