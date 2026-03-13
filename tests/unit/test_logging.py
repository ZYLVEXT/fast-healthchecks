"""Tests for optional probe logging (OBS-1)."""

import logging

import pytest

from fast_healthchecks.checks.function import FunctionHealthCheck
from fast_healthchecks.integrations.base import Probe, run_probe
from fast_healthchecks.logging import (
    NullLogger,
    get_probe_logger,
    get_stdlib_probe_logger,
    set_probe_logger,
)
from fast_healthchecks.utils import REDACT_PLACEHOLDER, redact_secrets_in_dict

pytestmark = pytest.mark.unit

_MIN_PROBE_LOG_RECORDS = 2


def test_default_logger_is_null_logger() -> None:
    """Default probe logger is NullLogger (logging disabled)."""
    assert type(get_probe_logger()) is NullLogger


def test_null_logger_log_is_no_op() -> None:
    """NullLogger.log() does nothing (no-op)."""
    logger = NullLogger()
    logger.log(logging.INFO, "msg", key="value")  # no raise, no side effect


def test_set_and_get_probe_logger() -> None:
    """set_probe_logger sets the logger returned by get_probe_logger."""
    custom = NullLogger()
    try:
        set_probe_logger(custom)
        assert get_probe_logger() is custom
    finally:
        set_probe_logger(NullLogger())


@pytest.mark.asyncio
async def test_when_logging_disabled_handler_receives_zero_records() -> None:
    """When logger is NullLogger, no records are emitted (4b)."""
    # Attach handler to stdlib logger that would be used if we enabled it
    stdlib_logger = logging.getLogger("fast_healthchecks.probe")
    records: list[logging.LogRecord] = []
    handler = logging.Handler()
    handler.emit = lambda r: records.append(r)  # type: ignore[method-assign]  # noqa: PLW0108
    stdlib_logger.addHandler(handler)
    stdlib_logger.setLevel(logging.DEBUG)
    try:
        set_probe_logger(NullLogger())
        probe = Probe(
            name="test",
            checks=[FunctionHealthCheck(func=lambda: True, name="A")],
        )
        await run_probe(probe)
        assert len(records) == 0
    finally:
        stdlib_logger.removeHandler(handler)
        set_probe_logger(NullLogger())


@pytest.mark.asyncio
async def test_when_logging_enabled_probe_start_and_end_logged() -> None:
    """When stdlib logger is set, probe_start and probe_end are logged."""
    records: list[logging.LogRecord] = []
    logger = logging.getLogger("fast_healthchecks.probe.test_enabled")
    logger.setLevel(logging.DEBUG)
    handler = logging.Handler()
    handler.emit = lambda r: records.append(r)  # type: ignore[method-assign]  # noqa: PLW0108
    logger.addHandler(handler)
    try:
        set_probe_logger(get_stdlib_probe_logger("fast_healthchecks.probe.test_enabled"))
        probe = Probe(
            name="p",
            checks=[FunctionHealthCheck(func=lambda: True, name="A")],
        )
        await run_probe(probe)
        assert len(records) >= _MIN_PROBE_LOG_RECORDS
        messages = [r.msg for r in records]
        assert "probe_start" in messages
        assert "probe_end" in messages
    finally:
        logger.removeHandler(handler)
        set_probe_logger(NullLogger())


def test_stdlib_logger_redacts_extra() -> None:
    """Stdlib probe logger redacts secret keys in extra (same as DOC-3)."""
    log_name = "fast_healthchecks.probe.test_redact"
    logger = get_stdlib_probe_logger(log_name)
    stdlib_logger = logging.getLogger(log_name)
    records: list[logging.LogRecord] = []
    h = logging.Handler()
    h.emit = lambda r: records.append(r)  # type: ignore[method-assign]  # noqa: PLW0108
    stdlib_logger.addHandler(h)
    stdlib_logger.setLevel(logging.DEBUG)
    try:
        logger.log(logging.INFO, "test", password="secret", user="u", other="ok")
        assert len(records) == 1
        assert getattr(records[0], "password", None) == REDACT_PLACEHOLDER
        assert getattr(records[0], "other", None) == "ok"
    finally:
        stdlib_logger.removeHandler(h)


def test_stdlib_logger_redacts_nested_meta() -> None:
    """Stdlib probe logger redacts nested secret keys in extra payloads."""
    log_name = "fast_healthchecks.probe.test_redact_nested"
    logger = get_stdlib_probe_logger(log_name)
    stdlib_logger = logging.getLogger(log_name)
    records: list[logging.LogRecord] = []
    h = logging.Handler()
    h.emit = lambda r: records.append(r)  # type: ignore[method-assign]  # noqa: PLW0108
    stdlib_logger.addHandler(h)
    stdlib_logger.setLevel(logging.DEBUG)
    try:
        logger.log(
            logging.INFO,
            "test_nested",
            error={"meta": {"password": "secret", "user": "alice", "token": "abc", "ok": "value"}},
        )
        assert len(records) == 1
        redacted_error = getattr(records[0], "error", None)
        assert isinstance(redacted_error, dict)
        assert redacted_error["meta"]["password"] == REDACT_PLACEHOLDER
        assert redacted_error["meta"]["user"] == REDACT_PLACEHOLDER
        assert redacted_error["meta"]["token"] == REDACT_PLACEHOLDER
        assert redacted_error["meta"]["ok"] == "value"
    finally:
        stdlib_logger.removeHandler(h)


def test_redact_secrets_in_dict_same_keys_as_utils() -> None:
    """Redaction uses same keys as utils (DOC-3 alignment)."""
    data = {"user": "u", "password": "p", "name": "n"}
    out = redact_secrets_in_dict(data)
    assert out["user"] != "u"
    assert out["password"] != "p"
    assert out["name"] == "n"
