from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ..dependencies import envelope, selected_context
from ..models import ComparisonRow, EntityData, Envelope
from ..releases import ReleaseContext


router = APIRouter(prefix="/api/v1", tags=["search"])


@router.get("/search", response_model=Envelope[list[EntityData]])
def search(
    q: str = Query(default="", max_length=200),
    entity_type: str | None = Query(default=None, max_length=100),
    jurisdiction: str | None = Query(default=None, max_length=10),
    limit: int = Query(default=50, ge=1, le=100),
    context: ReleaseContext = Depends(selected_context),
) -> Envelope[list[EntityData]]:
    rows = context.repository.search(q.strip(), entity_type, jurisdiction, limit)
    return envelope(context, rows, count=len(rows))


@router.get("/compare/{question}", response_model=Envelope[list[ComparisonRow]])
def compare(
    question: str,
    q: str | None = Query(default=None, max_length=200),
    jurisdiction: str | None = Query(default=None, max_length=10),
    limit: int = Query(default=100, ge=1, le=500),
    context: ReleaseContext = Depends(selected_context),
) -> Envelope[list[ComparisonRow]]:
    try:
        rows = context.repository.comparison(question, q, jurisdiction, limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return envelope(context, rows, question=question.lower(), count=len(rows))
