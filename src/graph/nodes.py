"""
LangGraph node functions for the Keylytics research pipeline.

Node inventory:
  planner_node         — LLM call; structured output → ResearchPlan
  research_agent_node  — ReAct agent; executes all 6 tools
  aggregator_node      — Deterministic; builds IntelligenceFindings + confidence scores
  strategy_agent_node  — LLM call; structured output → StrategyReport
  persist_node         — Deterministic; saves keywords to DB; finalises metadata

Routing helpers (used in graph.py):
  route_after_plan
  route_after_research
  route_after_strategy
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List


from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langgraph.types import interrupt

from src.graph.state import AgentState
from src.graph.tracing import extract_tool_call_counts, finalise_metadata
from src.logger_config import get_logger
from src.schemas import (
    IntelligenceFindings,
    KeywordFinding,
    ResearchPlan,
    StrategyReport,
)
from src.tools.langchain_adapters import get_langchain_tools

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Shared LLM instance
# ---------------------------------------------------------------------------
def _get_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.getenv("GEMINI_API_KEY", ""),
        temperature=0.3,
        convert_system_message_to_human=True,
    )


# ---------------------------------------------------------------------------
# PLANNER NODE
# ---------------------------------------------------------------------------
PLANNER_SYSTEM_PROMPT = """
You are the Research Planner for Keylytics, an AI-powered SEO market intelligence platform.

Given a seed keyword, your job is to produce a structured research plan as valid JSON.

Available modules:
- "keyword_discovery"   — finds related keywords with volume, CPC, competition
- "competitor_gap"      — identifies keyword opportunities competitors rank for
- "serp_analysis"       — analyses top SERP results and snippet opportunities
- "trend_forecasting"   — 6-month trend forecasts and seasonality
- "topic_clustering"    — groups keywords into semantic clusters

Rules:
1. Always include "keyword_discovery" — it is required for all other modules.
2. For a simple keyword, include 3 modules total (keyword_discovery + 2 others).
3. For a complex or competitive keyword, include all 5 modules.
4. Set max_keywords between 5 (quick) and 15 (comprehensive).
5. Write 2-3 specific, actionable objectives.

Return ONLY a JSON object with this exact structure — no markdown, no explanation:
{
  "seed_keyword": "<the keyword>",
  "objectives": ["<objective 1>", "<objective 2>"],
  "requested_modules": ["keyword_discovery", "<module2>", ...],
  "max_keywords": <integer 5-15>
}
"""


def planner_node(state: AgentState) -> AgentState:
    """
    Calls the LLM to produce a ResearchPlan from the seed keyword.
    Interrupts after writing the plan so a human can approve or edit it.
    """
    logger.info("planner_node: generating research plan")
    seed = state.get("seed_keyword", "")
    metadata = state.get("execution_metadata") or {}

    # Detect re-plan (human edited the plan)
    retries = metadata.get("planner_retries", 0)
    edited_plan = (state.get("human_feedback") or {}).get("edited_plan")

    if edited_plan:
        # Human provided an edited plan — validate and use it directly
        try:
            plan = ResearchPlan(**edited_plan)
            logger.info("planner_node: using human-edited plan")
            metadata["planner_retries"] = retries + 1
            return {
                **state,
                "research_plan": plan.model_dump(),
                "status": "awaiting_approval",
                "awaiting_human": True,
                "execution_metadata": metadata,
                "human_feedback": None,  # Clear so we don't re-enter this branch
            }
        except Exception as e:
            logger.warning(f"planner_node: invalid edited plan — {e}; replanning from LLM")

    llm = _get_llm()
    messages = [
        SystemMessage(content=PLANNER_SYSTEM_PROMPT),
        HumanMessage(content=f"Seed keyword: {seed}"),
    ]

    try:
        response = llm.invoke(messages)
        raw = response.content.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        plan_dict = json.loads(raw.strip())
        plan = ResearchPlan(**plan_dict)
        logger.info(f"planner_node: plan created — {plan.requested_modules}, max_keywords={plan.max_keywords}")
    except Exception as e:
        logger.error(f"planner_node: LLM call or parsing failed — {e}")
        # Fallback plan
        plan = ResearchPlan(
            seed_keyword=seed,
            objectives=["Discover high-value keywords", "Identify market opportunities"],
            requested_modules=["keyword_discovery", "competitor_gap", "serp_analysis"],
            max_keywords=10,
        )

    metadata["planner_retries"] = retries + 1

    # ── INTERRUPT: human must approve before research runs ────────────────
    interrupt({
        "checkpoint": "plan_approval",
        "research_plan": plan.model_dump(),
        "instructions": (
            "Review the research plan. "
            "Set human_feedback to: "
            '{"approved": true} to proceed, '
            '{"approved": true, "edited_plan": {...}} to modify, or '
            '{"approved": false} to cancel.'
        ),
    })

    return {
        **state,
        "research_plan": plan.model_dump(),
        "status": "awaiting_approval",
        "awaiting_human": True,
        "execution_metadata": metadata,
        "messages": [
            *state.get("messages", []),
            HumanMessage(content=f"Plan seed keyword: {seed}"),
            response if "response" in dir() else SystemMessage(content="Fallback plan used"),
        ],
    }


# ---------------------------------------------------------------------------
# RESEARCH AGENT NODE
# ---------------------------------------------------------------------------
RESEARCH_SYSTEM_PROMPT = """
You are the Research Agent for Keylytics, an AI-powered SEO intelligence platform.

