"""Base classes for all health checks.

Defines HealthCheck, HealthCheckDSN, ClientCachingMixin, healthcheck_safe(),
and shared timeout/lifecycle behavior. Backend-specific checks (Redis, Kafka,
PostgreSQL, etc.) subclass these.
"""

from __future__ import annotations

import asyncio
import contextlib
import functools
import inspect
from abc import ABC, abstractmethod
from traceback import format_exc
from typing import TYPE_CHECKING, Any, Concatenate, Generic, ParamSpec, Protocol, TypeVar, cast
from urllib.parse import urlsplit

from fast_healthchecks.errors import DEPENDENCY_UNHEALTHY, map_exception_to_health_error
from fast_healthchecks.models import HealthCheckResult
from fast_healthchecks.utils import maybe_redact

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

T_co = TypeVar("T_co", bound=HealthCheckResult, covariant=True)
T_parsed = TypeVar("T_parsed", bound=object)
ClientT = TypeVar("ClientT")
P = ParamSpec("P")

__all__ = (
    "DEFAULT_HC_TIMEOUT",
    "_CLIENT_CACHING_SLOTS",
    "ClientCachingMixin",
    "ConfigDictMixin",
    "HealthCheck",
    "HealthCheckDSN",
    "ToDictMixin",
    "healthcheck_safe",
    "result_on_error",
    "result_unhealthy_dependency",
)


DEFAULT_HC_TIMEOUT: float = 5.0

_CLIENT_CACHING_SLOTS: tuple[str, str, str, str] = (
    "_client",
    "_client_loop",
    "_ensure_client_lock",
    "_close_client_fn",
)


def result_on_error(name: str, exc: BaseException | None = None) -> HealthCheckResult:
    """Create a failed HealthCheckResult with current traceback.

    Returns:
        HealthCheckResult: Failed result with structured error.
    """
    if exc is None:
        msg = format_exc()
        return HealthCheckResult(
            name=name,
            healthy=False,
            error=map_exception_to_health_error(
                RuntimeError(msg),
                code=None,
                message="Check failed with exception",
            ),
        )
    return HealthCheckResult(name=name, healthy=False, error=map_exception_to_health_error(exc))


def result_unhealthy_dependency(
    name: str,
    *,
    message: str,
    meta: dict[str, object] | None = None,
) -> HealthCheckResult:
    """Create a failed result for a dependency that responded but is unhealthy.

    Returns:
        HealthCheckResult: Failed check result with ``DEPENDENCY_UNHEALTHY`` error code.
    """
    return HealthCheckResult(
        name=name,
        healthy=False,
        error=map_exception_to_health_error(
            RuntimeError(message),
            code=DEPENDENCY_UNHEALTHY,
            message=message,
            meta=meta,
        ),
    )


class _HasName(Protocol):
    _name: str


class _ConfigWithToDict(Protocol):
    def to_dict(self) -> dict[str, Any]: ...


def healthcheck_safe(
    *,
    invalidate_on_error: bool = False,
) -> Callable[
    [Callable[Concatenate[_HasName, P], Awaitable[HealthCheckResult]]],
    Callable[Concatenate[_HasName, P], Awaitable[HealthCheckResult]],
]:
    """Decorator that catches exceptions and returns a failed HealthCheckResult.

    Exception handling (re-raise vs wrap):
        CancelledError, SystemExit, and KeyboardInterrupt are never wrapped;
        they are re-raised so asyncio cancellation and process control work
        correctly. All other exceptions are caught and converted to a failed
        HealthCheckResult (existing contract).

    Returns:
        A decorator that wraps an async method and returns the decorated method.
    """

    def decorator(
        method: Callable[Concatenate[_HasName, P], Awaitable[HealthCheckResult]],
    ) -> Callable[Concatenate[_HasName, P], Awaitable[HealthCheckResult]]:
        @functools.wraps(method)
        async def wrapper(
            self: _HasName,
            *args: P.args,
            **kwargs: P.kwargs,
        ) -> HealthCheckResult:
            try:
                return await method(self, *args, **kwargs)
            except (asyncio.CancelledError, SystemExit, KeyboardInterrupt):
                raise
            except Exception as exc:  # noqa: BLE001
                if invalidate_on_error:
                    invalidate = getattr(self, "_invalidate_client", None)
                    if callable(invalidate):
                        maybe_awaitable = invalidate()
                        if inspect.isawaitable(maybe_awaitable):
                            await maybe_awaitable
                return result_on_error(self._name, exc)

        return wrapper

    return decorator


class ToDictMixin(ABC):
    """Mixin for health checks that support serialization to dict."""

    @abstractmethod
    def _build_dict(self) -> dict[str, Any]:
        """Return the check attributes as a dictionary (without redaction)."""
        ...  # pragma: no cover

    def to_dict(self, *, redact_secrets: bool = False) -> dict[str, Any]:
        """Convert the check to a dictionary.

        **API status:** Internal / test use only. Not part of the supported
        public API; do not rely on it in production code. See docs/api.md.

        Returns:
            dict: Check attributes, optionally with secrets redacted.
        """
        return maybe_redact(self._build_dict(), redact_secrets=redact_secrets)


class ConfigDictMixin(ToDictMixin):
    """Mixin that implements _build_dict from _config.to_dict() and _name."""

    _config: _ConfigWithToDict
    _name: str

    def _build_dict(self) -> dict[str, Any]:
        """Return the check attributes as a dictionary (without redaction)."""
        return {**self._config.to_dict(), "name": self._name}


