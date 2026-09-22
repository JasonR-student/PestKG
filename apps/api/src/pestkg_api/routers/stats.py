from __future__ import annotations

from fastapi import APIRouter, Depends

from ..dependencies import envelope, selected_context
from ..models import CountryData, Envelope, OverviewData, SchemaData
from ..releases import ReleaseContext


router = APIRouter(prefix="/api/v1", tags=["statistics"])


@router.get("/schema", response_model=Envelope[SchemaData])
def schema(
    context: ReleaseContext = Depends(selected_context),
) -> Envelope[SchemaData]:
    return envelope(context, context.repository.schema)


@router.get("/stats/overview", response_model=Envelope[OverviewData])
def overview(
    context: ReleaseContext = Depends(selected_context),
) -> Envelope[OverviewData]:
    return envelope(context, context.repository.overview())


@router.get("/stats/countries", response_model=Envelope[list[CountryData]])
def countries(
    context: ReleaseContext = Depends(selected_context),
) -> Envelope[list[CountryData]]:
    return envelope(context, context.repository.countries)
