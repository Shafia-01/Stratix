"""
FastAPI routes for LLM evaluation results.

GET /evals/{run_id}             — All EvalResults for a specific research run
GET /evals/trends/{seed_keyword} — Eval score trends over the last 10 runs
"""
from typing import Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.logger_config import get_logger
from src.schemas import EvalResult

logger = get_logger(__name__)
router = APIRouter(prefix="/evals", tags=["Evaluations"])


class EvalTrendPoint(BaseModel):
    """Single data point in an eval score trend series."""
    run_id: str
    evaluated_at: str
    plan_score: float
    report_score: float
    tool_score: float


@router.get("/{run_id}", response_model=List[EvalResult])
async def get_run_evals(run_id: str) -> List[EvalResult]:
    """
    Return all EvalResult objects for a specific research run.
    Includes plan_quality, report_quality, and tool_reliability evaluations.
    """
    try:
        from src.db_client import connect_db
        from src.models import EvalResultModel
        from sqlalchemy.orm import Session
        import json

        engine = connect_db()
        with Session(engine) as session:
            rows = (
                session.query(EvalResultModel)
                .filter(EvalResultModel.run_id == run_id)
                .order_by(EvalResultModel.evaluated_at.asc())
                .all()
            )
            if not rows:
                raise HTTPException(
                    status_code=404,
                    detail=f"No evaluations found for run_id='{run_id}'.",
                )
            results = []
            for r in rows:
                dim_scores = {}
                if r.dimension_scores:
                    try:
                        dim_scores = json.loads(r.dimension_scores)
                    except Exception:
                        pass
                results.append(
                    EvalResult(
                        run_id=r.run_id,
                        eval_type=r.eval_type,
                        score=r.score,
                        rationale=r.rationale or "",
                        dimension_scores=dim_scores,
                        evaluated_at=r.evaluated_at,
                    )
                )
            return results
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_run_evals failed for run_id={run_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends/{seed_keyword}", response_model=List[EvalTrendPoint])
async def get_eval_trends(seed_keyword: str) -> List[EvalTrendPoint]:
    """
    Return evaluation score trends for a keyword over the last 10 completed runs.
    Each trend point has plan_score, report_score, and tool_score for comparison.
    """
    try:
        from src.db_client import connect_db
        from src.models import EvalResultModel, ResearchRunLog
        from sqlalchemy.orm import Session

        engine = connect_db()
        with Session(engine) as session:
            # Get last 10 run_ids for this keyword
            run_rows = (
                session.query(ResearchRunLog.run_id, ResearchRunLog.completed_at)
                .filter(
                    ResearchRunLog.seed_keyword == seed_keyword,
                    ResearchRunLog.status == "completed",
                )
                .order_by(ResearchRunLog.completed_at.desc())
                .limit(10)
                .all()
            )
            if not run_rows:
                raise HTTPException(
                    status_code=404,
                    detail=f"No completed runs found for keyword='{seed_keyword}'.",
                )

            trends: List[EvalTrendPoint] = []
            for run_id, completed_at in reversed(run_rows):  # chronological order
                evals = (
                    session.query(EvalResultModel)
                    .filter(EvalResultModel.run_id == run_id)
                    .all()
                )
                score_map: Dict[str, float] = {e.eval_type: e.score for e in evals}
                trends.append(
                    EvalTrendPoint(
                        run_id=run_id,
                        evaluated_at=completed_at.isoformat() if completed_at else "",
                        plan_score=score_map.get("plan_quality", 0.0),
                        report_score=score_map.get("report_quality", 0.0),
                        tool_score=score_map.get("tool_reliability", 0.0),
                    )
                )
            return trends
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_eval_trends failed for keyword={seed_keyword}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
