import pytest
from pydantic import ValidationError
from src.schemas import (
    KeywordFinding,
    KeywordSuggestion,
    SerpAnalysisResult,
    CompetitorGapResult,
    TrendForecastResult,
    TopicClusterResult,
    IntentClassification,
    CompetitorEntry
)
from src.data_quality import DataSource

def test_keyword_finding_validation():
    # Valid model
    kw = KeywordFinding(
        seed="test",
        keyword="test key",
        volume=100.0,
        score=50.0,
        difficulty="Medium",
        intent="Informational",
        data_source=DataSource.LIVE,
        trend_data_source=DataSource.UNAVAILABLE
    )
    assert kw.volume == 100.0
    
    # Negative volume should fail
    with pytest.raises(ValidationError):
        KeywordFinding(
            seed="test",
            keyword="test key",
            volume=-50.0,
            score=50.0,
            difficulty="Medium",
            intent="Informational",
            data_source=DataSource.LIVE,
            trend_data_source=DataSource.UNAVAILABLE
        )
        
    # Negative score should fail
    with pytest.raises(ValidationError):
        KeywordFinding(
            seed="test",
            keyword="test key",
            volume=100.0,
            score=-1.0,
            difficulty="Medium",
            intent="Informational",
            data_source=DataSource.LIVE,
            trend_data_source=DataSource.UNAVAILABLE
        )

def test_new_tool_schemas_instantiation():
    # KeywordSuggestion
    sug = KeywordSuggestion(
        keyword="suggested key",
        volume=120.0,
        cpc=1.5,
        competition=0.4,
        data_source=DataSource.LIVE
    )
    assert sug.keyword == "suggested key"
    
    # SerpAnalysisResult
    serp = SerpAnalysisResult(
        keyword="serp key",
        serp_data={},
        snippet_analysis={},
        paa_questions={},
        ranking_analysis={},
        content_gaps={},
        optimization_suggestions=[],
        summary="summary info"
    )
    assert serp.keyword == "serp key"
    
    # CompetitorGapResult
    gap = CompetitorGapResult(
        competitors=[CompetitorEntry(domain="comp.com", rank=1)],
        opportunities=[],
        summary="gap summary"
    )
    assert gap.summary == "gap summary"

    # TrendForecastResult
    trend = TrendForecastResult(
        forecasts=[],
        seasonal_analysis={},
        insights=[],
        summary="trend summary"
    )
    assert trend.summary == "trend summary"

    # TopicClusterResult
    cluster = TopicClusterResult(
        clusters=[],
        insights=[],
        summary="cluster summary"
    )
    assert cluster.summary == "cluster summary"

    # IntentClassification
    intent = IntentClassification(
        keyword="intent key",
        intent="Commercial",
        source="rule"
    )
    assert intent.source == "rule"
