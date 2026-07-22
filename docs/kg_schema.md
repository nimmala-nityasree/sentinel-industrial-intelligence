# Knowledge Graph Schema

Defined in code at `backend/app/models/graph_models.py`; this document
explains the *why* behind each relationship and shows the Cypher patterns
that power the Contradiction & Drift Engine.

## Nodes

| Label | Key properties | Populated from |
|---|---|---|
| `Equipment` | `id`, `tag`, `name`, `area`, `criticality` | Extracted from any document mentioning an equipment tag |
| `Procedure` | `id`, `title`, `version`, `effective_date`, `document_id`, `required_inspection_interval_days` | SOPs |
| `WorkOrder` | `id`, `wo_number`, `description`, `performed_on`, `status`, `document_id` | Work order logs |
| `Incident` | `id`, `title`, `description`, `occurred_on`, `symptoms[]`, `document_id` | Near-miss / incident reports |
| `Personnel` | `id`, `name`, `role` | Training records |
| `RegulatoryClause` | `id`, `code`, `description`, `source` | Regulatory documents (OISD/Factory Act/DGMS/PESO) |

## Relationships

| Type | Direction | Meaning | Who writes it |
|---|---|---|---|
| `GOVERNS` | Procedure → Equipment | This SOP applies to this equipment | `knowledge_graph_agent` at ingestion |
| `SUPERSEDES` | Procedure(new) → Procedure(old) | Version lineage | `knowledge_graph_agent` at ingestion |
| `PERFORMED_ON` | WorkOrder → Equipment | This work order was carried out on this equipment | `knowledge_graph_agent` at ingestion |
| `OCCURRED_ON` | Incident → Equipment | This incident happened on this equipment | `knowledge_graph_agent` at ingestion |
| `TRAINED_ON` | Personnel → Procedure | This person was trained on this procedure version | `knowledge_graph_agent` at ingestion |
| `COMPLIES_WITH` | Procedure → RegulatoryClause | This SOP satisfies this regulatory clause | `knowledge_graph_agent` at ingestion (when present in source text) |
| `SIMILAR_FAILURE_MODE` | Incident ↔ Incident | Inferred: these two incidents likely share a root cause | `contradiction_agent`, written only after LLM similarity scoring exceeds threshold — this is the one relationship type the system infers rather than extracts |

## The three drift-detection queries (plain-English + Cypher)

### Procedure–practice drift
*"Find every piece of equipment whose governing procedure requires
periodic inspection, where the most recent work order is older than that
required interval."*

```cypher
MATCH (p:Procedure)-[:GOVERNS]->(e:Equipment)
WHERE p.required_inspection_interval_days IS NOT NULL
OPTIONAL MATCH (w:WorkOrder)-[:PERFORMED_ON]->(e)
WITH p, e, w ORDER BY w.performed_on DESC
WITH p, e, collect(w)[0] AS latest_wo
RETURN p, e, latest_wo
```

### Version drift
*"Find every procedure that has been superseded, where personnel are
trained on the old version but not the new one."*

```cypher
MATCH (new:Procedure)-[:SUPERSEDES]->(old:Procedure)
MATCH (pers:Personnel)-[:TRAINED_ON]->(old)
WHERE NOT (pers)-[:TRAINED_ON]->(new)
RETURN new, old, collect(pers.name) AS untrained_personnel
```

### Silent recurrence (candidate generation)
*"Find pairs of incidents within the lookback window that are not yet
linked as similar failure modes — these are candidates for LLM-based
symptom similarity scoring."*

```cypher
MATCH (i1:Incident)-[:OCCURRED_ON]->(e1:Equipment)
MATCH (i2:Incident)-[:OCCURRED_ON]->(e2:Equipment)
WHERE i1.id <> i2.id AND i1.occurred_on >= $cutoff AND i2.occurred_on >= $cutoff
  AND NOT (i1)-[:SIMILAR_FAILURE_MODE]-(i2)
  AND id(i1) < id(i2)
RETURN i1, i2
LIMIT 50
```

Each candidate pair is then scored by Gemini for symptom-similarity; pairs
scoring above `0.65` become a `SIMILAR_FAILURE_MODE` finding **and** a
persisted graph edge — meaning the graph gets smarter every time the scan
runs, not just the alert feed.

## Design rationale: why these three patterns and not others

The problem statement's own framing point at exactly these three failure
modes:

- 35% of time lost recreating/searching info → symptomatic of information
  existing in one system but not being checked against another
  (procedure-practice drift, version drift)
- 25% of engineers retiring with undocumented judgment → symptomatic of
  incidents not being cross-referenced against prior incidents once the
  person who remembered the prior one is gone (silent recurrence)

These are not arbitrary feature choices; they are the graph-native
translation of the problem statement's own diagnosis.
