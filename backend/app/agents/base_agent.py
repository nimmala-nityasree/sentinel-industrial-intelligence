"""
Agent base class and shared LangGraph state contract.

Every Sentinel agent (ingestion, knowledge graph, RAG copilot, contradiction,
maintenance/RCA, compliance) inherits from BaseAgent and implements `run()`.
This gives us:
  - A consistent way to append to `reasoning_trace`, which is what makes
    every finding explainable (the trace IS the audit log).
  - A single point (`SentinelState`) LangGraph nodes read/write, so the
    orchestrator graph in orchestrator.py stays declarative.
"""
from abc import ABC, abstractmethod
from typing import Any, TypedDict

from app.core.logging_config import logger


class SentinelState(TypedDict, total=False):
    """
    Shared state object passed between LangGraph nodes.

    Only the keys relevant to the active workflow are populated per run —
    e.g. a copilot query run populates `question`/`answer`, while a scan
    run populates `findings`.
    """

    # Copilot query workflow
    question: str
    equipment_filter: str | None
    top_k: int
    answer: str
    confidence: float
    evidence: list[dict]
    escalate_to_human: bool

    # Proactive scan workflow (contradiction / compliance / maintenance)
    findings: list[dict]

    # Shared
    reasoning_trace: list[str]
    error: str | None


class BaseAgent(ABC):
    """Abstract base class all Sentinel agents implement."""

    name: str = "base_agent"

    @abstractmethod
    def run(self, state: SentinelState) -> SentinelState:
        """Execute the agent's logic against shared state and return the updated state."""
        raise NotImplementedError

    def _trace(self, state: SentinelState, message: str) -> None:
        """Append a human-readable reasoning step to the shared trace and log it."""
        state.setdefault("reasoning_trace", [])
        entry = f"[{self.name}] {message}"
        state["reasoning_trace"].append(entry)
        logger.debug(entry)

    def _safe_get(self, d: dict, key: str, default: Any = None) -> Any:
        return d.get(key, default) if isinstance(d, dict) else default
