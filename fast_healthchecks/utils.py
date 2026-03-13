"""Utility functions for fast-healthchecks."""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from typing import Any
from urllib.parse import unquote, urlparse

from fast_healthchecks.models import HealthCheckSSRFError

REDACT_PLACEHOLDER = "***"
_SECRET_KEYS = frozenset(
    {
        "http_auth",
        "password",
        "sasl_plain_password",
        "sasl_plain_username",
        "token",
        "user",
        "username",
    },
)


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
        block_private_hosts: If True, reject localhost and private IP ranges.

    Raises:
        HealthCheckSSRFError: If scheme is not allowed or host is in blocked range.
    """
    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()
    if scheme not in allowed_schemes:
        msg = f"URL scheme must be one of {sorted(allowed_schemes)}, got {scheme!r}"
        raise HealthCheckSSRFError(msg)
    if not block_private_hosts:
        return
    host = (parsed.hostname or "").strip()
    if not host:
        return
    if host.lower() in {"localhost", "localhost.", "localhost6", "localhost6.localdomain6"}:
        msg = "URL host must not be localhost when block_private_hosts=True"
        raise HealthCheckSSRFError(msg)
    addr = _parse_ip_safe(host)
    if addr is None:
        return
    if addr.is_loopback or addr.is_private or addr.is_reserved:
        msg = "URL host must not be loopback or private when block_private_hosts=True"
        raise HealthCheckSSRFError(msg)


async def validate_host_ssrf_async(host: str) -> None:
    """Resolve host to IP(s) and reject if any are loopback/private/reserved (SSRF/DNS rebinding).

    Call this before making the request when block_private_hosts=True, so that
    hostnames that resolve to private IPs (e.g. internal DNS or DNS rebinding)
    are rejected.

    Args:
        host: The hostname to resolve and validate.

    Raises:
        HealthCheckSSRFError: If any resolved IP is loopback, private, or reserved.
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
    except OSError:
        # Resolution failed; let the subsequent request fail or handle
        return
    for _family, _type, _proto, _canon, sockaddr in infos:
        if not sockaddr:
            continue
        ip_str = sockaddr[0] if isinstance(sockaddr, (list, tuple)) else getattr(sockaddr, "host", None)
        if not isinstance(ip_str, str) or not ip_str:
            continue
        addr = _parse_ip_safe(ip_str)
        if addr is None:
            continue
        if addr.is_loopback or addr.is_private or addr.is_reserved:
            msg = "URL host must not resolve to loopback or private when block_private_hosts=True"
            raise HealthCheckSSRFError(msg)


__all__ = (
    "maybe_redact",
    "parse_query_string",
    "redact_secrets_in_dict",
    "validate_host_ssrf_async",
    "validate_url_ssrf",
)


def _redact_value(value: Any) -> Any:  # noqa: ANN401
    if isinstance(value, dict):
        return redact_secrets_in_dict(value)
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_value(item) for item in value)
    if isinstance(value, set):
        return {_redact_value(item) for item in value}
    return value


def redact_secrets_in_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of data with secret-like keys redacted recursively."""
    return {key: (REDACT_PLACEHOLDER if key in _SECRET_KEYS else _redact_value(value)) for key, value in data.items()}


def maybe_redact(data: dict[str, Any], *, redact_secrets: bool) -> dict[str, Any]:
    """Return data with secrets redacted if requested, otherwise return as-is."""
    return redact_secrets_in_dict(data) if redact_secrets else data


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
