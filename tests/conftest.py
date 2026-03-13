"""Pytest configuration and shared fixtures for fast-healthchecks tests."""

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Register warning filters for test runs only (upstream deps; not in production)."""
    # Litestar still imports pydantic.v1; cannot fix until Litestar drops V1.
    config.addinivalue_line(
        "filterwarnings",
        "ignore:Core Pydantic V1 functionality isn't compatible with Python 3.14 or greater:UserWarning",
    )
    # pytest-asyncio uses get_event_loop_policy (deprecated in 3.14).
    config.addinivalue_line(
        "filterwarnings",
        "ignore:'asyncio.get_event_loop_policy' is deprecated:DeprecationWarning",
    )
    # aiohttp.connector (e.g. opensearch-py async transport) emits deprecation on 3.14+.
    config.addinivalue_line(
        "filterwarnings",
        "ignore::DeprecationWarning:aiohttp.connector",
    )
