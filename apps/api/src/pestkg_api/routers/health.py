from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..constants import API_VERSION
from ..dependencies import manager, neo4j_reachable
from ..releases import ReleaseError


router = APIRouter(tags=["health"])


@router.get("/health/live")
def liveness(request: Request) -> dict[str, Any]:
    return {"status": "ok", "request_id": request.state.request_id}


@router.get("/health/ready")
def readiness(request: Request) -> JSONResponse:
    try:
        context = manager(request).resolve()
        neo4j_configured = request.app.state.neo4j is not None
        neo4j_ready = neo4j_reachable(request) if neo4j_configured else True
        content = {
            "status": "ready" if neo4j_ready else "not_ready",
            "release_id": context.release_id,
            "schema_version": context.schema_version,
            "data_mode": context.repository.mode,
            "neo4j_configured": neo4j_configured,
            "neo4j_reachable": neo4j_ready if neo4j_configured else False,
        }
        return JSONResponse(status_code=200 if neo4j_ready else 503, content=content)
    except ReleaseError as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "error": exc.code},
        )


@router.get("/health")
def health(request: Request) -> dict[str, Any]:
    context = manager(request).resolve()
    return {
        "status": "ok",
        "api_version": API_VERSION,
        "release_id": context.release_id,
        "schema_version": context.schema_version,
        "available_releases": len(manager(request).available_release_ids()),
        "data_mode": context.repository.mode,
        "neo4j_configured": request.app.state.neo4j is not None,
        "neo4j_reachable": neo4j_reachable(request),
        "neo4j_release_id": request.app.state.neo4j_release_id,
    }