You have access to these tools:
- keyword_research     — ALWAYS call this FIRST. Use the seed keyword and max_keywords from the plan.
- serp_analysis        — Call if "serp_analysis" is in requested_modules.
- competitor_gap       — Call if "competitor_gap" is in requested_modules.
- trend_forecast       — Call with the keyword LIST from keyword_research results.
- topic_cluster        — Call with the keyword LIST from keyword_research results.
- intent_classifier    — Call for the seed keyword only (not every keyword).

Rules:
1. Always call keyword_research first — other tools depend on its output.
2. Extract the keyword list from keyword_research before calling trend_forecast or topic_cluster.
3. If a tool returns {"error": ...}, log it in your reasoning and continue — do not stop.
4. After all requested tools have been called, stop and summarise what you collected.
5. Be efficient — call each tool exactly once unless a retry is clearly needed.

Current research plan:
{research_plan}
"""


def research_agent_node(state: AgentState) -> AgentState:
    """
    ReAct agent that calls all tools specified in the research_plan.
    Uses create_react_agent from langgraph.prebuilt.
    """
    logger.info("research_agent_node: starting tool execution")
    plan = state.get("research_plan") or {}
    prior_messages = state.get("messages", [])

    system_prompt = RESEARCH_SYSTEM_PROMPT.format(
        research_plan=json.dumps(plan, indent=2)
    )

    tools = get_langchain_tools()
    llm = _get_llm()

    # Build the ReAct sub-agent
    agent = create_react_agent(llm, tools)

    agent_messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(
            content=(
                f"Execute the research plan for seed keyword: '{plan.get('seed_keyword', '')}'. "
                f"Modules to run: {plan.get('requested_modules', [])}. "
                f"Max keywords: {plan.get('max_keywords', 10)}."
            )
        ),
    ]

    errors = list(state.get("errors", []))
    collected_data: Dict[str, Any] = {}

    try:
        result = agent.invoke({"messages": agent_messages})
        result_messages = result.get("messages", [])

        # Extract tool call counts for metadata
        tool_counts = extract_tool_call_counts(result_messages)

        # Parse collected_data from ToolMessages in the result
        for msg in result_messages:
            tool_name = getattr(msg, "name", None)
            if tool_name and hasattr(msg, "content"):
                try:
                    content = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
                    collected_data[tool_name] = content
                except (json.JSONDecodeError, TypeError):
                    collected_data[tool_name] = {"raw": str(msg.content)}

        metadata = state.get("execution_metadata") or {}
        metadata["tool_call_counts"] = tool_counts

        logger.info(f"research_agent_node: collected data from {list(collected_data.keys())}")

        return {
            **state,
            "collected_data": collected_data,
            "status": "in_progress",
            "awaiting_human": False,
            "messages": [*prior_messages, *result_messages],
            "execution_metadata": metadata,
            "errors": errors,
        }

    except Exception as e:
        logger.error(f"research_agent_node: agent execution failed — {e}", exc_info=True)
        errors.append(f"research_agent_node failed: {str(e)}")
        return {
            **state,
            "collected_data": collected_data,
            "status": "failed",
            "errors": errors,
        }


# ---------------------------------------------------------------------------
# AGGREGATOR NODE (deterministic)
# ---------------------------------------------------------------------------
def aggregator_node(state: AgentState) -> AgentState:
    """
    Builds IntelligenceFindings from collected_data and computes confidence scores.
    Pure Python — no LLM calls.
    """
    logger.info("aggregator_node: building intelligence findings")
    collected = state.get("collected_data") or {}
    plan = state.get("research_plan") or {}
    seed = plan.get("seed_keyword") or state.get("seed_keyword", "")
    errors = list(state.get("errors", []))

    # ── Build KeywordFinding list from keyword_research results ───────────
    keyword_findings: List[KeywordFinding] = []
    kw_result = collected.get("keyword_research", {})
    items = kw_result.get("items", []) if isinstance(kw_result, dict) else []

    for item in items:
        if isinstance(item, dict) and item.get("keyword"):
            try:
                kf = KeywordFinding(
                    seed=seed,
                    keyword=item["keyword"],
                    volume=float(item.get("volume", 0)),
                    competition=item.get("competition"),
                    cpc=item.get("cpc"),
                    trend=item.get("trend"),
                    score=float(item.get("score", 0.0)),
                    difficulty=item.get("difficulty", "Hard"),
                    intent=item.get("intent", "Informational"),
                    competitors=[],
                    data_source=item.get("data_source", "unavailable"),
                    trend_data_source=item.get("trend_data_source", "unavailable"),
                )
                keyword_findings.append(kf)
            except Exception as e:
                logger.warning(f"aggregator_node: skipping malformed keyword item — {e}")

    # ── Build IntelligenceFindings ─────────────────────────────────────────
    findings = IntelligenceFindings(
        seed_keyword=seed,
        keyword_findings=keyword_findings,
        competitor_gap=collected.get("competitor_gap"),
        topic_clusters=collected.get("topic_cluster"),
        trend_forecast=collected.get("trend_forecast"),
        serp_analysis=collected.get("serp_analysis"),
    )

    # ── Compute confidence scores ──────────────────────────────────────────
    max_kw = plan.get("max_keywords", 10) or 10
    requested = set(plan.get("requested_modules", []))

    def _err(tool_name: str) -> bool:
        result = collected.get(tool_name)
        return isinstance(result, dict) and "error" in result

    def _missing(tool_name: str) -> bool:
        return tool_name not in collected

    confidence_scores: Dict[str, float] = {}

    # keyword_research
    kw_count = len(keyword_findings)
    if _missing("keyword_research") or _err("keyword_research"):
        confidence_scores["keyword_research"] = 0.0
        errors.append("keyword_research returned no results")
    else:
        confidence_scores["keyword_research"] = round(min(kw_count / max(max_kw, 1), 1.0), 2)

    # serp_analysis
    if "serp_analysis" in requested:
        serp = collected.get("serp_analysis", {})
        has_organic = bool(
            isinstance(serp, dict)
            and serp.get("serp_data", {})
            and serp["serp_data"].get("organic_results")
        )
        confidence_scores["serp_analysis"] = 1.0 if has_organic else 0.3
        if not has_organic:
            errors.append("serp_analysis returned limited data")

    # competitor_gap
    if "competitor_gap" in requested:
        comp = collected.get("competitor_gap", {})
        has_opps = isinstance(comp, dict) and bool(comp.get("opportunities"))
        confidence_scores["competitor_gap"] = 1.0 if has_opps else 0.2
        if not has_opps:
            errors.append("competitor_gap found no opportunities")

    # trend_forecast
    if "trend_forecasting" in requested:
        trend = collected.get("trend_forecast", {})
        forecasts = trend.get("forecasts", {}) if isinstance(trend, dict) else {}
        valid = sum(
            1 for v in forecasts.values()
            if isinstance(v, dict) and v.get("forecast_scores")
        )
        total = max(len(forecasts), 1)
        confidence_scores["trend_forecast"] = round(valid / total, 2)

    # topic_cluster
    if "topic_clustering" in requested:
        cluster = collected.get("topic_cluster", {})
        clusters = cluster.get("clusters", []) if isinstance(cluster, dict) else []
        confidence_scores["topic_cluster"] = 1.0 if len(clusters) >= 2 else 0.4

    # intent_classifier — always returns something
    if "intent_classifier" in collected:
        confidence_scores["intent_classifier"] = 1.0

    logger.info(f"aggregator_node: confidence scores — {confidence_scores}")
    logger.info(f"aggregator_node: {len(keyword_findings)} keywords in findings")

    return {
        **state,
        "intelligence_findings": findings.model_dump(mode="json"),
        "confidence_scores": confidence_scores,
        "errors": errors,
        "status": "in_progress",
    }


# ---------------------------------------------------------------------------
# STRATEGY AGENT NODE
# ---------------------------------------------------------------------------
STRATEGY_SYSTEM_PROMPT = """
You are the Strategy Agent for Keylytics, an AI-powered SEO market intelligence platform.

