"""
AgentState TypedDict for the Keylytics LangGraph research pipeline.

Wraps the Pydantic models from src/schemas.py as serialisable dicts
so LangGraph's StateGraph can checkpoint and partially update state.
All fields are optional so individual nodes only write what they touch.
"""
from __future__ import annotations
from typing import Annotated, Any, Dict, List, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    # ── Entry ────────────────────────────────────────────────────────────
    seed_keyword: str

    # ── Planning stage ───────────────────────────────────────────────────
    research_plan: Optional[Dict[str, Any]]
    # Serialised ResearchPlan from src/schemas.py

    # ── Research stage ───────────────────────────────────────────────────
    collected_data: Optional[Dict[str, Any]]
    # Keyed by tool name: {"keyword_research": {...}, "serp_analysis": {...}, ...}

    # ── Aggregation stage ────────────────────────────────────────────────
    intelligence_findings: Optional[Dict[str, Any]]
    # Serialised IntelligenceFindings from src/schemas.py

    confidence_scores: Optional[Dict[str, float]]
    # Per-tool quality signals: 0.0–1.0

    # ── Strategy stage ───────────────────────────────────────────────────
    strategy_report: Optional[Dict[str, Any]]
    # Serialised StrategyReport from src/schemas.py

    # ── Human-in-the-Loop ────────────────────────────────────────────────
    human_feedback: Optional[Dict[str, Any]]
    # Keys: approved (bool), edited_plan (dict|None), regenerate (bool),
    #       notes (str|None)
    awaiting_human: bool
    # True when graph is paused at an interrupt checkpoint

    # ── LangChain message thread ─────────────────────────────────────────
    messages: Annotated[List[Any], add_messages]
    # Full ReAct message history; accumulated across nodes

    # ── Execution metadata ───────────────────────────────────────────────
    execution_metadata: Optional[Dict[str, Any]]
    # Keys: run_id, start_ts, end_ts, total_tool_calls,
    #       tool_call_counts {tool_name: int},
    #       planner_retries (int), strategy_retries (int),
    #       langsmith_run_url (str|None)

    status: str
    # pending | in_progress | awaiting_approval | completed | failed

    critic_feedback: Optional[Dict[str, Any]]
    # Keys: issues (List[str]), weak_claims (List[str]), 
    #       data_gaps (List[str]), overall_verdict (str), critic_score (float)
    critic_retries: int  # default 0, max 1

    errors: List[str]
    # Non-fatal errors accumulated across nodes; graph continues unless
    # keyword_research completely fails
