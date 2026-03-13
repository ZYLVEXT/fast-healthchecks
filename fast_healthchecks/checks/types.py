"""Type aliases for health checks."""

from __future__ import annotations

from typing import TypeAlias

from fast_healthchecks.checks._base import HealthCheck, HealthCheckDSN
from fast_healthchecks.models import HealthCheckResult

Check: TypeAlias = HealthCheck[HealthCheckResult]

__all__ = (
    "Check",
    "HealthCheck",
    "HealthCheckDSN",
)
