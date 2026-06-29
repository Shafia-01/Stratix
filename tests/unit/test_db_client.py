import pytest
import os
import glob
import json
import pandas as pd
from sqlalchemy import inspect, create_engine
from src.db_client import (
    connect_db,
    save_to_db,
    fetch_past_results,
    verify_database_schema,
    get_cached_intent,
    save_intent_to_db
)
import src.db_client

@pytest.mark.unit
def test_connect_db_creates_tables(tmp_db_path):
    engine = connect_db()
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "keywords" in tables
    assert "intent_cache" in tables


@pytest.mark.unit
def test_save_to_db_and_intent_normalization(tmp_db_path):
    # Test normalization of "... Intent" stripping and >50 char truncation
    records = [
        {
            "seed": "coffee",
            "keyword": "best organic coffee",
            "volume": 1200,
            "competition": 0.6,
            "cpc": 1.5,
            "trend": 20,
            "score": 0.75,
            "difficulty": "Medium",
            "intent": "Commercial Intent", # Should strip "Intent" -> "Commercial"
            "competitors": ["comp1.com", "comp2.com"]
        },
        {
            "seed": "tea",
            "keyword": "best organic green tea",
            "volume": 800,
            "competition": 0.4,
            "cpc": 1.0,
            "trend": 10,
            "score": 0.6,
            "difficulty": "Medium",
            "intent": "A" * 60, # Should truncate to 50 chars
            "competitors": []
        }
    ]
    save_to_db(records)

    # Fetch results
    df = fetch_past_results()
    assert len(df) == 2

    # Assertions
    row1 = df[df["keyword"] == "best organic coffee"].iloc[0]
    assert row1["intent"] == "Commercial"
    assert json.loads(row1["competitors"]) == ["comp1.com", "comp2.com"]

    row2 = df[df["keyword"] == "best organic green tea"].iloc[0]
    assert row2["intent"] == "A" * 50


@pytest.mark.unit
def test_save_to_db_failure_path_csv_fallback(tmp_db_path, monkeypatch, tmp_path):
    # Force a database error by monkeypatching connect_db to raise or corrupting session/engine
    monkeypatch.setattr(src.db_client, "connect_db", lambda: create_engine("sqlite:///invalid_path/nonexistent.db"))

    # We should change the current working directory or ensure cache folder goes to tmp_path
    cache_dir = tmp_path / "cache"
    monkeypatch.setattr(os, "makedirs", lambda path, exist_ok=True: cache_dir.mkdir(exist_ok=True, parents=True))

    # Monkeypatch pandas to_csv destination
    original_to_csv = pd.DataFrame.to_csv
    def mock_to_csv(self, path, *args, **kwargs):
        # Redirect to tmp_path/cache
        filename = os.path.basename(path)
        return original_to_csv(self, cache_dir / filename, *args, **kwargs)
    monkeypatch.setattr(pd.DataFrame, "to_csv", mock_to_csv)

    records = [{"seed": "test", "keyword": "fallback kw", "volume": 100}]

    # Should not raise exception
    save_to_db(records)

    # Assert CSV file is created in tmp cache
    csv_files = list(cache_dir.glob("keywords_*.csv"))
    assert len(csv_files) == 1
    df_csv = pd.read_csv(csv_files[0])
    assert df_csv.iloc[0]["keyword"] == "fallback kw"


@pytest.mark.unit
def test_fetch_past_results_empty_db(tmp_db_path):
    # Empty DB fetch should return all required columns with proper default fillers
    df = fetch_past_results()
    assert isinstance(df, pd.DataFrame)
    assert df.empty

    # Check that required columns exist in the empty dataframe's schema/columns
    required_cols = ['seed', 'keyword', 'volume', 'competition', 'cpc', 'score', 'difficulty']
    for col in required_cols:
        assert col in df.columns


@pytest.mark.unit
def test_fetch_past_results_failure_fallback_csv(tmp_db_path, monkeypatch, tmp_path):
    # Force DB fetch error
    monkeypatch.setattr(src.db_client, "connect_db", lambda: create_engine("sqlite:///invalid_path/nonexistent.db"))

    # Create a dummy CSV in the cache folder
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(exist_ok=True)
    # Monkeypatch glob and reading from cache to use our tmp_path cache
    monkeypatch.setattr(glob, "glob", lambda pattern: [str(p) for p in cache_dir.glob("*.csv")])

    dummy_csv = cache_dir / "keywords_20260613_120000.csv"
    df_dummy = pd.DataFrame([{
        "seed": "coffee",
        "keyword": "cached coffee",
        "volume": 200,
        "competition": 0.5,
        "cpc": 1.0,
        "score": 0.5,
        "difficulty": "Medium"
    }])
    df_dummy.to_csv(dummy_csv, index=False)

    df = fetch_past_results()
    assert len(df) == 1
    assert df.iloc[0]["keyword"] == "cached coffee"


@pytest.mark.unit
def test_verify_database_schema_valid_and_invalid(tmp_db_path, monkeypatch):
    # Freshly created DB has valid schema
    assert verify_database_schema() is True

    from sqlalchemy import text
    engine = connect_db()
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE keywords;"))
        conn.execute(text("CREATE TABLE keywords (id INTEGER PRIMARY KEY, keyword VARCHAR UNIQUE);"))
        conn.commit() # Commit transaction if needed

    assert verify_database_schema() is False


@pytest.mark.unit
def test_intent_cache_round_trip(tmp_db_path):
    # Save intent
    save_intent_to_db("fresh keyword", "Navigational")

    # Retrieve intent
    intent = get_cached_intent("fresh keyword")
    assert intent == "Navigational"
