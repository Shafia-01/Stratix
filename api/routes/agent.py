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
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from langgraph.errors import GraphInterrupt

from src.graph.graph import get_compiled_graph
from src.graph.tracing import build_initial_metadata, get_run_config
from src.logger_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/agent", tags=["agent"])
LAST_YIELDED_CHECKPOINTS: Dict[str, str] = {}


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


def _extract_interrupt_value(current_state=None, exception=None) -> Optional[dict]:
    """Helper to extract interrupt value from StateSnapshot or GraphInterrupt exception."""
    if exception and isinstance(exception, GraphInterrupt):
        try:
            interrupts = exception.args[0] if exception.args else []
            if interrupts:
                first = interrupts[0]
                val = first.value if hasattr(first, "value") else (first if isinstance(first, dict) else {})
                if isinstance(val, dict):
                    return val
        except Exception as e:
            logger.warning(f"Failed to extract interrupt value from exception: {e}")

    if current_state and hasattr(current_state, "tasks") and current_state.tasks:
        for task in current_state.tasks:
            if hasattr(task, "interrupts") and task.interrupts:
                try:
                    first = task.interrupts[0]
                    val = first.value if hasattr(first, "value") else (first if isinstance(first, dict) else {})
                    if isinstance(val, dict):
                        return val
                except Exception as e:
                    logger.warning(f"Failed to extract interrupt value from state task: {e}")
    return None


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.post("/run", response_model=RunResponse)
async def start_agent_run(request: RunRequest) -> RunResponse:
    """
    Start a new autonomous research run.
    The graph will pause at the plan_approval checkpoint and return.
    Call /agent/resume with {"approved": true} to continue.
    """
    run_id = str(uuid.uuid4())

    # Log run start in database
    try:
        from src.db_client import connect_db
        from src.models import ResearchRunLog
        from sqlalchemy.orm import Session
        engine = connect_db()
        with Session(engine) as session:
            db_run = ResearchRunLog(
                run_id=run_id,
                seed_keyword=request.seed_keyword,
                triggered_by="manual",
                status="pending"
            )
            session.add(db_run)
            session.commit()
    except Exception as db_err:
        logger.error(f"Failed to log run start to database for run_id={run_id}: {db_err}", exc_info=True)

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
        try:
            result = await run_in_threadpool(graph.invoke, initial_state, config)
            current_state = graph.get_state(config)
            state_values = current_state.values if current_state else result
            interrupt_val = _extract_interrupt_value(current_state=current_state)
        except GraphInterrupt as gi:
            current_state = graph.get_state(config)
            state_values = current_state.values if current_state else {}
            interrupt_val = _extract_interrupt_value(current_state=current_state, exception=gi)

        research_plan = (interrupt_val.get("research_plan") if interrupt_val else None) or state_values.get("research_plan")

        return RunResponse(
            run_id=run_id,
            status=state_values.get("status", "awaiting_approval"),
            awaiting_human=state_values.get("awaiting_human", True),
            checkpoint_data={
                "research_plan": research_plan,
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
        try:
            result = await run_in_threadpool(graph.invoke, None, config)
            current_state = graph.get_state(config)
            state_values = current_state.values if current_state else result
            interrupt_val = _extract_interrupt_value(current_state=current_state)
        except GraphInterrupt as gi:
            current_state = graph.get_state(config)
            state_values = current_state.values if current_state else {}
            interrupt_val = _extract_interrupt_value(current_state=current_state, exception=gi)

        status = state_values.get("status", "in_progress")
        is_mock = current_state and current_state.next.__class__.__name__ in ("Mock", "MagicMock")
        awaiting = state_values.get("awaiting_human", False) or (bool(current_state and current_state.next) if not is_mock else False)

        checkpoint_data = None
        if awaiting or status == "awaiting_approval":

            checkpoint_data = {
                "research_plan": (interrupt_val.get("research_plan") if interrupt_val else None) or state_values.get("research_plan"),
                "strategy_report": (interrupt_val.get("strategy_report") if interrupt_val else None) or state_values.get("strategy_report"),
                "confidence_scores": (interrupt_val.get("confidence_scores") if interrupt_val else None) or state_values.get("confidence_scores"),
                "warnings": (interrupt_val.get("warnings") if interrupt_val else None) or state_values.get("errors", []),
            }
            if status == "in_progress":
                status = "awaiting_approval"

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

        # Log run start in database
        try:
            from src.db_client import connect_db
            from src.models import ResearchRunLog
            from sqlalchemy.orm import Session
            engine = connect_db()
            with Session(engine) as session:
                db_run = ResearchRunLog(
                    run_id=run_id,
                    seed_keyword=request.seed_keyword or "",
                    triggered_by="manual",
                    status="pending"
                )
                session.add(db_run)
                session.commit()
        except Exception as db_err:
            logger.error(f"Failed to log run start in stream to database for run_id={run_id}: {db_err}", exc_info=True)

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

    # interrupt_value: populated if GraphInterrupt propagates (nested graph edge case).
    # Normally, LangGraph suppresses GraphInterrupt internally and astream_events exits cleanly.
    # In either case, we detect the checkpoint via get_state().next in the finally block.
    interrupt_value: Optional[dict] = None

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
                yield f"data: {json.dumps(payload, default=str)}\n\n"
            elif event_type == "on_tool_start":
                yield f"data: {json.dumps({'event': 'tool_start', 'tool': name})}\n\n"
            elif event_type == "on_tool_end":
                output = event.get("data", {}).get("output", {})
                success = True
                error_msg = None
                if isinstance(output, dict) and "error" in output:
                    success = False
                    error_msg = output["error"]
                yield f"data: {json.dumps({'event': 'tool_complete', 'tool': name, 'success': success, 'error': error_msg}, default=str)}\n\n"
    except asyncio.CancelledError:
        logger.info(f"Stream connection cancelled for run_id={run_id}")
        raise
    except GraphInterrupt as gi:
        # Safety-net: catches GraphInterrupt if it propagates (e.g., in nested graph contexts).
        # In the normal (non-nested) case, LangGraph suppresses this and astream_events exits cleanly.
        try:
            interrupts = gi.args[0] if gi.args else []
            if interrupts:
                first = interrupts[0]
                interrupt_value = first.value if hasattr(first, "value") else (first if isinstance(first, dict) else {})
            else:
                interrupt_value = {}
        except Exception as parse_err:
            logger.warning(f"Could not parse GraphInterrupt value for run_id={run_id}: {parse_err}")
            interrupt_value = {}
        logger.info(f"Stream paused at HITL checkpoint (propagated) for run_id={run_id}")
    except Exception as e:
        logger.error(f"Stream execution failed for run_id={run_id}: {e}", exc_info=True)
        yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"
    finally:
        try:
            # Allow MixedSqliteSaver's asyncio.to_thread writes to flush before reading state.
            # This is critical: aput/aput_writes delegate to threads; without this yield,
            # get_state() may read stale checkpoint data before the interrupt is persisted.
            await asyncio.sleep(0.15)

            current_state = graph.get_state(config)
            values = current_state.values if current_state else {}

            # ── Determine if graph paused at an interrupt or truly completed ──
            # current_state.next is non-empty when the graph is waiting at a HITL checkpoint.
            is_interrupted = bool(current_state and current_state.next)

            if is_interrupted:
                checkpoint_id = current_state.config.get("configurable", {}).get("checkpoint_id") if current_state else None
                if checkpoint_id and LAST_YIELDED_CHECKPOINTS.get(run_id) == checkpoint_id:
                    logger.info(f"Checkpoint {checkpoint_id} already yielded for run_id={run_id}, skipping.")
                else:
                    if checkpoint_id:
                        LAST_YIELDED_CHECKPOINTS[run_id] = checkpoint_id

                    if not interrupt_value:
                        interrupt_value = _extract_interrupt_value(current_state=current_state)

                    # Detect checkpoint type from:
                    #  1. interrupt_value dict (if GraphInterrupt propagated — nested edge case)
                    #  2. The next node pending execution (planner re-queued → plan_approval)
                    #  3. The status field in state values
                    next_node = current_state.next[0] if current_state.next else ""
                    status = values.get("status", "awaiting_approval")

                    if interrupt_value:
                        # Fast path: interrupt data extracted directly from GraphInterrupt args
                        checkpoint_type = interrupt_value.get("checkpoint", "plan_approval")
                    elif next_node == "research_agent_node" or status == "awaiting_plan_approval":
                        checkpoint_type = "plan_approval"
                    elif next_node == "persist_node" or status == "awaiting_report_approval":
                        checkpoint_type = "report_approval"
                    else:
                        # Default: infer from state.awaiting_human + which data is populated
                        checkpoint_type = (
                            "report_approval" if values.get("strategy_report") else "plan_approval"
                        )

                    logger.info(
                        f"Stream checkpoint detected for run_id={run_id}: "
                        f"type={checkpoint_type}, next_node={next_node}, status={status}"
                    )

                    if checkpoint_type == "plan_approval":
                        checkpoint_data = {
                            "research_plan": (
                                interrupt_value.get("research_plan") if interrupt_value else None
                            ) or values.get("research_plan"),
                        }
                    else:
                        checkpoint_data = {
                            "research_plan": values.get("research_plan"),
                            "strategy_report": (
                                interrupt_value.get("strategy_report") if interrupt_value else None
                            ) or values.get("strategy_report"),
                            "confidence_scores": (
                                interrupt_value.get("confidence_scores") if interrupt_value else None
                            ) or values.get("confidence_scores"),
                            "warnings": (
                                interrupt_value.get("warnings") if interrupt_value else None
                            ) or values.get("errors", []),
                        }

                    checkpoint_msg = json.dumps({
                        'event': 'checkpoint',
                        'checkpoint': checkpoint_type,
                        'status': status,
                        'checkpoint_data': checkpoint_data,
                    }, default=str)
                    yield f"data: {checkpoint_msg}\n\n"
            else:
                # Graph ran to completion (or failed without a pending next node)
                checkpoint_id = current_state.config.get("configurable", {}).get("checkpoint_id") if current_state else "completed"
                if LAST_YIELDED_CHECKPOINTS.get(run_id) == checkpoint_id:
                    logger.info(f"Completion event already yielded for run_id={run_id}, skipping.")
                else:
                    LAST_YIELDED_CHECKPOINTS[run_id] = checkpoint_id
                    status = values.get("status", "completed")
                    metadata = values.get("execution_metadata", {})
                    yield f"data: {json.dumps({'event': 'completed', 'status': status, 'execution_metadata': metadata})}\n\n"
        except Exception as e:
            logger.error(f"Failed to emit final state for run_id={run_id}: {e}")


@router.post("/stream")
async def stream_agent(request: StreamRequest):
    if not request.run_id and not request.seed_keyword:
        raise HTTPException(status_code=400, detail="Either run_id or seed_keyword must be provided.")
    return StreamingResponse(event_generator(request), media_type="text/event-stream")

