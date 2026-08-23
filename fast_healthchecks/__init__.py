"""Framework-neutral health checks with lazy public exports."""

# ruff: file-ignore[non-empty-init-module] - the lazy export table lives here

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fast_healthchecks.checks.configs import FunctionConfig
    from fast_healthchecks.checks.types import Check
    from fast_healthchecks.execution import Probe, ProbeRunner, RunPolicy
    from fast_healthchecks.models import (
        HealthCheckError,
        HealthCheckReport,
        HealthCheckResult,
        HealthCheckSSRFError,
        HealthCheckTimeoutError,
    )

__version__ = "1.1.1"

_EXPORTS = {
    "Check": ("fast_healthchecks.checks.types", "Check"),
    "FunctionConfig": ("fast_healthchecks.checks.configs", "FunctionConfig"),
    "HealthCheckError": ("fast_healthchecks.models", "HealthCheckError"),
    "HealthCheckReport": ("fast_healthchecks.models", "HealthCheckReport"),
    "HealthCheckResult": ("fast_healthchecks.models", "HealthCheckResult"),
    "HealthCheckSSRFError": ("fast_healthchecks.models", "HealthCheckSSRFError"),
    "HealthCheckTimeoutError": ("fast_healthchecks.models", "HealthCheckTimeoutError"),
    "Probe": ("fast_healthchecks.execution", "Probe"),
    "ProbeRunner": ("fast_healthchecks.execution", "ProbeRunner"),
    "RunPolicy": ("fast_healthchecks.execution", "RunPolicy"),
}

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


def __getattr__(name: str) -> Any:  # ruff: ignore[any-type] - the value is forwarded to a client library untouched
    """Load a public symbol only when first accessed.

    Returns:
        The requested public object.

    Raises:
        AttributeError: If ``name`` is not part of the public API.
    """
    target = _EXPORTS.get(name)
    if target is None:
        msg = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(msg)
    module_name, attribute = target
    value = getattr(import_module(module_name), attribute)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Return eager and lazy public attributes for interactive discovery."""
    return sorted({*globals(), *__all__})
