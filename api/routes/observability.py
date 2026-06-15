"""
FastAPI observability routes for Keylytics.

GET /metrics         — Prometheus-compatible text format metrics
GET /health/detailed — JSON component health check with eval scores and DB stats
"""
import os
from typing import Any, Dict, List

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from src.logger_config import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Observability"])


@router.get("/metrics", response_class=PlainTextResponse)
async def get_metrics_prometheus() -> str:
    """
    Expose all Keylytics metrics in Prometheus text exposition format.
    Compatible with Prometheus scrape targets and Grafana data sources.
    """
    try:
        from src.metrics import get_metrics
        return get_metrics().to_prometheus_text()
    except Exception as e:
        logger.error(f"Metrics endpoint failed: {e}", exc_info=True)
        return f"# ERROR: {e}\n"


@router.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """
    Extended health check returning:
    - Component status (DB, Gemini API, LangGraph)
    - Recent eval score averages
    - Active monitoring job count
    - DB record counts
    - In-memory metrics summary
    """
    health: Dict[str, Any] = {
        "status": "ok",
        "components": {},
        "eval_scores": {},
        "monitoring": {},
        "database": {},
        "metrics_summary": {},
    }

    # ── DB health ──────────────────────────────────────────────────────────
    try:
        from src.db_client import connect_db, verify_database_schema
        from src.models import Keyword, EvalResultModel, MonitoringJobModel
        from sqlalchemy.orm import Session

        connect_db()
        db_ok = verify_database_schema()
        health["components"]["database"] = "ok" if db_ok else "schema_error"

        engine = connect_db()
        with Session(engine) as session:
            kw_count = session.query(Keyword).count()
            eval_count = session.query(EvalResultModel).count()
            job_count = session.query(MonitoringJobModel).count()

        health["database"] = {
            "keywords": kw_count,
            "eval_results": eval_count,
            "monitoring_jobs": job_count,
        }
    except Exception as e:
        health["components"]["database"] = f"error: {str(e)[:100]}"
        logger.warning(f"detailed health: DB error — {e}")

    # ── Gemini API key ─────────────────────────────────────────────────────
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    health["components"]["gemini_api"] = "ok" if gemini_key.strip() else "missing_key"

    # ── LangGraph ─────────────────────────────────────────────────────────
    try:
        from src.graph.graph import get_compiled_graph
        get_compiled_graph()
        health["components"]["langgraph"] = "ok"
    except Exception as e:
        health["components"]["langgraph"] = f"error: {str(e)[:100]}"

    # ── Recent eval scores (last 10 runs) ─────────────────────────────────
    try:
        from src.db_client import connect_db
        from src.models import EvalResultModel
        from sqlalchemy.orm import Session

        engine = connect_db()
        with Session(engine) as session:
            recent_evals = (
                session.query(EvalResultModel)
                .order_by(EvalResultModel.evaluated_at.desc())
                .limit(30)
                .all()
            )
        by_type: Dict[str, List[float]] = {}
        for e in recent_evals:
            by_type.setdefault(e.eval_type, []).append(e.score)
        health["eval_scores"] = {
            t: round(sum(scores) / len(scores), 3) if scores else None
            for t, scores in by_type.items()
        }
    except Exception as e:
        health["eval_scores"] = {"error": str(e)[:100]}

    # ── Monitoring jobs ────────────────────────────────────────────────────
    try:
        from src.db_client import connect_db
        from src.models import MonitoringJobModel
        from sqlalchemy.orm import Session

        engine = connect_db()
        with Session(engine) as session:
            active_jobs = (
                session.query(MonitoringJobModel)
                .filter(MonitoringJobModel.status == "active")
                .count()
            )
        health["monitoring"]["active_jobs"] = active_jobs

        # Update gauge metric
        from src.metrics import get_metrics
        get_metrics().gauge("keylytics_monitoring_jobs_active", float(active_jobs))

    except Exception as e:
        health["monitoring"] = {"error": str(e)[:100]}

    # ── In-memory metrics summary ──────────────────────────────────────────
    try:
        from src.metrics import get_metrics
        health["metrics_summary"] = get_metrics().get_summary()
    except Exception as e:
        health["metrics_summary"] = {"error": str(e)[:100]}

    # Overall status
    component_statuses = health["components"].values()
    if any("error" in str(s) for s in component_statuses):
        health["status"] = "degraded"

    return health
