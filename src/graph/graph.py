"""
Builds and returns the compiled Keylytics LangGraph research pipeline.

Graph topology:
  START
    └─► planner_node
          └─► [INTERRUPT: plan_approval]
                ├─► research_agent_node  (approved)
                │     └─► aggregator_node
                │             └─► strategy_agent_node
                │                   └─► [INTERRUPT: report_approval]
                │                         ├─► persist_node  (approved)
                │                         │     └─► END
                │                         └─► strategy_agent_node  (regenerate, max 1)
                ├─► planner_node  (edited plan, max 2 retries)
                └─► END  (rejected)
"""
from langgraph.graph import StateGraph, START, END

from src.graph.state import AgentState
from src.graph.nodes import (
    planner_node,
    research_agent_node,
    aggregator_node,
    quality_gate_node,
    critic_node,
    strategy_agent_node,
    persist_node,
    route_after_plan,
    route_after_research,
    route_after_quality_gate,
    route_after_critic,
    route_after_strategy,
)
from src.logger_config import get_logger

logger = get_logger(__name__)

_compiled_graph = None


def build_graph():
    """Build and compile the Keylytics research StateGraph."""
    builder = StateGraph(AgentState)

    # ── Nodes ──────────────────────────────────────────────────────────────
    builder.add_node("planner_node", planner_node)
    builder.add_node("research_agent_node", research_agent_node)
    builder.add_node("aggregator_node", aggregator_node)
    builder.add_node("quality_gate_node", quality_gate_node)
    builder.add_node("critic_node", critic_node)
    builder.add_node("strategy_agent_node", strategy_agent_node)
    builder.add_node("persist_node", persist_node)

    # ── Edges ──────────────────────────────────────────────────────────────
    builder.add_edge(START, "planner_node")

    builder.add_conditional_edges(
        "planner_node",
        route_after_plan,
        {
            "research_agent_node": "research_agent_node",
            "planner_node": "planner_node",
            "__end__": END,
        },
    )

    builder.add_conditional_edges(
        "research_agent_node",
        route_after_research,
        {
            "aggregator_node": "aggregator_node",
            "__end__": END,
        },
    )

    builder.add_edge("aggregator_node", "quality_gate_node")

    builder.add_conditional_edges(
        "quality_gate_node",
        route_after_quality_gate,
        {
            "research_agent_node": "research_agent_node",
            "critic_node": "critic_node",
        },
    )

    builder.add_conditional_edges(
        "critic_node",
        route_after_critic,
        {
            "research_agent_node": "research_agent_node",
            "strategy_agent_node": "strategy_agent_node",
        },
    )

    builder.add_conditional_edges(
        "strategy_agent_node",
        route_after_strategy,
        {
            "strategy_agent_node": "strategy_agent_node",
            "persist_node": "persist_node",
        },
    )

    builder.add_edge("persist_node", END)

    # ── Compile with SqliteSaver checkpointer ─────────────────────────────
    import sqlite3
    from langgraph.checkpoint.sqlite import SqliteSaver
    import os
    DB_PATH = os.getenv("KEYLYTICS_DB_PATH", "keylytics.db")
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    checkpointer.setup()
    graph = builder.compile(checkpointer=checkpointer)
    logger.info("Keylytics research graph compiled successfully")
    return graph


def get_compiled_graph():
    """Return a singleton compiled graph instance."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph
