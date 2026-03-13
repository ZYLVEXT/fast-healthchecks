"""Optional structured logging for probe and check execution.

Logging is disabled by default (NullLogger). Enable by calling
``set_probe_logger(get_stdlib_probe_logger())`` or by passing a custom
logger that implements the same protocol. All extra fields passed to
``log()`` are redacted for secret keys (same keys as ``utils.redact_secrets_in_dict``)
before any output. No mandatory dependency on external logging frameworks.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

from fast_healthchecks.utils import redact_secrets_in_dict

__all__ = (
    "NullLogger",
    "get_probe_logger",
    "get_stdlib_probe_logger",
    "set_probe_logger",
)


class ProbeLoggerProtocol(Protocol):
    """Protocol for probe/check logging. Implementations must not emit secrets."""

    def log(self, level: int, msg: str, **extra: Any) -> None:  # noqa: ANN401
        """Log a message with optional structured extra fields.

        Extra dict is expected to be redacted by the implementation
        (e.g. same keys as DOC-3 / utils.redact_secrets_in_dict).
        """
        ...  # pragma: no cover


class NullLogger:
    """Logger that emits no records. Used when logging is disabled."""

    def log(self, level: int, msg: str, **extra: Any) -> None:  # noqa: ANN401
        """No-op."""


_probe_logger: ProbeLoggerProtocol = NullLogger()


def get_probe_logger() -> ProbeLoggerProtocol:
    """Return the current probe logger (default: NullLogger)."""
    return _probe_logger


def set_probe_logger(logger: ProbeLoggerProtocol) -> None:
    """Set the probe logger. Use NullLogger() to disable logging."""
    global _probe_logger  # noqa: PLW0603
    _probe_logger = logger


class _StdlibProbeLogger:
    """Stdlib-based probe logger. Redacts extra dict before logging."""

    def __init__(self, name: str = "fast_healthchecks.probe") -> None:
        self._logger = logging.getLogger(name)

    def log(self, level: int, msg: str, **extra: Any) -> None:  # noqa: ANN401
        """Log with redacted extra (no secrets in output)."""
        redacted = redact_secrets_in_dict(dict(extra))
        self._logger.log(level, msg, extra=redacted)


def get_stdlib_probe_logger(name: str = "fast_healthchecks.probe") -> ProbeLoggerProtocol:
    """Return a probe logger that uses stdlib logging with redaction.

    Use with set_probe_logger(get_stdlib_probe_logger()) to enable logging.
    """
    return _StdlibProbeLogger(name=name)
