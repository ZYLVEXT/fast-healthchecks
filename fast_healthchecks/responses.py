"""Response mapping primitives for healthchecks."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import asdict
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, NamedTuple

from fast_healthchecks.utils import redact_secrets_in_dict

if TYPE_CHECKING:
    from fast_healthchecks.models import HealthCheckReport

HandlerType = Callable[["ProbeAsgiResponse"], Awaitable[dict[str, Any] | None]]


class ProbeAsgiResponse(NamedTuple):
    """A response payload and computed health flag for ASGI handlers."""

    data: dict[str, Any]
    healthy: bool


async def map_report_to_asgi_http_response(  # noqa: PLR0913
    report: HealthCheckReport,
    *,
    debug: bool,
    exclude_fields: set[str],
    success_status: int,
    failure_status: int,
    success_handler: HandlerType,
    failure_handler: HandlerType,
) -> tuple[bytes, dict[str, str] | None, int]:
    """Map a healthcheck report to HTTP body, headers, and status code.

    Returns:
        Tuple of ``(body, headers, status_code)`` for framework response objects.
    """
    response = ProbeAsgiResponse(
        data=asdict(
            report,
            dict_factory=lambda x: {k: v for (k, v) in x if k not in exclude_fields},
        ),
        healthy=report.healthy,
    )
    status_code = success_status if response.healthy else failure_status
    content_needed = status_code not in {
        HTTPStatus.NO_CONTENT,
        HTTPStatus.NOT_MODIFIED,
    } and not (response.healthy and status_code < HTTPStatus.OK)

    if not content_needed:
        return b"", None, status_code

    if debug and not response.healthy:
        content_obj: dict[str, Any] | None = response.data
    else:
        handler = success_handler if response.healthy else failure_handler
        content_obj = await handler(response)

    if content_obj is None:
        return b"", None, status_code

    if isinstance(content_obj, dict):
        content_obj = redact_secrets_in_dict(content_obj)

    content = json.dumps(
        content_obj,
        ensure_ascii=False,
        allow_nan=False,
        indent=None,
        separators=(",", ":"),
    ).encode("utf-8")

    return (
        content,
        {
            "content-type": "application/json",
            "content-length": str(len(content)),
        },
        status_code,
    )


__all__ = ("ProbeAsgiResponse", "map_report_to_asgi_http_response")
