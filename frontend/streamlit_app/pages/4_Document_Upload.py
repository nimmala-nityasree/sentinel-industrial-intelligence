"""Document Upload page — ingestion entrypoint with live OCR/entity-extraction feedback."""
import sys
from pathlib import Path

import streamlit as st

sys.path.append(str(Path(__file__).resolve().parents[1]))
from utils.api_client import upload_document  # noqa: E402

st.set_page_config(page_title="Sentinel — Document Upload", page_icon="📄", layout="wide")
st.title("📄 Document Upload")
st.caption("Ingest SOPs, work orders, near-miss reports, training records, and scanned forms.")

st.info(
    "For the fastest demo, upload the synthetic corpus in `data/sample_documents/` — "
    "it's designed to trigger all three drift patterns Sentinel detects."
)

document_type = st.selectbox(
    "Document type",
    options=["sop", "work_order", "near_miss_report", "incident_report", "training_record", "regulatory_document"],
    format_func=lambda x: x.replace("_", " ").title(),
)

uploaded_file = st.file_uploader(
    "Choose a file (PDF, scanned image, or CSV)",
    type=["pdf", "png", "jpg", "jpeg", "tiff", "csv", "txt", "md"],
)

if uploaded_file is not None and st.button("Ingest document", type="primary"):
    with st.spinner("Extracting text (OCR if needed), indexing, and building graph entities..."):
        result = upload_document(uploaded_file.getvalue(), uploaded_file.name, document_type)

    if result:
        st.success(result["message"])
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Chunks indexed", result["chunks_indexed"])
        c2.metric("Entities extracted", result["entities_extracted"])
        c3.metric("OCR used", "Yes" if result["ocr_used"] else "No")
        c4.metric("Document type", result["document_type"].replace("_", " ").title())

        if result["ocr_used"]:
            st.caption(
                "This document required OCR — native text extraction found insufficient "
                "text, so Tesseract ran page-by-page against rasterized images."
            )

st.divider()
st.subheader("Batch-upload the demo corpus")
st.write(
    "The sample corpus in `data/sample_documents/` is intentionally constructed so that, "
    "once uploaded, a scan on the Alerts Dashboard finds a real overdue inspection, a real "
    "training-version gap, and a real unlinked recurring incident. Upload each file above "
    "with its matching document type, then head to **Alerts Dashboard** and click *Run scan*."
)
