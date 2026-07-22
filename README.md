# Sentinel — Industrial Knowledge Intelligence Platform

**ET AI Hackathon 2026 — Problem Statement 8: AI for Industrial Knowledge Intelligence: Unified Asset & Operations Brain**

> Sentinel does not answer questions about your documents. It tells you what your documents
> disagree about — before an auditor, an inspector, or an incident does.

## The problem (from the official problem statement)

- Industrial professionals lose **35% of working hours** searching for or recreating information
  that already exists somewhere in the organisation (McKinsey, 2024).
- The average large Indian plant operates across **7–12 disconnected document systems** —
  P&IDs, work orders, SOPs, inspection records, training logs, regulatory submissions.
- This fragmentation contributes to **18–22% of unplanned downtime** (BIS Research) because
  maintenance decisions get made without full equipment history.
- **25% of India's experienced industrial engineers** retire within a decade, taking
  undocumented tacit judgment with them, permanently.

The data isn't missing. The intelligence layer that connects it — and acts before harm — is.

## What Sentinel actually does differently

Every other team at this hackathon will build "chat with your PDFs." That solves *retrieval*.
It does nothing about *synthesis failure* — the actual failure mode named in the problem
statement (data present, unconnected, unacted upon).

Sentinel's core, distinguishing capability is the **Contradiction & Drift Engine**: an agent
that continuously walks a live knowledge graph built from heterogeneous plant documents and
surfaces three classes of hidden risk that no single-document search can ever find:

| Pattern | Example | Why a chatbot misses it |
|---|---|---|
| **Procedure–practice drift** | SOP requires 6-month valve inspection; work-order log shows 14 months elapsed | Requires joining two document types nobody queries together |
| **Version drift** | Procedure revised v2→v3; training records show workers only ever trained on v2 | Requires temporal reasoning across a third document type |
| **Silent recurrence** | Today's incident symptoms match a 2022 near-miss filed under a different equipment tag | Requires semantic + structural matching, not keyword search |

Every finding ships with: **source citations** (exact document + page/line), a **confidence
score**, and a **reasoning trace** (the literal agent path that produced the conclusion) —
satisfying the explainability requirement structurally, not as an afterthought.

## System capabilities (mapped to the problem statement's "what you may build" list)

- Universal Document Ingestion + Knowledge Graph Agent → `knowledge_graph_agent`
- Expert Knowledge Copilot (RAG, cited, confidence-scored) → `rag_copilot_agent`
- Maintenance Intelligence & RCA Agent → `maintenance_rca_agent`
- Quality & Regulatory Compliance Intelligence → `compliance_agent`
- Lessons Learned & Failure Intelligence Engine → `contradiction_agent` (silent recurrence mode)

## Architecture

See [`docs/architecture.md`](docs/architecture.md) for the full system diagram, agent
architecture, KG schema, RAG pipeline, and API documentation.

```
Documents (PDF/scan/CSV) → OCR + Entity Extraction → Knowledge Graph (Neo4j)
                                                    ↘ Vector Store (Chroma)
                     LangGraph Orchestrator
       ┌──────────────┬──────────────┬──────────────┬──────────────┐
   Copilot        Contradiction   Maintenance     Compliance
   (RAG)            & Drift         & RCA          Intelligence
       └──────────────┴──────────────┴──────────────┴──────────────┘
                          FastAPI backend
                          Streamlit dashboard
```

## Tech stack

Python 3.11 · FastAPI · LangGraph · LangChain · Gemini API · ChromaDB · Neo4j · Tesseract OCR ·
Streamlit · Docker Compose

## Quickstart

```bash
git clone <this-repo>
cd sentinel-industrial-intelligence
cp .env.example .env          # add your GEMINI_API_KEY
docker compose up --build
```

- Backend API: http://localhost:8000/docs
- Streamlit dashboard: http://localhost:8501
- Neo4j browser: http://localhost:7474 (user: neo4j / see .env)

Full install & deployment instructions: [`docs/deployment_guide.md`](docs/deployment_guide.md)

## Repository layout

```
sentinel-industrial-intelligence/
├── backend/            FastAPI app, agents, services, tests
├── frontend/            Streamlit multi-page dashboard
├── data/sample_documents/  Synthetic demo corpus (SOPs, work orders, near-miss reports)
├── docs/                Architecture, API docs, KG schema, deployment guide
└── docker-compose.yml   One-command local stack (backend + frontend + Neo4j)
```

## Status

Actively built for ET AI Hackathon 2026 submission. See `docs/architecture.md` for design
rationale and `docs/deployment_guide.md` for judge-facing setup instructions.
