"""Secret-redaction primitives without dependencies on health-check models."""

from __future__ import annotations

from typing import Any

REDACT_PLACEHOLDER = "***"

_SECRET_KEYS = frozenset(
    {
        "http_auth",
        "sasl_plain_username",
        "user",
        "username",
    },
)
_SECRET_KEY_FRAGMENTS = ("password", "secret", "token", "api_key", "credential")


def _is_secret_key(key: str) -> bool:
    normalized = key.casefold()
    return normalized in _SECRET_KEYS or any(fragment in normalized for fragment in _SECRET_KEY_FRAGMENTS)


def _redact_value(value: Any) -> Any:  # ruff: ignore[any-type] - redaction walks arbitrary log payloads
    if isinstance(value, dict):
        return redact_secrets_in_dict(value)
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_value(item) for item in value)
    if isinstance(value, set):
        return {_redact_value(item) for item in value}
    return value


def redact_secrets_in_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Return a recursively redacted copy of a string-keyed dictionary."""
    return {key: (REDACT_PLACEHOLDER if _is_secret_key(key) else _redact_value(value)) for key, value in data.items()}


def maybe_redact(data: dict[str, Any], *, redact_secrets: bool) -> dict[str, Any]:
    """Return data with secrets redacted when requested."""
    return redact_secrets_in_dict(data) if redact_secrets else data


__all__ = ("REDACT_PLACEHOLDER", "maybe_redact", "redact_secrets_in_dict")
