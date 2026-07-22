"""
API-level tests using FastAPI's TestClient.

External services are mocked at the SDK level via conftest.py, so these
tests verify routing, request/response schema conformance, and error
handling — not live agent reasoning quality (that's judged live in the demo).
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "Sentinel" in response.json()["service"]


def test_copilot_query_rejects_short_question():
    response = client.post("/api/v1/query/copilot", json={"question": "V"})
    assert response.status_code == 422  # pydantic min_length validation


def test_copilot_query_valid_shape(monkeypatch):
    from app.api import routes_query

    def fake_run_copilot_query(question, equipment_filter, top_k):
        return {
            "answer": "Inspection interval is 180 days per SOP-114.",
            "confidence": 0.82,
            "evidence": [],
            "escalate_to_human": False,
            "reasoning_trace": ["retrieved 3 chunks"],
        }

    monkeypatch.setattr(routes_query, "run_copilot_query", fake_run_copilot_query)

    response = client.post(
        "/api/v1/query/copilot",
        json={"question": "How often should V-204 be inspected?", "top_k": 5},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["confidence"] == 0.82
    assert body["escalate_to_human"] is False


def test_alerts_scan_returns_findings_shape(monkeypatch):
    from app.api import routes_alerts

    def fake_run_full_scan():
        return {"findings": []}

    monkeypatch.setattr(routes_alerts, "run_full_scan", fake_run_full_scan)

    response = client.post("/api/v1/alerts/scan")
    assert response.status_code == 200
    body = response.json()
    assert body["total_findings"] == 0
    assert body["findings"] == []
