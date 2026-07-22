# Deployment & Demo Guide

## Prerequisites

- Docker + Docker Compose (recommended path)
- OR Python 3.11+, Tesseract OCR, and a running Neo4j instance (manual path)
- A Gemini API key (https://ai.google.dev/) — free tier is sufficient for the demo corpus

## Option A — Docker Compose (recommended)

```bash
git clone <this-repo>
cd sentinel-industrial-intelligence
cp .env.example .env
# edit .env and set GEMINI_API_KEY=<your key>
docker compose up --build
```

Wait for all three containers (`neo4j`, `backend`, `frontend`) to report
healthy — Neo4j takes ~20-30s to become ready, and `backend` will wait for
it via `depends_on: condition: service_healthy`.

- Dashboard: http://localhost:8501
- API docs: http://localhost:8000/docs
- Neo4j browser: http://localhost:7474 (user `neo4j`, password from `.env`)

To stop: `docker compose down` (add `-v` to also wipe the Neo4j/Chroma volumes).

## Option B — Manual local setup

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Install Tesseract OCR: `apt install tesseract-ocr poppler-utils` (Linux) or `brew install tesseract poppler` (macOS)
# Start a local Neo4j instance (Docker: docker run -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/sentinel_pass neo4j:5.20-community)
cp ../.env.example .env  # edit as needed
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
BACKEND_API_URL=http://localhost:8000 streamlit run streamlit_app/Home.py
```

## Recommended demo script (~5 minutes)

1. **Open the dashboard Home page** — point out the live backend health
   check and empty graph stats (proves nothing is pre-seeded/mocked).
2. **Document Upload page** — upload the six files in
   `data/sample_documents/` one at a time with their matching document
   types (`sop_valve_inspection_v2.md` → sop, `sop_valve_inspection_v3.md`
   → sop, `work_order_log.csv` → work_order, `training_records.csv` →
   training_record, `near_miss_report_2022.txt` → near_miss_report,
   `incident_report_2026.txt` → incident_report). Point out the OCR/entity
   count feedback after each upload.
3. **Knowledge Graph page** — show the populated graph: equipment, two
   procedure versions, work orders, two incidents, three personnel.
4. **Alerts Dashboard page** — click **Run multi-agent scan**. Walk through
   the three findings live:
   - Procedure–practice drift on V-204 (overdue inspection)
   - Version drift (R. Sharma / K. Iyer trained only on v2)
   - Silent recurrence (2022 near-miss ↔ 2026 incident, different equipment
     tags, matched on symptom similarity)
   For each, expand the card and show the **evidence** and **reasoning
   trace** — this is the explainability payoff.
5. **Expert Copilot page** — ask *"How often should V-204 be inspected?"*
   and show the cited answer + confidence score. Then ask an out-of-corpus
   question (e.g. *"What's the weather forecast for tomorrow?"*) to show
   the confidence-based escalation refusing to hallucinate.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Backend container unhealthy / crash-loops | Check `GEMINI_API_KEY` is set in `.env` — the backend fails fast if Gemini calls error on first use |
| `Neo4j auth error` | Ensure `NEO4J_PASSWORD` in `.env` matches what Neo4j was initialized with; if you changed it after first run, `docker compose down -v` to reset the volume |
| OCR returns empty text for a scanned upload | Confirm `tesseract-ocr` and `poppler-utils` are installed in the container/host (already handled in `backend/Dockerfile`) |
| Streamlit graph page shows no nodes | Confirm documents were uploaded successfully (check `entities_extracted > 0` in the upload response) before visiting the Knowledge Graph page |
| Copilot always escalates to human | Lower `MIN_ANSWER_CONFIDENCE` in `.env` for a smaller demo corpus, or upload more chunks of the relevant SOP so retrieval has more corroborating evidence |

## Running tests

```bash
cd backend
pip install -r requirements.txt
pytest -v
```

All unit/API tests run against mocked Neo4j/Chroma/Gemini SDKs (see
`backend/tests/conftest.py`) — no live infrastructure required for `pytest`.
