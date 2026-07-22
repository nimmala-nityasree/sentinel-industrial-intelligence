"""
Contradiction & Drift Agent — Sentinel's core differentiating capability.

Implements three proactive discovery patterns explicitly requested by the
problem statement's "Lessons Learned & Failure Intelligence Engine" and
implicit in "Quality & Regulatory Compliance Intelligence":

  1. Procedure-practice drift  — SOP requirement vs. actual maintenance history
  2. Version drift             — superseded procedure vs. stale training records
  3. Silent recurrence         — semantically similar incidents never cross-referenced

Every output is an AgentFinding: cited, confidence-scored, with a reasoning
trace — never a bare alert string.
"""
import uuid
from datetime import date, datetime

from app.agents.base_agent import BaseAgent, SentinelState
from app.config import settings
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

_SIMILARITY_PROMPT_TEMPLATE = """
Compare the symptoms of two industrial incidents and estimate how likely
they represent the SAME underlying failure mode, even if filed under
different equipment tags or wording.

Incident A symptoms: {symptoms_a}
Incident B symptoms: {symptoms_b}

Return JSON only: {{"similarity_score": <float 0.0-1.0>, "rationale": "<one sentence>"}}
"""

_SIMILARITY_THRESHOLD = 0.65


class ContradictionAgent(BaseAgent):
    name = "contradiction_agent"

    def run(self, state: SentinelState) -> SentinelState:
        self._trace(state, "Starting full contradiction & drift scan")
        findings: list[AgentFinding] = []

        findings.extend(self._detect_procedure_practice_drift(state))
        findings.extend(self._detect_version_drift(state))
        findings.extend(self._detect_silent_recurrence(state))

        self._trace(state, f"Scan complete — {len(findings)} findings generated")
        state["findings"] = [f.model_dump() for f in findings]
        return state

    # ------------------------------------------------------------------ #
    # Pattern 1: Procedure-practice drift
    # ------------------------------------------------------------------ #

    def _detect_procedure_practice_drift(self, state: SentinelState) -> list[AgentFinding]:
        rows = graph_service.find_procedure_practice_drift()
        findings = []

        for row in rows:
            last_performed = row.get("last_performed_on")
            required_days = row.get("required_interval_days")
            if not required_days:
                continue

            days_elapsed = self._days_since(last_performed)
            if days_elapsed is None or days_elapsed <= required_days:
                continue  # compliant — no finding

            overdue_ratio = days_elapsed / required_days
            severity = self._severity_from_overdue_ratio(overdue_ratio)
            confidence = round(min(0.65 + 0.05 * min(overdue_ratio, 5), 0.97), 2)

            finding = AgentFinding(
                finding_id=str(uuid.uuid4()),
                finding_type=FindingType.PROCEDURE_PRACTICE_DRIFT,
                title=f"Overdue inspection: {row['equipment_tag']} ({row['equipment_name']})",
                description=(
                    f"Procedure '{row['procedure_title']}' requires inspection every "
                    f"{required_days} days. The last recorded work order on "
                    f"{row['equipment_tag']} was {days_elapsed} days ago "
                    f"({last_performed or 'no work order on record'}) — "
                    f"{overdue_ratio:.1f}x the required interval."
                ),
                severity=severity,
                confidence=confidence,
                evidence=[
                    EvidenceCitation(
                        document_id=row["procedure_document_id"],
                        document_name=row["procedure_title"],
                        document_type=DocumentType.SOP,
                        excerpt=f"Required inspection interval: {required_days} days",
                        location="procedure record",
                    ),
                    EvidenceCitation(
                        document_id=row.get("wo_document_id") or "none",
                        document_name=f"Work order {row.get('work_order_id', 'N/A')}",
                        document_type=DocumentType.WORK_ORDER,
                        excerpt=f"Last performed on: {last_performed or 'no record found'}",
                        location="work order log",
                    ),
                ],
                affected_equipment_ids=[row["equipment_id"]],
                reasoning_trace=[
                    f"Matched Procedure({row['procedure_title']}) -[GOVERNS]-> Equipment({row['equipment_tag']})",
                    "Matched latest WorkOrder -[PERFORMED_ON]-> same Equipment",
                    f"Computed elapsed days ({days_elapsed}) vs required interval ({required_days})",
                    f"Elapsed exceeds requirement by {overdue_ratio:.1f}x -> flagged",
                ],
                recommended_action=(
                    f"Schedule an inspection of {row['equipment_tag']} immediately and verify "
                    "whether an undocumented inspection occurred outside the logged work order system."
                ),
            )
            findings.append(finding)

        self._trace(state, f"Procedure-practice drift: {len(findings)} finding(s)")
        return findings

    # ------------------------------------------------------------------ #
    # Pattern 2: Version drift
    # ------------------------------------------------------------------ #

    def _detect_version_drift(self, state: SentinelState) -> list[AgentFinding]:
        rows = graph_service.find_version_drift()
        findings = []

        for row in rows:
            untrained = row.get("untrained_personnel", [])
            if not untrained:
                continue

            finding = AgentFinding(
                finding_id=str(uuid.uuid4()),
                finding_type=FindingType.VERSION_DRIFT,
                title=f"Training gap: '{row['title']}' updated to {row['new_version']}",
                description=(
                    f"Procedure '{row['title']}' was revised from {row['old_version']} to "
                    f"{row['new_version']}, but {len(untrained)} personnel record(s) show training "
                    f"only on the superseded version: {', '.join(untrained)}."
                ),
                severity=SeverityLevel.HIGH,
                confidence=0.9,
                evidence=[
                    EvidenceCitation(
                        document_id=row["old_document_id"],
                        document_name=f"{row['title']} ({row['old_version']})",
                        document_type=DocumentType.SOP,
                        excerpt=f"Superseded version: {row['old_version']}",
                        location="procedure record",
                    ),
                    EvidenceCitation(
                        document_id=row["new_document_id"],
                        document_name=f"{row['title']} ({row['new_version']})",
                        document_type=DocumentType.SOP,
                        excerpt=f"Current version: {row['new_version']}",
                        location="procedure record",
                    ),
                ],
                reasoning_trace=[
                    f"Matched Procedure({row['new_version']}) -[SUPERSEDES]-> Procedure({row['old_version']})",
                    "Matched Personnel -[TRAINED_ON]-> old version with no edge to new version",
                    f"{len(untrained)} personnel record(s) affected",
                ],
                recommended_action=(
                    f"Schedule retraining on {row['title']} {row['new_version']} for: "
                    f"{', '.join(untrained)} before their next shift on governed equipment."
                ),
            )
            findings.append(finding)

        self._trace(state, f"Version drift: {len(findings)} finding(s)")
        return findings

    # ------------------------------------------------------------------ #
    # Pattern 3: Silent recurrence (Lessons Engine)
    # ------------------------------------------------------------------ #

    def _detect_silent_recurrence(self, state: SentinelState) -> list[AgentFinding]:
        candidates = graph_service.find_silent_recurrence_candidates(
            lookback_days=settings.drift_detection_lookback_days
        )
        findings = []

        for c in candidates:
            symptoms_a, symptoms_b = c.get("symptoms_a") or [], c.get("symptoms_b") or []
            if not symptoms_a or not symptoms_b:
                continue

            try:
                result = llm_service.generate_json(
                    _SIMILARITY_PROMPT_TEMPLATE.format(symptoms_a=symptoms_a, symptoms_b=symptoms_b)
                )
            except Exception as exc:
                logger.warning(f"Similarity scoring failed for incident pair: {exc}")
                continue

            score = float(result.get("similarity_score", 0.0))
            if score < _SIMILARITY_THRESHOLD:
                continue

            graph_service.link_similar_incidents(c["incident_a_id"], c["incident_b_id"], score)

            finding = AgentFinding(
                finding_id=str(uuid.uuid4()),
                finding_type=FindingType.SILENT_RECURRENCE,
                title=f"Recurring failure pattern: '{c['incident_a_title']}' ~ '{c['incident_b_title']}'",
                description=(
                    f"Incident on {c['equipment_a_tag']} ('{c['incident_a_title']}') shares an "
                    f"estimated {score:.0%} symptom similarity with a separate incident on "
                    f"{c['equipment_b_tag']} ('{c['incident_b_title']}'), but the two were never "
                    f"cross-referenced. {result.get('rationale', '')}"
                ),
                severity=SeverityLevel.MEDIUM if score < 0.8 else SeverityLevel.HIGH,
                confidence=round(score, 2),
                evidence=[
                    EvidenceCitation(
                        document_id=c["doc_a"],
                        document_name=c["incident_a_title"],
                        document_type=DocumentType.NEAR_MISS_REPORT,
                        excerpt=f"Symptoms: {', '.join(symptoms_a)}",
                        location="incident record",
                    ),
                    EvidenceCitation(
                        document_id=c["doc_b"],
                        document_name=c["incident_b_title"],
                        document_type=DocumentType.NEAR_MISS_REPORT,
                        excerpt=f"Symptoms: {', '.join(symptoms_b)}",
                        location="incident record",
                    ),
                ],
                reasoning_trace=[
                    "Selected candidate incident pair within lookback window via graph query",
                    f"LLM symptom-similarity score: {score:.2f} (threshold {_SIMILARITY_THRESHOLD})",
                    "Linked as SIMILAR_FAILURE_MODE in knowledge graph",
                ],
                recommended_action=(
                    "Review both incident reports jointly for a shared root cause and consider "
                    "extending the corrective action from one to both equipment items."
                ),
            )
            findings.append(finding)

        self._trace(state, f"Silent recurrence: {len(findings)} finding(s)")
        return findings

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _days_since(iso_date_str: str | None) -> int | None:
        if not iso_date_str:
            return None
        try:
            then = datetime.fromisoformat(iso_date_str).date()
        except ValueError:
            return None
        return (date.today() - then).days

    @staticmethod
    def _severity_from_overdue_ratio(ratio: float) -> SeverityLevel:
        if ratio >= 3:
            return SeverityLevel.CRITICAL
        if ratio >= 2:
            return SeverityLevel.HIGH
        if ratio >= 1.3:
            return SeverityLevel.MEDIUM
        return SeverityLevel.LOW


contradiction_agent = ContradictionAgent()
