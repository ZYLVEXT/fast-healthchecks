import asyncio
import time

import pytest

from fast_healthchecks.checks.function import FunctionHealthCheck
from fast_healthchecks.models import HealthCheckResult

pytestmark = pytest.mark.unit


def dummy_sync_function(arg: str, kwarg: int = 1) -> None:
    time.sleep(0.1)


def dummy_sync_function_fail(arg: str, kwarg: int = 1) -> None:
    time.sleep(0.1)
    msg = "Test exception"
    raise ValueError(msg) from None


async def dummy_async_function(arg: str, kwarg: int = 1) -> None:
    await asyncio.sleep(0.1)


async def dummy_async_function_fail(arg: str, kwarg: int = 1) -> None:
    await asyncio.sleep(0.1)
    msg = "Test exception"
    raise ValueError(msg) from None


def dummy_sync_function_returns_false() -> bool:
    return False


async def dummy_async_function_returns_false() -> bool:
    await asyncio.sleep(0.01)
    return False


@pytest.mark.asyncio
async def test_sync_function_success() -> None:
    check = FunctionHealthCheck(func=dummy_sync_function, args=("arg",), kwargs={"kwarg": 2}, timeout=0.2)
    result = await check()
    assert result == HealthCheckResult(name="Function", healthy=True, error_details=None)


@pytest.mark.asyncio
async def test_sync_function_failure() -> None:
    check = FunctionHealthCheck(func=dummy_sync_function_fail, args=("arg",), kwargs={"kwarg": 2}, timeout=0.2)
    result = await check()
    assert result.healthy is False
    assert result.error_details is not None
    assert "Test exception" in result.error_details


@pytest.mark.asyncio
async def test_async_function_success() -> None:
    check = FunctionHealthCheck(func=dummy_async_function, args=("arg",), kwargs={"kwarg": 2}, timeout=0.2)
    result = await check()
    assert result == HealthCheckResult(name="Function", healthy=True, error_details=None)


@pytest.mark.asyncio
async def test_async_function_failure() -> None:
    check = FunctionHealthCheck(func=dummy_async_function_fail, args=("arg",), kwargs={"kwarg": 2}, timeout=0.2)
    result = await check()
    assert result.healthy is False
    assert result.error_details is not None
    assert "Test exception" in result.error_details


@pytest.mark.asyncio
async def test_sync_function_returns_false() -> None:
    check = FunctionHealthCheck(func=dummy_sync_function_returns_false, timeout=0.2)
    result = await check()
    assert result == HealthCheckResult(name="Function", healthy=False, error_details=None)


@pytest.mark.asyncio
async def test_async_function_returns_false() -> None:
    check = FunctionHealthCheck(func=dummy_async_function_returns_false, timeout=0.2)
    result = await check()
    assert result == HealthCheckResult(name="Function", healthy=False, error_details=None)
