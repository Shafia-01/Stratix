import pytest
from sqlalchemy import inspect
from src.db_client import connect_db, save_to_db, fetch_past_results, verify_database_schema, get_cached_intent, save_intent_to_db

def test_connect_db_creates_tables():
    engine = connect_db()
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "keywords" in tables
    assert "intent_cache" in tables

def test_save_to_db_and_fetch():
    record = {
        "seed": "testseed",
        "keyword": "my keyword",
        "volume": 500,
        "competition": 0.4,
        "cpc": 1.2,
        "trend": 75,
        "score": 0.65,
        "difficulty": "Medium",
        "intent": "Commercial",
        "competitors": ["comp1.com", "comp2.com"]
    }
    
    save_to_db([record])
    df = fetch_past_results(limit=1)
    
    assert not df.empty
    assert df.iloc[0]["keyword"] == "my keyword"
    assert df.iloc[0]["seed"] == "testseed"

def test_save_to_db_upsert():
    record1 = {
        "seed": "testseed",
        "keyword": "my keyword",
        "volume": 500,
        "competition": 0.4,
        "cpc": 1.2,
        "trend": 75,
        "score": 0.65,
        "difficulty": "Medium",
        "intent": "Commercial"
    }
    
    record2 = {
        "seed": "testseed",
        "keyword": "my keyword",
        "volume": 600,  # updated volume
        "competition": 0.4,
        "cpc": 1.2,
        "trend": 75,
        "score": 0.70,  # updated score
        "difficulty": "Medium",
        "intent": "Commercial"
    }
    
    save_to_db([record1])
    save_to_db([record2])
    
    df = fetch_past_results(limit=10)
    assert len(df) == 1
    assert df.iloc[0]["volume"] == 600
    assert df.iloc[0]["score"] == 0.70

def test_intent_cache_round_trip():
    save_intent_to_db("test_keyword", "Informational")
    intent = get_cached_intent("test_keyword")
    assert intent == "Informational"

def test_verify_database_schema():
    assert verify_database_schema() is True
