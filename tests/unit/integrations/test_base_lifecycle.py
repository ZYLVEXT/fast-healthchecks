"""Tests for close_probes and healthcheck_shutdown lifecycle helpers."""

from unittest.mock import AsyncMock

import pytest

from fast_healthchecks.checks.function import FunctionHealthCheck
from fast_healthchecks.integrations.base import Probe, close_probes, healthcheck_shutdown

pytestmark = pytest.mark.unit


def _success_check() -> bool:
    return True


@pytest.mark.asyncio
async def test_close_probes_calls_aclose_on_checks_that_have_it() -> None:
    """close_probes calls aclose() on each check that has it."""
    check_with_aclose = FunctionHealthCheck(func=_success_check, name="A")
    check_with_aclose.aclose = AsyncMock()  # type: ignore[method-assign]
    check_no_aclose = FunctionHealthCheck(func=_success_check, name="B")
    probe = Probe(name="p", checks=[check_with_aclose, check_no_aclose])
    await close_probes([probe])
    check_with_aclose.aclose.assert_awaited_once_with()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_close_probes_ignores_exceptions() -> None:
    """close_probes suppresses exceptions so one failure does not block others."""
    check_ok = FunctionHealthCheck(func=_success_check, name="A")
    check_ok.aclose = AsyncMock()  # type: ignore[method-assign]
    check_fail = FunctionHealthCheck(func=_success_check, name="B")
    check_fail.aclose = AsyncMock(side_effect=RuntimeError("close failed"))  # type: ignore[method-assign]
    probe = Probe(name="p", checks=[check_ok, check_fail])
    await close_probes([probe])
    check_ok.aclose.assert_awaited_once_with()  # type: ignore[attr-defined]
    check_fail.aclose.assert_awaited_once_with()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_close_probes_empty_iterable() -> None:
    """close_probes with no probes does nothing."""
    await close_probes([])


@pytest.mark.asyncio
async def test_healthcheck_shutdown_returns_callable_that_closes_probes() -> None:
    """healthcheck_shutdown(probes) returns an async callable that closes those probes."""
    check = FunctionHealthCheck(func=_success_check, name="A")
    check.aclose = AsyncMock()  # type: ignore[method-assign]
    probe = Probe(name="p", checks=[check])
    shutdown = healthcheck_shutdown([probe])
    await shutdown()
    check.aclose.assert_awaited_once_with()  # type: ignore[attr-defined]
