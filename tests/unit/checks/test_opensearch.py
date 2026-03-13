"""Unit tests for OpenSearchHealthCheck."""

import asyncio
import ssl
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from opensearchpy import AsyncOpenSearch

from fast_healthchecks.checks.opensearch import OpenSearchHealthCheck
from tests.utils import assert_check_init

pytestmark = pytest.mark.unit

test_ssl_context = ssl.create_default_context()
EXPECTED_CLIENT_CREATIONS_AFTER_RECREATE = 2


@pytest.mark.parametrize(
    ("params", "expected", "exception"),
    [
        (
            {},
            {
                "hosts": ["localhost:9200"],
                "http_auth": None,
                "use_ssl": False,
                "verify_certs": False,
                "ssl_show_warn": False,
                "ca_certs": None,
                "timeout": 5.0,
                "name": "OpenSearch",
            },
            None,
        ),
        (
            {
                "hosts": ["localhost:9200"],
            },
            {
                "hosts": ["localhost:9200"],
                "http_auth": None,
                "use_ssl": False,
                "verify_certs": False,
                "ssl_show_warn": False,
                "ca_certs": None,
                "timeout": 5.0,
                "name": "OpenSearch",
            },
            None,
        ),
        (
            {
                "hosts": ["localhost:9200"],
                "http_auth": ("username", "password"),
            },
            {
                "hosts": ["localhost:9200"],
                "http_auth": ("username", "password"),
                "use_ssl": False,
                "verify_certs": False,
                "ssl_show_warn": False,
                "ca_certs": None,
                "timeout": 5.0,
                "name": "OpenSearch",
            },
            None,
        ),
        (
            {
                "hosts": ["localhost:9200"],
                "http_auth": ("username", "password"),
                "use_ssl": True,
            },
            {
                "hosts": ["localhost:9200"],
                "http_auth": ("username", "password"),
                "use_ssl": True,
                "verify_certs": False,
                "ssl_show_warn": False,
                "ca_certs": None,
                "timeout": 5.0,
                "name": "OpenSearch",
            },
            None,
        ),
        (
            {
                "hosts": ["localhost:9200"],
                "http_auth": ("username", "password"),
                "use_ssl": True,
                "verify_certs": True,
            },
            {
                "hosts": ["localhost:9200"],
                "http_auth": ("username", "password"),
                "use_ssl": True,
                "verify_certs": True,
                "ssl_show_warn": False,
                "ca_certs": None,
                "timeout": 5.0,
                "name": "OpenSearch",
            },
            None,
        ),
        (
            {
                "hosts": ["localhost:9200"],
                "http_auth": ("username", "password"),
                "use_ssl": True,
                "verify_certs": True,
                "ssl_show_warn": True,
            },
            {
                "hosts": ["localhost:9200"],
                "http_auth": ("username", "password"),
                "use_ssl": True,
                "verify_certs": True,
                "ssl_show_warn": True,
                "ca_certs": None,
                "timeout": 5.0,
                "name": "OpenSearch",
            },
            None,
        ),
        (
            {
                "hosts": ["localhost:9200"],
                "http_auth": ("username", "password"),
                "use_ssl": True,
                "verify_certs": True,
                "ssl_show_warn": True,
                "ca_certs": "ca_certs",
            },
            {
                "hosts": ["localhost:9200"],
                "http_auth": ("username", "password"),
                "use_ssl": True,
                "verify_certs": True,
                "ssl_show_warn": True,
                "ca_certs": "ca_certs",
                "timeout": 5.0,
                "name": "OpenSearch",
            },
            None,
        ),
        (
            {
                "hosts": ["localhost:9200"],
                "http_auth": ("username", "password"),
                "use_ssl": True,
                "verify_certs": True,
                "ssl_show_warn": True,
                "ca_certs": "ca_certs",
                "timeout": 1.5,
            },
            {
                "hosts": ["localhost:9200"],
                "http_auth": ("username", "password"),
                "use_ssl": True,
                "verify_certs": True,
                "ssl_show_warn": True,
                "ca_certs": "ca_certs",
                "timeout": 1.5,
                "name": "OpenSearch",
            },
            None,
        ),
        (
            {
                "hosts": ["localhost:9200"],
                "http_auth": ("username", "password"),
                "use_ssl": True,
                "verify_certs": True,
                "ssl_show_warn": True,
                "ca_certs": "ca_certs",
                "timeout": 1.5,
                "name": "Test",
            },
            {
                "hosts": ["localhost:9200"],
                "http_auth": ("username", "password"),
                "use_ssl": True,
                "verify_certs": True,
                "ssl_show_warn": True,
                "ca_certs": "ca_certs",
                "timeout": 1.5,
                "name": "Test",
            },
            None,
        ),
    ],
)
def test__init(params: dict[str, Any], expected: dict[str, Any] | str, exception: type[BaseException] | None) -> None:
    """OpenSearchHealthCheck.__init__ and to_dict match expected or raise."""
    assert_check_init(lambda: OpenSearchHealthCheck(**params), expected, exception)


