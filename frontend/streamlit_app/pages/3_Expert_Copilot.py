"""Expert Copilot page — cited, confidence-scored Q&A, plus an on-demand RCA generation panel."""
import sys
from pathlib import Path

import streamlit as st

sys.path.append(str(Path(__file__).resolve().parents[1]))
from utils.api_client import generate_rca, query_copilot  # noqa: E402

st.set_page_config(page_title="Sentinel — Expert Copilot", page_icon="💬", layout="wide")
st.title("💬 Expert Copilot")
st.caption("Answers are generated strictly from retrieved evidence — never from the model's general knowledge.")

tab_qa, tab_rca = st.tabs(["Ask a question", "Generate RCA"])

with tab_qa:
    question = st.text_input(
        "Ask an operational, maintenance, or compliance question",
        placeholder="e.g. How often should valve V-204 be inspected?",
    )
    top_k = st.slider("Evidence chunks to retrieve", min_value=1, max_value=20, value=5)

    if st.button("Ask", type="primary") and question:
        with st.spinner("Retrieving evidence and generating a cited answer..."):
            result = query_copilot(question, top_k=top_k)

        if result:
            if result["escalate_to_human"]:
                st.warning("⚠️ Confidence below threshold — escalating rather than guessing.")
            else:
                st.success(f"Confidence: {result['confidence']:.0%}")

            st.markdown("### Answer")
            st.write(result["answer"])

            if result["evidence"]:
                st.markdown("### Evidence")
                for ev in result["evidence"]:
                    st.markdown(
                        f"- *{ev['document_name']}* ({ev['document_type']}, {ev.get('location', 'n/a')}): "
                        f"{ev['excerpt']}"
                    )

            with st.expander("Reasoning trace (explainability)"):
                for step in result["reasoning_trace"]:
                    st.markdown(f"1. {step}")

with tab_rca:
    st.write("Generate an evidence-grounded root-cause hypothesis for a specific incident.")
    incident_title = st.text_input("Incident title", placeholder="e.g. Gas pressure anomaly, Unit 3")
    incident_description = st.text_area("Incident description")
    symptoms_raw = st.text_input("Symptoms (comma-separated)", placeholder="unusual vibration, temperature spike")

    if st.button("Generate RCA hypothesis", type="primary") and incident_title:
        symptoms = [s.strip() for s in symptoms_raw.split(",") if s.strip()]
        with st.spinner("Cross-referencing related historical incidents..."):
            rca = generate_rca(incident_title, incident_description, symptoms)

        if rca:
            st.markdown(f"**Root cause category:** {rca.get('root_cause_category', 'unknown')}")
            st.progress(min(max(rca.get("confidence", 0.0), 0.0), 1.0))
            st.write(rca.get("justification", ""))
