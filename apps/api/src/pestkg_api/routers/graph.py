from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ..dependencies import envelope, neo4j_for_context, selected_context
from ..models import EntityData, Envelope, GraphData
from ..releases import ReleaseContext


router = APIRouter(prefix="/api/v1", tags=["graph"])


@router.get("/entities/{node_id:path}", response_model=Envelope[EntityData])
def entity(
    node_id: str,
    context: ReleaseContext = Depends(selected_context),
) -> Envelope[EntityData]:
    record = context.repository.entity(node_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    return envelope(context, record)


@router.get("/graph/neighborhood", response_model=Envelope[GraphData])
def neighborhood(
    request: Request,
    node_id: str,
    depth: int = Query(default=1, ge=1, le=2),
    context: ReleaseContext = Depends(selected_context),
) -> Envelope[GraphData]:
    settings = request.app.state.settings
    graph = None
    graph_store = neo4j_for_context(request, context)
    if graph_store:
        try:
            graph = graph_store.neighborhood(
                node_id, depth, settings.graph_node_limit, settings.graph_edge_limit
            )
        except Exception:
            graph = None
    if graph is None:
        graph = context.repository.neighborhood(
            node_id, depth, settings.graph_node_limit, settings.graph_edge_limit
        )
        source = "duckdb"
    else:
        source = "neo4j"
    if not graph["nodes"]:
        raise HTTPException(status_code=404, detail="Entity or neighborhood not found")
    return envelope(
        context,
        graph,
        query_engine=source,
        node_limit=settings.graph_node_limit,
        edge_limit=settings.graph_edge_limit,
    )


@router.get("/graph/path", response_model=Envelope[GraphData])
def graph_path(
    request: Request,
    start_id: str,
    end_id: str,
    max_depth: int = Query(default=3, ge=1, le=3),
    context: ReleaseContext = Depends(selected_context),
) -> Envelope[GraphData]:
    graph = None
    graph_store = neo4j_for_context(request, context)
    if graph_store:
        try:
            graph = graph_store.shortest_path(start_id, end_id, max_depth)
        except Exception:
            graph = None
    if graph is None:
        graph = context.repository.shortest_path(start_id, end_id, max_depth)
        source = "duckdb"
    else:
        source = "neo4j"
    return envelope(context, graph, query_engine=source, max_depth=max_depth)
