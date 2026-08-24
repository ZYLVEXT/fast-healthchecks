"""Health-check protocols and configuration contracts with lazy exports."""

# ruff: file-ignore[non-empty-init-module] - the lazy export table lives here

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fast_healthchecks.checks.configs import (
        FunctionConfig,
        KafkaConfig,
        MongoConfig,
        OpenSearchConfig,
        PostgresAsyncPGConfig,
        PostgresPsycopgConfig,
        RabbitMQConfig,
        RedisConfig,
        UrlConfig,
    )
    from fast_healthchecks.checks.types import Check, HealthCheck, HealthCheckDSN

_CONFIG_EXPORTS = {
    "FunctionConfig",
    "KafkaConfig",
    "MongoConfig",
    "OpenSearchConfig",
    "PostgresAsyncPGConfig",
    "PostgresPsycopgConfig",
    "RabbitMQConfig",
    "RedisConfig",
    "UrlConfig",
}
_TYPE_EXPORTS = {"Check", "HealthCheck", "HealthCheckDSN"}

__all__ = (
    "Check",
    "FunctionConfig",
    "HealthCheck",
    "HealthCheckDSN",
    "KafkaConfig",
    "MongoConfig",
    "OpenSearchConfig",
    "PostgresAsyncPGConfig",
    "PostgresPsycopgConfig",
    "RabbitMQConfig",
    "RedisConfig",
    "UrlConfig",
)


def __getattr__(name: str) -> Any:  # ruff: ignore[any-type] - the value is forwarded to a client library untouched
    """Load a configuration or protocol only when first accessed.

    Returns:
        The requested configuration or protocol.

    Raises:
        AttributeError: If ``name`` is not exported by this package.
    """
    if name in _CONFIG_EXPORTS:
        module_name = "fast_healthchecks.checks.configs"
    elif name in _TYPE_EXPORTS:
        module_name = "fast_healthchecks.checks.types"
    else:
        msg = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(msg)
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Return eager and lazy public attributes for interactive discovery."""
    return sorted({*globals(), *__all__})
