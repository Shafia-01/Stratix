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
    import asyncio
    from langgraph.checkpoint.sqlite import SqliteSaver
    import os

    class MixedSqliteSaver(SqliteSaver):
        """A SqliteSaver checkpointer that implements the asynchronous interface of BaseCheckpointSaver
        by delegating to its synchronous methods running inside a thread pool. This resolves the async-methods
        unsupported error under astream_events/astream while maintaining synchronous compatibility."""
        
        async def aget_tuple(self, config: dict):
            return await asyncio.to_thread(self.get_tuple, config)

        async def alist(self, config: dict, *, filter: dict = None, before: dict = None, limit: int = None):
            def _get_list():
                return list(self.list(config, filter=filter, before=before, limit=limit))
            items = await asyncio.to_thread(_get_list)
            for item in items:
                yield item

        async def aput(self, config: dict, checkpoint: dict, metadata: dict, new_versions: dict):
            return await asyncio.to_thread(self.put, config, checkpoint, metadata, new_versions)

        async def aput_writes(self, config: dict, writes: list, task_id: str, task_path: str = ''):
            return await asyncio.to_thread(self.put_writes, config, writes, task_id, task_path)

        async def adelete_thread(self, config: dict):
            if hasattr(self, 'delete_thread'):
                return await asyncio.to_thread(self.delete_thread, config)

    DB_PATH = os.getenv("STRATIX_DB_PATH") or os.getenv("KEYLYTICS_DB_PATH", "keylytics.db")
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    checkpointer = MixedSqliteSaver(conn)
    checkpointer.setup()
    graph = builder.compile(checkpointer=checkpointer)
    logger.info("Stratix research graph compiled successfully with MixedSqliteSaver")
    return graph


def get_compiled_graph():
    """Return a singleton compiled graph instance."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph
