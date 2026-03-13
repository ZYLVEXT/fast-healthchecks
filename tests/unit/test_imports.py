"""Tests for optional-check import errors and install hints."""

import importlib

import pytest

pytestmark = pytest.mark.imports


def test_probe_runner_is_main_entrypoint() -> None:
    """ProbeRunner and RunPolicy are importable from the root package."""
    pkg = importlib.import_module("fast_healthchecks")

    assert hasattr(pkg, "ProbeRunner"), "ProbeRunner must be in root __all__"
    assert hasattr(pkg, "RunPolicy"), "RunPolicy must be in root __all__"
    assert "ProbeRunner" in pkg.__all__
    assert "RunPolicy" in pkg.__all__


def test_run_probe_not_in_root_api() -> None:
    """run_probe is not in root __all__ (removed in v1.0)."""
    pkg = importlib.import_module("fast_healthchecks")

    assert "run_probe" not in pkg.__all__
    assert not hasattr(pkg, "run_probe")


def test_healthcheck_shutdown_not_in_root_api() -> None:
    """healthcheck_shutdown is not in root __all__ (removed in v1.0)."""
    pkg = importlib.import_module("fast_healthchecks")

    assert "healthcheck_shutdown" not in pkg.__all__
    assert not hasattr(pkg, "healthcheck_shutdown")


@pytest.mark.parametrize(
    ("module_path", "message_substring"),
    [
        (
            "fast_healthchecks.checks.postgresql.asyncpg",
            r"asyncpg is not installed. Install it with `pip install fast-healthchecks\[asyncpg\]`.",
        ),
        (
            "fast_healthchecks.checks.postgresql.psycopg",
            r"psycopg is not installed. Install it with `pip install fast-healthchecks\[psycopg\]`.",
        ),
        (
            "fast_healthchecks.checks.kafka",
            r"aiokafka is not installed. Install it with `pip install fast-healthchecks\[aiokafka\]`.",
        ),
        (
            "fast_healthchecks.checks.mongo",
            r"motor is not installed. Install it with `pip install fast-healthchecks\[motor\]`.",
        ),
        (
            "fast_healthchecks.checks.opensearch",
            r"opensearch-py is not installed. Install it with `pip install fast-healthchecks\[opensearch\]`.",
        ),
        (
            "fast_healthchecks.checks.rabbitmq",
            r"aio-pika is not installed. Install it with `pip install fast-healthchecks\[aio-pika\]`.",
        ),
        (
            "fast_healthchecks.checks.redis",
            r"redis is not installed. Install it with `pip install fast-healthchecks\[redis\]`.",
        ),
        (
            "fast_healthchecks.checks.url",
            r"httpx is not installed. Install it with `pip install fast-healthchecks\[httpx\]`.",
        ),
    ],
)
def test_import_error_optional_check(module_path: str, message_substring: str) -> None:
    """Importing optional check without extra raises ImportError with install hint."""
    with pytest.raises(ImportError, match=message_substring):
        importlib.import_module(module_path)
