"""Health check that performs an HTTP GET to a URL.

UrlHealthCheck caches an httpx AsyncClient and supports optional basic auth,
SSL verification, and SSRF protection (block_private_hosts).
"""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING, Any, final
from urllib.parse import urlparse

from fast_healthchecks.checks._base import (
    _CLIENT_CACHING_SLOTS,
    ClientCachingMixin,
    ConfigDictMixin,
    HealthCheck,
    healthcheck_safe,
    result_unhealthy_dependency,
)
from fast_healthchecks.checks._imports import raise_optional_import_error
from fast_healthchecks.checks.configs import UrlConfig
from fast_healthchecks.models import HealthCheckResult
from fast_healthchecks.utils import validate_host_ssrf_async, validate_url_ssrf

try:
    from httpx import AsyncClient, AsyncHTTPTransport, BasicAuth, Response
except ImportError as exc:
    raise_optional_import_error("httpx", "httpx", exc)

if TYPE_CHECKING:
    import asyncio
    from collections.abc import Awaitable, Callable


def _close_url_client(client: AsyncClient) -> Awaitable[None]:
    return client.aclose()


@final
class UrlHealthCheck(ClientCachingMixin["AsyncClient"], ConfigDictMixin, HealthCheck[HealthCheckResult]):
    """Health check that performs an HTTP GET to a configurable URL.

    Supports basic auth, custom timeout, SSL verification, and optional
    SSRF protection via ``block_private_hosts`` (see config).
    """

    __slots__ = (*_CLIENT_CACHING_SLOTS, "_config", "_name")

    _config: UrlConfig
    _name: str
    _client: AsyncClient | None
    _client_loop: asyncio.AbstractEventLoop | None

    @property
    def _auth(self) -> BasicAuth | None:
        c = self._config
        return BasicAuth(c.username, c.password or "") if c.username else None

    @property
    def _transport(self) -> AsyncHTTPTransport:
        return AsyncHTTPTransport(verify=self._config.verify_ssl)

    @property
    def _block_private_hosts(self) -> bool:
        return self._config.block_private_hosts

    def __init__(
        self,
        *,
        config: UrlConfig | None = None,
        name: str = "HTTP",
        close_client_fn: Callable[[AsyncClient], Awaitable[None]] = _close_url_client,
        **kwargs: Any,  # noqa: ANN401
    ) -> None:
        """Initialize the health check.

        Warning:
            Pass only trusted URLs from application configuration. Do not use
            user-controlled input for ``url`` to avoid SSRF.

        Args:
            config: Connection config. If None, built from kwargs (url, username, etc.).
            name: The name of the health check.
            close_client_fn: Callable to close the cached client.
            **kwargs: Passed to UrlConfig when config is None (url required).
        """
        if config is None:
            kwargs = dict(kwargs)
            if "url" in kwargs:
                kwargs["url"] = str(kwargs["url"])
            config = UrlConfig(**kwargs)
        validate_url_ssrf(config.url, block_private_hosts=config.block_private_hosts)
        self._config = config
        self._name = name
        super().__init__(close_client_fn=close_client_fn)

    def _create_client(self) -> AsyncClient:
        c = self._config
        transport = AsyncHTTPTransport(verify=c.verify_ssl)
        return AsyncClient(
            auth=self._auth,
            timeout=c.timeout,
            transport=transport,
            follow_redirects=c.follow_redirects,
        )

    @healthcheck_safe(invalidate_on_error=True)
    async def __call__(self) -> HealthCheckResult:
        """Perform the health check.

        When block_private_hosts is True, resolves the URL host before the request
        and rejects if it resolves to loopback/private (SSRF/DNS rebinding protection).

        Returns:
            HealthCheckResult: Result with healthy=True if response is success.
        """
        if self._config.block_private_hosts:
            parsed = urlparse(self._config.url)
            host = parsed.hostname or ""
            await validate_host_ssrf_async(host)
        client = await self._ensure_client()
        response: Response = await client.get(self._config.url)
        if response.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR or (
            self._config.username and response.status_code in {HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN}
        ):
            response.raise_for_status()
        if response.is_success:
            return HealthCheckResult(name=self._name, healthy=True)
        return result_unhealthy_dependency(
            name=self._name,
            message=f"HTTP dependency returned status {response.status_code}",
            meta={"status_code": response.status_code},
        )
