import os
from typing import Any

import pytest
from dotenv import dotenv_values


def pytest_configure(config: pytest.Config) -> None:
    """Ignore unraisable warnings from health-check clients not closed at TestClient teardown.

    When using xdist or multiple test runs, cached clients (aiohttp, OpenSearch, etc.)
    can be GC'd after their event loop is closed, triggering ResourceWarning in __del__.
    TestClient does not expose a shutdown hook to call aclose() on checks.
    """
    config.addinivalue_line(
        "filterwarnings",
        "ignore:Exception ignored in:pytest.PytestUnraisableExceptionWarning",
    )


@pytest.fixture(scope="session", name="env_config")
def fixture_env_config() -> dict[str, Any]:
    return {
        **dotenv_values(".env"),  # load shared default test environment variables
        **os.environ,  # override loaded values with environment variables
    }
