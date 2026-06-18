"""
LangSmith tracing utilities for the Keylytics research pipeline.
"""
import os
import uuid
from datetime import datetime, timezone
from src.logger_config import get_logger

logger = get_logger(__name__)


def get_run_id() -> str:
    return str(uuid.uuid4())


def get_run_config(seed_keyword: str, run_id: str) -> dict:
    """
    Build RunnableConfig with LangSmith metadata for a graph run.
    Pass this as the second argument to compiled_graph.invoke(state, config).
    """
    return {
        "recursion_limit": 12,
        "configurable": {"thread_id": run_id},
        "run_name": f"keylytics-research-{seed_keyword[:30]}",
        "tags": ["keylytics", "phase3", "market-intelligence"],
        "metadata": {
            "seed_keyword": seed_keyword,
            "run_id": run_id,
            "version": "phase3",
            "environment": os.getenv("STRATIX_ENV") or os.getenv("KEYLYTICS_ENV", "development"),
        },
    }


def build_initial_metadata(run_id: str) -> dict:
    """Build the initial execution_metadata dict for a new run."""
    return {
        "run_id": run_id,
        "start_ts": datetime.now(timezone.utc).isoformat(),
        "end_ts": None,
        "total_tool_calls": 0,
        "tool_call_counts": {},
        "planner_retries": 0,
        "strategy_retries": 0,
        "langsmith_run_url": None,
    }


def finalise_metadata(metadata: dict) -> dict:
    """Stamp end time and compute total tool calls."""
    metadata = metadata.copy()
    metadata["end_ts"] = datetime.now(timezone.utc).isoformat()
    metadata["total_tool_calls"] = sum(metadata.get("tool_call_counts", {}).values())

    langchain_project = os.getenv("LANGCHAIN_PROJECT", "keylytics-phase3")
    run_id = metadata.get("run_id", "")
    metadata["langsmith_run_url"] = (
        f"https://smith.langchain.com/o/projects/{langchain_project}/runs/{run_id}"
        if run_id else None
    )
    return metadata


def extract_tool_call_counts(messages: list) -> dict:
    """
    Count how many times each tool was called by scanning the message thread.
    Works with LangChain ToolMessage objects.
    """
    counts: dict = {}
    for msg in messages:
        # LangChain ToolMessage has a 'name' attribute
        name = getattr(msg, "name", None)
        if name:
            counts[name] = counts.get(name, 0) + 1
    return counts
