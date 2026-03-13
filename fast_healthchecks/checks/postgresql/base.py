"""This module provides the base class for PostgreSQL health checks."""

from __future__ import annotations

import ssl
from abc import abstractmethod
from functools import lru_cache
from typing import Generic, cast
from urllib.parse import SplitResult, unquote, urlsplit

from fast_healthchecks.checks._base import DEFAULT_HC_TIMEOUT, HealthCheckDSN, T_co
from fast_healthchecks.checks.dsn_parsing import VALID_SSLMODES, PostgresParseDsnResult, SslMode
from fast_healthchecks.utils import parse_query_string


@lru_cache(maxsize=128, typed=True)
def create_ssl_context(
    sslmode: SslMode,
    sslcert: str | None,
    sslkey: str | None,
    sslrootcert: str | None,
) -> ssl.SSLContext | None:
    """Create an SSL context from the query parameters.

    Results are cached by path arguments (sslmode, sslcert, sslkey, sslrootcert).
    After certificate rotation, either restart the process or call
    ``create_ssl_context.cache_clear()`` to avoid using stale contexts.

    Args:
        sslmode: The SSL mode to use.
        sslcert: The path to the SSL certificate.
        sslkey: The path to the SSL key.
        sslrootcert: The path to the SSL root certificate.

    Returns:
        ssl.SSLContext | None: The SSL context.

    Raises:
        ValueError: If provided SSL options are invalid for selected mode.
    """
    sslctx: ssl.SSLContext | None = None
    match sslmode:
        case "disable":
            sslctx = None
        case "allow":
            sslctx = None
        case "prefer":
            sslctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        case "require":
            sslctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            sslctx.check_hostname = False
            sslctx.verify_mode = ssl.CERT_NONE
        case "verify-ca":
            sslctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=sslrootcert)
            sslctx.check_hostname = False
            sslctx.verify_mode = ssl.CERT_REQUIRED
        case "verify-full":
            if sslcert is None:
                msg = "sslcert is required for verify-full"
                raise ValueError(msg) from None
            sslctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=sslrootcert)
            sslctx.check_hostname = True
            sslctx.load_cert_chain(
                certfile=sslcert,
                keyfile=sslkey,
            )
        case _:  # pragma: no cover
            msg = f"Unsupported sslmode: {sslmode}"
            raise ValueError(msg) from None
    return sslctx


class BasePostgreSQLHealthCheck(HealthCheckDSN[T_co, PostgresParseDsnResult], Generic[T_co]):
    """Base class for PostgreSQL health checks."""

    @classmethod
    def _allowed_schemes(cls) -> tuple[str, ...]:
        return ("postgresql", "postgres")

    @classmethod
    def _default_name(cls) -> str:
        return "PostgreSQL"

    @classmethod
    @abstractmethod
    def _from_parsed_dsn(
        cls,
        parsed: PostgresParseDsnResult,
        *,
        name: str = "PostgreSQL",
        timeout: float = DEFAULT_HC_TIMEOUT,
        **kwargs: object,
    ) -> BasePostgreSQLHealthCheck[T_co]:
        """Create a check instance from parsed DSN."""
        ...  # pragma: no cover

    @classmethod
    def validate_sslmode(cls, mode: str) -> SslMode:
        """Validate the SSL mode.

        Args:
            mode: The SSL mode to validate.

        Returns:
            SslMode: The validated SSL mode.

        Raises:
            ValueError: If the SSL mode is invalid.
        """
        if mode not in VALID_SSLMODES:
            msg = f"Invalid sslmode: {mode}"
            raise ValueError(msg) from None
        return cast("SslMode", mode)

    @classmethod
    def parse_dsn(cls, dsn: str) -> PostgresParseDsnResult:
        """Parse the DSN and return the results.

        Args:
            dsn: The DSN to parse.

        Returns:
            PostgresParseDsnResult: The results of parsing the DSN.
        """
        parse_result: SplitResult = urlsplit(dsn)
        query = parse_query_string(parse_result.query)
        sslmode: SslMode = cls.validate_sslmode(query.get("sslmode", "disable"))
        sslcert_raw: str | None = query.get("sslcert")
        sslkey_raw: str | None = query.get("sslkey")
        sslrootcert_raw: str | None = query.get("sslrootcert")
        sslcert = unquote(sslcert_raw) if sslcert_raw else None
        sslkey = unquote(sslkey_raw) if sslkey_raw else None
        sslrootcert = unquote(sslrootcert_raw) if sslrootcert_raw else None
        sslctx: ssl.SSLContext | None = create_ssl_context(sslmode, sslcert, sslkey, sslrootcert)
        direct_tls_raw: str = query.get("direct_tls", "").lower()
        direct_tls: bool = direct_tls_raw in {"1", "true", "yes", "on"}
        return {
            "parse_result": parse_result,
            "sslmode": sslmode,
            "sslcert": sslcert,
            "sslkey": sslkey,
            "sslrootcert": sslrootcert,
            "sslctx": sslctx,
            "direct_tls": direct_tls,
        }
