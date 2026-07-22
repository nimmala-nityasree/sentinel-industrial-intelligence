"""
Pydantic schemas shared across the API layer and the agent layer.

Design principle: every AI-generated finding in Sentinel — whether it's a
copilot answer, a contradiction alert, an RCA suggestion, or a compliance
gap — is represented by `EvidenceCitation` + `AgentFinding`. This is what
makes "explainable AI with source citations and confidence" an enforced
data contract instead of a prose promise.
"""
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    SOP = "sop"
    WORK_ORDER = "work_order"
    NEAR_MISS_REPORT = "near_miss_report"
    INCIDENT_REPORT = "incident_report"
    TRAINING_RECORD = "training_record"
    REGULATORY_DOCUMENT = "regulatory_document"
    PID_DRAWING = "pid_drawing"
    OTHER = "other"


class FindingType(str, Enum):
    PROCEDURE_PRACTICE_DRIFT = "procedure_practice_drift"
    VERSION_DRIFT = "version_drift"
    SILENT_RECURRENCE = "silent_recurrence"
    COMPLIANCE_GAP = "compliance_gap"
    MAINTENANCE_RISK = "maintenance_risk"
    ROOT_CAUSE = "root_cause"


class SeverityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EvidenceCitation(BaseModel):
    """A single piece of supporting evidence backing an agent finding or answer."""

    document_id: str
    document_name: str
    document_type: DocumentType
    excerpt: str = Field(..., description="Short, exact excerpt supporting the claim (<= 300 chars)")
    location: str | None = Field(None, description="Page number, line range, or row reference")
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)


class AgentFinding(BaseModel):
    """
    Universal output shape for every proactive discovery Sentinel makes —
    contradictions, compliance gaps, maintenance risks, RCA hypotheses.
    """

    finding_id: str
    finding_type: FindingType
    title: str
    description: str
    severity: SeverityLevel
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence: list[EvidenceCitation]
    affected_equipment_ids: list[str] = Field(default_factory=list)
    reasoning_trace: list[str] = Field(
        default_factory=list,
        description="Ordered list of agent reasoning steps that produced this finding",
    )
    recommended_action: str
    detected_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    document_type: DocumentType
    chunks_indexed: int
    entities_extracted: int
    ocr_used: bool
    message: str


class CopilotQueryRequest(BaseModel):
    question: str = Field(..., min_length=3)
    equipment_filter: str | None = None
    top_k: int = Field(default=5, ge=1, le=20)


class CopilotQueryResponse(BaseModel):
    answer: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence: list[EvidenceCitation]
    escalate_to_human: bool
    reasoning_trace: list[str]


class AlertsResponse(BaseModel):
    total_findings: int
    findings: list[AgentFinding]


class GraphStatsResponse(BaseModel):
    equipment_count: int
    procedure_count: int
    work_order_count: int
    incident_count: int
    personnel_count: int
    relationship_count: int
