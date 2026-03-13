"""Immutable configuration dataclasses for health checks.

Encapsulates connection parameters to avoid long parameter lists (PLR0913)
and centralize serialization for to_dict().
"""

from __future__ import annotations

import ssl as _ssl  # noqa: TC003
from dataclasses import asdict, dataclass, field
from typing import Any, Literal, TypeAlias

from fast_healthchecks.checks._base import DEFAULT_HC_TIMEOUT

SecurityProtocol: TypeAlias = Literal["SSL", "PLAINTEXT", "SASL_PLAINTEXT", "SASL_SSL"]
SaslMechanism: TypeAlias = Literal["PLAIN", "GSSAPI", "SCRAM-SHA-256", "SCRAM-SHA-512", "OAUTHBEARER"]

VALID_SECURITY_PROTOCOLS: frozenset[str] = frozenset({"SSL", "PLAINTEXT", "SASL_PLAINTEXT", "SASL_SSL"})
VALID_SASL_MECHANISMS: frozenset[str] = frozenset({"PLAIN", "GSSAPI", "SCRAM-SHA-256", "SCRAM-SHA-512", "OAUTHBEARER"})


@dataclass(frozen=True)
class RedisConfig:
    """Configuration for Redis health check."""

    host: str = "localhost"
    port: int = 6379
    database: int | str = 0
    user: str | None = None
    password: str | None = None
    ssl: bool = False
    ssl_ca_certs: str | None = None
    timeout: float = DEFAULT_HC_TIMEOUT

    def to_dict(self) -> dict[str, Any]:
        """Return config as a dict for serialization."""
        return asdict(self)


@dataclass(frozen=True)
class KafkaConfig:
    """Configuration for Kafka health check."""

    bootstrap_servers: str = "localhost:9092"
    ssl_context: _ssl.SSLContext | None = None
    security_protocol: SecurityProtocol = "PLAINTEXT"
    sasl_mechanism: SaslMechanism = "PLAIN"
    sasl_plain_username: str | None = None
    sasl_plain_password: str | None = None
    timeout: float = DEFAULT_HC_TIMEOUT

    def __post_init__(self) -> None:
        """Validate security_protocol and sasl_mechanism.

        Raises:
            ValueError: If security_protocol or sasl_mechanism is invalid.
        """
        if self.security_protocol not in VALID_SECURITY_PROTOCOLS:
            msg = f"Invalid security protocol: {self.security_protocol}"
            raise ValueError(msg)
        if self.sasl_mechanism not in VALID_SASL_MECHANISMS:
            msg = f"Invalid SASL mechanism: {self.sasl_mechanism}"
            raise ValueError(msg)

    def to_dict(self) -> dict[str, Any]:
        """Return config as a dict for serialization."""
        # ssl_context is not deepcopy-safe; build dict manually
        return {
            "bootstrap_servers": self.bootstrap_servers,
            "ssl_context": self.ssl_context,
            "security_protocol": self.security_protocol,
            "sasl_mechanism": self.sasl_mechanism,
            "sasl_plain_username": self.sasl_plain_username,
            "sasl_plain_password": self.sasl_plain_password,
            "timeout": self.timeout,
        }


@dataclass(frozen=True)
class MongoConfig:
    """Configuration for MongoDB health check."""

    hosts: str | list[str] = "localhost"
    port: int | None = 27017
    user: str | None = None
    password: str | None = None
    database: str | None = None
    auth_source: str = "admin"
    timeout: float = DEFAULT_HC_TIMEOUT

    def to_dict(self) -> dict[str, Any]:
        """Return config as a dict for serialization."""
        return asdict(self)


@dataclass(frozen=True)
class OpenSearchConfig:
    """Configuration for OpenSearch health check."""

    hosts: list[str] = field(default_factory=lambda: ["localhost:9200"])
    http_auth: tuple[str, str] | None = None
    use_ssl: bool = False
    verify_certs: bool = False
    ssl_show_warn: bool = False
    ca_certs: str | None = None
    timeout: float = DEFAULT_HC_TIMEOUT

    def to_dict(self) -> dict[str, Any]:
        """Return config as a dict for serialization."""
        return asdict(self)


