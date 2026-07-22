# API Documentation

Base URL (local): `http://localhost:8000/api/v1`
Interactive Swagger UI: `http://localhost:8000/docs`

## Health

### `GET /health`
Liveness check used by the Docker healthcheck and the dashboard status indicator.

```bash
curl http://localhost:8000/api/v1/health
```
```json
{"status": "ok", "service": "sentinel-backend"}
```

---

## Documents

### `POST /documents/upload`
Ingests a document: OCR (if needed) → chunk → embed/index → entity extraction → graph write.

**Form fields:**
- `file` (required) — the document (pdf, png, jpg, jpeg, tiff, csv, txt, md)
- `document_type` (required) — one of `sop`, `work_order`, `near_miss_report`,
  `incident_report`, `training_record`, `regulatory_document`, `pid_drawing`, `other`

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@data/sample_documents/sop_valve_inspection_v3.md" \
  -F "document_type=sop"
```

**Response (`DocumentUploadResponse`):**
```json
{
  "document_id": "b3f1...",
  "filename": "sop_valve_inspection_v3.md",
  "document_type": "sop",
  "chunks_indexed": 3,
  "entities_extracted": 2,
  "ocr_used": false,
  "message": "Document ingested, indexed, and merged into the knowledge graph."
}
```

---

## Copilot

### `POST /query/copilot`
Cited, confidence-scored RAG answer with explicit human-escalation when evidence is weak.

**Request:**
```json
{"question": "How often should V-204 be inspected?", "top_k": 5}
```

**Response (`CopilotQueryResponse`):**
```json
{
  "answer": "Per SOP-114, valve V-204 requires inspection every 180 days.",
  "confidence": 0.82,
  "evidence": [{"document_id": "...", "document_name": "SOP-114-v3", "document_type": "sop",
                "excerpt": "...every 180 days...", "location": "chunk 1", "retrieved_at": "..."}],
  "escalate_to_human": false,
  "reasoning_trace": ["Retrieving top-5 evidence chunks...", "Retrieval confidence estimated at 0.82", "..."]
}
```

If confidence falls below `MIN_ANSWER_CONFIDENCE` (default `0.55`),
`escalate_to_human` is `true` and the answer explicitly recommends
consulting a subject-matter expert instead of guessing.

---

## Alerts

### `POST /alerts/scan`
Runs the full multi-agent scan (contradiction, maintenance/RCA, compliance) and returns every finding.

```bash
curl -X POST http://localhost:8000/api/v1/alerts/scan
```

**Response (`AlertsResponse`):** a list of `AgentFinding` objects, each with
`finding_type`, `severity`, `confidence`, `evidence[]`, `reasoning_trace[]`,
and `recommended_action`. See `docs/kg_schema.md` for what each
`finding_type` means.

### `POST /alerts/rca`
On-demand root-cause-analysis hypothesis for a specific incident.

**Request:**
```json
{
  "incident_title": "Compressor vibration event",
  "incident_description": "...",
  "symptoms": ["unusual vibration", "temperature spike"]
}
```

**Response:**
```json
{"root_cause_category": "mechanical wear", "justification": "...", "confidence": 0.7}
```

---

## Knowledge graph

### `GET /graph/stats`
Headline counts for the dashboard.

```json
{"equipment_count": 4, "procedure_count": 2, "work_order_count": 6,
 "incident_count": 2, "personnel_count": 3, "relationship_count": 11}
```

### `GET /graph/export?limit=150`
Bounded node/edge export for the Streamlit graph visualization page.

```json
{"nodes": [{"id": "...", "label": "V-204"}], "edges": [{"source": "...", "target": "...", "type": "GOVERNS"}]}
```