@pytest.mark.parametrize(
    ("dsn", "kwargs", "expected", "exception"),
    [
        (
            "http://localhost:9200",
            {},
            {
                "hosts": ["localhost:9200"],
                "http_auth": None,
                "use_ssl": False,
                "verify_certs": False,
                "ssl_show_warn": False,
                "ca_certs": None,
                "timeout": 5.0,
                "name": "OpenSearch",
            },
            None,
        ),
        (
            "https://user:password@localhost",
            {"verify_certs": True, "timeout": 1.5, "name": "Test"},
            {
                "hosts": ["localhost:443"],
                "http_auth": ("user", "password"),
                "use_ssl": True,
                "verify_certs": True,
                "ssl_show_warn": False,
                "ca_certs": None,
                "timeout": 1.5,
                "name": "Test",
            },
            None,
        ),
        (
            "HTTPS://localhost:9200",
            {},
            {
                "hosts": ["localhost:9200"],
                "http_auth": None,
                "use_ssl": True,
                "verify_certs": False,
                "ssl_show_warn": False,
                "ca_certs": None,
                "timeout": 5.0,
                "name": "OpenSearch",
            },
            None,
        ),
        (
            "opensearch://localhost:9200",
            {},
            r"DSN scheme must be one of http, https",
            ValueError,
        ),
        ("", {}, "DSN cannot be empty", ValueError),
        (
            "https://",
            {},
            "OpenSearch DSN must include a host",
            ValueError,
        ),
    ],
)
def test_from_dsn(
    dsn: str,
    kwargs: dict[str, Any],
    expected: dict[str, Any] | str,
    exception: type[BaseException] | None,
) -> None:
    """Test from_dsn with various DSN options."""
    assert_check_init(lambda: OpenSearchHealthCheck.from_dsn(dsn, **kwargs), expected, exception)


@pytest.mark.asyncio
async def test_AsyncOpenSearch_args_kwargs() -> None:
    """Constructor args/kwargs are passed through to AsyncOpenSearch."""
    health_check = OpenSearchHealthCheck(
        hosts=["localhost:9200"],
        http_auth=("user", "password"),
        use_ssl=True,
        verify_certs=True,
        ssl_show_warn=True,
        ca_certs="ca_certs",
        timeout=1.5,
        name="OpenSearch",
    )
    with patch("fast_healthchecks.checks.opensearch.AsyncOpenSearch", spec=AsyncOpenSearch) as mock:
        await health_check()
        mock.assert_called_once_with(
            hosts=["localhost:9200"],
            http_auth=("user", "password"),
            use_ssl=True,
            verify_certs=True,
            ssl_show_warn=True,
            ca_certs="ca_certs",
            timeout=1.5,
        )


@pytest.mark.asyncio
async def test_AsyncOpenSearch_reused_between_calls() -> None:
    """Same client instance is reused across __call__ invocations."""
    health_check = OpenSearchHealthCheck(hosts=["localhost:9200"])
    mock_client = AsyncMock(spec=AsyncOpenSearch)
    mock_client.info = AsyncMock(return_value={"version": {"number": "2.19.0"}})
    with patch("fast_healthchecks.checks.opensearch.AsyncOpenSearch", return_value=mock_client) as factory:
        await health_check()
        await health_check()
        factory.assert_called_once_with(
            hosts=["localhost:9200"],
            http_auth=None,
            use_ssl=False,
            verify_certs=False,
            ssl_show_warn=False,
            ca_certs=None,
            timeout=5.0,
        )


