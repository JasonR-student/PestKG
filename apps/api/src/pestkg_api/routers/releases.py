from __future__ import annotations

from fastapi import APIRouter, Request

from ..dependencies import envelope, manager
from ..models import Envelope, ReleaseData


router = APIRouter(prefix="/api/v1/releases", tags=["releases"])


@router.get("", response_model=Envelope[list[ReleaseData]])
def releases(request: Request) -> Envelope[list[ReleaseData]]:
    context = manager(request).resolve()
    rows = manager(request).list_releases()
    return envelope(context, rows, count=len(rows), active_release=context.release_id)


@router.get("/active", response_model=Envelope[ReleaseData])
def active_release(request: Request) -> Envelope[ReleaseData]:
    context = manager(request).resolve()
    return envelope(context, manager(request).release_summary(context.release_id))


@router.get("/{release_id}", response_model=Envelope[ReleaseData])
def release_detail(request: Request, release_id: str) -> Envelope[ReleaseData]:
    context = manager(request).resolve(release_id)
    return envelope(context, manager(request).release_summary(release_id))
