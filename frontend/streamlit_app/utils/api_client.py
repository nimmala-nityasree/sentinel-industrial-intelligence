"""
Backend API client.

Every Streamlit page imports from here instead of calling `requests` directly
— keeps the base URL, timeout, and error handling in one place, and makes
each page's code read as intent ("get_alerts()") rather than HTTP plumbing.
"""
import os

import requests
import streamlit as st

BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")
API_PREFIX = "/api/v1"
DEFAULT_TIMEOUT = 60


def _url(path: str) -> str:
    return f"{BACKEND_API_URL}{API_PREFIX}{path}"


def check_health() -> bool:
    try:
        r = requests.get(_url("/health"), timeout=5)
        return r.status_code == 200
    except requests.RequestException:
        return False


def upload_document(file_bytes: bytes, filename: str, document_type: str) -> dict | None:
    try:
        files = {"file": (filename, file_bytes)}
        data = {"document_type": document_type}
        r = requests.post(_url("/documents/upload"), files=files, data=data, timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as exc:
        st.error(f"Upload failed: {exc}")
        return None


def query_copilot(question: str, top_k: int = 5, equipment_filter: str | None = None) -> dict | None:
    try:
        payload = {"question": question, "top_k": top_k}
        if equipment_filter:
            payload["equipment_filter"] = equipment_filter
        r = requests.post(_url("/query/copilot"), json=payload, timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as exc:
        st.error(f"Copilot query failed: {exc}")
        return None


def run_scan() -> dict | None:
    try:
        r = requests.post(_url("/alerts/scan"), timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as exc:
        st.error(f"Scan failed: {exc}")
        return None


def get_graph_stats() -> dict | None:
    try:
        r = requests.get(_url("/graph/stats"), timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as exc:
        st.error(f"Could not fetch graph stats: {exc}")
        return None


def get_graph_export(limit: int = 150) -> dict | None:
    try:
        r = requests.get(_url("/graph/export"), params={"limit": limit}, timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as exc:
        st.error(f"Could not fetch graph export: {exc}")
        return None


def generate_rca(incident_title: str, incident_description: str, symptoms: list[str]) -> dict | None:
    try:
        payload = {
            "incident_title": incident_title,
            "incident_description": incident_description,
            "symptoms": symptoms,
        }
        r = requests.post(_url("/alerts/rca"), json=payload, timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as exc:
        st.error(f"RCA generation failed: {exc}")
        return None
