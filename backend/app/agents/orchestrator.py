"""
LangGraph orchestrator.

Two declarative graphs:

1. `copilot_graph`   — single-node graph wrapping the RAG copilot agent.
   Kept as a graph (not a direct function call) so it's trivial to extend
   later with a query-classification node that routes between copilot,
   RCA, and compliance sub-agents based on question intent.

2. `scan_graph`      — runs the contradiction, maintenance/RCA, and
   compliance agents in sequence over the shared knowledge graph and merges
   their findings into one list. This is the "Multi-Agent AI System"
   requirement made literal and inspectable: each node is a distinct agent
   with a distinct responsibility, and the graph structure IS the
   architecture diagram.
"""
from langgraph.graph import END, StateGraph

from app.agents.base_agent import SentinelState
from app.agents.compliance_agent import compliance_agent
from app.agents.contradiction_agent import contradiction_agent
from app.agents.maintenance_rca_agent import maintenance_rca_agent
from app.agents.rag_copilot_agent import rag_copilot_agent
from app.core.logging_config import logger


# ---------------------------------------------------------------------- #
# Copilot graph
# ---------------------------------------------------------------------- #

def _build_copilot_graph():
    graph = StateGraph(SentinelState)
    graph.add_node("rag_copilot", rag_copilot_agent.run)
    graph.set_entry_point("rag_copilot")
    graph.add_edge("rag_copilot", END)
    return graph.compile()


copilot_graph = _build_copilot_graph()


# ---------------------------------------------------------------------- #
# Proactive multi-agent scan graph
# ---------------------------------------------------------------------- #

def _merge_findings_node(state: SentinelState) -> SentinelState:
    """
    Terminal node: each upstream agent overwrote `findings` with its own
    list, so this node's real job is just to confirm the merge point is
    reached and log a summary — kept explicit for readability of the graph.
    """
    count = len(state.get("findings", []))
    logger.info(f"Multi-agent scan merge node reached with {count} accumulated findings")
    return state


def _contradiction_node(state: SentinelState) -> SentinelState:
    result = contradiction_agent.run(state)
    _accumulate(state, result)
    return state


def _maintenance_node(state: SentinelState) -> SentinelState:
    result = maintenance_rca_agent.run(state)
    _accumulate(state, result)
    return state


def _compliance_node(state: SentinelState) -> SentinelState:
    result = compliance_agent.run(state)
    _accumulate(state, result)
    return state


def _accumulate(state: SentinelState, agent_result: SentinelState) -> None:
    """Each agent's run() sets state['findings'] to ITS OWN findings; accumulate across nodes."""
    existing = state.get("_all_findings", [])
    existing.extend(agent_result.get("findings", []))
    state["_all_findings"] = existing
    state["findings"] = existing  # keep 'findings' as the running total for downstream nodes


def _build_scan_graph():
    graph = StateGraph(SentinelState)
    graph.add_node("contradiction_scan", _contradiction_node)
    graph.add_node("maintenance_scan", _maintenance_node)
    graph.add_node("compliance_scan", _compliance_node)
    graph.add_node("merge", _merge_findings_node)

    graph.set_entry_point("contradiction_scan")
    graph.add_edge("contradiction_scan", "maintenance_scan")
    graph.add_edge("maintenance_scan", "compliance_scan")
    graph.add_edge("compliance_scan", "merge")
    graph.add_edge("merge", END)
    return graph.compile()


scan_graph = _build_scan_graph()


def run_copilot_query(question: str, equipment_filter: str | None, top_k: int) -> SentinelState:
    initial_state: SentinelState = {
        "question": question,
        "equipment_filter": equipment_filter,
        "top_k": top_k,
        "reasoning_trace": [],
    }
    return copilot_graph.invoke(initial_state)


def run_full_scan() -> SentinelState:
    initial_state: SentinelState = {"reasoning_trace": [], "_all_findings": []}
    return scan_graph.invoke(initial_state)
