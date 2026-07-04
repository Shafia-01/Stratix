"""
FastAPI routes for the Keylytics LangGraph research pipeline.

POST /agent/run     — Start a new research run (returns run_id + initial state)
POST /agent/resume  — Resume a paused run with human feedback
GET  /agent/status/{run_id} — Poll current state of a run
"""
import uuid
import json
import asyncio
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
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
    # Use a minimal config with thread_id for resume — no need for full run config
    config = {"configurable": {"thread_id": request.run_id}}

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


class StreamRequest(BaseModel):
    seed_keyword: Optional[str] = Field(None, description="Seed keyword to research")
    user_goal: Optional[str] = Field(None, description="Optional free-text goal")
    run_id: Optional[str] = Field(None, description="Run ID to resume")
    human_feedback: Optional[Dict[str, Any]] = Field(None, description="Human feedback for resume")


async def event_generator(request: StreamRequest):
    graph = get_compiled_graph()
    if request.run_id:
        run_id = request.run_id
        config = {"configurable": {"thread_id": run_id}}
        update_data = {"awaiting_human": False}
        if request.human_feedback:
            update_data["human_feedback"] = request.human_feedback
        graph.update_state(config, update_data)
        initial_state = None
    else:
        run_id = str(uuid.uuid4())
        config = get_run_config(request.seed_keyword or "", run_id)
        initial_state = {
            "seed_keyword": request.seed_keyword or "",
            "status": "pending",
            "awaiting_human": False,
            "messages": [],
            "errors": [],
            "execution_metadata": build_initial_metadata(run_id),
            "human_feedback": None,
        }

    yield f"data: {json.dumps({'event': 'run_started', 'run_id': run_id})}\n\n"

    try:
        async for event in graph.astream_events(initial_state, config, version="v2"):
            event_type = event.get("event")
            name = event.get("name")
            metadata = event.get("metadata", {})
            node_name = metadata.get("langgraph_node")

            if event_type == "on_chain_start" and node_name:
                yield f"data: {json.dumps({'event': 'node_start', 'node': node_name})}\n\n"
            elif event_type == "on_chain_end" and node_name:
                output = event.get("data", {}).get("output", {})
                payload = {'event': 'node_complete', 'node': node_name}
                if isinstance(output, dict):
                    if "confidence_scores" in output and output["confidence_scores"]:
                        payload["confidence_scores"] = output["confidence_scores"]
                    if "critic_feedback" in output and output["critic_feedback"]:
                        payload["critic_feedback"] = output["critic_feedback"]
                    if "errors" in output and output["errors"]:
                        payload["errors"] = output["errors"]
                yield f"data: {json.dumps(payload)}\n\n"
            elif event_type == "on_tool_start":
                yield f"data: {json.dumps({'event': 'tool_start', 'tool': name})}\n\n"
            elif event_type == "on_tool_end":
                output = event.get("data", {}).get("output", {})
                success = True
                error_msg = None
                if isinstance(output, dict) and "error" in output:
                    success = False
                    error_msg = output["error"]
                yield f"data: {json.dumps({'event': 'tool_complete', 'tool': name, 'success': success, 'error': error_msg})}\n\n"
    except asyncio.CancelledError:
        logger.info(f"Stream connection cancelled for run_id={run_id}")
        raise
    except Exception as e:
        logger.error(f"Stream execution failed for run_id={run_id}: {e}", exc_info=True)
        yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"
    finally:
        try:
            current_state = graph.get_state(config)
            if current_state and current_state.next:
                next_node = current_state.next[0]
                values = current_state.values
                status = values.get("status")

                if next_node == "research_agent_node" or status == "awaiting_plan_approval":
                    checkpoint_type = "plan_approval"
                    checkpoint_data = {
                        "research_plan": values.get("research_plan"),
                    }
                else:
                    checkpoint_type = "report_approval"
                    checkpoint_data = {
                        "research_plan": values.get("research_plan"),
                        "strategy_report": values.get("strategy_report"),
                        "confidence_scores": values.get("confidence_scores"),
                        "warnings": values.get("errors", []),
                    }
                yield f"data: {json.dumps({
                    'event': 'checkpoint',
                    'checkpoint': checkpoint_type,
                    'status': status,
                    'checkpoint_data': checkpoint_data
                })}\n\n"
            else:
                current_state = graph.get_state(config)
                values = current_state.values if current_state else {}
                status = values.get("status", "completed")
                yield f"data: {json.dumps({'event': 'completed', 'status': status})}\n\n"
        except Exception as e:
            logger.error(f"Failed to fetch final state for run_id={run_id}: {e}")


@router.post("/stream")
async def stream_agent(request: StreamRequest):
    if not request.run_id and not request.seed_keyword:
        raise HTTPException(status_code=400, detail="Either run_id or seed_keyword must be provided.")
    return StreamingResponse(event_generator(request), media_type="text/event-stream")

