import pytest
import sqlite3
import threading
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.db_client import connect_db, _configure_sqlite_pragmas
from src.db_utils import apply_sqlite_pragmas
from src.models import Keyword
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from sqlalchemy import event

@pytest.mark.integration
def test_sqlite_concurrency_no_locks(tmp_db_path):
    # Initialize the three connection types

    # 1. DB Client (SQLAlchemy)
    db_engine = connect_db()

    # 2. Scheduler Jobstore (SQLAlchemy)
    jobstore = SQLAlchemyJobStore(url=f"sqlite:///{tmp_db_path}")
    event.listen(jobstore.engine, "connect", _configure_sqlite_pragmas)

    # Create the tables
    with jobstore.engine.connect() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS test_scheduler_jobs (id VARCHAR(256) PRIMARY KEY, data BLOB)"))
        conn.commit()

    # 3. Raw sqlite3 connection (like graph checkpointer)
    raw_conn = sqlite3.connect(tmp_db_path, check_same_thread=False)
    apply_sqlite_pragmas(raw_conn)
    raw_conn.execute("CREATE TABLE IF NOT EXISTS test_checkpoints (thread_id TEXT PRIMARY KEY, checkpoint_data TEXT)")
    raw_conn.commit()

    errors = []

    def writer_db_client(idx):
        try:
            with Session(db_engine) as session:
                kw = Keyword(
                    seed="concurrency",
                    keyword=f"kw_{idx}",
                    volume=100.0,
                    competition=0.5,
                    cpc=1.5,
                    trend=10.0,
                    score=60.0,
                    difficulty="Medium",
                    intent="Informational",
                    competitors="[]"
                )
                session.add(kw)
                session.commit()
        except Exception as e:
            errors.append(e)

    def writer_scheduler(idx):
        try:
            with jobstore.engine.connect() as conn:
                conn.execute(
                    text("INSERT INTO test_scheduler_jobs (id, data) VALUES (:id, :data)"),
                    {"id": f"job_{idx}", "data": b"dummy_data"}
                )
                conn.commit()
        except Exception as e:
            errors.append(e)

    def writer_raw_checkpointer(idx):
        try:
            conn = sqlite3.connect(tmp_db_path, timeout=5.0)
            apply_sqlite_pragmas(conn)
            conn.execute("INSERT INTO test_checkpoints (thread_id, checkpoint_data) VALUES (?, ?)", (f"thread_{idx}", "data"))
            conn.commit()
            conn.close()
        except Exception as e:
            errors.append(e)

    threads = []
    # Burst of ~20 concurrent writes to each
    for i in range(20):
        t1 = threading.Thread(target=writer_db_client, args=(i,))
        t2 = threading.Thread(target=writer_scheduler, args=(i,))
        t3 = threading.Thread(target=writer_raw_checkpointer, args=(i,))
        threads.extend([t1, t2, t3])

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    # Close raw connection
    raw_conn.close()

    # Assert no locking errors occurred
    assert len(errors) == 0, f"Concurrency errors occurred: {errors}"
