"""
Knowledge Graph Agent — entity extraction + graph construction.

Directly implements the problem statement's "Universal Document Ingestion &
Knowledge Graph Agent": extracts entities (equipment tags, process
parameters, personnel, dates) from raw document text and builds/updates the
knowledge graph, maintaining relationships across document types.

We use a single constrained JSON-generation call per document rather than a
sequence of smaller calls — cheaper, and keeps entity relationships
(e.g. "this procedure governs this equipment tag") consistent within one
LLM pass instead of stitched together after the fact.
"""
import uuid

from app.agents.base_agent import BaseAgent, SentinelState
from app.core.logging_config import logger
from app.models.schemas import DocumentType
from app.services.graph_service import graph_service
from app.services.llm_service import llm_service

_EXTRACTION_PROMPT_TEMPLATE = """
You are an industrial document entity-extraction engine. Extract structured
entities from the document text below and return them as JSON matching
EXACTLY this schema (omit any list that has no entries, use empty list []
instead of omitting the key):

{{
  "equipment": [{{"tag": "V-204", "name": "Feed valve", "area": "unit 3"}}],
  "procedures": [{{"title": "Valve Inspection SOP", "version": "v3",
                    "effective_date": "2025-01-15",
                    "required_inspection_interval_days": 180,
                    "governs_equipment_tag": "V-204",
                    "supersedes_version": "v2"}}],
  "work_orders": [{{"wo_number": "WO-4471", "description": "Routine inspection",
                     "performed_on": "2024-06-01", "status": "completed",
                     "equipment_tag": "V-204"}}],
  "incidents": [{{"title": "Gas pressure anomaly", "description": "...",
                   "occurred_on": "2022-03-11",
                   "symptoms": ["unusual vibration", "temperature spike"],
                   "equipment_tag": "V-204"}}],
  "personnel": [{{"name": "R. Sharma", "role": "technician",
                   "trained_on_procedure_version": "v2"}}]
}}

Document type hint: {document_type}
Document text:
---
{text}
---

Extract only entities explicitly present or clearly implied in the text.
Do not invent equipment tags, dates, or names not present in the source.
"""


class KnowledgeGraphAgent(BaseAgent):
    name = "knowledge_graph_agent"

    def extract_and_persist(self, document_id: str, document_type: DocumentType, text: str) -> int:
        """
        Extract entities from raw text and persist them to Neo4j.
        Returns the count of entities extracted (for the upload response).
        """
        prompt = _EXTRACTION_PROMPT_TEMPLATE.format(
            document_type=document_type.value, text=text[:12000]  # cap to control token cost
        )

        try:
            extracted = llm_service.generate_json(prompt)
        except Exception as exc:
            logger.error(f"Entity extraction failed for document {document_id}: {exc}")
            return 0

        entity_count = 0
        equipment_tags_seen: dict[str, str] = {}

        for eq in extracted.get("equipment", []):
            eq_id = str(uuid.uuid4())
            graph_service.upsert_equipment(
                id=eq_id, tag=eq["tag"], name=eq.get("name", eq["tag"]), area=eq.get("area", "unspecified")
            )
            equipment_tags_seen[eq["tag"]] = eq_id
            entity_count += 1

        procedure_id_by_version: dict[str, str] = {}
        for proc in extracted.get("procedures", []):
            proc_id = str(uuid.uuid4())
            graph_service.upsert_procedure(
                id=proc_id,
                title=proc["title"],
                version=proc.get("version", "v1"),
                effective_date=proc.get("effective_date", ""),
                document_id=document_id,
                governs_equipment_tag=proc.get("governs_equipment_tag"),
                required_inspection_interval_days=proc.get("required_inspection_interval_days"),
            )
            procedure_id_by_version[proc.get("version", "v1")] = proc_id
            entity_count += 1

        for wo in extracted.get("work_orders", []):
            graph_service.upsert_work_order(
                id=str(uuid.uuid4()),
                wo_number=wo.get("wo_number", "unknown"),
                description=wo.get("description", ""),
                performed_on=wo.get("performed_on", ""),
                status=wo.get("status", "unknown"),
                document_id=document_id,
                equipment_tag=wo.get("equipment_tag"),
            )
            entity_count += 1

        for inc in extracted.get("incidents", []):
            graph_service.upsert_incident(
                id=str(uuid.uuid4()),
                title=inc.get("title", "Untitled incident"),
                description=inc.get("description", ""),
                occurred_on=inc.get("occurred_on", ""),
                symptoms=inc.get("symptoms", []),
                document_id=document_id,
                equipment_tag=inc.get("equipment_tag"),
            )
            entity_count += 1

        logger.info(f"Knowledge graph agent extracted {entity_count} entities from document {document_id}")
        return entity_count

    def run(self, state: SentinelState) -> SentinelState:
        # Invoked directly by the ingestion API route today; kept LangGraph-compatible
        # so it can be wired into the orchestrator graph for future async ingestion flows.
        self._trace(state, "Entity extraction delegated to extract_and_persist()")
        return state


knowledge_graph_agent = KnowledgeGraphAgent()
