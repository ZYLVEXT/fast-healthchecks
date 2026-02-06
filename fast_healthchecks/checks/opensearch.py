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

import asyncio
import contextlib
from traceback import format_exc
from typing import Any, final
from urllib.parse import unquote, urlsplit

from fast_healthchecks.checks._base import DEFAULT_HC_TIMEOUT, HealthCheck
from fast_healthchecks.models import HealthCheckResult

IMPORT_ERROR_MSG = "opensearch-py is not installed. Install it with `pip install fast-healthchecks[opensearch]`."

try:
    from opensearchpy import AsyncOpenSearch
except ImportError as exc:
    raise ImportError(IMPORT_ERROR_MSG) from exc


@final
class OpenSearchHealthCheck(HealthCheck[HealthCheckResult]):
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

    __slots__ = (
        "_ca_certs",
        "_client",
        "_client_loop",
        "_hosts",
        "_http_auth",
        "_name",
        "_ssl_show_warn",
        "_timeout",
        "_use_ssl",
        "_verify_certs",
    )

    _hosts: list[str]
    _http_auth: tuple[str, str] | None
    _use_ssl: bool
    _verify_certs: bool
    _ssl_show_warn: bool
    _ca_certs: str | None
    _timeout: float
    _name: str
    _client: AsyncOpenSearch | None
    _client_loop: asyncio.AbstractEventLoop | None

    def __init__(  # noqa: PLR0913
        self,
        *,
        hosts: list[str],
        http_auth: tuple[str, str] | None = None,
        use_ssl: bool = False,
        verify_certs: bool = False,
        ssl_show_warn: bool = False,
        ca_certs: str | None = None,
        timeout: float = DEFAULT_HC_TIMEOUT,
        name: str = "OpenSearch",
    ) -> None:
        """Initialize the OpenSearchHealthCheck.

        Args:
            hosts: The OpenSearch hosts.
            http_auth: The HTTP authentication.
            use_ssl: Whether to use SSL or not.
            verify_certs: Whether to verify certificates or not.
            ssl_show_warn: Whether to show SSL warnings or not.
            ca_certs: The CA certificates.
            timeout: The timeout for the health check.
            name: The name of the health check.
        """
        self._hosts = hosts
        self._http_auth = http_auth
        self._use_ssl = use_ssl
        self._verify_certs = verify_certs
        self._ssl_show_warn = ssl_show_warn
        self._ca_certs = ca_certs
        self._timeout = timeout
        self._name = name
        self._client = None
        self._client_loop = None

    async def aclose(self) -> None:
        """Close the cached OpenSearch client if present."""
        if self._client is not None:
            await self._client.close()
            self._client = None
            self._client_loop = None

    def _get_client(self) -> AsyncOpenSearch:
        if self._client is None:
            try:
                self._client_loop = asyncio.get_running_loop()
            except RuntimeError:
                self._client_loop = None
            self._client = AsyncOpenSearch(
                hosts=self._hosts,
                http_auth=self._http_auth,
                use_ssl=self._use_ssl,
                verify_certs=self._verify_certs,
                ssl_show_warn=self._ssl_show_warn,
                ca_certs=self._ca_certs,
                timeout=self._timeout,
            )
        return self._client

    @classmethod
    def from_dsn(  # noqa: PLR0913
        cls,
        dsn: str,
        *,
        verify_certs: bool = False,
        ssl_show_warn: bool = False,
        ca_certs: str | None = None,
        timeout: float = DEFAULT_HC_TIMEOUT,
        name: str = "OpenSearch",
    ) -> OpenSearchHealthCheck:
        """Create an OpenSearchHealthCheck from an HTTP/HTTPS DSN.

        Returns:
            OpenSearchHealthCheck: The configured check instance.

        Raises:
            ValueError: If DSN has unsupported scheme or missing host.
        """
        parsed = urlsplit(str(dsn))
        if parsed.scheme not in {"http", "https"}:
            msg = "OpenSearch DSN must start with http:// or https://"
            raise ValueError(msg) from None

        if not parsed.hostname:
            msg = "OpenSearch DSN must include a host"
            raise ValueError(msg) from None

        http_auth: tuple[str, str] | None = None
        if parsed.username is not None:
            http_auth = (unquote(parsed.username), unquote(parsed.password or ""))

        port = parsed.port or (443 if parsed.scheme == "https" else 9200)
        return cls(
            hosts=[f"{parsed.hostname}:{port}"],
            http_auth=http_auth,
            use_ssl=parsed.scheme == "https",
            verify_certs=verify_certs,
            ssl_show_warn=ssl_show_warn,
            ca_certs=ca_certs,
            timeout=timeout,
            name=name,
        )

    async def __call__(self) -> HealthCheckResult:
        """Perform the health check on OpenSearch.

        Returns:
            HealthCheckResult: The result of the health check.
        """
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if self._client is not None and self._client_loop is not running:
            with contextlib.suppress(Exception):
                await self._client.close()
            self._client = None
            self._client_loop = None
        client = self._get_client()
        try:
            info = await client.info()
            return HealthCheckResult(name=self._name, healthy=info["version"]["number"] is not None)
        except Exception:  # noqa: BLE001
            return HealthCheckResult(name=self._name, healthy=False, error_details=format_exc())

    def to_dict(self) -> dict[str, Any]:
        """Convert the OpenSearchHealthCheck to a dictionary.

        Returns:
            dict: The check attributes as a dictionary.
        """
        return {
            "hosts": self._hosts,
            "http_auth": self._http_auth,
            "use_ssl": self._use_ssl,
            "verify_certs": self._verify_certs,
            "ssl_show_warn": self._ssl_show_warn,
            "ca_certs": self._ca_certs,
            "timeout": self._timeout,
            "name": self._name,
        }
