"""
Sentinel dashboard — Home page.

Streamlit auto-discovers pages/ as additional nav entries. This file is the
landing page: it states the product's differentiator up front (not a
generic "upload a document" prompt) and surfaces live system status so a
judge sees the stack is actually running, not mocked.
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent))
from utils.api_client import check_health, get_graph_stats  # noqa: E402

st.set_page_config(
    page_title="Sentinel — Industrial Knowledge Intelligence",
    page_icon="🛰️",
    layout="wide",
)

st.title("Sentinel — Industrial Knowledge Intelligence Platform")
st.caption("ET AI Hackathon 2026 · Problem Statement 8: Unified Asset & Operations Brain")

st.markdown(
    """
    > Sentinel does not answer questions about your documents.
    > It tells you what your documents **disagree about** — before an
    > auditor, an inspector, or an incident does.
    """
)

col1, col2 = st.columns([1, 3])
with col1:
    healthy = check_health()
    if healthy:
        st.success("Backend: connected")
    else:
        st.error("Backend: unreachable — start the FastAPI service (see README)")

st.divider()

st.subheader("Knowledge graph at a glance")
stats = get_graph_stats() if healthy else None

if stats:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Equipment", stats.get("equipment_count", 0))
    c2.metric("Procedures", stats.get("procedure_count", 0))
    c3.metric("Work orders", stats.get("work_order_count", 0))
    c4.metric("Incidents", stats.get("incident_count", 0))
    c5.metric("Relationships", stats.get("relationship_count", 0))
else:
    st.info("No graph data yet. Upload sample documents from the **Document Upload** page to get started.")

st.divider()

st.subheader("Where to go next")
nav_col1, nav_col2, nav_col3 = st.columns(3)
with nav_col1:
    st.markdown("### 🚨 Alerts Dashboard")
    st.write(
        "Run the multi-agent scan and see every contradiction, compliance gap, and "
        "maintenance risk Sentinel found — each with evidence and a confidence score."
    )
with nav_col2:
    st.markdown("### 🕸️ Knowledge Graph")
    st.write("Explore the equipment–procedure–incident graph built from your uploaded documents.")
with nav_col3:
    st.markdown("### 💬 Expert Copilot")
    st.write("Ask operational questions and get cited answers — with honest escalation when evidence is weak.")

st.divider()
st.caption(
    "Tip for the demo: upload the sample corpus in `data/sample_documents/` first, "
    "then run a scan from the Alerts Dashboard to see live findings."
)
