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
