"""Helpers for optional dependency imports.

Backends and integrations are optional; each has an extra in pyproject.toml
(asyncpg, psycopg, redis, aio-pika, httpx, aiokafka, motor, fastapi, faststream,
litestar, opensearch). Install with e.g. pip install fast-healthchecks[redis].
"""

from __future__ import annotations

from typing import NoReturn


def raise_optional_import_error(extra: str, package: str, exc: ImportError) -> NoReturn:
    """Raise ImportError with install hint. Call from except ImportError handler.

    Args:
        extra: The extra name (e.g. "redis") for pip install fast-healthchecks[{extra}].
        package: Human-readable package name for the error message.
        exc: The original ImportError to chain.

    Raises:
        ImportError: Always, with message directing user to install the extra.
    """
    msg = f"{package} is not installed. Install it with `pip install fast-healthchecks[{extra}]`."
    raise ImportError(msg) from exc
