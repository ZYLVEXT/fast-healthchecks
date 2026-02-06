"""Models for healthchecks."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = (
    "HealthCheckReport",
    "HealthCheckResult",
)


@dataclass(frozen=True)
class HealthCheckResult:
    """Result of a healthcheck.

    Attributes:
        name: Name of the healthcheck.
        healthy: Whether the healthcheck passed.
        error_details: Details of the error if the healthcheck failed.
    """

    name: str
    healthy: bool
    error_details: str | None = None

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
