"""Tests for close_probes and healthcheck_shutdown lifecycle helpers."""

import pytest

from fast_healthchecks.checks.function import FunctionHealthCheck
from fast_healthchecks.integrations.base import Probe, close_probes, healthcheck_shutdown

from .helpers import CheckWithAclose

pytestmark = pytest.mark.unit


def _success_check() -> bool:
    """Return True for lifecycle tests.

    Returns:
        True.
    """
    return True


@pytest.mark.asyncio
async def test_close_probes_calls_aclose_on_checks_that_have_it() -> None:
    """close_probes calls aclose() on each check that has it."""
    check_with_aclose = CheckWithAclose(name="A")
    check_no_aclose = FunctionHealthCheck(func=_success_check, name="B")
    probe = Probe(name="p", checks=[check_with_aclose, check_no_aclose])
    await close_probes([probe])
    check_with_aclose._aclose_mock.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_close_probes_ignores_exceptions() -> None:
    """close_probes suppresses exceptions so one failure does not block others."""
    check_ok = CheckWithAclose(name="A")
    check_fail = CheckWithAclose(name="B", aclose_side_effect=RuntimeError("close failed"))
    probe = Probe(name="p", checks=[check_ok, check_fail])
    await close_probes([probe])
    check_ok._aclose_mock.assert_awaited_once_with()
    check_fail._aclose_mock.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_close_probes_empty_iterable() -> None:
    """close_probes with no probes does nothing."""
    await close_probes([])


@pytest.mark.asyncio
async def test_healthcheck_shutdown_returns_callable_that_closes_probes() -> None:
    """healthcheck_shutdown(probes) returns an async callable that closes those probes."""
    check = CheckWithAclose(name="A")
    probe = Probe(name="p", checks=[check])
    shutdown = healthcheck_shutdown([probe])
    await shutdown()
    check._aclose_mock.assert_awaited_once_with()
