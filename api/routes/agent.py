"""
FastAPI routes for the Keylytics LangGraph research pipeline.

POST /agent/run     — Start a new research run (returns run_id + initial state)
POST /agent/resume  — Resume a paused run with human feedback
GET  /agent/status/{run_id} — Poll current state of a run
"""
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.graph.graph import get_compiled_graph
from src.graph.tracing import build_initial_metadata, get_run_config
from src.logger_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/agent", tags=["agent"])


# ── Request / Response models ──────────────────────────────────────────────

class RunRequest(BaseModel):
    seed_keyword: str = Field(..., description="Seed keyword to research")
    user_goal: Optional[str] = Field(
        None, description="Optional free-text goal to guide the planner"
    )


class ResumeRequest(BaseModel):
    run_id: str = Field(..., description="Run ID returned by /agent/run")
    human_feedback: Dict[str, Any] = Field(
        ...,
        description=(
            "Human feedback dict. Examples: "
            '{"approved": true} | '
            '{"approved": true, "edited_plan": {...}} | '
            '{"regenerate": true, "notes": "Focus on transactional keywords"}'
        ),
    )


class RunResponse(BaseModel):
    run_id: str
    status: str
    awaiting_human: bool
    checkpoint_data: Optional[Dict[str, Any]] = None
    message: str


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.post("/run", response_model=RunResponse)
async def start_agent_run(request: RunRequest) -> RunResponse:
    """
    Start a new autonomous research run.
    The graph will pause at the plan_approval checkpoint and return.
    Call /agent/resume with {"approved": true} to continue.
    """
    run_id = str(uuid.uuid4())
    graph = get_compiled_graph()
    config = get_run_config(request.seed_keyword, run_id)

    initial_state = {
        "seed_keyword": request.seed_keyword,
        "status": "pending",
        "awaiting_human": False,
        "messages": [],
        "errors": [],
        "execution_metadata": build_initial_metadata(run_id),
        "human_feedback": None,
    }

    try:
        result = graph.invoke(initial_state, config)
        # Graph will have interrupted at plan_approval checkpoint
        current_state = graph.get_state(config)
        interrupted_values = current_state.values if current_state else result

        return RunResponse(
            run_id=run_id,
            status=interrupted_values.get("status", "awaiting_approval"),
            awaiting_human=interrupted_values.get("awaiting_human", True),
            checkpoint_data={
                "research_plan": interrupted_values.get("research_plan"),
            },
            message=(
                "Research plan generated. "
                "Call POST /agent/resume with your approval to start data collection."
            ),
        )
    except Exception as e:
        logger.error(f"start_agent_run failed for run_id={run_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resume", response_model=RunResponse)
async def resume_agent_run(request: ResumeRequest) -> RunResponse:
    """
    Resume a paused run by providing human feedback.
    The graph will run until the next interrupt or completion.
    """
    graph = get_compiled_graph()
    config = get_run_config("", request.run_id)
    config["configurable"]["thread_id"] = request.run_id

    try:
        # Update state with human feedback
        graph.update_state(
            config,
            {"human_feedback": request.human_feedback, "awaiting_human": False},
        )

        # Resume execution
        result = graph.invoke(None, config)
        current_state = graph.get_state(config)
        state_values = current_state.values if current_state else result

        status = state_values.get("status", "in_progress")
        awaiting = state_values.get("awaiting_human", False)

        checkpoint_data = None
        if status == "awaiting_approval":
            checkpoint_data = {
                "research_plan": state_values.get("research_plan"),
                "strategy_report": state_values.get("strategy_report"),
                "confidence_scores": state_values.get("confidence_scores"),
                "warnings": state_values.get("errors", []),
            }

        message_map = {
            "awaiting_approval": "Checkpoint reached. Review and call /agent/resume again.",
            "completed": "Research complete. Strategy report saved to database.",
            "failed": "Run failed. Check errors field for details.",
            "in_progress": "Run in progress.",
        }

        return RunResponse(
            run_id=request.run_id,
            status=status,
            awaiting_human=awaiting,
            checkpoint_data=checkpoint_data,
            message=message_map.get(status, "Run executing."),
        )
    except Exception as e:
        logger.error(f"resume_agent_run failed for run_id={request.run_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{run_id}", response_model=RunResponse)
async def get_run_status(run_id: str) -> RunResponse:
    """Poll the current status of a research run."""
    graph = get_compiled_graph()
    config = {"configurable": {"thread_id": run_id}}

    try:
        current_state = graph.get_state(config)
        if not current_state:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

        state_values = current_state.values
        return RunResponse(
            run_id=run_id,
            status=state_values.get("status", "unknown"),
            awaiting_human=state_values.get("awaiting_human", False),
            checkpoint_data={
                "execution_metadata": state_values.get("execution_metadata"),
                "errors": state_values.get("errors", []),
                "confidence_scores": state_values.get("confidence_scores"),
            },
            message="Status retrieved successfully.",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_run_status failed for run_id={run_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
