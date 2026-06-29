"""
Tests for typed Pydantic schemas in schemas.py.
Verifies all new typed models (ForecastEntry, TopicClusterEntry, CompetitorOpportunity)
validate correctly and enum serialization works as expected.
"""

import pytest
from pydantic import ValidationError
from src.schemas import (
    ForecastPoint,
    ForecastEntry,
    SeasonalAnalysisEntry,
    ClusterMetrics,
    TopicClusterEntry,
    CompetitorOpportunity,
    TrendForecastResult,
    TopicClusterResult,
    CompetitorGapResult,
    CompetitorEntry,
)
from src.data_quality import DataSource


# ---------------------------------------------------------------------------
# ForecastPoint
# ---------------------------------------------------------------------------
class TestForecastPoint:
    def test_valid_creation(self):
        fp = ForecastPoint(month=1, score=75.0, confidence=80.0)
        assert fp.month == 1
        assert fp.score == 75.0

    def test_month_is_int(self):
        fp = ForecastPoint(month=6, score=50.0, confidence=90.0)
        assert isinstance(fp.month, int)


# ---------------------------------------------------------------------------
# ForecastEntry
# ---------------------------------------------------------------------------
class TestForecastEntry:
    def _make_entry(self):
        return ForecastEntry(
            forecast_scores=[ForecastPoint(month=1, score=70.0, confidence=85.0)],
            predicted_growth=15.3,
            trend_direction="strong_growth",
            recommendation="Invest now.",
        )

    def test_valid_creation(self):
        entry = self._make_entry()
        assert len(entry.forecast_scores) == 1
        assert entry.trend_direction == "strong_growth"

    def test_serializes_to_dict(self):
        entry = self._make_entry()
        d = entry.model_dump(mode="json")
        assert "forecast_scores" in d
        assert isinstance(d["forecast_scores"], list)


# ---------------------------------------------------------------------------
# SeasonalAnalysisEntry
# ---------------------------------------------------------------------------
class TestSeasonalAnalysisEntry:
    def test_all_optional_fields_none(self):
        sa = SeasonalAnalysisEntry(seasonality_strength=0.5)
        assert sa.peak_season is None
        assert sa.low_season is None
        assert sa.growth_rate is None
        assert sa.recommendation is None

    def test_with_all_fields(self):
        sa = SeasonalAnalysisEntry(
            peak_season=12,
            low_season=6,
            seasonality_strength=1.2,
            growth_rate=0.15,
            recommendation="Target Q4 campaigns.",
        )
        assert sa.peak_season == 12


# ---------------------------------------------------------------------------
# ClusterMetrics
# ---------------------------------------------------------------------------
class TestClusterMetrics:
    def test_valid_metrics(self):
        cm = ClusterMetrics(
            avg_volume=5000.0,
            avg_competition=0.4,
            avg_cpc=1.2,
            avg_score=0.7,
            total_volume=25000.0,
        )
        assert cm.total_volume == 25000.0


# ---------------------------------------------------------------------------
# TopicClusterEntry
# ---------------------------------------------------------------------------
class TestTopicClusterEntry:
    def _make_entry(self):
        return TopicClusterEntry(
            cluster_name="AI Tools",
            description="Artificial intelligence tools for content creation",
            keywords=["ai writing", "ai tools", "gpt writer"],
            primary_intent="commercial",
            industry_focus="technology",
            keyword_count=3,
            opportunity_score=0.75,
            metrics=ClusterMetrics(
                avg_volume=3000.0,
                avg_competition=0.35,
                avg_cpc=1.5,
                avg_score=0.7,
                total_volume=9000.0,
            ),
        )

    def test_valid_creation(self):
        entry = self._make_entry()
        assert entry.cluster_name == "AI Tools"
        assert len(entry.keywords) == 3

    def test_serializes_to_json(self):
        entry = self._make_entry()
        d = entry.model_dump(mode="json")
        assert "metrics" in d
        assert d["metrics"]["avg_volume"] == 3000.0


# ---------------------------------------------------------------------------
# CompetitorOpportunity
# ---------------------------------------------------------------------------
class TestCompetitorOpportunity:
    def test_valid_creation(self):
        opp = CompetitorOpportunity(
            keyword="ai content tools",
            opportunity_type="keyword_gap",
            gap_score=82.5,
            traffic_potential="high",
            reasoning="Competitor ranks but you don't.",
        )
        assert opp.traffic_potential == "high"

    def test_invalid_traffic_potential_raises(self):
        with pytest.raises(ValidationError):
            CompetitorOpportunity(
                keyword="test",
                opportunity_type="keyword_gap",
                gap_score=50.0,
                traffic_potential="extreme",  # Invalid literal
                reasoning="test",
            )


# ---------------------------------------------------------------------------
# Full result model round-trips
# ---------------------------------------------------------------------------
class TestTrendForecastResult:
    def test_round_trip(self):
        result = TrendForecastResult(
            forecasts={
                "coffee": ForecastEntry(
                    forecast_scores=[ForecastPoint(month=1, score=60.0, confidence=70.0)],
                    predicted_growth=5.0,
                    trend_direction="stable",
                    recommendation="Maintain presence.",
                )
            },
            seasonal_analysis={
                "coffee": SeasonalAnalysisEntry(seasonality_strength=0.3)
            },
            insights=["Coffee is seasonal in winter."],
            summary="Stable trend.",
        )
        d = result.model_dump(mode="json")
        assert "coffee" in d["forecasts"]
        assert d["forecasts"]["coffee"]["trend_direction"] == "stable"


class TestTopicClusterResult:
    def test_clusters_is_typed_list(self):
        result = TopicClusterResult(
            clusters=[
                TopicClusterEntry(
                    cluster_name="SEO Tools",
                    description="Tools for SEO",
                    keywords=["seo tool", "rank tracker"],
                    primary_intent="commercial",
                    industry_focus="marketing",
                    keyword_count=2,
                    opportunity_score=0.6,
                    metrics=ClusterMetrics(
                        avg_volume=2000.0,
                        avg_competition=0.4,
                        avg_cpc=1.0,
                        avg_score=0.6,
                        total_volume=4000.0,
                    ),
                )
            ],
            insights=["SEO tools market is growing."],
            summary="One cluster found.",
        )
        assert isinstance(result.clusters, list)
        assert isinstance(result.clusters[0], TopicClusterEntry)


class TestCompetitorGapResult:
    def test_opportunities_is_typed_list(self):
        result = CompetitorGapResult(
            competitors=[
                CompetitorEntry(domain="example.com", rank=1, title="Example", url="https://example.com")
            ],
            opportunities=[
                CompetitorOpportunity(
                    keyword="best seo tool",
                    opportunity_type="keyword_gap",
                    gap_score=75.0,
                    traffic_potential="medium",
                    reasoning="Competitor ranks at position 3.",
                )
            ],
            summary="One gap found.",
        )
        assert isinstance(result.opportunities[0], CompetitorOpportunity)
        assert result.opportunities[0].traffic_potential == "medium"


# ---------------------------------------------------------------------------
# DataSource enum serialization
# ---------------------------------------------------------------------------
class TestDataSourceEnum:
    def test_enum_serializes_to_string(self):
        assert DataSource.LIVE.value == "live"
        assert DataSource.CACHED.value == "cached"
