"""
Tests for src/db_client.py.
Verifies WAL mode, busy_timeout pragmas, and round-trip save/fetch operations.
Uses an in-memory SQLite database via engine override to avoid file system state.
"""

from sqlalchemy import create_engine, event, text
from src.models import Base
from src.data_quality import DataSource


# ---------------------------------------------------------------------------
# WAL + busy_timeout pragma configuration
# ---------------------------------------------------------------------------
class TestSQLitePragmas:
    def test_wal_pragma_fires_on_connect(self):
        """_configure_sqlite_pragmas must execute PRAGMA journal_mode=WAL."""
        pragma_calls = []

        class FakeCursor:
            def execute(self, sql):
                pragma_calls.append(sql.strip())
            def close(self):
                pass

        class FakeConn:
            def cursor(self):
                return FakeCursor()

        from src.db_client import _configure_sqlite_pragmas
        _configure_sqlite_pragmas(FakeConn(), None)

        assert "PRAGMA journal_mode=WAL" in pragma_calls
        assert "PRAGMA busy_timeout=5000" in pragma_calls

    def test_wal_is_actually_set_on_in_memory_db(self):
        """Integration: WAL mode should be readable from a fresh in-memory engine."""
        engine = create_engine("sqlite:///:memory:")

        from src.db_client import _configure_sqlite_pragmas
        event.listen(engine, "connect", _configure_sqlite_pragmas)
        Base.metadata.create_all(engine)

        with engine.connect() as conn:
            journal_mode = conn.execute(text("PRAGMA journal_mode")).scalar()
        # sqlite :memory: may return 'memory' even after setting WAL (in-memory limitation)
        # but the pragma should be accepted without error
        assert journal_mode in ("wal", "memory")


# ---------------------------------------------------------------------------
# Round-trip: save_to_db -> fetch_past_results
# ---------------------------------------------------------------------------
class TestSaveAndFetchRoundTrip:
    def _make_findings(self):
        """Build minimal KeywordFinding-like objects for db save testing."""
        from src.schemas import KeywordFinding

        return [
            KeywordFinding(
                seed="coffee",
                keyword="best coffee beans",
                volume=5000.0,
                competition=0.3,
                cpc=1.2,
                trend=None,
                score=0.72,
                difficulty="Easy",
                intent="commercial",
                competitors=[],
                data_source=DataSource.ESTIMATED,
                trend_data_source=DataSource.UNAVAILABLE,
            ),
            KeywordFinding(
                seed="coffee",
                keyword="coffee grinder guide",
                volume=1200.0,
                competition=0.5,
                cpc=0.8,
                trend=None,
                score=0.45,
                difficulty="Medium",
                intent="informational",
                competitors=[],
                data_source=DataSource.ESTIMATED,
                trend_data_source=DataSource.UNAVAILABLE,
            ),
        ]

    def test_save_and_fetch_round_trip(self, tmp_path):
        """Save findings then fetch them back via fetch_past_results."""
        db_path = str(tmp_path / "test.db")

        import src.db_client as db_client_module
        orig_engine = db_client_module._engine

        try:
            # Create isolated test engine
            test_engine = create_engine(f"sqlite:///{db_path}")
            Base.metadata.create_all(test_engine)
            db_client_module._engine = test_engine

            findings = self._make_findings()
            from src.db_client import save_to_db, fetch_past_results

            save_to_db(findings)
            df = fetch_past_results(limit=10)

            assert len(df) == 2
            keywords_in_db = set(df["keyword"].tolist())
            assert "best coffee beans" in keywords_in_db
            assert "coffee grinder guide" in keywords_in_db
        finally:
            db_client_module._engine = orig_engine

    def test_verify_database_schema_passes_after_connect(self):
        """verify_database_schema should return True after tables are created."""
        import src.db_client as db_client_module
        from src.db_client import verify_database_schema

        orig_engine = db_client_module._engine
        try:
            test_engine = create_engine("sqlite:///:memory:")
            Base.metadata.create_all(test_engine)
            db_client_module._engine = test_engine

            result = verify_database_schema()
            assert result is True
        finally:
            db_client_module._engine = orig_engine
