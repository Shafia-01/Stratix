"""
FastAPI dependency providers for Keylytics API.
"""

from sqlalchemy.engine import Engine
from src.db_client import connect_db


def get_db_session() -> Engine:
    """
    FastAPI dependency that returns a connected SQLAlchemy engine.
    Ensures the database schema exists before returning.
    Usage: engine = Depends(get_db_session)
    """
    return connect_db()


import os
from fastapi import HTTPException, Security
from fastapi.security.api_key import APIKeyHeader

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Validates the X-API-Key header against STRATIX_API_KEY (or STRATIX_AI_API_KEY, KEYLYTICS_API_KEY) env var.
    If neither is set, authentication is disabled (dev mode).
    """
    expected_key = os.getenv("STRATIX_API_KEY") or os.getenv("STRATIX_AI_API_KEY") or os.getenv("KEYLYTICS_API_KEY", "")
    if not expected_key:
        # Auth disabled in development if env var not set
        return "dev-mode"
    if api_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")
    return api_key
