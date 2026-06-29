import pytest
import os
import pandas as pd
from src.agent import run_agent
from src.lightweight_agent import run_lightweight_agent
from src.schemas import KeywordFinding

@pytest.fixture(autouse=True)
def mock_agent_dependencies(monkeypatch, mock_gemini, mock_http):
    """Mock functions that make external calls during agent execution."""
    # Mock trends client
    monkeypatch.setattr("src.agent.get_trend_score", lambda kw: 50.0)
    # Mock competitor client
    monkeypatch.setattr("src.agent.get_competitor_data", lambda kw: [{"domain": "competitor.com", "rank": 1}])
    # Mock intent classifier
    monkeypatch.setattr("src.agent.classify_intent", lambda kw: "Informational")
    monkeypatch.setattr("src.lightweight_agent.get_keyword_metrics", lambda kw: {
        "volume": 2000, "competition": 0.4, "cpc": 1.2, "data_source": "live"
    })

@pytest.mark.integration
def test_run_lightweight_agent_pipeline(tmp_db_path):
    results = run_lightweight_agent("organic coffee", max_keywords=3)
    assert len(results) > 0
    # Validate structure using Pydantic schema validation
    for res in results:
        # Pydantic validation
        validated = KeywordFinding.model_validate(res)
        assert validated.seed == "organic coffee"
        assert validated.volume == 2000.0


@pytest.mark.integration
def test_run_agent_pipeline(tmp_db_path, tmp_path, monkeypatch):
    # Mock path for temp cache files to avoid creating files in project directory
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(exist_ok=True)
    monkeypatch.setattr(os, "makedirs", lambda path, exist_ok=True: cache_dir.mkdir(exist_ok=True, parents=True))

    # Mock pd.DataFrame.to_csv to write to temp path
    original_to_csv = pd.DataFrame.to_csv
    def mock_to_csv(self, path, *args, **kwargs):
        filename = os.path.basename(path)
        return original_to_csv(self, cache_dir / filename, *args, **kwargs)
    monkeypatch.setattr(pd.DataFrame, "to_csv", mock_to_csv)

    results = run_agent("organic coffee", max_keywords=2)
    assert len(results) > 0

    # Validate structure using Pydantic schema
    for res in results:
        validated = KeywordFinding.model_validate(res)
        assert validated.seed == "organic coffee"
        assert validated.trend == 50.0
        assert validated.competitors[0].domain == "competitor.com"
