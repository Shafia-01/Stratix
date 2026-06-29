"""
GET /timeline/{run_id} — Reconstruct agent execution timeline from LangGraph checkpoint history.
"""
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException
from src.schemas import ExecutionTimeline, TimelineEvent
from src.graph.graph import get_compiled_graph
from src.logger_config import get_logger
from datetime import datetime, timezone

logger = get_logger(__name__)
router = APIRouter(prefix="/timeline", tags=["Timeline"])

@router.get("/{run_id}", response_model=ExecutionTimeline)
async def get_execution_timeline(run_id: str) -> ExecutionTimeline:
    """
    Reconstruct the agent execution timeline from LangGraph checkpoint state history.
    Iterates through all checkpointed states for the run and extracts node transitions,
    tool call counts, HITL interrupts, and confidence score progression.
    """
    try:
        graph = get_compiled_graph()
        config = {"configurable": {"thread_id": run_id}}

        # Get current state
        current_state = graph.get_state(config)
        if not current_state or not current_state.values:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

        state_vals = current_state.values

        # Get full state history
        history = list(graph.get_state_history(config))

        events: List[TimelineEvent] = []
        seen_nodes = set()

        # Walk history in chronological order (history is newest-first)
        for checkpoint in reversed(history):
            checkpoint_vals = checkpoint.values if hasattr(checkpoint, 'values') else {}
            next_node = None
            if hasattr(checkpoint, 'next') and checkpoint.next:
                next_node = checkpoint.next[0] if checkpoint.next else None

            if next_node and next_node not in seen_nodes:
                seen_nodes.add(next_node)
                event_type = "node_start"
                if checkpoint_vals.get("awaiting_human"):
                    event_type = "hitl_interrupt"

                metadata: Dict[str, Any] = {}

                if next_node == "research_agent_node":
                    tool_counts = (checkpoint_vals.get("execution_metadata") or {}).get("tool_call_counts", {})
                    metadata["tool_counts"] = tool_counts

                if next_node == "aggregator_node":
                    metadata["confidence_scores"] = checkpoint_vals.get("confidence_scores", {})

                if next_node == "critic_node":
                    metadata["critic_feedback"] = checkpoint_vals.get("critic_feedback", {})

                if event_type == "hitl_interrupt":
                    if checkpoint_vals.get("research_plan") and "strategy_report" not in checkpoint_vals:
                        metadata["checkpoint"] = "plan_approval"
                    else:
                        metadata["checkpoint"] = "report_approval"

                events.append(TimelineEvent(
                    event_type=event_type,
                    node_name=next_node,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    metadata=metadata,
                ))

        # Tool call events from final execution_metadata
        tool_counts = (state_vals.get("execution_metadata") or {}).get("tool_call_counts", {})
        for tool_name, count in tool_counts.items():
            events.append(TimelineEvent(
                event_type="tool_call",
                node_name="research_agent_node",
                timestamp=datetime.now(timezone.utc).isoformat(),
                metadata={"tool_name": tool_name, "call_count": count, "success": True},
            ))

        # Error events
        for error in (state_vals.get("errors") or []):
            events.append(TimelineEvent(
                event_type="error",
                node_name="unknown",
                timestamp=datetime.now(timezone.utc).isoformat(),
                metadata={"error_message": error},
            ))

        # Compute eval scores from DB
        eval_scores: Dict[str, float] = {}
        try:
            from src.db_client import connect_db
            from src.models import EvalResultModel
            from sqlalchemy.orm import Session
            engine = connect_db()
            with Session(engine) as session:
                evals = session.query(EvalResultModel).filter(EvalResultModel.run_id == run_id).all()
                eval_scores = {e.eval_type: e.score for e in evals}
        except Exception:
            pass

        critic_feedback = state_vals.get("critic_feedback") or {}

        return ExecutionTimeline(
            run_id=run_id,
            seed_keyword=state_vals.get("seed_keyword", ""),
            status=state_vals.get("status", "unknown"),
            events=events,
            confidence_scores=state_vals.get("confidence_scores") or {},
            critic_verdict=critic_feedback.get("overall_verdict"),
            eval_scores=eval_scores,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_execution_timeline failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
