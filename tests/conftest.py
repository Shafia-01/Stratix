import pytest
import os
import src.db_client

@pytest.fixture(autouse=True)
def tmp_db_path(tmp_path, monkeypatch):
    db_file = tmp_path / "test_keylytics.db"
    monkeypatch.setenv("KEYLYTICS_DB_PATH", str(db_file))
    # Reset engine singleton in db_client
    src.db_client._engine = None
    src.db_client.DB_PATH = str(db_file)
    yield db_file
    # Cleanup after test
    src.db_client._engine = None
    if db_file.exists():
        try:
            os.remove(db_file)
        except Exception:
            pass
