"""
LangGraph node functions for the Keylytics research pipeline.

Node inventory:
  plan_generation_node     — LLM call; structured output → ResearchPlan
  plan_approval_node       — Deterministic; interrupt() checkpoint for human approval
  research_agent_node      — ReAct agent; executes all 6 tools
  aggregator_node          — Deterministic; builds IntelligenceFindings + confidence scores
  strategy_generation_node — LLM call; structured output → StrategyReport
  strategy_approval_node   — Deterministic; interrupt() checkpoint for human approval
  persist_node             — Deterministic; saves keywords to DB; finalises metadata + evals

Routing helpers (used in graph.py):
  route_after_plan
  route_after_research
  route_after_strategy
"""
from __future__ import annotations

import json
import threading
from typing import Any, Dict, List, Optional


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
from src.llm_config import get_chat_llm

def _get_llm() -> ChatGoogleGenerativeAI:
    return get_chat_llm(temperature=0.3)


def _get_string_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and "text" in part:
                parts.append(part["text"])
            elif hasattr(part, "text"):
                parts.append(getattr(part, "text"))
        return "".join(parts)
    return str(content)



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
4. Always set max_keywords to exactly 5.
5. Write 2-3 specific, actionable objectives.

Return ONLY a JSON object with this exact structure — no markdown, no explanation:
{
  "seed_keyword": "<the keyword>",
  "objectives": ["<objective 1>", "<objective 2>"],
  "requested_modules": ["keyword_discovery", "<module2>", ...],
  "max_keywords": 5
}
"""


def plan_generation_node(state: AgentState) -> AgentState:
    """
    Calls the LLM to produce a ResearchPlan from the seed keyword, or adopts
    a human-edited plan if provided in state.
    Does NOT interrupt — plan generation checkpoint commits immediately upon return.
    """
    logger.info("plan_generation_node: generating research plan")
    seed = state.get("seed_keyword", "")
    metadata = dict(state.get("execution_metadata") or {})

    # Detect re-plan (human edited the plan)
    retries = metadata.get("planner_retries", 0)
    edited_plan = (state.get("human_feedback") or {}).get("edited_plan")

    if edited_plan:
        # Human provided an edited plan — validate and use it directly
        try:
            plan = ResearchPlan(**edited_plan)
            logger.info("plan_generation_node: using human-edited plan")
            metadata["planner_retries"] = retries + 1
            return {
                **state,
                "research_plan": plan.model_dump(mode="json"),
                "status": "in_progress",
                "awaiting_human": False,
                "execution_metadata": metadata,
            }
        except Exception as e:
            logger.warning(f"plan_generation_node: invalid edited plan — {e}; replanning from LLM")

    llm = _get_llm()
    messages = [
        SystemMessage(content=PLANNER_SYSTEM_PROMPT),
        HumanMessage(content=f"Seed keyword: {seed}"),
    ]

    # Initialise response to None before the try block
    response: Optional[Any] = None
    try:
        response = llm.invoke(messages)
        raw = _get_string_content(response.content).strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        plan_dict = json.loads(raw.strip())
        plan = ResearchPlan(**plan_dict)
        logger.info(f"plan_generation_node: plan created — {plan.requested_modules}, max_keywords={plan.max_keywords}")
    except Exception as e:
        logger.error(f"plan_generation_node: LLM call or parsing failed — {e}")
        response = None
        # Fallback plan
        plan = ResearchPlan(
            seed_keyword=seed,
            objectives=["Discover high-value keywords", "Identify market opportunities"],
            requested_modules=["keyword_discovery", "competitor_gap", "serp_analysis"],
            max_keywords=5,
        )

    metadata["planner_retries"] = retries + 1

    return {
        **state,
        "research_plan": plan.model_dump(mode="json"),
        "status": "in_progress",
        "awaiting_human": False,
        "execution_metadata": metadata,
        # Use response if it is not None, else fall back to SystemMessage
        "messages": [
            *state.get("messages", []),
            HumanMessage(content=f"Plan seed keyword: {seed}"),
            *([response] if response is not None else [SystemMessage(content="Fallback plan used")]),
        ],
    }


def plan_approval_node(state: AgentState) -> AgentState:
    """
    Reads research_plan from state and interrupts so a human can approve or edit it.
    Contains NO LLM call.
    """
    logger.info("plan_approval_node: requesting human approval for research plan")
    plan_dict = state.get("research_plan") or {}
    metadata = state.get("execution_metadata") or {}

    human_input = interrupt({
        "checkpoint": "plan_approval",
        "research_plan": plan_dict,
        "instructions": (
            "Review the research plan. "
            "Set human_feedback to: "
            '{"approved": true} to proceed, '
            '{"approved": true, "edited_plan": {...}} to modify, or '
            '{"approved": false} to cancel.'
        ),
    })
    if human_input:
        logger.debug(f"plan_approval_node: interrupt returned human_input={human_input!r}")

    return {
        **state,
        "human_feedback": human_input if human_input else state.get("human_feedback"),
        "status": "in_progress",
        "awaiting_human": False,
        "execution_metadata": metadata,
    }


# ---------------------------------------------------------------------------
# RESEARCH AGENT NODE
# ---------------------------------------------------------------------------
RESEARCH_SYSTEM_PROMPT = """
You are the Research Agent for Keylytics, an AI-powered SEO intelligence platform.

