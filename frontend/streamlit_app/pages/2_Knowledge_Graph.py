"""Knowledge Graph page — interactive visualization of the live Neo4j graph via streamlit-agraph."""
import sys
from pathlib import Path

import streamlit as st
from streamlit_agraph import Config, Edge, Node, agraph

sys.path.append(str(Path(__file__).resolve().parents[1]))
from utils.api_client import get_graph_export, get_graph_stats  # noqa: E402

st.set_page_config(page_title="Sentinel — Knowledge Graph", page_icon="🕸️", layout="wide")
st.title("🕸️ Industrial Knowledge Graph")
st.caption("Equipment · Procedures · Work orders · Incidents · Personnel — as actually stored in Neo4j.")

stats = get_graph_stats()
if stats:
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Equipment", stats.get("equipment_count", 0))
    c2.metric("Procedures", stats.get("procedure_count", 0))
    c3.metric("Work orders", stats.get("work_order_count", 0))
    c4.metric("Incidents", stats.get("incident_count", 0))
    c5.metric("Personnel", stats.get("personnel_count", 0))
    c6.metric("Relationships", stats.get("relationship_count", 0))

st.divider()

limit = st.slider("Max nodes to render", min_value=20, max_value=400, value=150, step=10)
export = get_graph_export(limit=limit)

if not export or not export.get("nodes"):
    st.info("Graph is empty. Upload documents from the Document Upload page first.")
else:
    nodes = [Node(id=n["id"], label=n["label"][:30], size=18) for n in export["nodes"]]
    edges = [Edge(source=e["source"], target=e["target"], label=e.get("type", "")) for e in export["edges"]]

    config = Config(
        width=1100,
        height=650,
        directed=True,
        physics=True,
        hierarchical=False,
        collapsible=False,
    )
    agraph(nodes=nodes, edges=edges, config=config)

    st.caption(
        "Drag nodes to explore. Edges show GOVERNS, PERFORMED_ON, SUPERSEDES, TRAINED_ON, "
        "OCCURRED_ON, SIMILAR_FAILURE_MODE, and COMPLIES_WITH relationships."
    )
