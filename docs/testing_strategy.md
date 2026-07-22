# Testing Strategy

## Philosophy

Sentinel's riskiest logic is not "does FastAPI route correctly" — it's
**"does the drift-detection math produce the right severity/confidence,
and does OCR correctly decide when to fall back."** Tests are weighted
toward those pure-logic paths, with external SDKs (Neo4j, Chroma, Gemini)
mocked at the boundary so the suite runs in CI without live infrastructure.

## Test pyramid

```
        ┌─────────────────────────┐
        │   API tests (test_api)   │  FastAPI TestClient, mocked orchestrator calls
        ├─────────────────────────┤
        │ Service unit tests        │  OCR routing, chunking edge cases
        ├─────────────────────────┤
        │ Agent logic unit tests    │  Severity thresholds, date math, confidence heuristics
        └─────────────────────────┘
```

## What's covered today

| File | Covers |
|---|---|
| `tests/test_text_chunking.py` | Overlap correctness, empty input, boundary conditions |
| `tests/test_ocr_service.py` | File-type routing (txt/csv/unsupported), native extraction |
| `tests/test_contradiction_agent.py` | Severity-from-overdue-ratio thresholds, date parsing edge cases |
| `tests/test_api.py` | Route wiring, request validation (short question → 422), response shape conformance |

## What's intentionally mocked, and why

`tests/conftest.py` patches `neo4j.GraphDatabase.driver`,
`chromadb.PersistentClient`, and `google.generativeai` before any `app.*`
module is imported. These are module-level singletons
(`graph_service`, `vector_store_service`, `llm_service`) instantiated at
import time — without mocking, `pytest` would require live Neo4j/Chroma/
Gemini just to collect tests. This keeps `pytest` fast and CI-friendly.

## What's deliberately NOT unit tested (and why)

- **End-to-end drift detection against a real graph** — this requires a
  populated Neo4j instance and is instead verified live during the demo
  against the seeded sample corpus (`data/sample_documents/`), which is
  specifically constructed to trigger all three drift patterns
  deterministically (see `docs/deployment_guide.md` demo script).
- **LLM output quality** (entity extraction accuracy, RCA hypothesis
  quality) — inherently non-deterministic; judged qualitatively during the
  live demo rather than asserted against a fixed expected string.

## Extending coverage (next steps for a production hardening pass)

1. Add a `test_integration_full_pipeline.py` that runs against
   `docker compose up` in CI (e.g. GitHub Actions service containers for
   Neo4j) to validate the actual Cypher queries against seeded fixture data.
2. Add golden-file tests for `knowledge_graph_agent.extract_and_persist`
   using recorded (cached) Gemini responses, so entity-extraction
   regressions can be caught without live API calls.
3. Add contract tests for `EvidenceCitation`/`AgentFinding` schemas to
   guarantee frontend/backend never drift on response shape.

## Running the suite

```bash
cd backend
pip install -r requirements.txt
pytest -v
```