@pytest.mark.asyncio
async def test__call_success() -> None:
    """Check returns healthy when cluster health succeeds."""
    health_check = OpenSearchHealthCheck(hosts=["localhost:9200"])
    mock_client = AsyncMock(spec=AsyncOpenSearch)
    mock_client.info = AsyncMock()
    mock_client.info.side_effect = [
        {
            "name": "b2a910773ffb",
            "cluster_name": "docker-cluster",
            "cluster_uuid": "dIZBX0OeT_qjp0YGVkfe-g",
            "version": {
                "distribution": "opensearch",
                "number": "2.19.0",
                "build_type": "tar",
                "build_hash": "fd9a9d90df25bea1af2c6a85039692e815b894f5",
                "build_date": "2025-02-05T16:13:57.130576800Z",
                "build_snapshot": False,
                "lucene_version": "9.12.1",
                "minimum_wire_compatibility_version": "7.10.0",
                "minimum_index_compatibility_version": "7.0.0",
            },
            "tagline": "The OpenSearch Project: https://opensearch.org/",
        },
    ]
    with patch("fast_healthchecks.checks.opensearch.AsyncOpenSearch", return_value=mock_client):
        result = await health_check()
        assert result.healthy is True
        assert result.name == "OpenSearch"
        assert result.error is None
        mock_client.info.assert_called_once_with()
        mock_client.info.assert_awaited_once_with()


@pytest.mark.asyncio
async def test__call_failure() -> None:
    """Check returns unhealthy when client raises."""
    health_check = OpenSearchHealthCheck(hosts=["localhost:9200"])
    mock_client = AsyncMock(spec=AsyncOpenSearch)
    mock_client.info = AsyncMock()
    mock_client.info.side_effect = [Exception("Connection error")]
    with patch("fast_healthchecks.checks.opensearch.AsyncOpenSearch", return_value=mock_client):
        result = await health_check()
        assert result.healthy is False
        assert result.name == "OpenSearch"
        assert result.error is not None
        assert "Connection error" in result.error.message
        mock_client.info.assert_called_once_with()
        mock_client.info.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_aclose_clears_client() -> None:
    """aclose() closes and clears cached client."""
    health_check = OpenSearchHealthCheck(hosts=["localhost:9200"])
    mock_client = AsyncMock(spec=AsyncOpenSearch)
    mock_client.info = AsyncMock(return_value={"version": {"number": "2.19.0"}})
    with patch("fast_healthchecks.checks.opensearch.AsyncOpenSearch", return_value=mock_client) as factory:
        await health_check()
        assert health_check._client is not None
        await health_check.aclose()
        assert health_check._client is None
        assert health_check._client_loop is None
        await health_check()
        assert factory.call_count == EXPECTED_CLIENT_CREATIONS_AFTER_RECREATE


@pytest.mark.asyncio
async def test_aclose_idempotent_when_no_client() -> None:
    """aclose() when no client is safe and idempotent."""
    health_check = OpenSearchHealthCheck(hosts=["localhost:9200"])
    await health_check.aclose()
    assert health_check._client is None


@pytest.mark.asyncio
async def test_loop_invalidation_recreates_client() -> None:
    """Client from different event loop is recreated on next __call__."""
    health_check = OpenSearchHealthCheck(hosts=["localhost:9200"])
    real_loop = asyncio.get_running_loop()
    other_loop = object()
    mock_client = AsyncMock(spec=AsyncOpenSearch)
    mock_client.info = AsyncMock(return_value={"version": {"number": "2.19.0"}})
    with (
        patch("fast_healthchecks.checks.opensearch.AsyncOpenSearch", return_value=mock_client) as factory,
        patch(
            "fast_healthchecks.checks._base.asyncio.get_running_loop",
            side_effect=[real_loop, real_loop, other_loop, other_loop],
        ),
    ):
        await health_check()
        await health_check()
        assert factory.call_count == EXPECTED_CLIENT_CREATIONS_AFTER_RECREATE


@pytest.mark.asyncio
async def test_get_client_with_no_running_loop() -> None:
    """_ensure_client works when get_running_loop raises."""
    health_check = OpenSearchHealthCheck(hosts=["localhost:9200"])
    mock_client = AsyncMock(spec=AsyncOpenSearch)
    mock_client.info = AsyncMock(return_value={"version": {"number": "2.19.0"}})
    with (
        patch("fast_healthchecks.checks._base.asyncio.get_running_loop", side_effect=RuntimeError),
        patch("fast_healthchecks.checks.opensearch.AsyncOpenSearch", return_value=mock_client) as factory,
    ):
        result = await health_check()
        assert result.healthy is True
        factory.assert_called_once()
        assert health_check._client_loop is None
