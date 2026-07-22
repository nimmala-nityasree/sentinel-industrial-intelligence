"""
Alerts & proactive intelligence API.

`POST /alerts/scan` runs the full multi-agent LangGraph scan (contradiction
+ maintenance/RCA + compliance) synchronously and returns every finding.
For a hackathon-scale corpus this completes in seconds; in production this
would run on a schedule/webhook and this endpoint would just read the
latest cached results.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.maintenance_rca_agent import maintenance_rca_agent
from app.agents.orchestrator import run_full_scan
from app.core.exceptions import SentinelException
from app.core.logging_config import logger
from app.models.schemas import AgentFinding, AlertsResponse

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("/scan", response_model=AlertsResponse)
def run_scan() -> AlertsResponse:
    """Runs the contradiction, maintenance, and compliance agents in sequence."""
    try:
        result = run_full_scan()
    except SentinelException as exc:
        logger.error(f"Multi-agent scan failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    findings_raw = result.get("findings", [])
    findings = [AgentFinding(**f) for f in findings_raw]
    return AlertsResponse(total_findings=len(findings), findings=findings)


class RCARequest(BaseModel):
    incident_title: str
    incident_description: str
    symptoms: list[str]


@router.post("/rca")
def generate_rca(request: RCARequest) -> dict:
    """On-demand root cause analysis hypothesis for a specific incident."""
    return maintenance_rca_agent.generate_rca(
        incident_title=request.incident_title,
        incident_description=request.incident_description,
        symptoms=request.symptoms,
    )