@dataclass(frozen=True)
class RabbitMQConfig:
    """Configuration for RabbitMQ health check.

    **Security:** The default ``user`` and ``password`` (``"guest"``) match
    RabbitMQ's default credentials and are intended for local development only.
    Do not use these defaults in production or on non-local brokers; set
    explicit credentials or use a secrets manager. See SECURITY.md.
    """

    host: str = "localhost"
    port: int = 5672
    user: str = "guest"
    password: str = "guest"  # noqa: S105
    vhost: str = "/"
    secure: bool = False
    timeout: float = DEFAULT_HC_TIMEOUT

    def to_dict(self) -> dict[str, Any]:
        """Return config as a dict for serialization."""
        return asdict(self)


@dataclass(frozen=True)
class UrlConfig:
    """Configuration for URL health check.

    Use only trusted URLs from application configuration; do not pass
    user-controlled input to avoid SSRF. Validation and behaviour are
    provided by :func:`~fast_healthchecks.utils.validate_url_ssrf` and
    :func:`~fast_healthchecks.utils.validate_host_ssrf_async`. See the
    SSRF documentation in the docs.
    """

    url: str = ""
    username: str | None = None
    password: str | None = None
    verify_ssl: bool = True
    follow_redirects: bool = True
    timeout: float = DEFAULT_HC_TIMEOUT
    block_private_hosts: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Return config as a dict for serialization."""
        return asdict(self)


@dataclass(frozen=True)
class PostgresAsyncPGConfig:
    """Configuration for PostgreSQL health check (asyncpg driver)."""

    host: str = "localhost"
    port: int = 5432
    user: str | None = None
    password: str | None = None
    database: str | None = None
    ssl: _ssl.SSLContext | None = None
    direct_tls: bool = False
    timeout: float = DEFAULT_HC_TIMEOUT

    def to_dict(self) -> dict[str, Any]:
        """Return config as a dict for serialization."""
        # ssl is not serializable; include as None in dict for consistent keys
        return {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "password": self.password,
            "database": self.database,
            "ssl": self.ssl,
            "direct_tls": self.direct_tls,
            "timeout": self.timeout,
        }


@dataclass(frozen=True)
class PostgresPsycopgConfig:
    """Configuration for PostgreSQL health check (psycopg driver)."""

    host: str = "localhost"
    port: int = 5432
    user: str | None = None
    password: str | None = None
    database: str | None = None
    sslmode: str | None = None
    sslcert: str | None = None
    sslkey: str | None = None
    sslrootcert: str | None = None
    timeout: float = DEFAULT_HC_TIMEOUT

    def to_dict(self) -> dict[str, Any]:
        """Return config as a dict for serialization."""
        return asdict(self)


@dataclass(frozen=True)
class FunctionConfig:
    """Configuration for function health check."""

    args: tuple[object, ...] = ()
    kwargs: dict[str, object] | None = None
    timeout: float = DEFAULT_HC_TIMEOUT

    def to_dict(self) -> dict[str, Any]:
        """Return config as a dict for serialization."""
        d = asdict(self)
        d["args"] = list(d.get("args") or ())
        d["kwargs"] = dict(d["kwargs"]) if d.get("kwargs") else {}
        return d


__all__ = (
    "VALID_SASL_MECHANISMS",
    "VALID_SECURITY_PROTOCOLS",
    "FunctionConfig",
    "KafkaConfig",
    "MongoConfig",
    "OpenSearchConfig",
    "PostgresAsyncPGConfig",
    "PostgresPsycopgConfig",
    "RabbitMQConfig",
    "RedisConfig",
    "SaslMechanism",
    "SecurityProtocol",
    "UrlConfig",
)
