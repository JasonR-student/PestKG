from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, TypeVar

from fastapi import Header, Query, Request

from .constants import API_VERSION
from .models import Envelope
from .neo4j_store import Neo4jStore
from .releases import ReleaseContext, ReleaseError, ReleaseManager


T = TypeVar("T")


def manager(request: Request) -> ReleaseManager:
    return request.app.state.release_manager


def selected_context(
    request: Request,
    release: str | None = Query(default=None, max_length=128),
    release_header: str | None = Header(
        default=None, alias="X-PestKG-Release", max_length=128
    ),
) -> ReleaseContext:
    if release and release_header and release != release_header:
        raise ReleaseError(
            "release_selector_conflict",
            "Query and header release selectors disagree",
            status_code=400,
            details={"query": release, "header": release_header},
        )
    context = manager(request).resolve(release_header or release)
    request.state.release_id = context.release_id
    return context


def envelope(context: ReleaseContext, data: T, **meta: Any) -> Envelope[T]:
    return Envelope[T](
        api_version=API_VERSION,
        release_id=context.release_id,
        schema_version=context.schema_version,
        data=data,
        meta={"generated_at": datetime.now(timezone.utc).isoformat(), **meta},
        links={"release": f"/api/v1/releases/{context.release_id}"},
    )


def neo4j_reachable(request: Request) -> bool:
    if request.app.state.neo4j is None:
        return False
    try:
        return bool(request.app.state.neo4j.verify())
    except Exception:
        return False


def neo4j_for_context(
    request: Request, context: ReleaseContext
) -> Neo4jStore | None:
    if (
        request.app.state.neo4j is not None
        and request.app.state.neo4j_release_id == context.release_id
        and manager(request).active_release_id == context.release_id
    ):
        return request.app.state.neo4j
    return None
