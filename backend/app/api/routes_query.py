"""Expert Copilot query API — cited, confidence-scored RAG answering via the LangGraph copilot graph."""
from fastapi import APIRouter, HTTPException

from app.agents.orchestrator import run_copilot_query
from app.core.exceptions import SentinelException
from app.core.logging_config import logger
from app.models.schemas import CopilotQueryRequest, CopilotQueryResponse

router = APIRouter(prefix="/query", tags=["copilot"])


@router.post("/copilot", response_model=CopilotQueryResponse)
def query_copilot(request: CopilotQueryRequest) -> CopilotQueryResponse:
    try:
        result = run_copilot_query(
            question=request.question,
            equipment_filter=request.equipment_filter,
            top_k=request.top_k,
        )
    except SentinelException as exc:
        logger.error(f"Copilot query failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return CopilotQueryResponse(
        answer=result.get("answer", ""),
        confidence=result.get("confidence", 0.0),
        evidence=result.get("evidence", []),
        escalate_to_human=result.get("escalate_to_human", False),
        reasoning_trace=result.get("reasoning_trace", []),
    )
