"""This module provides a health check class for URLs.

Classes:
    UrlHealthCheck: A class to perform health checks on URLs.

Usage:
    The UrlHealthCheck class can be used to perform health checks on URLs by calling it.

Example:
    health_check = UrlHealthCheck(
        url="https://www.google.com",
    )
    result = await health_check()
    print(result.healthy)
"""

from __future__ import annotations

import asyncio
import contextlib
from http import HTTPStatus
from traceback import format_exc
from typing import TYPE_CHECKING, Any, final

from fast_healthchecks.checks._base import DEFAULT_HC_TIMEOUT, HealthCheck
from fast_healthchecks.models import HealthCheckResult

IMPORT_ERROR_MSG = "httpx is not installed. Install it with `pip install fast-healthchecks[httpx]`."

try:
    from httpx import AsyncClient, AsyncHTTPTransport, BasicAuth, Response
except ImportError as exc:
    raise ImportError(IMPORT_ERROR_MSG) from exc

if TYPE_CHECKING:
    from httpx._types import URLTypes


@final
class UrlHealthCheck(HealthCheck[HealthCheckResult]):
    """A class to perform health checks on URLs.

    Attributes:
        _name: The name of the health check.
        _password: The password to authenticate with.
        _timeout: The timeout for the connection.
        _url: The URL to connect to.
        _username: The user to authenticate with.
        _verify_ssl: Whether to verify the SSL certificate.
    """

    __slots__ = (
        "_auth",
        "_client",
        "_client_loop",
        "_follow_redirects",
        "_name",
        "_password",
        "_timeout",
        "_transport",
        "_url",
        "_username",
        "_verify_ssl",
    )

    _url: URLTypes
    _username: str | None
    _password: str | None
    _auth: BasicAuth | None
    _verify_ssl: bool
    _transport: AsyncHTTPTransport | None
    _follow_redirects: bool
    _timeout: float
    _name: str
    _client: AsyncClient | None
    _client_loop: asyncio.AbstractEventLoop | None

    def __init__(  # noqa: PLR0913
        self,
        *,
        url: URLTypes,
        username: str | None = None,
        password: str | None = None,
        verify_ssl: bool = True,
        follow_redirects: bool = True,
        timeout: float = DEFAULT_HC_TIMEOUT,
        name: str = "HTTP",
    ) -> None:
        """Initialize the health check.

        Warning:
            Pass only trusted URLs from application configuration. Do not use
            user-controlled input for ``url`` to avoid SSRF.

        Args:
            url: The URL to connect to.
            username: The user to authenticate with.
            password: The password to authenticate with.
            verify_ssl: Whether to verify the SSL certificate.
            follow_redirects: Whether to follow redirects.
            timeout: The timeout for the connection.
            name: The name of the health check.
        """
        self._url = url
        self._username = username
        self._password = password
        self._auth = BasicAuth(self._username, self._password or "") if self._username else None
        self._verify_ssl = verify_ssl
        self._transport = AsyncHTTPTransport(verify=self._verify_ssl)
        self._follow_redirects = follow_redirects
        self._timeout = timeout
        self._name = name
        self._client = None
        self._client_loop = None

    async def aclose(self) -> None:
        """Close the cached HTTP client if present."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            self._client_loop = None

    def _get_client(self) -> AsyncClient:
        if self._client is None:
            try:
                self._client_loop = asyncio.get_running_loop()
            except RuntimeError:
                self._client_loop = None
            self._client = AsyncClient(
                auth=self._auth,
                timeout=self._timeout,
                transport=self._transport,
                follow_redirects=self._follow_redirects,
            )
        return self._client

    async def __call__(self) -> HealthCheckResult:
        """Perform the health check.

        Returns:
            HealthCheckResult: The result of the health check.
        """
        try:
            try:
                running = asyncio.get_running_loop()
            except RuntimeError:
                running = None
            if self._client is not None and self._client_loop is not running:
                with contextlib.suppress(Exception):
                    await self._client.aclose()
                self._client = None
                self._client_loop = None
            client = self._get_client()
            response: Response = await client.get(self._url)
            if response.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR or (
                self._username and response.status_code in {HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN}
            ):
                response.raise_for_status()
            return HealthCheckResult(name=self._name, healthy=response.is_success)
        except Exception:  # noqa: BLE001
            return HealthCheckResult(name=self._name, healthy=False, error_details=format_exc())

    def to_dict(self) -> dict[str, Any]:
        """Convert the UrlHealthCheck to a dictionary.

        Returns:
            dict: The check attributes as a dictionary.
        """
        return {
            "url": str(self._url),
            "username": self._username,
            "password": self._password,
            "verify_ssl": self._verify_ssl,
            "follow_redirects": self._follow_redirects,
            "timeout": self._timeout,
            "name": self._name,
        }