class ClientCachingMixin(ABC, Generic[ClientT]):
    """Mixin for health checks that cache a client and need lifecycle management.

    Use this mixin for checks that maintain a long-lived client (Redis, Kafka,
    Mongo, Url, OpenSearch, RabbitMQ). Implement _create_client (returning
    ClientT or Awaitable[ClientT]) and pass close_client_fn to __init__.
    Register probes with healthcheck_shutdown() so cached clients are closed.
    """

    _client: ClientT | None
    _client_loop: asyncio.AbstractEventLoop | None
    _ensure_client_lock: asyncio.Lock
    _close_client_fn: Callable[[ClientT], Awaitable[None]]

    def __init__(
        self,
        *args: object,
        close_client_fn: Callable[[ClientT], Awaitable[None]],
        **kwargs: object,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._close_client_fn = close_client_fn
        self._client = None
        self._client_loop = None
        self._ensure_client_lock = asyncio.Lock()

    @abstractmethod
    def _create_client(self) -> ClientT | Awaitable[ClientT]:
        """Create and return a new client (or awaitable). Called when cache is empty or invalid."""
        ...  # pragma: no cover

    async def aclose(self) -> None:
        """Close the cached client if present.

        Yields once so the event loop can run transport cleanup callbacks
        (e.g. aiohttp connection_lost) before returning.
        """
        async with self._ensure_client_lock:
            if self._client is not None:
                await self._close_client_fn(self._client)
                self._client = None
                self._client_loop = None
        await asyncio.sleep(0.1)

    async def _ensure_client(self) -> ClientT:
        """Return cached client, creating or recreating if needed.

        Raises:
            RuntimeError: If client creation fails (e.g. _create_client returns None).
        """
        async with self._ensure_client_lock:
            try:
                running = asyncio.get_running_loop()
            except RuntimeError:
                running = None
            if self._client is not None and self._client_loop is not running:
                with contextlib.suppress(Exception):
                    await self._close_client_fn(self._client)
                self._client = None
                self._client_loop = None
            if self._client is None:
                try:
                    self._client_loop = asyncio.get_running_loop()
                except RuntimeError:
                    self._client_loop = None

                client_or_awaitable = self._create_client()
                if asyncio.iscoroutine(client_or_awaitable):
                    self._client = cast("ClientT", await client_or_awaitable)
                else:
                    self._client = cast("ClientT", client_or_awaitable)

            if self._client is None:  # pragma: no cover
                msg = "Failed to create client"
                raise RuntimeError(msg)
            return self._client

    async def _invalidate_client(self) -> None:
        """Close and clear the cached client."""
        async with self._ensure_client_lock:
            if self._client is not None:
                with contextlib.suppress(Exception):
                    await self._close_client_fn(self._client)
                self._client = None
                self._client_loop = None
        await asyncio.sleep(0.1)


class HealthCheck(Protocol[T_co]):
    """Base class for health checks."""

    async def __call__(self) -> T_co: ...


class HealthCheckDSN(ConfigDictMixin, HealthCheck[T_co], Generic[T_co, T_parsed]):
    """Base class for health checks that can be created from a DSN.

    Contract: subclasses must define _allowed_schemes(), _default_name(),
    parse_dsn(), and _from_parsed_dsn(). The check stores its display name in
    _name (used in HealthCheckResult and error reporting). DSN validation uses
    validate_dsn(); fast_healthchecks.dsn NewTypes are typing-only, not runtime.

    Type parameters: T_co is the result type (e.g. HealthCheckResult);
    T_parsed is the type returned by parse_dsn() and accepted by _from_parsed_dsn().
    """

    @classmethod
    @abstractmethod
    def _allowed_schemes(cls) -> tuple[str, ...]:
        """Return DSN schemes allowed for this check (e.g. ('redis', 'rediss'))."""
        raise NotImplementedError  # pragma: no cover

    @classmethod
    @abstractmethod
    def _default_name(cls) -> str:
        """Return the default check name for from_dsn (e.g. 'Redis')."""
        raise NotImplementedError  # pragma: no cover

    @classmethod
    @abstractmethod
    def parse_dsn(cls, dsn: str) -> T_parsed:
        """Parse the DSN string. Subclasses must implement."""
        raise NotImplementedError  # pragma: no cover

    @classmethod
    @abstractmethod
    def _from_parsed_dsn(
        cls,
        parsed: T_parsed,
        *,
        name: str = "Service",
        timeout: float = DEFAULT_HC_TIMEOUT,
        **kwargs: object,
    ) -> HealthCheckDSN[T_co, T_parsed]:
        """Create a check instance from parsed DSN."""
        raise NotImplementedError  # pragma: no cover

    @classmethod
    def from_dsn(
        cls,
        dsn: str,
        *,
        name: str | None = None,
        timeout: float = DEFAULT_HC_TIMEOUT,
        **kwargs: object,
    ) -> HealthCheckDSN[T_co, T_parsed]:
        """Create a check instance from a DSN string.

        Returns:
            HealthCheckDSN: Configured check instance.
        """
        if name is None:
            name = cls._default_name()
        dsn = cls.validate_dsn(dsn, allowed_schemes=cls._allowed_schemes())
        parsed = cls.parse_dsn(dsn)
        return cls._from_parsed_dsn(parsed, name=name, timeout=timeout, **kwargs)

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
