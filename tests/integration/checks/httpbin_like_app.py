"""Minimal Litestar app that mimics httpbingo endpoints for URL integration tests."""

from __future__ import annotations

import asyncio
import base64

from litestar import Litestar, Request, Response, get


@get("/status/{code:int}", sync_to_thread=False)
def status(code: int) -> Response:
    """Return HTTP status from path /status/{code}."""
    return Response(content=b"", status_code=code)


@get("/basic-auth/{user:str}/{passwd:str}", sync_to_thread=False)
def basic_auth(request: Request, user: str, passwd: str) -> Response:
    """Return 200 if Authorization matches path user/passwd, else 401."""
    expected = base64.b64encode(f"{user}:{passwd}".encode()).decode()
    auth = request.headers.get("authorization", "")
    if auth == f"Basic {expected}":
        return Response(content=b"", status_code=200)
    return Response(content=b"Unauthorized", status_code=401)


@get("/delay/{seconds:float}")
async def delay(seconds: float) -> Response:
    """Wait path param seconds then return 200.

    Path: /delay/{seconds}.

    Returns:
        Response with status 200 and empty body.
    """
    await asyncio.sleep(seconds)
    return Response(content=b"", status_code=200)


def create_app() -> Litestar:
    """Create Litestar app with httpbingo-like routes.

    Returns:
        Litestar: ASGI app with /status/{code}, /basic-auth/{user}/{passwd}, /delay/{seconds}.
    """
    return Litestar(
        route_handlers=[status, basic_auth, delay],
    )


app: Litestar = create_app()
