"""Unit tests for FunctionHealthCheck."""

import asyncio
import time
from typing import Any

import pytest

from fast_healthchecks.checks import FunctionConfig
from fast_healthchecks.checks.function import FunctionHealthCheck
from fast_healthchecks.errors import DEPENDENCY_UNHEALTHY
from fast_healthchecks.models import HealthCheckResult
from tests.utils import assert_check_init

pytestmark = pytest.mark.unit


def dummy_sync_function(arg: str, kwarg: int = 1) -> None:
    """Sync callable used by tests."""
    time.sleep(0.1)


def dummy_sync_function_fail(arg: str, kwarg: int = 1) -> None:
    """Sync callable that raises for tests.

    Raises:
        ValueError: Always.
    """
    time.sleep(0.1)
    msg = "Test exception"
    raise ValueError(msg) from None


async def dummy_async_function(arg: str, kwarg: int = 1) -> None:
    """Async callable used by tests."""
    await asyncio.sleep(0.1)


async def dummy_async_function_fail(arg: str, kwarg: int = 1) -> None:
    """Async callable that raises for tests.

    Raises:
        ValueError: Always.
    """
    await asyncio.sleep(0.1)
    msg = "Test exception"
    raise ValueError(msg) from None


def dummy_sync_function_returns_false() -> bool:
    """Return False for unhealthy test."""
    return False


async def dummy_async_function_returns_false() -> bool:
    """Return False for unhealthy test."""
    await asyncio.sleep(0.01)
    return False


@pytest.mark.parametrize(
    ("params", "expected", "exception"),
    [
        (
            {"func": dummy_sync_function},
            {
                "name": "Function",
                "timeout": 5.0,
                "args": [],
                "kwargs": {},
            },
            None,
        ),
        (
            {"func": dummy_sync_function, "name": "Custom", "timeout": 2.0},
            {
                "name": "Custom",
                "timeout": 2.0,
                "args": [],
                "kwargs": {},
            },
            None,
        ),
        (
            {
                "func": dummy_sync_function,
                "args": ("a",),
                "kwargs": {"kwarg": 3},
            },
            {
                "name": "Function",
                "timeout": 5.0,
                "args": ["a"],
                "kwargs": {"kwarg": 3},
            },
            None,
        ),
    ],
)
def test_init(params: dict[str, Any], expected: dict[str, Any], exception: type[BaseException] | None) -> None:
    """FunctionHealthCheck.__init__ and to_dict match expected or raise."""
    assert_check_init(lambda: FunctionHealthCheck(**params), expected, exception)


def test_init_raises_type_error_when_func_missing_without_config() -> None:
    """FunctionHealthCheck raises TypeError when config is None and func not provided."""
    with pytest.raises(TypeError, match=r"func is required when config is not provided"):
        FunctionHealthCheck(name="X")


def test_init_raises_type_error_when_func_missing_with_config() -> None:
    """FunctionHealthCheck raises TypeError when config is provided but func is not."""
    config = FunctionConfig(timeout=1.0)
    with pytest.raises(TypeError, match=r"func is required"):
        FunctionHealthCheck(config=config, name="X")


@pytest.mark.asyncio
async def test_sync_function_success() -> None:
    """Sync function check returns healthy."""
    check = FunctionHealthCheck(func=dummy_sync_function, args=("arg",), kwargs={"kwarg": 2}, timeout=0.2)
    result = await check()
    assert result == HealthCheckResult(name="Function", healthy=True)


@pytest.mark.asyncio
async def test_sync_function_failure() -> None:
    """Sync function check captures exception."""
    check = FunctionHealthCheck(func=dummy_sync_function_fail, args=("arg",), kwargs={"kwarg": 2}, timeout=0.2)
    result = await check()
    assert result.healthy is False
    assert result.error is not None
    assert "Test exception" in result.error.message


@pytest.mark.asyncio
async def test_async_function_success() -> None:
    """Async function check returns healthy."""
    check = FunctionHealthCheck(func=dummy_async_function, args=("arg",), kwargs={"kwarg": 2}, timeout=0.2)
    result = await check()
    assert result == HealthCheckResult(name="Function", healthy=True)


@pytest.mark.asyncio
async def test_async_function_failure() -> None:
    """Async function check captures exception."""
    check = FunctionHealthCheck(func=dummy_async_function_fail, args=("arg",), kwargs={"kwarg": 2}, timeout=0.2)
    result = await check()
    assert result.healthy is False
    assert result.error is not None
    assert "Test exception" in result.error.message


@pytest.mark.asyncio
async def test_sync_function_returns_false() -> None:
    """Sync function returning False yields unhealthy."""
    check = FunctionHealthCheck(func=dummy_sync_function_returns_false, timeout=0.2)
    result = await check()
    assert result.healthy is False
    assert result.error is not None
    assert result.error.code == DEPENDENCY_UNHEALTHY


@pytest.mark.asyncio
async def test_async_function_returns_false() -> None:
    """Async function returning False yields unhealthy."""
    check = FunctionHealthCheck(func=dummy_async_function_returns_false, timeout=0.2)
    result = await check()
    assert result.healthy is False
    assert result.error is not None
    assert result.error.code == DEPENDENCY_UNHEALTHY
