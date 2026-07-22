# Sentinel — System Architecture

## 1. Layered overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Streamlit Dashboard                         │
│   Home │ Alerts Dashboard │ Knowledge Graph │ Expert Copilot │ Upload│
└───────────────────────────────┬───────────────────────────────────-─┘
                                 │ REST (JSON)
┌────────────────────────────────▼──────────────────────────────────┐
│                          FastAPI Backend                           │
│  routes_documents │ routes_query │ routes_alerts │ routes_graph    │
└────────────────────────────────┬───────────────────────────────────┘
                                 │
┌────────────────────────────────▼───────────────────────────────────┐
│                    LangGraph Orchestrator (agents/)                │
│                                                                      │
│  copilot_graph:  [rag_copilot_agent] → END                         │
│                                                                      │
│  scan_graph:     [contradiction_agent] → [maintenance_rca_agent]    │
│                        → [compliance_agent] → [merge] → END         │
│                                                                      │
│  (ingestion path, invoked directly from routes_documents):          │
│  ingestion_service → knowledge_graph_agent                          │
└───────┬───────────────────────┬───────────────────────┬────────────┘
        │                       │                       │
┌───────▼────────┐   ┌──────────▼─────────┐   ┌──────────▼──────────┐
│  OCR Service    │   │  Vector Store       │   │  Graph Service      │
│  (Tesseract +   │   │  Service (Chroma +  │   │  (Neo4j)            │
│  native PDF     │   │  Gemini embeddings) │   │                      │
│  extraction)    │   │                     │   │                      │
└─────────────────┘   └─────────────────────┘   └──────────────────────┘
                                 │
                         ┌───────▼────────┐
                         │  LLM Service    │
                         │  (Gemini API)   │
                         └─────────────────┘
```

## 2. Why this shape, not a simpler one

A single-agent RAG chatbot would collapse the "Vector Store" and "Graph
Service" boxes into one retrieval call and skip the orchestrator entirely.
Sentinel keeps them separate and adds the orchestrator because the product
claim — proactive discovery of contradictions, not just answers to
questions — requires **reasoning across structured relationships**
(the graph), not just semantic similarity (the vector store). The two
retrieval mechanisms serve genuinely different purposes:

- **Vector store (Chroma):** "What does the SOP say about X?" — semantic
  similarity over unstructured text. Powers the Expert Copilot.
- **Knowledge graph (Neo4j):** "Which work order was the last one performed
  on the equipment this procedure governs, and how long ago was that?" —
  structural traversal across explicit relationships. Powers the
  Contradiction & Drift Engine, Maintenance/RCA agent, and Compliance
  agent.

## 3. Agent architecture

| Agent | Problem statement mapping | Core responsibility |
|---|---|---|
| `knowledge_graph_agent` | Universal Document Ingestion & Knowledge Graph Agent | LLM-based entity extraction from raw ingested text; writes nodes/relationships to Neo4j |
| `rag_copilot_agent` | Expert Knowledge Copilot | Cited, confidence-scored RAG answering; escalates to human below confidence threshold |
| `contradiction_agent` | Lessons Learned & Failure Intelligence Engine | Runs the three drift-detection patterns (procedure-practice drift, version drift, silent recurrence) |
| `maintenance_rca_agent` | Maintenance Intelligence & RCA Agent | Frequency-based predictive maintenance risk flagging + on-demand RCA hypothesis generation |
| `compliance_agent` | Quality & Regulatory Compliance Intelligence | Reframes drift findings as audit-facing compliance gaps; detects procedures with no regulatory mapping |

Each agent inherits `BaseAgent` and implements `run(state) -> state`,
appending to a shared `reasoning_trace` list — this is literally the
explainability mechanism: every finding's `reasoning_trace` field in the
API response is the ordered list of steps the agent took to reach it.

## 4. Data flow: ingestion

1. User uploads a document via `/documents/upload` with a declared
   `document_type`.
2. `ingestion_service` extracts text (native PDF parsing, or Tesseract OCR
   fallback for scans/images), chunks it, embeds and indexes it in Chroma.
3. `knowledge_graph_agent` runs a single constrained Gemini call over the
   raw text to extract entities (equipment, procedures, work orders,
   incidents, personnel) as JSON, then writes them to Neo4j via
   `graph_service`, including inferred relationships like `GOVERNS` and
   `SUPERSEDES`.

## 5. Data flow: proactive scan

`POST /alerts/scan` invokes `scan_graph`, which runs three agents in
sequence over the **same** knowledge graph, each contributing
`AgentFinding` objects to a shared accumulator:

1. `contradiction_agent` runs three Cypher queries (see
   `docs/kg_schema.md`) directly against Neo4j and layers LLM-based
   symptom-similarity scoring on top for the silent-recurrence pattern.
2. `maintenance_rca_agent` aggregates incident co-occurrence per equipment
   tag as a transparent, explainable predictive-risk heuristic.
3. `compliance_agent` reframes overdue-inspection findings as compliance
   exposures and flags procedures with no regulatory clause mapping.

## 6. Explainability & trust design

Every `AgentFinding` and every copilot answer carries:

- `confidence` (0.0–1.0) — computed via a stated, inspectable heuristic
  (never a black-box score with no formula behind it)
- `evidence` — a list of `EvidenceCitation` objects with document name,
  type, and exact excerpt/location
- `reasoning_trace` — the ordered list of steps the agent took

The copilot additionally implements a hard confidence floor
(`MIN_ANSWER_CONFIDENCE`, default 0.55): below this, it refuses to answer
and explicitly recommends human escalation rather than guessing — directly
answering the problem statement's implicit requirement that citizen/field-
facing tools keep false positive/false confidence rates very low.

## 7. Scalability notes

- Chroma and Neo4j are both horizontally replaceable: `VectorStoreService`
  and `GraphService` are the only modules that import their respective
  SDKs, so swapping Chroma→FAISS/Pinecone or Neo4j→managed Aura requires
  touching exactly one file each.
- The ingestion pipeline is per-document and stateless — safe to
  parallelize across workers for a large document backlog.
- LangGraph's node-based structure means new agents (e.g. a P&ID computer
  vision agent) can be added to `scan_graph` as an additional node without
  touching existing agent code (open/closed principle).