You have access to exactly these 5 tools:
- keyword_research     — ALWAYS call this FIRST. Use the seed keyword and max_keywords from the plan. Call only if "keyword_discovery" is in requested_modules (it should always be).
- serp_analysis        — Call only if "serp_analysis" is in requested_modules.
- competitor_gap       — Call only if "competitor_gap" is in requested_modules.
- trend_forecast       — Call only if "trend_forecasting" is in requested_modules. Use with the keyword LIST from keyword_research results.
- topic_cluster        — Call only if "topic_clustering" is in requested_modules. Use with the keyword LIST from keyword_research results.

Rules:
1. Always call keyword_research first — other tools depend on its output.
2. Extract the keyword list from keyword_research before calling trend_forecast or topic_cluster.
3. Call ONLY the tools that correspond to the modules listed in requested_modules of the current research plan. Do NOT call any tool for a module that is not in requested_modules.
4. If a tool returns {{"error": ...}}, log it in your reasoning and continue — do not stop.
5. After all requested tools have been called, stop and summarise what you collected.
6. Be efficient — call each tool exactly once unless a retry is clearly needed.
7. Do NOT call any tool not listed above.

Current research plan:
{research_plan}
"""


MODULE_TOOL_MAP = {
    "keyword_discovery": "keyword_research",
    "competitor_gap": "competitor_gap",
    "serp_analysis": "serp_analysis",
    "trend_forecasting": "trend_forecast",
    "topic_clustering": "topic_cluster",
}

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

    requested_modules = plan.get("requested_modules", [])
    allowed_tool_names = {"keyword_research"} | {
        MODULE_TOOL_MAP[m] for m in requested_modules if m in MODULE_TOOL_MAP
    }
    retry_targets = state.get("retry_target_tools")
    if retry_targets is not None:
        allowed_tool_names = {t for t in allowed_tool_names if t in retry_targets}
    EXCLUDED_TOOLS = {"intent_classifier"}
    tools = [
        t for t in get_langchain_tools()
        if t.name not in EXCLUDED_TOOLS and t.name in allowed_tool_names
    ]
    llm = _get_llm()

    # Build the ReAct sub-agent
    agent = create_react_agent(llm, tools)

    collected_keys = list((state.get("collected_data") or {}).keys())
    valid_tools = [k for k in collected_keys if k not in allowed_tool_names]

    human_content = (
        f"Execute the research plan for seed keyword: '{plan.get('seed_keyword', '')}'. "
        f"Modules to run: {plan.get('requested_modules', [])}. "
        f"Max keywords: {plan.get('max_keywords', 10)}."
    )
    if retry_targets is not None:
        human_content += (
            f"\nThis is a retry pass. "
            f"Tools with already valid data: {valid_tools}. "
            f"Tools that need to be (re)run: {list(allowed_tool_names)}. "
            f"Do NOT attempt calls outside this restricted list."
        )

    agent_messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_content),
    ]

    errors = list(state.get("errors", []))
    collected_data: Dict[str, Any] = {}

    try:
        result = agent.invoke({"messages": agent_messages})
        result_messages = result.get("messages", [])

        # Extract tool call counts for metadata
        tool_counts = extract_tool_call_counts(result_messages)

        # Emit per-tool metrics
        try:
            from src.metrics import get_metrics
            m = get_metrics()
            for tool_name, count in tool_counts.items():
                for _ in range(count):
                    m.increment("keylytics_tool_calls_total", {"tool_name": tool_name, "status": "success"})
        except Exception:
            pass  # Metrics are non-critical

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
        prior_tool_counts = metadata.get("tool_call_counts") or {}
        merged_tool_counts = dict(prior_tool_counts)
        for t_name, count in tool_counts.items():
            merged_tool_counts[t_name] = merged_tool_counts.get(t_name, 0) + count
        metadata["tool_call_counts"] = merged_tool_counts

        logger.info(f"research_agent_node: collected data from {list(collected_data.keys())}")

        merged_collected_data = dict(state.get("collected_data") or {})
        merged_collected_data.update(collected_data)

        return {
            **state,
            "collected_data": merged_collected_data,
            "status": "in_progress",
            "awaiting_human": False,
            # Clear stale human_feedback
            "human_feedback": None,
            "messages": [*prior_messages, *result_messages],
            "execution_metadata": metadata,
            "errors": errors,
            "retry_target_tools": None,
        }

    except Exception as e:
        logger.error(f"research_agent_node: agent execution failed — {e}", exc_info=True)
        errors.append(f"research_agent_node failed: {str(e)}")
        merged_collected_data = dict(state.get("collected_data") or {})
        merged_collected_data.update(collected_data)
        return {
            **state,
            "collected_data": merged_collected_data,
            "status": "failed",
            # Clear stale human_feedback even on failure
            "human_feedback": None,
            "errors": errors,
            "retry_target_tools": None,
        }


# ---------------------------------------------------------------------------
# AGGREGATOR NODE (deterministic)
# ---------------------------------------------------------------------------
def aggregator_node(state: AgentState) -> AgentState:
    """
    Builds IntelligenceFindings from collected_data and computes confidence scores.
    Pure Python — no LLM calls.

    Task 4.5: uses structured rubrics for confidence scoring.
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

    # ── Compute confidence scores (Task 4.5: structured rubrics) ──────────
    max_kw = plan.get("max_keywords", 10) or 10
    requested = set(plan.get("requested_modules", []))

    def _err(tool_name: str) -> bool:
        result = collected.get(tool_name)
        return isinstance(result, dict) and "error" in result

    def _missing(tool_name: str) -> bool:
        return tool_name not in collected

    confidence_scores: Dict[str, float] = {}

    # keyword_research rubric
    # 1.0 if count >= max_keywords AND avg(volume) > 0
    # 0.7 if count >= max_keywords AND avg(volume) == 0 (Gemini fallback)
    # linear scale below max_keywords
    kw_count = len(keyword_findings)
    if _missing("keyword_research") or _err("keyword_research"):
        confidence_scores["keyword_research"] = 0.0
        errors.append("keyword_research returned no results")
    else:
        avg_volume = (
            sum(kf.volume for kf in keyword_findings) / kw_count
            if kw_count > 0 else 0.0
        )
        fill_ratio = min(kw_count / max(max_kw, 1), 1.0)
        if fill_ratio >= 1.0:
            confidence_scores["keyword_research"] = 1.0 if avg_volume > 0 else 0.7
        else:
            # Linear scale: at half fill and avg_volume>0 → 0.5; no volume → 0.35
            base = 1.0 if avg_volume > 0 else 0.7
            confidence_scores["keyword_research"] = round(fill_ratio * base, 2)

    # serp_analysis rubric
    # 1.0 if organic_results >= 5 AND paa_questions >= 2
    # 0.6 if organic_results >= 3
    # 0.2 if organic_results < 3
    if "serp_analysis" in requested:
        if _missing("serp_analysis") or _err("serp_analysis"):
            confidence_scores["serp_analysis"] = 0.0
            errors.append("serp_analysis returned no results")
        else:
            serp = collected.get("serp_analysis", {})
            serp_data = serp.get("serp_data", {}) if isinstance(serp, dict) else {}
            organic = serp_data.get("organic_results", []) if isinstance(serp_data, dict) else []
            paa = serp.get("paa_questions", {}) if isinstance(serp, dict) else {}
            paa_count = len(paa) if isinstance(paa, dict) else 0
            organic_count = len(organic) if isinstance(organic, list) else 0
            if organic_count >= 5 and paa_count >= 2:
                confidence_scores["serp_analysis"] = 1.0
            elif organic_count >= 3:
                confidence_scores["serp_analysis"] = 0.6
            else:
                confidence_scores["serp_analysis"] = 0.2
                errors.append("serp_analysis returned limited data")

    # competitor_gap rubric
    # 1.0 if opportunities >= 3 AND any gap_score > 70
    # 0.5 if opportunities >= 1
    # 0.0 if no opportunities
    if "competitor_gap" in requested:
        if _missing("competitor_gap") or _err("competitor_gap"):
            confidence_scores["competitor_gap"] = 0.0
            errors.append("competitor_gap returned no results")
        else:
            comp = collected.get("competitor_gap", {})
            opps = comp.get("opportunities", []) if isinstance(comp, dict) else []
            opp_count = len(opps) if isinstance(opps, list) else 0
            high_gap = any(
                (o.get("gap_score", 0) if isinstance(o, dict) else 0) > 70
                for o in (opps if isinstance(opps, list) else [])
            )
            if opp_count >= 3 and high_gap:
                confidence_scores["competitor_gap"] = 1.0
            elif opp_count >= 1:
                confidence_scores["competitor_gap"] = 0.5
            else:
                confidence_scores["competitor_gap"] = 0.0
                errors.append("competitor_gap found no opportunities")

    # trend_forecast rubric
    # fraction of keywords with non-empty forecast_scores AND r_squared > 0.3
    if "trend_forecasting" in requested:
        if _missing("trend_forecast") or _err("trend_forecast"):
            confidence_scores["trend_forecast"] = 0.0
        else:
            trend = collected.get("trend_forecast", {})
            forecasts = trend.get("forecasts", {}) if isinstance(trend, dict) else {}
            total = max(len(forecasts), 1)
            valid = sum(
                1 for v in (forecasts.values() if isinstance(forecasts, dict) else [])
                if isinstance(v, dict)
                and v.get("forecast_scores")
                and (v.get("r_squared") is None or v.get("r_squared") > 0.3)
            )
            confidence_scores["trend_forecast"] = round(valid / total, 2)

    # topic_cluster rubric
    # 1.0 if clusters >= 3 AND avg(keyword_count) >= 3
    # 0.5 if clusters >= 2
    # 0.2 if clusters == 1
    if "topic_clustering" in requested:
        if _missing("topic_cluster") or _err("topic_cluster"):
            confidence_scores["topic_cluster"] = 0.0
        else:
            cluster = collected.get("topic_cluster", {})
            clusters = cluster.get("clusters", []) if isinstance(cluster, dict) else []
            n = len(clusters) if isinstance(clusters, list) else 0
            avg_kw_count = (
                sum(c.get("keyword_count", 0) for c in clusters if isinstance(c, dict)) / n
                if n > 0 else 0
            )
            if n >= 3 and avg_kw_count >= 3:
                confidence_scores["topic_cluster"] = 1.0
            elif n >= 2:
                confidence_scores["topic_cluster"] = 0.5
            elif n == 1:
                confidence_scores["topic_cluster"] = 0.2
            else:
                confidence_scores["topic_cluster"] = 0.0

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
        # Clear stale human_feedback
        "human_feedback": None,
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
6. critic_feedback is provided in the context. Address each issue and weak_claim in the executive_summary or recommendations. Do not ignore them.
7. data_quality_summary.data_limitations contains a list of known data quality issues. Each limitation MUST be acknowledged in the executive_summary. Do not present low-confidence data as if it were high-confidence.

