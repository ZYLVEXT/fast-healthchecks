"""This module contains the base classes for all health checks."""

from __future__ import annotations

from typing import Generic, Protocol, TypeVar
from urllib.parse import urlsplit

from fast_healthchecks.models import HealthCheckResult

T_co = TypeVar("T_co", bound=HealthCheckResult, covariant=True)

__all__ = (
    "DEFAULT_HC_TIMEOUT",
    "HealthCheck",
    "HealthCheckDSN",
)


DEFAULT_HC_TIMEOUT: float = 5.0


class HealthCheck(Protocol[T_co]):
    """Base class for health checks."""

    async def __call__(self) -> T_co: ...


class HealthCheckDSN(HealthCheck[T_co], Generic[T_co]):
    """Base class for health checks that can be created from a DSN."""

    @classmethod
    def from_dsn(
        cls,
        dsn: str,
        *,
        name: str = "Service",
        timeout: float = DEFAULT_HC_TIMEOUT,
    ) -> HealthCheckDSN[T_co]:
        raise NotImplementedError

    @classmethod
    def validate_dsn(cls, dsn: str, *, allowed_schemes: tuple[str, ...]) -> str:
        """Validate the DSN has an allowed scheme.

        Allows compound schemes (e.g. postgresql+asyncpg) when the base
        part before '+' is in allowed_schemes. Scheme comparison is case-insensitive.

        Returns:
            str: The DSN string (stripped of leading/trailing whitespace).

        Raises:
            TypeError: If dsn is not a string.
            ValueError: If DSN is empty or scheme is not in allowed_schemes.
        """
        if not isinstance(dsn, str):
            msg = f"DSN must be str, got {type(dsn).__name__!r}"
            raise TypeError(msg) from None

        dsn = dsn.strip()
        if not dsn:
            msg = "DSN cannot be empty"
            raise ValueError(msg) from None

        if not allowed_schemes:
            msg = "allowed_schemes cannot be empty"
            raise ValueError(msg) from None

        parsed = urlsplit(dsn)
        scheme = (parsed.scheme or "").lower()
        base_scheme = scheme.split("+", 1)[0] if "+" in scheme else scheme

        allowed_set = frozenset(s.lower() for s in allowed_schemes)
        if scheme not in allowed_set and base_scheme not in allowed_set:
            schemes_str = ", ".join(sorted(allowed_set))
            msg = f"DSN scheme must be one of {schemes_str} (or compound e.g. postgresql+driver), got {scheme!r}"
            raise ValueError(msg) from None

        return dsn
