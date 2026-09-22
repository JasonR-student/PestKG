from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from ..cursors import decode_cursor, encode_cursor, filters_fingerprint
from ..dependencies import envelope, selected_context
from ..models import (
    Envelope,
    ExportRequest,
    RegistrationUseData,
    RegistrationUseQuery,
)
from ..releases import ReleaseContext


router = APIRouter(prefix="/api/v1", tags=["registration-uses"])


@router.post(
    "/registration-uses/query",
    response_model=Envelope[list[RegistrationUseData]],
)
def registration_uses(
    payload: RegistrationUseQuery,
    context: ReleaseContext = Depends(selected_context),
) -> Envelope[list[RegistrationUseData]]:
    filter_payload = payload.filters.model_dump(mode="json")
    filter_hash = filters_fingerprint(filter_payload)
    offset = decode_cursor(payload.cursor, context.release_id, filter_hash)
    rows, total = context.repository.query_registration_uses(
        payload.filters, offset, payload.page_size
    )
    next_cursor = (
        encode_cursor(offset + len(rows), context.release_id, filter_hash)
        if offset + len(rows) < total
        else None
    )
    return envelope(
        context,
        rows,
        total=total,
        page_size=payload.page_size,
        next_cursor=next_cursor,
    )


@router.post("/exports/registration-uses")
def export_registration_uses(
    request: Request,
    payload: ExportRequest,
    context: ReleaseContext = Depends(selected_context),
) -> StreamingResponse:
    export_limit: int = request.app.state.settings.export_limit
    stream, total = context.repository.iter_registration_uses(
        payload.filters, export_limit + 1
    )
    if total > export_limit:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "export_too_large",
                "message": "Export exceeds the synchronous row limit",
                "details": {"total": total, "limit": export_limit},
                "total": total,
                "limit": export_limit,
                "download_url": f"/downloads/{context.release_id}/",
            },
        )
    filename = f"registration-uses-{context.release_id}.csv"
    return StreamingResponse(
        stream,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-PestKG-Release": context.release_id,
        },
    )
