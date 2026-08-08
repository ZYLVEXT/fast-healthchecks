"""Utility functions for fast-healthchecks."""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import unquote, urlparse

from fast_healthchecks.models import HealthCheckSSRFError
from fast_healthchecks.redaction import REDACT_PLACEHOLDER, maybe_redact, redact_secrets_in_dict


def _parse_ip_safe(ip_str: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    """Return ip_address(ip_str) or None if invalid."""
    try:
        return ipaddress.ip_address(ip_str)
    except ValueError:
        return None


def validate_url_ssrf(
    url: str,
    *,
    allowed_schemes: frozenset[str] = frozenset({"http", "https"}),
    block_private_hosts: bool = False,
) -> None:
    """Validate URL for SSRF-sensitive use (e.g. healthchecks from config).

    Args:
        url: The URL string to validate.
        allowed_schemes: Schemes permitted (default http, https).
        block_private_hosts: If True, reject localhost and non-global IP ranges.

    Raises:
        HealthCheckSSRFError: If scheme or hostname is invalid, or the host is in a blocked range.
    """
    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()
    if scheme not in allowed_schemes:
        msg = f"URL scheme must be one of {sorted(allowed_schemes)}, got {scheme!r}"
        raise HealthCheckSSRFError(msg)
    host = (parsed.hostname or "").strip()
    if not host:
        msg = "URL must include a hostname"
        raise HealthCheckSSRFError(msg)
    if not block_private_hosts:
        return
    if host.lower() in {"localhost", "localhost.", "localhost6", "localhost6.localdomain6"}:
        msg = "URL host must not be localhost when block_private_hosts=True"
        raise HealthCheckSSRFError(msg)
    addr = _parse_ip_safe(host)
    if addr is None:
        return
    if not addr.is_global:
        msg = "URL host must not be loopback or private when block_private_hosts=True"
        raise HealthCheckSSRFError(msg)


async def validate_host_ssrf_async(host: str) -> None:
    """Resolve a host and reject failures or any non-global address.

    Call this before making the request when block_private_hosts=True, so that
    hostnames that resolve to private IPs (e.g. internal DNS or DNS rebinding)
    are rejected.

    Args:
        host: The hostname to resolve and validate.

    Raises:
        HealthCheckSSRFError: If resolution fails or any resolved IP is non-global.
    """
    host = (host or "").strip()
    if not host:
        return
    if host.lower() in {"localhost", "localhost.", "localhost6", "localhost6.localdomain6"}:
        msg = "URL host must not be localhost when block_private_hosts=True"
        raise HealthCheckSSRFError(msg)
    try:
        loop = asyncio.get_running_loop()
        infos = await loop.run_in_executor(None, lambda: socket.getaddrinfo(host, None))
    except OSError as exc:
        msg = "URL host could not be resolved safely"
        raise HealthCheckSSRFError(msg) from exc
    for _family, _type, _proto, _canon, sockaddr in infos:
        if not sockaddr:
            continue
        ip_str = sockaddr[0] if isinstance(sockaddr, (list, tuple)) else getattr(sockaddr, "host", None)
        if not isinstance(ip_str, str) or not ip_str:
            continue
        addr = _parse_ip_safe(ip_str)
        if addr is None:
            continue
        if not addr.is_global:
            msg = "URL host must not resolve to loopback or private when block_private_hosts=True"
            raise HealthCheckSSRFError(msg)


__all__ = (
    "REDACT_PLACEHOLDER",
    "maybe_redact",
    "parse_query_string",
    "redact_secrets_in_dict",
    "validate_host_ssrf_async",
    "validate_url_ssrf",
)


def parse_query_string(query: str) -> dict[str, str]:
    """Parse a URL query string into a dictionary.

    Keys and values are URL-decoded (unquoted). Pairs without '=' are stored
    with an empty value. Values containing '=' are preserved.

    Args:
        query: The query string (e.g. 'key1=value1&key2=value2').

    Returns:
        A dictionary of key-value pairs.
    """
    if not query:
        return {}
    result: dict[str, str] = {}
    for part in query.split("&"):
        kv = part.split("=", 1)
        key = unquote(kv[0]) if kv[0] else ""
        value = unquote(kv[1]) if len(kv) > 1 else ""
        result[key] = value
    return result
