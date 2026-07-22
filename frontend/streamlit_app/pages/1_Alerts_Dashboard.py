"""Alerts Dashboard — the flagship page showing every contradiction, compliance gap, and maintenance risk finding."""
import sys
from pathlib import Path

import streamlit as st

sys.path.append(str(Path(__file__).resolve().parents[1]))
from utils.api_client import run_scan  # noqa: E402

st.set_page_config(page_title="Sentinel — Alerts Dashboard", page_icon="🚨", layout="wide")
st.title("🚨 Alerts Dashboard")
st.caption("Everything a chatbot would miss because it requires reading two documents together.")

SEVERITY_COLOR = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🟢",
}

FINDING_TYPE_LABEL = {
    "procedure_practice_drift": "Procedure ↔ Practice Drift",
    "version_drift": "Version Drift",
    "silent_recurrence": "Silent Recurrence",
    "compliance_gap": "Compliance Gap",
    "maintenance_risk": "Maintenance Risk",
    "root_cause": "Root Cause",
}

if st.button("🔍 Run multi-agent scan", type="primary"):
    with st.spinner("Running contradiction, maintenance, and compliance agents over the knowledge graph..."):
        result = st.session_state["scan_result"] = run_scan()
else:
    result = st.session_state.get("scan_result")

if not result:
    st.info("Click **Run multi-agent scan** to see live findings. Upload documents first if you haven't.")
else:
    findings = result.get("findings", [])
    st.metric("Total findings", result.get("total_findings", len(findings)))

    if not findings:
        st.success("No contradictions, compliance gaps, or maintenance risks detected in the current graph.")

    type_options = sorted({f["finding_type"] for f in findings})
    selected_types = st.multiselect(
        "Filter by finding type",
        options=type_options,
        default=type_options,
        format_func=lambda t: FINDING_TYPE_LABEL.get(t, t),
    )

    filtered = [f for f in findings if f["finding_type"] in selected_types]
    filtered.sort(key=lambda f: {"critical": 0, "high": 1, "medium": 2, "low": 3}[f["severity"]])

    for finding in filtered:
        icon = SEVERITY_COLOR.get(finding["severity"], "⚪")
        label = FINDING_TYPE_LABEL.get(finding["finding_type"], finding["finding_type"])
        header = f"{icon} {finding['title']}  ·  {label}  ·  confidence {finding['confidence']:.0%}"
        with st.expander(header):
            st.write(finding["description"])

            st.markdown("**Recommended action**")
            st.write(finding["recommended_action"])

            st.markdown("**Evidence**")
            for ev in finding["evidence"]:
                st.markdown(
                    f"- *{ev['document_name']}* ({ev['document_type']}, {ev.get('location', 'n/a')}): {ev['excerpt']}"
                )

            st.markdown("**Reasoning trace**")
            for step in finding["reasoning_trace"]:
                st.markdown(f"1. {step}")
