"""This module provides a health check class for OpenSearch.

Classes:
    OpenSearchHealthCheck: A class to perform health checks on OpenSearch.

Usage:
    The OpenSearchHealthCheck class can be used to perform health checks on OpenSearch by calling it.

Example:
    health_check = OpenSearchHealthCheck(
        hosts=["localhost:9200"],
        http_auth=("username", "password"),
        use_ssl=True,
        verify_certs=True,
        ssl_show_warn=False,
        ca_certs="/path/to/ca.pem",
    )
    result = await health_check()
    print(result.healthy)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast, final
from urllib.parse import unquote, urlsplit

from fast_healthchecks.checks._base import (
    _CLIENT_CACHING_SLOTS,
    DEFAULT_HC_TIMEOUT,
    ClientCachingMixin,
    HealthCheckDSN,
    healthcheck_safe,
)
from fast_healthchecks.checks._imports import raise_optional_import_error
from fast_healthchecks.checks.configs import OpenSearchConfig
from fast_healthchecks.checks.dsn_parsing import OpenSearchParseDsnResult
from fast_healthchecks.models import HealthCheckResult

if TYPE_CHECKING:
    import asyncio
    from collections.abc import Awaitable, Callable

try:
    from opensearchpy import AsyncOpenSearch
except ImportError as exc:
    raise_optional_import_error("opensearch", "opensearch-py", exc)


def _close_opensearch_client(client: AsyncOpenSearch) -> Awaitable[None]:
    return client.close()


@final
class OpenSearchHealthCheck(
    ClientCachingMixin["AsyncOpenSearch"],
    HealthCheckDSN[HealthCheckResult, OpenSearchParseDsnResult],
):
    """A class to perform health checks on OpenSearch.

    Attributes:
        _hosts: The OpenSearch hosts.
        _name: The name of the health check.
        _http_auth: The HTTP authentication.
        _use_ssl: Whether to use SSL or not.
        _verify_certs: Whether to verify certificates or not.
        _ssl_show_warn: Whether to show SSL warnings or not.
        _ca_certs: The CA certificates.
        _timeout: The timeout for the health check.
    """

    __slots__ = (*_CLIENT_CACHING_SLOTS, "_config", "_name")

    _config: OpenSearchConfig
    _name: str
    _client: AsyncOpenSearch | None
    _client_loop: asyncio.AbstractEventLoop | None

    def __init__(
        self,
        *,
        config: OpenSearchConfig | None = None,
        name: str = "OpenSearch",
        close_client_fn: Callable[[AsyncOpenSearch], Awaitable[None]] = _close_opensearch_client,
        **kwargs: Any,  # noqa: ANN401
    ) -> None:
        """Initialize the OpenSearchHealthCheck.

        Args:
            config: Connection config. If None, built from kwargs (hosts, http_auth, etc.).
            name: The name of the health check.
            close_client_fn: Callable to close the cached client.
            **kwargs: Passed to OpenSearchConfig when config is None.
        """
        if config is None:
            config = OpenSearchConfig(**kwargs)
        self._config = config
        self._name = name
        super().__init__(close_client_fn=close_client_fn)

    def _create_client(self) -> AsyncOpenSearch:
        c = self._config
        return AsyncOpenSearch(
            hosts=c.hosts,
            http_auth=c.http_auth,
            use_ssl=c.use_ssl,
            verify_certs=c.verify_certs,
            ssl_show_warn=c.ssl_show_warn,
            ca_certs=c.ca_certs,
            timeout=c.timeout,
        )

    @classmethod
    def _allowed_schemes(cls) -> tuple[str, ...]:
        return ("http", "https")

    @classmethod
    def _default_name(cls) -> str:
        return "OpenSearch"

    @classmethod
    def parse_dsn(cls, dsn: str) -> OpenSearchParseDsnResult:
        """Parse the OpenSearch DSN and return the results.

        Args:
            dsn: The DSN to parse.

        Returns:
            OpenSearchParseDsnResult: The results of parsing the DSN.

        Raises:
            ValueError: If DSN has missing host.
        """
        parsed = urlsplit(dsn)
        if not parsed.hostname:
            msg = "OpenSearch DSN must include a host"
            raise ValueError(msg) from None

        http_auth: tuple[str, str] | None = None
        if parsed.username is not None:
            http_auth = (unquote(parsed.username), unquote(parsed.password or ""))

        port = parsed.port or (443 if parsed.scheme == "https" else 9200)
        return {
            "hosts": [f"{parsed.hostname}:{port}"],
            "http_auth": http_auth,
            "use_ssl": parsed.scheme == "https",
        }

    @classmethod
    def _from_parsed_dsn(
        cls,
        parsed: OpenSearchParseDsnResult,
        *,
        name: str = "OpenSearch",
        timeout: float = DEFAULT_HC_TIMEOUT,
        **kwargs: object,
    ) -> OpenSearchHealthCheck:
        config = OpenSearchConfig(
            hosts=parsed["hosts"],
            http_auth=parsed["http_auth"],
            use_ssl=parsed["use_ssl"],
            verify_certs=cast("bool", kwargs.get("verify_certs", False)),
            ssl_show_warn=cast("bool", kwargs.get("ssl_show_warn", False)),
            ca_certs=cast("str | None", kwargs.get("ca_certs")),
            timeout=timeout,
        )
        return cls(config=config, name=name)

    @healthcheck_safe(invalidate_on_error=True)
    async def __call__(self) -> HealthCheckResult:
        """Perform the health check on OpenSearch.

        Returns:
            HealthCheckResult: The result of the health check.
        """
        client = await self._ensure_client()
        await client.info()
        return HealthCheckResult(name=self._name, healthy=True)
