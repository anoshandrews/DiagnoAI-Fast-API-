import logging
from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from backend.app.core.config import get_settings
from backend.app.graph.nodes import (
    adaptive_questioner_node,
    emergency_escalation_node,
    handoff_synthesizer_node,
    hydrate_context_node,
    symptom_extractor_node,
    triage_guardrail_node,
)
from backend.app.graph.state import AgentState

logger = logging.getLogger(__name__)


def route_after_triage(state: AgentState) -> Literal["emergency_escalation", "symptom_extractor"]:
    if state.get("intake_stage") == "red_flag":
        return "emergency_escalation"
    return "symptom_extractor"


def route_after_extraction(state: AgentState) -> Literal["handoff_synthesizer", "adaptive_questioner"]:
    if state.get("intake_stage") == "completed":
        return "handoff_synthesizer"
    return "adaptive_questioner"


def build_intake_graph():
    """
    Constructs the stateful LangGraph clinical intake graph.
    """
    builder = StateGraph(AgentState)

    # 1. Register nodes
    builder.add_node("hydrate_context", hydrate_context_node)
    builder.add_node("triage_guardrail", triage_guardrail_node)
    builder.add_node("emergency_escalation", emergency_escalation_node)
    builder.add_node("symptom_extractor", symptom_extractor_node)
    builder.add_node("adaptive_questioner", adaptive_questioner_node)
    builder.add_node("handoff_synthesizer", handoff_synthesizer_node)

    # 2. Wire edges
    builder.add_edge(START, "hydrate_context")
    builder.add_edge("hydrate_context", "triage_guardrail")

    builder.add_conditional_edges(
        "triage_guardrail",
        route_after_triage,
        {
            "emergency_escalation": "emergency_escalation",
            "symptom_extractor": "symptom_extractor",
        },
    )

    builder.add_conditional_edges(
        "symptom_extractor",
        route_after_extraction,
        {
            "handoff_synthesizer": "handoff_synthesizer",
            "adaptive_questioner": "adaptive_questioner",
        },
    )

    builder.add_edge("emergency_escalation", END)
    builder.add_edge("adaptive_questioner", END)
    builder.add_edge("handoff_synthesizer", END)

    # In-memory checkpointer for thread-level state resumption
    checkpointer = MemorySaver()
    compiled_app = builder.compile(checkpointer=checkpointer)
    return compiled_app


# Singleton compiled graph instance
intake_graph = build_intake_graph()