You will receive structured intelligence findings from keyword research, competitor analysis,
SERP analysis, trend forecasting, and topic clustering.

Your job is to synthesise these findings into a concise, actionable strategy report
as valid JSON — no markdown, no explanation, just the JSON object.

Rules:
1. executive_summary: 3-5 sentences. High-level insight. Reference specific data.
2. top_opportunities: Select the top 5 KeywordFinding items by score. Include all their fields.
3. recommendations: Exactly 5 actionable recommendations. Start each with an action verb.
   Be specific — reference actual keywords, clusters, or competitor data from the findings.
4. If confidence for a tool is below 0.4, note the data limitation in executive_summary.
5. If human_feedback.notes is provided, incorporate those notes into the recommendations.

Return ONLY this JSON structure:
{
  "seed_keyword": "<seed>",
  "executive_summary": "<summary>",
  "top_opportunities": [<up to 5 KeywordFinding dicts>],
  "recommendations": ["<rec1>", "<rec2>", "<rec3>", "<rec4>", "<rec5>"],
  "version": "phase3"
}
"""


def strategy_agent_node(state: AgentState) -> AgentState:
    """
    LLM call to synthesise findings into a StrategyReport.
    Interrupts after writing the report so a human can approve or request regeneration.
    """
    logger.info("strategy_agent_node: synthesising strategy report")
    findings = state.get("intelligence_findings") or {}
    confidence = state.get("confidence_scores") or {}
    plan = state.get("research_plan") or {}
    human_feedback = state.get("human_feedback") or {}
    metadata = state.get("execution_metadata") or {}
    errors = list(state.get("errors", []))

    # Check regeneration retry limit
    strategy_retries = metadata.get("strategy_retries", 0)
    if strategy_retries >= 1:
        logger.warning("strategy_agent_node: max retries reached; using existing report")
        interrupt({
            "checkpoint": "report_approval",
            "note": "Maximum regeneration attempts reached. Approving current report.",
            "strategy_report": state.get("strategy_report"),
        })
        return {**state, "status": "awaiting_approval", "awaiting_human": True}

    llm = _get_llm()

    context = {
        "intelligence_findings": findings,
        "confidence_scores": confidence,
        "research_objectives": plan.get("objectives", []),
        "human_notes": human_feedback.get("notes", ""),
    }

    messages = [
        SystemMessage(content=STRATEGY_SYSTEM_PROMPT),
        HumanMessage(content=f"Intelligence context:\n{json.dumps(context, indent=2, default=str)}"),
    ]

    try:
        response = llm.invoke(messages)
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        report_dict = json.loads(raw.strip())

        # Validate via StrategyReport schema (findings field is required by schema)
        # We attach a minimal IntelligenceFindings for schema compliance
        from src.schemas import IntelligenceFindings as IF
        findings_obj = IF(**findings) if findings else IF(
            seed_keyword=plan.get("seed_keyword", ""),
            keyword_findings=[],
        )
        _ = StrategyReport(
            seed_keyword=report_dict.get("seed_keyword", plan.get("seed_keyword", "")),
            executive_summary=report_dict.get("executive_summary", ""),
            findings=findings_obj,
            top_opportunities=[],  # Simplified for schema; full data in strategy_report dict
            recommendations=report_dict.get("recommendations", []),
            version="phase3",
        )
        logger.info("strategy_agent_node: report generated successfully")

    except Exception as e:
        logger.error(f"strategy_agent_node: failed — {e}", exc_info=True)
        errors.append(f"strategy_agent_node failed: {str(e)}")
        report_dict = {
            "seed_keyword": plan.get("seed_keyword", ""),
            "executive_summary": "Strategy generation encountered an error. Manual review recommended.",
            "top_opportunities": [],
            "recommendations": [
                "Review keyword research results manually.",
                "Analyse competitor gaps identified in the data.",
                "Investigate SERP opportunities for quick wins.",
                "Focus on high-volume, low-competition keywords.",
                "Develop content strategy aligned with identified topic clusters.",
            ],
            "version": "phase3",
        }

    metadata["strategy_retries"] = strategy_retries + 1

    # ── INTERRUPT: human must approve before persisting ───────────────────
    interrupt({
        "checkpoint": "report_approval",
        "strategy_report": report_dict,
        "confidence_scores": confidence,
        "warnings": errors,
        "instructions": (
            "Review the strategy report. "
            "Set human_feedback to: "
            '{"approved": true} to save and complete, '
            '{"regenerate": true, "notes": "<your notes>"} to regenerate once, or '
            '{"approved": true} after reviewing regenerated report.'
        ),
    })

    return {
        **state,
        "strategy_report": report_dict,
        "status": "awaiting_approval",
        "awaiting_human": True,
        "execution_metadata": metadata,
        "errors": errors,
        "messages": [
            *state.get("messages", []),
            *messages,
            response if "response" in dir() else SystemMessage(content="Fallback report"),
        ],
    }


# ---------------------------------------------------------------------------
# PERSIST NODE (deterministic)
# ---------------------------------------------------------------------------
def persist_node(state: AgentState) -> AgentState:
    """
    Saves keyword findings to the database and finalises execution metadata.
    Calls src/db_client.py::save_to_db — no LLM calls.
    """
    logger.info("persist_node: saving results to database")
    findings = state.get("intelligence_findings") or {}
    metadata = state.get("execution_metadata") or {}
    errors = list(state.get("errors", []))

    keyword_findings = findings.get("keyword_findings", [])
    if keyword_findings:
        try:
            from src.db_client import save_to_db
            save_to_db(keyword_findings)
            logger.info(f"persist_node: saved {len(keyword_findings)} keywords")
        except Exception as e:
            logger.error(f"persist_node: db save failed — {e}", exc_info=True)
            errors.append(f"persist_node db error: {str(e)}")

    metadata = finalise_metadata(metadata)

    return {
        **state,
        "status": "completed",
        "awaiting_human": False,
        "execution_metadata": metadata,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# ROUTING FUNCTIONS
# ---------------------------------------------------------------------------
def route_after_plan(state: AgentState) -> str:
    """Route based on human feedback after planner_node interrupt."""
    feedback = state.get("human_feedback") or {}
    if feedback.get("approved"):
        return "research_agent_node"
    if feedback.get("edited_plan"):
        meta = state.get("execution_metadata") or {}
        if meta.get("planner_retries", 0) < 2:
            return "planner_node"
    return "__end__"


def route_after_research(state: AgentState) -> str:
    """Route based on research results."""
    collected = state.get("collected_data") or {}
    if not collected or "keyword_research" not in collected:
        return "__end__"
    kw_result = collected.get("keyword_research", {})
    if isinstance(kw_result, dict) and "error" in kw_result:
        return "__end__"
    return "aggregator_node"


def route_after_strategy(state: AgentState) -> str:
    """Route based on human feedback after strategy_agent_node interrupt."""
    feedback = state.get("human_feedback") or {}
    if feedback.get("regenerate"):
        meta = state.get("execution_metadata") or {}
        if meta.get("strategy_retries", 0) < 1:
            return "strategy_agent_node"
    return "persist_node"
