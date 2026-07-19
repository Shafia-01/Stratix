"""
LLM-as-judge evaluator for Keylytics research pipeline outputs.

Uses Gemini at temperature=0.0 to score plan quality, report quality,
and tool reliability for every completed research run.

Results are persisted to the eval_results SQLAlchemy table.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from src.evals.rubrics import (
    PLAN_QUALITY_RUBRIC,
    REPORT_QUALITY_RUBRIC,
    TOOL_RELIABILITY_RUBRIC,
)
from src.logger_config import get_logger
from src.schemas import EvalResult

logger = get_logger(__name__)


from src.llm_config import get_chat_llm

def _get_eval_llm() -> ChatGoogleGenerativeAI:
    """Low-temperature LLM instance for deterministic evaluation."""
    return get_chat_llm(temperature=0.0)


def _parse_eval_response(raw: str) -> Dict[str, Any]:
    """Strip markdown fences and parse the JSON evaluation response."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def _save_eval_result(result: EvalResult) -> None:
    """Persist an EvalResult to the eval_results SQLAlchemy table."""
    try:
        from src.db_client import connect_db
        from src.models import EvalResultModel
        from sqlalchemy.orm import Session

        engine = connect_db()
        with Session(engine) as session:
            row = EvalResultModel(
                run_id=result.run_id,
                eval_type=result.eval_type,
                score=result.score,
                rationale=result.rationale,
                dimension_scores=json.dumps(result.dimension_scores),
                evaluated_at=result.evaluated_at,
            )
            session.add(row)
            session.commit()
        logger.info(f"Saved eval result: run_id={result.run_id}, type={result.eval_type}, score={result.score:.2f}")
    except Exception as e:
        logger.error(f"Failed to save eval result: {e}", exc_info=True)


class KeylyticsEvaluator:
    """
    LLM-as-judge evaluator for the Keylytics research pipeline.

    All methods:
    1. Build an evaluation prompt using the relevant rubric.
    2. Call Gemini at temperature=0.0.
    3. Parse the JSON response.
    4. Return a normalised EvalResult (score 0.0–1.0).
    5. Persist to DB.
    """

    def __init__(self) -> None:
        self._llm = _get_eval_llm()

    def _call_llm(self, rubric: str, content: str) -> Dict[str, Any]:
        """Call the evaluator LLM and return the parsed JSON response."""
        messages = [
            SystemMessage(content=rubric),
            HumanMessage(content=content),
        ]
        response = self._llm.invoke(messages)
        return _parse_eval_response(response.content)

    def evaluate_plan(self, run_id: str, plan: Dict[str, Any]) -> EvalResult:
        """Evaluate research plan quality (objectives, modules, max_keywords)."""
        if not plan:
            return self._fallback_result(run_id, "plan_quality", "No plan provided")

        try:
            data = self._call_llm(
                PLAN_QUALITY_RUBRIC,
                f"Research Plan:\n{json.dumps(plan, indent=2, default=str)}",
            )
            raw_score = int(data.get("score", 1))  # 1–5
            normalized = round((raw_score - 1) / 4.0, 2)  # 0.0–1.0
            dim_scores = {
                k: round((int(v) - 1) / 4.0, 2)
                for k, v in (data.get("dimension_scores") or {}).items()
                if v is not None
            }
            result = EvalResult(
                run_id=run_id,
                eval_type="plan_quality",
                score=normalized,
                rationale=data.get("rationale", ""),
                dimension_scores=dim_scores,
                evaluated_at=datetime.now(timezone.utc),
            )
        except Exception as e:
            logger.warning(f"evaluate_plan failed for run_id={run_id}: {e}")
            result = self._fallback_result(run_id, "plan_quality", str(e))

        _save_eval_result(result)
        return result

    def evaluate_report(
        self,
        run_id: str,
        report: Dict[str, Any],
        confidence_scores: Dict[str, float],
    ) -> EvalResult:
        """Evaluate strategy report quality (data grounding, actionability, etc.)."""
        if not report:
            return self._fallback_result(run_id, "report_quality", "No report provided")

        content = (
            f"Strategy Report:\n{json.dumps(report, indent=2, default=str)}\n\n"
            f"Confidence Scores:\n{json.dumps(confidence_scores, indent=2)}"
        )

        try:
            data = self._call_llm(REPORT_QUALITY_RUBRIC, content)
            raw_score = int(data.get("score", 1))
            normalized = round((raw_score - 1) / 4.0, 2)
            dim_scores = {
                k: round((int(v) - 1) / 4.0, 2)
                for k, v in (data.get("dimension_scores") or {}).items()
                if v is not None
            }
            result = EvalResult(
                run_id=run_id,
                eval_type="report_quality",
                score=normalized,
                rationale=data.get("rationale", ""),
                dimension_scores=dim_scores,
                evaluated_at=datetime.now(timezone.utc),
            )
        except Exception as e:
            logger.warning(f"evaluate_report failed for run_id={run_id}: {e}")
            result = self._fallback_result(run_id, "report_quality", str(e))

        _save_eval_result(result)
        return result

    def evaluate_tool_reliability(
        self,
        run_id: str,
        collected_data: Dict[str, Any],
    ) -> EvalResult:
        """Evaluate the completeness and coherence of tool outputs."""
        if not collected_data:
            return self._fallback_result(run_id, "tool_reliability", "No tool data provided")

        # Summarise tool outputs without sending full raw data to the evaluator
        summary: Dict[str, Any] = {}
        for tool, data in collected_data.items():
            if isinstance(data, dict):
                summary[tool] = {
                    "has_error": "error" in data,
                    "top_keys": list(data.keys())[:5],
                    "items_count": len(data.get("items", data.get("clusters", data.get("opportunities", [])))),
                }
            else:
                summary[tool] = {"has_error": True, "raw_type": type(data).__name__}

        try:
            data = self._call_llm(
                TOOL_RELIABILITY_RUBRIC,
                f"Tool Output Summary:\n{json.dumps(summary, indent=2)}",
            )
            raw_score = int(data.get("score", 1))
            normalized = round((raw_score - 1) / 4.0, 2)
            raw_dim = data.get("dimension_scores") or {}
            dim_scores = {
                k: round((int(v) - 1) / 4.0, 2)
                for k, v in raw_dim.items()
                if v is not None
            }
            result = EvalResult(
                run_id=run_id,
                eval_type="tool_reliability",
                score=normalized,
                rationale=data.get("rationale", ""),
                dimension_scores=dim_scores,
                evaluated_at=datetime.now(timezone.utc),
            )
        except Exception as e:
            logger.warning(f"evaluate_tool_reliability failed for run_id={run_id}: {e}")
            result = self._fallback_result(run_id, "tool_reliability", str(e))

        _save_eval_result(result)
        return result

    @staticmethod
    def _fallback_result(
        run_id: str,
        eval_type: str,
        reason: str,
    ) -> EvalResult:
        """Return a zero-score fallback EvalResult when evaluation fails."""
        return EvalResult(
            run_id=run_id,
            eval_type=eval_type,  # type: ignore[arg-type]
            score=0.0,
            rationale=f"Evaluation unavailable: {reason}",
            dimension_scores={},
            evaluated_at=datetime.now(timezone.utc),
        )
