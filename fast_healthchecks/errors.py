"""Error mapping primitives for healthchecks."""

from __future__ import annotations

import asyncio
from traceback import format_exception
from typing import Final, Literal

from fast_healthchecks.models import HealthError

ErrorCode = Literal[
    "CHECK_TIMEOUT",
    "PROBE_TIMEOUT",
    "CHECK_EXCEPTION",
    "DEPENDENCY_UNHEALTHY",
]

# Error codes for healthcheck failures:
# - CHECK_TIMEOUT: Overall check execution exceeded timeout.
# - PROBE_TIMEOUT: Individual probe exceeded its timeout.
# - CHECK_EXCEPTION: Check raised an unexpected exception.
# - DEPENDENCY_UNHEALTHY: A dependency was marked unhealthy.

CHECK_TIMEOUT: Final[ErrorCode] = "CHECK_TIMEOUT"
PROBE_TIMEOUT: Final[ErrorCode] = "PROBE_TIMEOUT"
CHECK_EXCEPTION: Final[ErrorCode] = "CHECK_EXCEPTION"
DEPENDENCY_UNHEALTHY: Final[ErrorCode] = "DEPENDENCY_UNHEALTHY"

__all__ = (
    "CHECK_EXCEPTION",
    "CHECK_TIMEOUT",
    "DEPENDENCY_UNHEALTHY",
    "PROBE_TIMEOUT",
    "ErrorCode",
    "map_exception_to_health_error",
)


def _format_exception_message(exc: BaseException) -> str:
    """Format an exception into a readable error message.

    Returns:
        A traceback-like message when traceback is available, otherwise
        ``"<ExceptionType>: <message>"``.
    """
    if exc.__traceback__ is not None:
        return "".join(format_exception(type(exc), exc, exc.__traceback__))
    return f"{type(exc).__name__}: {exc}"


def map_exception_to_health_error(
    exc: BaseException,
    *,
    code: ErrorCode | None = None,
    message: str | None = None,
    timeout_ms: int | None = None,
    meta: dict[str, object] | None = None,
) -> HealthError:
    """Map an exception to ``HealthError`` with an official error code.

    Args:
        exc: Source exception.
        code: Explicit error code override.
        message: Explicit message override.
        timeout_ms: Optional timeout value in milliseconds.
        meta: Optional additional metadata.

    Returns:
        Structured ``HealthError``.
    """
    resolved_code = code
    if resolved_code is None:
        resolved_code = CHECK_TIMEOUT if isinstance(exc, asyncio.TimeoutError) else CHECK_EXCEPTION

    return HealthError(
        code=resolved_code,
        message=message or _format_exception_message(exc),
        duration_ms=0,
        timeout_ms=timeout_ms,
        meta=meta or {},
    )
