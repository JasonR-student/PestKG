from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from ..dependencies import manager


router = APIRouter(tags=["downloads"])


def download_response(
    request: Request, release_id: str, relative_path: str
) -> FileResponse:
    path = manager(request).download_path(release_id, relative_path)
    return FileResponse(
        path,
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "X-PestKG-Release": release_id,
        },
    )


@router.get("/downloads/{release_id}/", include_in_schema=False)
def download_catalog(request: Request, release_id: str) -> FileResponse:
    return download_response(request, release_id, "index.json")


@router.get(
    "/downloads/{release_id}/{relative_path:path}",
    include_in_schema=False,
)
def download_artifact(
    request: Request, release_id: str, relative_path: str
) -> FileResponse:
    return download_response(request, release_id, relative_path)
