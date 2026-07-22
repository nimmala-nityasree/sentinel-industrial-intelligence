"""
Compliance Intelligence Agent.

Implements the problem statement's "Quality & Regulatory Compliance
Intelligence": maps regulatory requirements against current procedures and
flags gaps, auto-generating compliance evidence packages.

Design note: procedure-practice drift findings (overdue inspections) ARE
compliance gaps by definition — OISD/Factory Act require documented
adherence to stated inspection intervals. Rather than duplicate that logic,
this agent re-labels qualifying contradiction findings as compliance gaps
AND adds a distinct check the contradiction agent doesn't cover: procedures
with no linked regulatory clause at all, i.e. undocumented compliance
posture, which is itself an audit risk.
"""
import uuid

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


class ComplianceAgent(BaseAgent):
    name = "compliance_agent"

    def run(self, state: SentinelState) -> SentinelState:
        self._trace(state, "Running compliance gap scan")
        findings: list[AgentFinding] = []

        findings.extend(self._reclassify_overdue_inspections_as_compliance_gaps())
        findings.extend(self._detect_unmapped_procedures())

        state["findings"] = [f.model_dump() for f in findings]
        self._trace(state, f"Compliance scan complete — {len(findings)} finding(s)")
        return state

    def _reclassify_overdue_inspections_as_compliance_gaps(self) -> list[AgentFinding]:
        """
        Overdue inspections are, by regulatory framing, compliance gaps —
        not just operational risk. Pull the same graph signal the
        contradiction agent uses, but frame and evidence it as an audit
        finding (what a compliance officer needs to see) rather than a
        maintenance alert.
        """
        rows = graph_service.find_procedure_practice_drift()
        findings = []
        for row in rows:
            required_days = row.get("required_interval_days")
            if not required_days:
                continue
            findings.append(
                AgentFinding(
                    finding_id=str(uuid.uuid4()),
                    finding_type=FindingType.COMPLIANCE_GAP,
                    title=f"Compliance exposure: {row['equipment_tag']} inspection cadence",
                    description=(
                        f"Governing procedure '{row['procedure_title']}' mandates a "
                        f"{required_days}-day inspection cadence for {row['equipment_tag']}. "
                        "Current work-order records do not demonstrate adherence, which "
                        "constitutes an audit-ready compliance exposure under standard "
                        "OISD/Factory Act-style inspection cadence requirements."
                    ),
                    severity=SeverityLevel.HIGH,
                    confidence=0.85,
                    evidence=[
                        EvidenceCitation(
                            document_id=row["procedure_document_id"],
                            document_name=row["procedure_title"],
                            document_type=DocumentType.SOP,
                            excerpt=f"Mandated interval: {required_days} days",
                            location="procedure record",
                        )
                    ],
                    affected_equipment_ids=[row["equipment_id"]],
                    reasoning_trace=[
                        "Reused procedure-practice drift signal from knowledge graph",
                        "Reframed as regulatory compliance exposure per inspection-cadence framing",
                    ],
                    recommended_action=(
                        "Generate a corrective action record now, before the next scheduled audit, "
                        "documenting either the inspection or a justified deviation approval."
                    ),
                )
            )
        return findings

    def _detect_unmapped_procedures(self) -> list[AgentFinding]:
        """
        Procedures with no COMPLIES_WITH edge to any regulatory clause are
        an audit-readiness gap: when an inspector asks "which regulation
        does this SOP satisfy," there's no documented answer.
        """
        query = """
        MATCH (p:Procedure)
        WHERE NOT (p)-[:COMPLIES_WITH]->(:RegulatoryClause)
        RETURN p.id AS procedure_id, p.title AS title, p.document_id AS document_id
        """
        try:
            rows = graph_service._read(query, {})
        except Exception as exc:
            logger.warning(f"Unmapped-procedure check failed: {exc}")
            return []

        findings = []
        for row in rows:
            findings.append(
                AgentFinding(
                    finding_id=str(uuid.uuid4()),
                    finding_type=FindingType.COMPLIANCE_GAP,
                    title=f"Undocumented regulatory mapping: {row['title']}",
                    description=(
                        f"Procedure '{row['title']}' has no recorded link to a regulatory clause "
                        "(OISD / Factory Act / DGMS / PESO). This does not necessarily mean the "
                        "procedure is non-compliant, but it means compliance posture cannot be "
                        "demonstrated to an auditor without manual lookup."
                    ),
                    severity=SeverityLevel.MEDIUM,
                    confidence=0.7,
                    evidence=[
                        EvidenceCitation(
                            document_id=row["document_id"],
                            document_name=row["title"],
                            document_type=DocumentType.SOP,
                            excerpt="No COMPLIES_WITH relationship found in knowledge graph",
                            location="graph query",
                        )
                    ],
                    reasoning_trace=[
                        f"Queried all Procedure nodes lacking COMPLIES_WITH edges",
                        f"'{row['title']}' has zero regulatory clause links",
                    ],
                    recommended_action=(
                        "Assign a compliance owner to map this procedure to its governing "
                        "regulatory clause(s) and record the link in the knowledge graph."
                    ),
                )
            )
        return findings


compliance_agent = ComplianceAgent()
