"""Shared DSN parsing types for health checks.

This module is the single source of TypedDict shapes and type aliases for
DSN parse results (Redis, Kafka, Mongo, OpenSearch, RabbitMQ, Postgres).
All TypedDicts are total=True; no Any is used.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, TypeAlias, TypedDict
from urllib.parse import ParseResult, SplitResult

ParsedUrl: TypeAlias = ParseResult | SplitResult

if TYPE_CHECKING:
    import ssl

    from redis.asyncio.connection import ConnectKwargs

__all__ = (
    "VALID_SSLMODES",
    "KafkaParseDsnResult",
    "MongoParseDsnResult",
    "OpenSearchParseDsnResult",
    "ParsedUrl",
    "PostgresParseDsnResult",
    "RabbitMQParseDsnResult",
    "RedisParseDsnResult",
    "SslMode",
)


class RedisParseDsnResult(TypedDict, total=True):
    """Result of parsing a Redis DSN."""

    parse_result: ConnectKwargs
    scheme: str


SslMode: TypeAlias = Literal["disable", "allow", "prefer", "require", "verify-ca", "verify-full"]
VALID_SSLMODES: frozenset[str] = frozenset({"disable", "allow", "prefer", "require", "verify-ca", "verify-full"})


class KafkaParseDsnResult(TypedDict, total=True):
    """Result of parsing a Kafka DSN."""

    bootstrap_servers: str
    sasl_plain_username: str | None
    sasl_plain_password: str | None
    security_protocol: str


class MongoParseDsnResult(TypedDict, total=True):
    """Result of parsing a MongoDB DSN."""

    parse_result: ParsedUrl
    authSource: str


class OpenSearchParseDsnResult(TypedDict, total=True):
    """Result of parsing an OpenSearch DSN."""

    hosts: list[str]
    http_auth: tuple[str, str] | None
    use_ssl: bool


class RabbitMQParseDsnResult(TypedDict, total=True):
    """Result of parsing a RabbitMQ/AMQP DSN."""

    parse_result: ParsedUrl


class PostgresParseDsnResult(TypedDict, total=True):
    """Result of parsing a PostgreSQL DSN."""

    parse_result: ParsedUrl
    sslmode: SslMode
    sslcert: str | None
    sslkey: str | None
    sslrootcert: str | None
    sslctx: ssl.SSLContext | None
    direct_tls: bool
