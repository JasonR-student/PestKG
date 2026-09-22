from __future__ import annotations

from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import Request, Response


async def request_contract(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    supplied_request_id = request.headers.get("X-Request-ID", "").strip()
    request.state.request_id = (
        supplied_request_id[:128] if supplied_request_id else uuid4().hex
    )
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    if hasattr(request.state, "release_id"):
        response.headers["X-PestKG-Release"] = request.state.release_id
    if request.url.path.startswith("/api/"):
        vary = response.headers.get("Vary")
        response.headers["Vary"] = (
            f"{vary}, X-PestKG-Release" if vary else "X-PestKG-Release"
        )
    return response
