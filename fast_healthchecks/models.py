"""Models for healthchecks."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

__all__ = (
    "HealthCheckError",
    "HealthCheckReport",
    "HealthCheckResult",
    "HealthCheckSSRFError",
    "HealthCheckTimeoutError",
    "HealthError",
)


class HealthCheckError(Exception):
    """Base exception for health-check-related failures.

    Raised or used as a base for timeouts, SSRF validation, and other
    health-check errors. Subclasses preserve the original exception type
    (e.g. HealthCheckTimeoutError is also an asyncio.TimeoutError) so
    existing code that catches TimeoutError or ValueError continues to work.
    """


class HealthCheckTimeoutError(HealthCheckError, asyncio.TimeoutError):
    """Raised when a probe or check run exceeds its timeout.

    Subclass of both HealthCheckError and asyncio.TimeoutError so that
    ``except asyncio.TimeoutError`` or ``except TimeoutError`` still catch it.
    """

    code: str

    def __init__(self, message: str = "Probe timed out", *, code: str = "PROBE_TIMEOUT") -> None:
        """Create timeout error with machine-readable timeout code."""
        super().__init__(message)
        self.code = code


class HealthCheckSSRFError(HealthCheckError, ValueError):
    """Raised when URL or host validation fails (SSRF / block_private_hosts).

    Subclass of both HealthCheckError and ValueError so that
    ``except ValueError`` still catches it.
    """


@dataclass(frozen=True)
class HealthError:
    """Machine-readable error details for failed health checks.

    Attributes:
        code: Machine-readable error code (e.g., "PROBE_TIMEOUT", "CHECK_EXCEPTION").
        message: Human-readable error message describing what went wrong.
        duration_ms: Time in milliseconds that the probe took to execute.
        timeout_ms: Timeout limit in milliseconds that was applied to the probe.
        meta: Additional metadata about the error (e.g., exception type, URL).
            Secrets are automatically redacted from this field.
    """

    code: str
    message: str
    duration_ms: int = 0
    timeout_ms: int | None = None
    meta: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, init=False)
class HealthCheckResult:
    """Result of a healthcheck.

    Attributes:
        name: Name of the healthcheck.
        healthy: Whether the healthcheck passed.
        error: Structured error details if the healthcheck failed.
    """

    name: str
    healthy: bool
    error: HealthError | None = None

    def __init__(
        self,
        name: str,
        healthy: bool,  # noqa: FBT001
        error: HealthError | None = None,
        *,
        error_details: str | None = None,
    ) -> None:
        """Create a health check result.

        The ``error_details`` keyword is accepted for backward compatibility
        and is converted into ``error.message``.

        Raises:
            ValueError: If both ``error`` and ``error_details`` are provided.
        """
        if error is not None and error_details is not None:
            msg = "Provide either error or error_details, not both"
            raise ValueError(msg)

        resolved_error = error
        if resolved_error is None and error_details is not None:
            resolved_error = HealthError(code="CHECK_EXCEPTION", message=error_details)

        object.__setattr__(self, "name", name)
        object.__setattr__(self, "healthy", healthy)
        object.__setattr__(self, "error", resolved_error)

    @property
    def error_details(self) -> str | None:
        """Backward-compatible error message accessor."""
        if self.error is None:
            return None
        return self.error.message

    def __str__(self) -> str:
        """Return a string representation of the result."""
        return f"{self.name}: {'healthy' if self.healthy else 'unhealthy'}"


@dataclass(frozen=True)
class HealthCheckReport:
    """Report of healthchecks.

    Attributes:
        results: List of healthcheck results.
        allow_partial_failure: If True, report is healthy when at least one check passes.
    """

    results: list[HealthCheckResult]
    allow_partial_failure: bool = False

    def __str__(self) -> str:
        """Return a string representation of the report."""
        return "\n".join(str(result) for result in self.results)

    @property
    def healthy(self) -> bool:
        """Return whether all healthchecks passed (or allowed partial failure)."""
        if self.allow_partial_failure:
            return any(result.healthy for result in self.results)
        return all(result.healthy for result in self.results)
