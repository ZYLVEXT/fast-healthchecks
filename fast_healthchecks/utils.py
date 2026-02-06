"""Utility functions for fast-healthchecks."""

from __future__ import annotations

from urllib.parse import unquote

__all__ = ("parse_query_string",)


def parse_query_string(query: str) -> dict[str, str]:
    """Parse a URL query string into a dictionary.

    Args:
        query: The query string (e.g. 'key1=value1&key2=value2').

    Returns:
        A dictionary of key-value pairs. Values containing '=' are preserved.
        Pairs without '=' are stored with an empty value.
    """
    if not query:
        return {}
    result: dict[str, str] = {}
    for part in query.split("&"):
        kv = part.split("=", 1)
        key = kv[0]
        value = unquote(kv[1]) if len(kv) > 1 else ""
        result[key] = value
    return result
