"""
Report diff computation for Keylytics keyword monitoring.

Compares two consecutive StrategyReport dicts for the same seed keyword
and produces a ReportDiff with keyword score deltas, new/dropped recommendations,
and per-tool confidence score changes.

Usage:
    from src.report_diff import compute_report_diff
    diff = compute_report_diff(prev_report_dict, curr_report_dict, prev_conf, curr_conf)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.logger_config import get_logger
from src.schemas import KeywordDelta, ReportDiff

logger = get_logger(__name__)


def _extract_keyword_scores(
    report: Dict[str, Any],
) -> Dict[str, float]:
    """Extract {keyword: score} mapping from a StrategyReport dict."""
    scores: Dict[str, float] = {}
    for opp in report.get("top_opportunities", []):
        if isinstance(opp, dict) and opp.get("keyword"):
            scores[opp["keyword"]] = float(opp.get("score", 0.0))
    return scores


def _simple_recommendation_similarity(rec_a: str, rec_b: str) -> bool:
    """
    Naive string-matching similarity for recommendations.
    Returns True if the first 40 characters match (same action verb + topic).
    Phase 5 will replace this with LLM-based semantic similarity.
    """
    return rec_a[:40].lower() == rec_b[:40].lower()


def compute_report_diff(
    prev: Dict[str, Any],
    curr: Dict[str, Any],
    prev_confidence: Optional[Dict[str, float]] = None,
    curr_confidence: Optional[Dict[str, float]] = None,
) -> ReportDiff:
    """
    Compare two consecutive StrategyReport dicts and produce a ReportDiff.

    Args:
        prev:             Previous StrategyReport dict.
        curr:             Current StrategyReport dict.
        prev_confidence:  Previous run confidence scores (optional).
        curr_confidence:  Current run confidence scores (optional).

    Returns:
        ReportDiff with keyword deltas, recommendation changes, and confidence deltas.
    """
    seed_keyword = curr.get("seed_keyword") or prev.get("seed_keyword", "")
    prev_scores = _extract_keyword_scores(prev)
    curr_scores = _extract_keyword_scores(curr)

    # ── Keyword deltas ─────────────────────────────────────────────────────
    keyword_deltas: List[KeywordDelta] = []
    all_keywords = set(prev_scores) | set(curr_scores)

    for kw in all_keywords:
        prev_s = prev_scores.get(kw)
        curr_s = curr_scores.get(kw)

        if prev_s is None and curr_s is not None:
            direction = "new"
            delta = curr_s
        elif curr_s is None and prev_s is not None:
            direction = "dropped"
            delta = -prev_s
        else:
            delta = (curr_s or 0.0) - (prev_s or 0.0)
            direction = "improved" if delta >= 0 else "declined"

        keyword_deltas.append(
            KeywordDelta(
                keyword=kw,
                prev_score=prev_s,
                curr_score=curr_s,
                delta=round(delta, 4),
                direction=direction,
            )
        )

    # Sort: new first, then by abs(delta) descending
    keyword_deltas.sort(key=lambda d: (-abs(d.delta), d.direction))

    # ── Recommendation diff ────────────────────────────────────────────────
    prev_recs: List[str] = prev.get("recommendations", []) or []
    curr_recs: List[str] = curr.get("recommendations", []) or []

    new_recs: List[str] = []
    dropped_recs: List[str] = []

    for rec in curr_recs:
        matched = any(_simple_recommendation_similarity(rec, pr) for pr in prev_recs)
        if not matched:
            new_recs.append(rec)

    for rec in prev_recs:
        matched = any(_simple_recommendation_similarity(rec, cr) for cr in curr_recs)
        if not matched:
            dropped_recs.append(rec)

    # ── Confidence score deltas ────────────────────────────────────────────
    prev_conf = prev_confidence or {}
    curr_conf = curr_confidence or {}
    all_tools = set(prev_conf) | set(curr_conf)
    conf_delta: Dict[str, float] = {
        tool: round((curr_conf.get(tool, 0.0) - prev_conf.get(tool, 0.0)), 4)
        for tool in all_tools
    }

    # ── Human-readable summary ─────────────────────────────────────────────
    improved = [d for d in keyword_deltas if d.direction == "improved"]
    declined = [d for d in keyword_deltas if d.direction == "declined"]
    new_kw = [d for d in keyword_deltas if d.direction == "new"]
    dropped_kw = [d for d in keyword_deltas if d.direction == "dropped"]

    summary_parts = []
    if new_kw:
        summary_parts.append(f"{len(new_kw)} new keyword(s) appeared in top opportunities.")
    if dropped_kw:
        summary_parts.append(f"{len(dropped_kw)} keyword(s) dropped out of top opportunities.")
    if improved:
        top = max(improved, key=lambda d: d.delta)
        summary_parts.append(f"Biggest improvement: '{top.keyword}' (+{top.delta:.2f}).")
    if declined:
        worst = min(declined, key=lambda d: d.delta)
        summary_parts.append(f"Biggest decline: '{worst.keyword}' ({worst.delta:.2f}).")
    if new_recs:
        summary_parts.append(f"{len(new_recs)} new recommendation(s) added.")
    if dropped_recs:
        summary_parts.append(f"{len(dropped_recs)} recommendation(s) removed.")
    if not summary_parts:
        summary_parts.append("No significant changes detected between the two reports.")

    summary = " ".join(summary_parts)

    diff = ReportDiff(
        seed_keyword=seed_keyword,
        generated_at=datetime.now(timezone.utc),
        keyword_deltas=keyword_deltas,
        new_recommendations=new_recs,
        dropped_recommendations=dropped_recs,
        confidence_delta=conf_delta,
        summary=summary,
    )
    logger.info(f"compute_report_diff: {seed_keyword} — {summary}")
    return diff


def save_report_diff(
    diff: ReportDiff,
    prev_run_id: Optional[str] = None,
    curr_run_id: Optional[str] = None,
) -> None:
    """Persist a ReportDiff to the report_diffs table."""
    try:
        from src.db_client import connect_db
        from src.models import ReportDiffModel
        from sqlalchemy.orm import Session

        engine = connect_db()
        with Session(engine) as session:
            row = ReportDiffModel(
                seed_keyword=diff.seed_keyword,
                prev_run_id=prev_run_id,
                curr_run_id=curr_run_id,
                diff_json=json.dumps(diff.model_dump(mode="json"), default=str),
                generated_at=diff.generated_at,
            )
            session.add(row)
            session.commit()
        logger.info(f"Saved report diff for seed_keyword={diff.seed_keyword!r}")
    except Exception as e:
        logger.error(f"Failed to save report diff: {e}", exc_info=True)


def get_latest_report_diff(seed_keyword: str) -> Optional[ReportDiff]:
    """Fetch the most recent stored ReportDiff for a keyword."""
    try:
        from src.db_client import connect_db
        from src.models import ReportDiffModel
        from sqlalchemy.orm import Session

        engine = connect_db()
        with Session(engine) as session:
            row = (
                session.query(ReportDiffModel)
                .filter(ReportDiffModel.seed_keyword == seed_keyword)
                .order_by(ReportDiffModel.generated_at.desc())
                .first()
            )
            if not row:
                return None
            data = json.loads(row.diff_json)
            return ReportDiff(**data)
    except Exception as e:
        logger.error(f"Failed to fetch report diff: {e}", exc_info=True)
        return None