Return ONLY this JSON structure:
{
  "seed_keyword": "<seed>",
  "executive_summary": "<summary>",
  "top_opportunities": [<up to 5 KeywordFinding dicts>],
  "recommendations": ["<rec1>", "<rec2>", "<rec3>", "<rec4>", "<rec5>"],
  "version": "phase3"
}
"""


def strategy_generation_node(state: AgentState) -> AgentState:
    """
    LLM call to synthesise findings into a StrategyReport.
    Does NOT interrupt — report generation checkpoint commits immediately upon return.
    """
    logger.info("strategy_generation_node: synthesising strategy report")
    findings = state.get("intelligence_findings") or {}
    confidence = state.get("confidence_scores") or {}
    plan = state.get("research_plan") or {}
    human_feedback = state.get("human_feedback") or {}
    metadata = dict(state.get("execution_metadata") or {})
    errors = list(state.get("errors", []))

    strategy_retries = metadata.get("strategy_retries", 0)

    llm = _get_llm()

    # Task 4.5: include confidence_scores in context so LLM can reference them
    context = {
        "intelligence_findings": findings,
        "confidence_scores": confidence,
        "research_objectives": plan.get("objectives", []),
        "human_notes": human_feedback.get("notes", ""),
        "critic_feedback": state.get("critic_feedback") or {},
        "data_quality_summary": (state.get("execution_metadata") or {}).get("data_quality_summary", {}),
    }

    messages = [
        SystemMessage(content=STRATEGY_SYSTEM_PROMPT),
        HumanMessage(content=f"Intelligence context:\n{json.dumps(context, indent=2, default=str)}"),
    ]

    # Initialise response to None before the try block
    response: Optional[Any] = None
    report_dict: Dict[str, Any] = {}

    try:
        response = llm.invoke(messages)
        raw = _get_string_content(response.content).strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        report_dict = json.loads(raw.strip())

        # Validate the real report_dict including top_opportunities
        # Parse each top_opportunity item as KeywordFinding (with graceful fallback)
        raw_opps = report_dict.get("top_opportunities", [])
        validated_opps: List[KeywordFinding] = []
        for opp in (raw_opps if isinstance(raw_opps, list) else []):
            if isinstance(opp, dict):
                try:
                    validated_opps.append(KeywordFinding(**opp))
                except Exception as opp_err:
                    logger.warning(f"strategy_generation_node: skipping invalid top_opportunity — {opp_err}")

        # Build IntelligenceFindings object for StrategyReport schema compliance
        findings_obj = (
            IntelligenceFindings(**findings) if findings
            else IntelligenceFindings(
                seed_keyword=plan.get("seed_keyword", ""),
                keyword_findings=[],
            )
        )

        # Construct fully validated StrategyReport
        validated_report = StrategyReport(
            seed_keyword=report_dict.get("seed_keyword", plan.get("seed_keyword", "")),
            executive_summary=report_dict.get("executive_summary", ""),
            findings=findings_obj,
            top_opportunities=validated_opps,
            recommendations=report_dict.get("recommendations", []),
            version="phase3",
        )

        # Re-serialize from the validated object so state carries schema-validated data
        serialized = validated_report.model_dump(mode="json")
        report_dict["top_opportunities"] = serialized["top_opportunities"]
        report_dict["seed_keyword"] = serialized["seed_keyword"]
        report_dict["executive_summary"] = serialized["executive_summary"]
        report_dict["recommendations"] = serialized["recommendations"]
        logger.info("strategy_generation_node: report generated and schema-validated successfully")

    except Exception as e:
        logger.error(f"strategy_generation_node: failed — {e}", exc_info=True)
        errors.append(f"strategy_generation_node failed: {str(e)}")
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

    return {
        **state,
        "strategy_report": report_dict,
        "status": "in_progress",
        "awaiting_human": False,
        "execution_metadata": metadata,
        "errors": errors,
        "messages": [
            *state.get("messages", []),
            *messages,
            # Use response if not None, else fall back to SystemMessage
            *([response] if response is not None else [SystemMessage(content="Fallback report")]),
        ],
    }


def strategy_approval_node(state: AgentState) -> AgentState:
    """
    Reads strategy_report from state and interrupts so a human can approve or request regeneration.
    Contains NO LLM call.
    """
    logger.info("strategy_approval_node: requesting human approval for strategy report")
    report_dict = state.get("strategy_report") or {}
    confidence = state.get("confidence_scores") or {}
    metadata = state.get("execution_metadata") or {}
    errors = list(state.get("errors", []))

    human_input = interrupt({
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
    if human_input:
        logger.debug(f"strategy_approval_node: interrupt returned human_input={human_input!r}")

    return {
        **state,
        "strategy_report": report_dict,
        "human_feedback": human_input if human_input else state.get("human_feedback"),
        "status": "in_progress",
        "awaiting_human": False,
        "execution_metadata": metadata,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# PERSIST NODE (deterministic)
# ---------------------------------------------------------------------------
def persist_node(state: AgentState) -> AgentState:
    """
    Saves keyword findings to the database and finalises execution metadata.
    Triggers LLM evaluation of plan quality, report quality, and tool reliability.
    Calls src/db_client.py::save_to_db — no LLM calls for persistence itself.

    Task 4.3b: triggers KeylyticsEvaluator after keyword save.
    Task 4.4b: increments graph run completion metric.
    """
    logger.info("persist_node: saving results to database")
    findings = state.get("intelligence_findings") or {}
    metadata = state.get("execution_metadata") or {}
    errors = list(state.get("errors", []))
    run_id = metadata.get("run_id", "")

    keyword_findings = findings.get("keyword_findings", [])
    if keyword_findings:
        try:
            from src.db_client import save_to_db
            save_to_db(keyword_findings)
            logger.info(f"persist_node: saved {len(keyword_findings)} keywords")
        except Exception as e:
            logger.error(f"persist_node: db save failed — {e}", exc_info=True)
            errors.append(f"[persist:db] db error: {str(e)}")

    metadata = finalise_metadata(metadata)

    # Save run completion/status to ResearchRunLog database table
    try:
        from src.db_client import connect_db
        from src.models import ResearchRunLog
        from sqlalchemy.orm import Session
        from datetime import datetime, timezone
        engine = connect_db()
        with Session(engine) as session:
            row = session.query(ResearchRunLog).filter(ResearchRunLog.run_id == run_id).first()
            if not row:
                row = ResearchRunLog(
                    run_id=run_id,
                    seed_keyword=state.get("seed_keyword") or (state.get("research_plan") or {}).get("seed_keyword") or "unknown",
                    triggered_by="manual"
                )
                session.add(row)
            row.status = "completed"
            row.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            report = state.get("strategy_report")
            if report:
                row.strategy_report = json.dumps(report, default=str)
            confidence = state.get("confidence_scores")
            if confidence:
                row.confidence_scores = json.dumps(confidence)
            session.commit()
            # Verify the commit was durable before returning so the graph's
            # status: completed is only reported after the row is confirmed flushed
            session.refresh(row)
            if row.status != "completed":
                logger.error(f"persist_node: status verification failed for run_id={run_id} — row.status={row.status}")
                errors.append(f"[persist:db] status verification failed: row.status={row.status}")
            else:
                logger.info(f"persist_node: saved run completion for run_id={run_id} to ResearchRunLog (verified)")
    except Exception as e:
        logger.error(f"persist_node: failed to save run completion to ResearchRunLog: {e}", exc_info=True)

    # Task 4.4b: increment run completion metric
    final_status = "completed_with_errors" if errors else "completed"
    try:
        from src.metrics import get_metrics
        m = get_metrics()
        m.increment("keylytics_graph_runs_total", {"status": final_status})
        m.observe("keylytics_keyword_count_per_run", float(len(keyword_findings)))
    except Exception:
        pass  # Metrics are non-critical

    # Task 4.3b: trigger LLM evaluation in background thread (non-blocking)
    plan_dict = dict(state.get("research_plan") or {})
    report_dict = dict(state.get("strategy_report") or {})
    confidence_dict = dict(state.get("confidence_scores") or {})
    collected_dict = dict(state.get("collected_data") or {})

    eval_thread = threading.Thread(
        target=_run_background_evaluations,
        args=(run_id, plan_dict, report_dict, confidence_dict, collected_dict),
        daemon=True,
    )
    eval_thread.start()
    logger.info(f"persist_node: background evaluation thread started for run_id={run_id}")

    metadata["persist_had_errors"] = bool(errors)

    return {
        **state,
        "status": "completed",
        "awaiting_human": False,
        # Clear stale human_feedback
        "human_feedback": None,
        "execution_metadata": metadata,
        "errors": errors,
    }


def _run_background_evaluations(
    run_id: str,
    plan_dict: Dict[str, Any],
    report_dict: Dict[str, Any],
    confidence_scores: Dict[str, float],
    collected_data: Dict[str, Any],
) -> None:
    """
    Executes LLM-as-judge evaluations in a background daemon thread.
    Catches and logs all errors without affecting main process state.
    """
    logger.info(f"_run_background_evaluations: starting evaluation for run_id={run_id}")
    try:
        from src.evals.evaluator import KeylyticsEvaluator
        evaluator = KeylyticsEvaluator()

        plan_eval = evaluator.evaluate_plan(run_id, plan_dict)
        report_eval = evaluator.evaluate_report(
            run_id,
            report_dict,
            confidence_scores,
        )
        tool_eval = evaluator.evaluate_tool_reliability(
            run_id,
            collected_data,
        )

        # Emit eval score metrics
        try:
            from src.metrics import get_metrics
            m = get_metrics()
            m.observe("keylytics_plan_eval_score", plan_eval.score)
            m.observe("keylytics_report_eval_score", report_eval.score)
        except Exception:
            pass

        logger.info(
            f"_run_background_evaluations: evaluations complete for run_id={run_id} — "
            f"plan={plan_eval.score:.2f}, report={report_eval.score:.2f}, "
            f"tool={tool_eval.score:.2f}"
        )
    except Exception as e:
        logger.error(f"_run_background_evaluations: evaluation failed for run_id={run_id} — {e}", exc_info=True)


# ---------------------------------------------------------------------------
# ROUTING FUNCTIONS
# ---------------------------------------------------------------------------
def route_after_plan(state: AgentState) -> str:
    """Route based on human feedback after plan_approval_node interrupt.

    Priority:
    1. approved=True → always go to research (even if edited_plan is present)
    2. edited_plan only → loop back through plan_generation_node to validate (max 2 retries)
    3. Otherwise → end (rejected/cancelled)
    """
    feedback = state.get("human_feedback") or {}
    # approved takes absolute priority — if the human approved (with or without edits), proceed
    if feedback.get("approved"):
        return "research_agent_node"
    # edited_plan without explicit approval → re-validate via planner (capped at 2 retries)
    if feedback.get("edited_plan"):
        meta = state.get("execution_metadata") or {}
        if meta.get("planner_retries", 0) < 2:
            return "plan_generation_node"
    return "__end__"


def route_after_research(state: AgentState) -> str:
    """Route based on research results."""
    collected = state.get("collected_data") or {}
    if not collected or "keyword_research" not in collected:
        return "__end__"
    kw_result = collected.get("keyword_research", {})
    if isinstance(kw_result, dict) and "error" in kw_result:
        return "__end__"
    items = kw_result.get("items", []) if isinstance(kw_result, dict) else []
    if not items:
        return "__end__"
    return "aggregator_node"


def route_after_strategy(state: AgentState) -> str:
    """Route based on human feedback after strategy_approval_node interrupt."""
    feedback = state.get("human_feedback") or {}
    if feedback.get("regenerate"):
        meta = state.get("execution_metadata") or {}
        if meta.get("strategy_retries", 0) < 1:
            return "strategy_generation_node"
    return "persist_node"


# ---------------------------------------------------------------------------
# CRITIC NODE & QUALITY GATE NODE
# ---------------------------------------------------------------------------

CRITIC_SYSTEM_PROMPT = """
You are the Critic Agent for Keylytics, an adversarial quality reviewer for SEO market intelligence findings.

