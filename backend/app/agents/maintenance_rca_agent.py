"""
Maintenance Intelligence & RCA Agent.

Implements the problem statement's "Maintenance Intelligence & RCA Agent":
fuses work-order history, equipment failure records, and inspection
findings to (a) flag equipment trending toward failure based on repeated
incident/work-order activity, and (b) generate a structured, evidence-
grounded Root Cause Analysis hypothesis on request — never a bare guess,
always tied to the specific incidents that informed it.
"""
import uuid
from collections import Counter

from app.agents.base_agent import BaseAgent, SentinelState
from app.core.logging_config import logger
from app.models.schemas import (
    AgentFinding,
    DocumentType,
    EvidenceCitation,
    FindingType,
    SeverityLevel,
)
from app.services.graph_service import graph_service
from app.services.llm_service import llm_service

_RCA_PROMPT_TEMPLATE = """
You are supporting a Root Cause Analysis for an industrial incident.

Incident: {incident_title}
Description: {incident_description}
Symptoms: {symptoms}

Related historical incidents on the same or similar equipment:
{related_incidents}

Based ONLY on the information above, propose the most likely root cause
category (e.g. "mechanical wear", "process deviation", "maintenance gap",
"operator error", "design limitation") and a one-paragraph justification
that explicitly references which piece of evidence supports it.

Return JSON only:
{{"root_cause_category": "...", "justification": "...", "confidence": <float 0.0-1.0>}}
"""


class MaintenanceRCAAgent(BaseAgent):
    name = "maintenance_rca_agent"

    def run(self, state: SentinelState) -> SentinelState:
        """Proactive scan mode: flag equipment with repeated recent incident activity."""
        self._trace(state, "Scanning incident recurrence frequency per equipment")
        findings = self._detect_repeat_failure_risk()
        state["findings"] = [f.model_dump() for f in findings]
        self._trace(state, f"Maintenance risk scan complete — {len(findings)} finding(s)")
        return state

    def _detect_repeat_failure_risk(self) -> list[AgentFinding]:
        """
        Flags equipment with 2+ incidents/near-misses on record as elevated
        risk — a simple, explainable frequency heuristic rather than a
        black-box predictive model, appropriate for a hackathon-scale
        dataset while still directly answering "predictive maintenance".
        """
        rows = graph_service.find_silent_recurrence_candidates(lookback_days=3650)
        equipment_incident_counts: Counter = Counter()
        equipment_incident_titles: dict[str, list[str]] = {}

        for row in rows:
            for tag, title, doc in (
                (row["equipment_a_tag"], row["incident_a_title"], row["doc_a"]),
                (row["equipment_b_tag"], row["incident_b_title"], row["doc_b"]),
            ):
                if not tag:
                    continue
                equipment_incident_counts[tag] += 1
                equipment_incident_titles.setdefault(tag, []).append(title)

        findings = []
        for tag, count in equipment_incident_counts.items():
            if count < 2:
                continue
            titles = list(dict.fromkeys(equipment_incident_titles[tag]))  # dedupe, preserve order
            findings.append(
                AgentFinding(
                    finding_id=str(uuid.uuid4()),
                    finding_type=FindingType.MAINTENANCE_RISK,
                    title=f"Elevated failure risk: {tag}",
                    description=(
                        f"{tag} appears in {count} recorded incident/near-miss pairings, "
                        f"more than any single-incident baseline. Related events: {', '.join(titles[:3])}."
                    ),
                    severity=SeverityLevel.HIGH if count >= 3 else SeverityLevel.MEDIUM,
                    confidence=round(min(0.5 + 0.1 * count, 0.9), 2),
                    evidence=[
                        EvidenceCitation(
                            document_id="aggregate",
                            document_name=f"{count} incident records for {tag}",
                            document_type=DocumentType.INCIDENT_REPORT,
                            excerpt=f"Recurring titles: {', '.join(titles[:3])}",
                            location="incident graph aggregation",
                        )
                    ],
                    affected_equipment_ids=[tag],
                    reasoning_trace=[
                        f"Counted incident co-occurrence for equipment tag {tag} across knowledge graph",
                        f"{count} incidents exceed single-occurrence baseline -> elevated risk flag",
                    ],
                    recommended_action=(
                        f"Prioritize {tag} for the next predictive maintenance cycle and review "
                        "whether prior corrective actions actually addressed the root cause."
                    ),
                )
            )
        return findings

    def generate_rca(self, incident_title: str, incident_description: str, symptoms: list[str]) -> dict:
        """
        On-demand RCA hypothesis generation, called from the API when a user
        requests root-cause support for a specific incident.
        """
        related_rows = graph_service.find_silent_recurrence_candidates(lookback_days=3650)
        related_text = "\n".join(
            f"- {r['incident_a_title']} (symptoms: {r.get('symptoms_a')})" for r in related_rows[:5]
        ) or "No related historical incidents found in the graph."

        prompt = _RCA_PROMPT_TEMPLATE.format(
            incident_title=incident_title,
            incident_description=incident_description,
            symptoms=symptoms,
            related_incidents=related_text,
        )
        try:
            return llm_service.generate_json(prompt)
        except Exception as exc:
            logger.error(f"RCA generation failed: {exc}")
            return {
                "root_cause_category": "unknown",
                "justification": "RCA generation failed — insufficient evidence or LLM error.",
                "confidence": 0.0,
            }


maintenance_rca_agent = MaintenanceRCAAgent()
