"""
Health check route for Keylytics API.
GET /health → {"status": "ok", "db": bool, "gemini": bool}
"""

import os
from fastapi import APIRouter
from src.db_client import connect_db, verify_database_schema
from src.logger_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/health", tags=["Health"])
async def health_check() -> dict:
    """
    Liveness + readiness probe.
    - db: True if SQLite engine connects and schema is intact.
    - gemini: True if GEMINI_API_KEY env var is set and non-empty.
    """
    # --- DB check ---
    db_ok = False
    try:
        connect_db()
        db_ok = verify_database_schema()
    except Exception as exc:
        logger.warning(f"Health check: DB unavailable — {exc}")

    # --- Gemini API key presence check ---
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    gemini_ok = bool(gemini_key and gemini_key.strip())

    return {"status": "ok", "db": db_ok, "gemini": gemini_ok}
