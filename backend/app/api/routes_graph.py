"""Knowledge graph read API — stats for the dashboard header and a bounded graph export for visualization."""
from fastapi import APIRouter, HTTPException

from app.core.exceptions import SentinelException
from app.core.logging_config import logger
from app.models.schemas import GraphStatsResponse
from app.services.graph_service import graph_service

router = APIRouter(prefix="/graph", tags=["knowledge-graph"])


@router.get("/stats", response_model=GraphStatsResponse)
def get_graph_stats() -> GraphStatsResponse:
    try:
        stats = graph_service.get_graph_stats()
    except SentinelException as exc:
        logger.error(f"Graph stats query failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return GraphStatsResponse(**stats)


@router.get("/export")
def export_graph(limit: int = 150) -> dict:
    """
    Bounded export of nodes and relationships for the Streamlit graph
    visualization page. Capped at `limit` per node type to keep the
    pyvis/streamlit-agraph render responsive during a live demo.
    """
    query = """
    MATCH (n)
    OPTIONAL MATCH (n)-[r]->(m)
    RETURN n, r, m
    LIMIT $limit
    """
    try:
        rows = graph_service._read(query, {"limit": limit})
    except SentinelException as exc:
        logger.error(f"Graph export failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    for row in rows:
        n = row.get("n")
        if n:
            node_id = str(n.get("id", id(n)))
            nodes[node_id] = {"id": node_id, "label": n.get("tag") or n.get("title") or n.get("name") or node_id}
        m = row.get("m")
        r = row.get("r")
        if n and m and r:
            m_id = str(m.get("id", id(m)))
            nodes[m_id] = {"id": m_id, "label": m.get("tag") or m.get("title") or m.get("name") or m_id}
            edges.append({"source": str(n.get("id", id(n))), "target": m_id, "type": r.type if hasattr(r, "type") else "related"})

    return {"nodes": list(nodes.values()), "edges": edges}