Your job is to challenge the research findings BEFORE a strategy report is written.
You receive intelligence findings and confidence scores.

Identify:
1. weak_claims — statements in the keyword findings that are not supported by high-confidence data
2. data_gaps — modules that returned low confidence (<0.4) but whose results are being used as if reliable
3. issues — structural problems (too few keywords, no competitor data, missing trends)
4. overall_verdict — "PASS" if findings are sufficient for a quality report, "REVISE" if critical gaps exist

Be specific. Reference actual keywords, confidence scores, and tool names.

Scoring:
- overall_verdict = "PASS" if: keyword_research confidence >= 0.4 AND at least 3 keywords found
- overall_verdict = "REVISE" otherwise

Return ONLY valid JSON — no markdown, no explanation:
{
  "weak_claims": ["<claim>"],
  "data_gaps": ["<gap>"],
  "issues": ["<issue>"],
  "overall_verdict": "PASS" or "REVISE",
  "critic_score": <float 0.0-1.0>
}
"""

def critic_node(state: AgentState) -> AgentState:
    """
    Adversarial critic that reviews intelligence findings before strategy synthesis.
    Returns critic_feedback to state. If verdict is REVISE and retries < 1,
    route_after_critic will send back to research_agent_node for targeted retry.
    """
    logger.info("critic_node: reviewing intelligence findings")
    findings = state.get("intelligence_findings") or {}
    confidence = state.get("confidence_scores") or {}
    metadata = state.get("execution_metadata") or {}
    errors = list(state.get("errors", []))

    critic_retries = metadata.get("critic_retries", 0)

    llm = _get_llm()
    context = {
        "intelligence_findings_summary": {
            "keyword_count": len(findings.get("keyword_findings", [])),
            "has_competitor_gap": findings.get("competitor_gap") is not None,
            "has_serp_analysis": findings.get("serp_analysis") is not None,
            "has_trend_forecast": findings.get("trend_forecast") is not None,
            "has_topic_clusters": findings.get("topic_clusters") is not None,
        },
        "confidence_scores": confidence,
        "errors_so_far": errors,
    }

    messages = [
        SystemMessage(content=CRITIC_SYSTEM_PROMPT),
        HumanMessage(content=f"Review these findings:\n{json.dumps(context, indent=2)}"),
    ]

    critic_feedback: Dict[str, Any] = {}
    try:
        response = llm.invoke(messages)
        raw = _get_string_content(response.content).strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        critic_feedback = json.loads(raw.strip())
        logger.info(
            f"critic_node: verdict={critic_feedback.get('overall_verdict')}, "
            f"score={critic_feedback.get('critic_score')}"
        )
    except Exception as e:
        logger.warning(f"critic_node: failed — {e}; defaulting to PASS")
        critic_feedback = {
            "weak_claims": [],
            "data_gaps": [],
            "issues": [f"Critic evaluation failed: {str(e)}"],
            "overall_verdict": "PASS",
            "critic_score": 0.5,
        }

    metadata["critic_retries"] = critic_retries + 1
    verdict = critic_feedback.get("overall_verdict", "PASS")
    retry_target_tools = None
    if verdict == "REVISE" and (critic_retries + 1) <= 1:
        plan = state.get("research_plan") or {}
        requested = plan.get("requested_modules", [])
        requested_tools = {"keyword_research"} | {
            MODULE_TOOL_MAP[m] for m in requested if m in MODULE_TOOL_MAP
        }
        collected = state.get("collected_data") or {}
        retry_target_tools = []
        for t in requested_tools:
            score = confidence.get(t, 0.0)
            err_dict = collected.get(t)
            is_error = isinstance(err_dict, dict) and "error" in err_dict
            is_missing = t not in collected
            if is_missing or is_error or score < 0.4:
                retry_target_tools.append(t)

    return {
        **state,
        "critic_feedback": critic_feedback,
        "execution_metadata": metadata,
        "human_feedback": None,
        "retry_target_tools": retry_target_tools,
    }


def route_after_critic(state: AgentState) -> str:
    """Route based on critic verdict. REVISE with retries available → back to research."""
    feedback = state.get("critic_feedback") or {}
    metadata = state.get("execution_metadata") or {}
    critic_retries = metadata.get("critic_retries", 0)

    verdict = feedback.get("overall_verdict", "PASS")
    if verdict == "REVISE" and critic_retries <= 1:
        logger.info("critic_node: REVISE verdict — routing back to research_agent_node")
        return "research_agent_node"
    return "strategy_generation_node"


# Configurable thresholds
QUALITY_GATE_MIN_KEYWORD_CONFIDENCE = 0.3
QUALITY_GATE_MIN_KEYWORDS = 3

def quality_gate_node(state: AgentState) -> AgentState:
    """
    Deterministic quality gate. Enforces minimum data standards before
    strategy synthesis. If standards are not met and retry budget remains,
    routes back to research_agent_node.

    Gate criteria:
    - keyword_research confidence >= QUALITY_GATE_MIN_KEYWORD_CONFIDENCE
    - at least QUALITY_GATE_MIN_KEYWORDS keyword findings

    Adds data_quality_summary to state for use by strategy_agent_node.
    """
    logger.info("quality_gate_node: evaluating data quality")
    confidence = state.get("confidence_scores") or {}
    findings = state.get("intelligence_findings") or {}
    metadata = state.get("execution_metadata") or {}
    errors = list(state.get("errors", []))

    keyword_confidence = confidence.get("keyword_research", 0.0)
    keyword_count = len(findings.get("keyword_findings", []))

    gate_passed = (
        keyword_confidence >= QUALITY_GATE_MIN_KEYWORD_CONFIDENCE
        and keyword_count >= QUALITY_GATE_MIN_KEYWORDS
    )

    data_limitations: list[str] = []
    if keyword_confidence < QUALITY_GATE_MIN_KEYWORD_CONFIDENCE:
        data_limitations.append(
            f"Keyword research confidence is low ({keyword_confidence:.0%}). "
            "Results may not reflect accurate search volumes."
        )
    if keyword_count < QUALITY_GATE_MIN_KEYWORDS:
        data_limitations.append(
            f"Only {keyword_count} keywords found. "
            "Strategy recommendations are based on limited data."
        )

    # Add data limitations from low-confidence tools
    for tool, score in confidence.items():
        if tool != "keyword_research" and score < 0.4:
            data_limitations.append(
                f"{tool.replace('_', ' ').title()} returned low-confidence data ({score:.0%})."
            )

    data_quality_summary = {
        "gate_passed": gate_passed,
        "keyword_confidence": keyword_confidence,
        "keyword_count": keyword_count,
        "data_limitations": data_limitations,
    }

    logger.info(
        f"quality_gate_node: gate_passed={gate_passed}, "
        f"keyword_confidence={keyword_confidence:.2f}, keyword_count={keyword_count}"
    )

    gate_retries = metadata.get("gate_retries", 0)
    if not gate_passed:
        gate_retries += 1

    retry_target_tools = None
    if not gate_passed and gate_retries <= 1:
        plan = state.get("research_plan") or {}
        requested = plan.get("requested_modules", [])
        requested_tools = {"keyword_research"} | {
            MODULE_TOOL_MAP[m] for m in requested if m in MODULE_TOOL_MAP
        }
        collected = state.get("collected_data") or {}
        retry_target_tools = []
        for t in requested_tools:
            score = confidence.get(t, 0.0)
            err_dict = collected.get(t)
            is_error = isinstance(err_dict, dict) and "error" in err_dict
            is_missing = t not in collected
            if is_missing or is_error or score < 0.4:
                retry_target_tools.append(t)

    return {
        **state,
        "execution_metadata": {
            **metadata,
            "data_quality_summary": data_quality_summary,
            "gate_retries": gate_retries,
        },
        "errors": errors + (data_limitations if not gate_passed else []),
        "human_feedback": None,
        "retry_target_tools": retry_target_tools,
    }


def route_after_quality_gate(state: AgentState) -> str:
    """Gate failed with retry budget → back to research. Gate passed → critic."""
    metadata = state.get("execution_metadata") or {}
    summary = metadata.get("data_quality_summary", {})
    gate_passed = summary.get("gate_passed", True)

    # Count how many times we've been through the gate
    gate_retries = metadata.get("gate_retries", 0)

    if not gate_passed and gate_retries <= 1:
        logger.info("quality_gate_node: gate failed — routing back to research_agent_node")
        return "research_agent_node"

    return "critic_node"


