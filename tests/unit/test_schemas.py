import pytest
from datetime import datetime, timezone
from pydantic import ValidationError
from src.schemas import (
    CompetitorEntry,
    KeywordFinding,
    OpportunityScore,
    ResearchPlan,
    MarketState
)
from src.data_quality import DataSource

@pytest.mark.unit
def test_competitor_entry_valid():
    data = {
        "domain": "example.com",
        "rank": 1,
        "title": "Example Title",
        "url": "https://example.com"
    }
    entry = CompetitorEntry(**data)
    assert entry.domain == "example.com"
    assert entry.rank == 1
    assert entry.title == "Example Title"
    assert entry.url == "https://example.com"


@pytest.mark.unit
def test_keyword_finding_valid_and_validation():
    data = {
        "seed": "coffee",
        "keyword": "best organic coffee",
        "volume": 1200.0,
        "competition": 0.8,
        "cpc": 1.5,
        "trend": 0.05,
        "score": 0.75,
        "difficulty": "Medium",
        "intent": "Commercial",
        "competitors": [{"domain": "comp.com", "rank": 2}],
        "data_source": "live",
        "trend_data_source": "cached"
    }
    finding = KeywordFinding(**data)
    assert finding.keyword == "best organic coffee"
    assert finding.volume == 1200.0
    assert finding.score == 0.75
    assert finding.difficulty == "Medium"
    assert finding.data_source == DataSource.LIVE

    # JSON round trip
    json_str = finding.model_dump_json()
    parsed = KeywordFinding.model_validate_json(json_str)
    assert parsed.keyword == finding.keyword
    assert parsed.data_source == DataSource.LIVE

    # Negative volume validation
    data["volume"] = -10.0
    with pytest.raises(ValidationError):
        KeywordFinding(**data)

    # Out of bounds score
    data["volume"] = 1200.0
    data["score"] = -1.5
    with pytest.raises(ValidationError):
        KeywordFinding(**data)

    # Invalid difficulty
    data["score"] = 0.75
    data["difficulty"] = "SuperHard"
    with pytest.raises(ValidationError):
        KeywordFinding(**data)


@pytest.mark.unit
def test_opportunity_score_validation():
    data = {
        "score": 0.85,
        "difficulty": "Easy",
        "mode": "standard",
        "volume": 5000.0,
        "cpc": 2.5,
        "competition": 0.3
    }
    score = OpportunityScore(**data)
    assert score.score == 0.85
    assert score.difficulty == "Easy"

    data["score"] = -0.1
    with pytest.raises(ValidationError):
        OpportunityScore(**data)


@pytest.mark.unit
def test_research_plan_validation():
    data = {
        "seed_keyword": "organic soap",
        "objectives": ["find keywords", "analyze competition"],
        "requested_modules": ["keyword_discovery", "topic_clustering"],
        "max_keywords": 10,
        "created_at": datetime.now(timezone.utc)
    }
    plan = ResearchPlan(**data)
    assert plan.max_keywords == 10

    # max_keywords out of bounds
    data["max_keywords"] = 0
    with pytest.raises(ValidationError):
        ResearchPlan(**data)

    data["max_keywords"] = 100
    with pytest.raises(ValidationError):
        ResearchPlan(**data)


@pytest.mark.unit
def test_market_state_flow():
    plan_data = {
        "seed_keyword": "organic soap",
        "objectives": ["find keywords"],
        "requested_modules": ["keyword_discovery"],
        "max_keywords": 10
    }
    state = MarketState(
        research_plan=ResearchPlan(**plan_data),
        status="pending"
    )
    assert state.status == "pending"
    assert state.findings is None
    assert state.errors == []
