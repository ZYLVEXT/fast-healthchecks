"""Health check that runs a user-provided callable (sync or async).

FunctionHealthCheck runs the callable each time the check is executed; sync
functions are run in a thread pool via run_in_executor.
"""

from __future__ import annotations

import asyncio
import functools
import inspect
from typing import TYPE_CHECKING, Any, final

from fast_healthchecks.checks._base import (
    ConfigDictMixin,
    HealthCheck,
    healthcheck_safe,
    result_unhealthy_dependency,
)
from fast_healthchecks.checks.configs import FunctionConfig
from fast_healthchecks.models import HealthCheckResult

if TYPE_CHECKING:
    from collections.abc import Callable
    from concurrent.futures import Executor


@final
class FunctionHealthCheck(ConfigDictMixin, HealthCheck[HealthCheckResult]):
    """Health check that runs a callable (sync or async) each time it is executed.

    Async callables are detected via ``inspect.iscoroutinefunction`` on the
    callable itself and on its ``__call__`` method, so instances of classes
    with ``async def __call__`` run on the event loop. Exotic wrappers that
    hide the coroutine function may still be misdetected as sync.

    Synchronous functions are run via ``loop.run_in_executor(executor, ...)``.
    The default executor is ``None`` (shared thread pool). Long-running blocking
    sync checks can exhaust the pool; pass a dedicated :class:`Executor` if
    needed. A timeout abandons the worker thread rather than cancelling it —
    Python offers no way to kill a running thread — so the blocking call may
    keep running in the background after the check fails.
    """

    __slots__ = ("_config", "_executor", "_func", "_name")

    _config: FunctionConfig
    _func: Callable[..., Any]
    _executor: Executor | None
    _name: str

    def __init__(
        self,
        *,
        config: FunctionConfig | None = None,
        func: Callable[..., Any] | None = None,
        name: str = "Function",
        executor: Executor | None = None,
        **kwargs: Any,  # ruff: ignore[any-type] - the value is forwarded to a client library untouched
    ) -> None:
        """Initialize the FunctionHealthCheck.

        Args:
            config: Config (args, kwargs, timeout). If None, built from kwargs.
            func: The function to perform the health check on (required if config is None).
            name: The name of the health check.
            executor: Executor for sync functions. Defaults to None (thread pool).
            **kwargs: Passed to FunctionConfig when config is None (args, kwargs, timeout).

        Raises:
            TypeError: When func is not provided.
        """
        if config is None:
            kwargs_copy = dict(kwargs)
            func = kwargs_copy.pop("func", func)
            executor = kwargs_copy.pop("executor", executor)
            if func is None:
                msg = "func is required when config is not provided"
                raise TypeError(msg)
            config = FunctionConfig(**kwargs_copy)
        elif func is None:
            msg = "func is required"
            raise TypeError(msg)
        self._config = config
        self._func = func
        self._executor = executor
        self._name = name

    @healthcheck_safe(invalidate_on_error=False)
    async def __call__(self) -> HealthCheckResult:
        """Perform the health check on the function.

        Sync functions run in the given executor (default: shared thread pool).

        Returns:
            HealthCheckResult: The result of the health check.
        """
        c = self._config
        args = c.args or ()
        kwargs = dict(c.kwargs) if c.kwargs else {}
        task: asyncio.Future[Any]
        is_async = inspect.iscoroutinefunction(self._func) or inspect.iscoroutinefunction(
            getattr(self._func, "__call__", None),  # ruff: ignore[unreliable-callable-check] - detects async __call__ on callable instances
        )
        if is_async:
            task = self._func(*args, **kwargs)
        else:
            loop = asyncio.get_running_loop()
            task = loop.run_in_executor(
                self._executor,
                functools.partial(self._func, *args, **kwargs),
            )
        result = await asyncio.wait_for(task, timeout=c.timeout)
        healthy = bool(result) if isinstance(result, bool) else True
        if healthy:
            return HealthCheckResult(name=self._name, healthy=True)
        return result_unhealthy_dependency(name=self._name, message="Function returned unhealthy status")
