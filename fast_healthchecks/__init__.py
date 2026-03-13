"""Framework-agnostic health checks for ASGI apps (FastAPI, FastStream, Litestar).

Optional backends and framework integrations are available as install extras.
See the project's pyproject.toml for extra names (e.g. asyncpg, redis, fastapi).
"""

from fast_healthchecks.checks import FunctionConfig
from fast_healthchecks.checks.types import Check
from fast_healthchecks.execution import ProbeRunner, RunPolicy
from fast_healthchecks.integrations.base import Probe
from fast_healthchecks.models import (
    HealthCheckError,
    HealthCheckReport,
    HealthCheckResult,
    HealthCheckSSRFError,
    HealthCheckTimeoutError,
)

__version__ = "1.0.0"

__all__ = (
    "Check",
    "FunctionConfig",
    "HealthCheckError",
    "HealthCheckReport",
    "HealthCheckResult",
    "HealthCheckSSRFError",
    "HealthCheckTimeoutError",
    "Probe",
    "ProbeRunner",
    "RunPolicy",
    "__version__",
)
