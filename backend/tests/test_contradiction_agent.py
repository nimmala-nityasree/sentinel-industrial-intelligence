"""
Unit tests for the Contradiction & Drift Agent's pure-logic helpers.

These tests target the deterministic scoring functions directly (severity
from overdue ratio, days-since parsing) rather than the full run() pipeline,
which depends on live Neo4j + Gemini — those are covered by the
integration test in test_api.py using mocked services.
"""
from datetime import date, timedelta

from app.agents.contradiction_agent import ContradictionAgent
from app.models.schemas import SeverityLevel


def test_severity_from_overdue_ratio_thresholds():
    agent = ContradictionAgent()
    assert agent._severity_from_overdue_ratio(1.1) == SeverityLevel.LOW
    assert agent._severity_from_overdue_ratio(1.5) == SeverityLevel.MEDIUM
    assert agent._severity_from_overdue_ratio(2.5) == SeverityLevel.HIGH
    assert agent._severity_from_overdue_ratio(4.0) == SeverityLevel.CRITICAL


def test_days_since_valid_iso_date():
    agent = ContradictionAgent()
    ten_days_ago = (date.today() - timedelta(days=10)).isoformat()
    assert agent._days_since(ten_days_ago) == 10


def test_days_since_none_input_returns_none():
    agent = ContradictionAgent()
    assert agent._days_since(None) is None


def test_days_since_malformed_date_returns_none():
    agent = ContradictionAgent()
    assert agent._days_since("not-a-date") is None
