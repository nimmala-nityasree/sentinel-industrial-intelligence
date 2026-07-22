"""
Shared pytest fixtures.

Sentinel's services (graph_service, vector_store_service, llm_service) are
module-level singletons that connect to external systems (Neo4j, Chroma,
Gemini) at import time. To keep the unit test suite fast and independent of
live infrastructure, this conftest patches those SDK entrypoints BEFORE any
`app.*` module is imported — pytest guarantees conftest.py runs first for
tests in the same directory tree.

Tests that need real end-to-end behavior belong in a separate
`test_integration_*.py` suite, run explicitly against `docker compose up`
per docs/deployment_guide.md — not part of the default `pytest` run.
"""
import os
from unittest.mock import MagicMock, patch

import pytest

# Ensure required env vars exist so pydantic-settings doesn't error before mocks apply.
os.environ.setdefault("GEMINI_API_KEY", "test-key")
os.environ.setdefault("NEO4J_PASSWORD", "test-pass")

_neo4j_patch = patch("neo4j.GraphDatabase.driver", return_value=MagicMock())
_chroma_patch = patch("chromadb.PersistentClient", return_value=MagicMock())
_genai_patch = patch("google.generativeai.configure", return_value=None)
_genai_model_patch = patch("google.generativeai.GenerativeModel", return_value=MagicMock())

for _p in (_neo4j_patch, _chroma_patch, _genai_patch, _genai_model_patch):
    _p.start()


@pytest.fixture(autouse=True)
def _reset_mocks_between_tests():
    """Keep mock call history isolated per test."""
    yield
