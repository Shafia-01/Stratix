import sqlite3
from sqlalchemy import event
from sqlalchemy.engine import Engine

def apply_sqlite_pragmas(conn_or_engine):
    """
    Apply WAL journal mode and 5000ms busy timeout to raw sqlite3 connections or SQLAlchemy engines.
    """
    if isinstance(conn_or_engine, Engine):
        @event.listens_for(conn_or_engine, "connect", insert=True)
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()
    else:
        try:
            conn_or_engine.execute("PRAGMA journal_mode=WAL")
            conn_or_engine.execute("PRAGMA busy_timeout=5000")
        except AttributeError:
            cursor = conn_or_engine.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()
