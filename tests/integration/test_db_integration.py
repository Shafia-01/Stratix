import pytest
from src.db_client import save_to_db, fetch_past_results, verify_database_schema

@pytest.mark.integration
def test_db_client_integration_round_trip(tmp_db_path):
    # 1. Verify fresh DB schema is valid
    assert verify_database_schema() is True

    # 2. Insert records
    records = [
        {
            "seed": "soap",
            "keyword": "organic soap recipe",
            "volume": 200,
            "competition": 0.3,
            "cpc": 0.8,
            "trend": 15.0,
            "score": 0.65,
            "difficulty": "Medium",
            "intent": "Informational",
            "competitors": ["comp1.com", "comp2.com"]
        }
    ]
    save_to_db(records)

    # 3. Retrieve and assert correctness
    df = fetch_past_results()
    assert len(df) == 1
    assert df.iloc[0]["keyword"] == "organic soap recipe"
    assert df.iloc[0]["seed"] == "soap"
    assert df.iloc[0]["volume"] == 200.0
    assert df.iloc[0]["difficulty"] == "Medium"
    assert df.iloc[0]["intent"] == "Informational"
