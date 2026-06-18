"""
Pydantic schema definitions for Keylytics.
These represent data contracts only (no business logic/agent execution)
used to structure validation, representation, and serialization of pipeline stages.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict
from src.data_quality import DataSource


class CompetitorEntry(BaseModel):
    """Represents a competitor's domain rank or metrics relative to a keyword."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    domain: str = Field(..., description="The competitor's domain name (e.g. example.com)")
    rank: int = Field(..., description="Organic search rank for the competitor")
    title: Optional[str] = Field(None, description="The page title shown in search results")
    url: Optional[str] = Field(None, description="The landing page URL")


class KeywordFinding(BaseModel):
    """Structured record of a single analyzed keyword suggestion."""
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    seed: str = Field(..., description="The original seed keyword used for generation")
    keyword: str = Field(..., description="The suggested keyword variant")
    volume: float = Field(..., description="Search volume (monthly/annualized)")
    competition: Optional[float] = Field(None, description="Competition density index (0.0 to 1.0)")
    cpc: Optional[float] = Field(None, description="Cost-per-click value in USD")
    trend: Optional[float] = Field(None, description="Google Trends slope or relative value")
    score: float = Field(..., description="Calculated opportunity score")
    difficulty: Literal["Easy", "Medium", "Hard"] = Field(..., description="Difficulty classification level")
    intent: str = Field(..., description="Classified intent (e.g., Informational, Commercial)")
    competitors: List[CompetitorEntry] = Field(default_factory=list, description="Top organic competitor details")
    data_source: DataSource = Field(..., description="Origin source of core search metrics")
    trend_data_source: DataSource = Field(..., description="Origin source of trend metric")

    @field_validator("volume")
    @classmethod
    def validate_non_negative_volume(cls, v: float) -> float:
        if v < 0:
            raise ValueError("volume cannot be negative")
        return v

    @field_validator("score")
    @classmethod
    def validate_score_range(cls, v: float) -> float:
        if v < 0.0:
            raise ValueError("score must be non-negative")
        return v


class OpportunityScore(BaseModel):
    """Detailed breakdown of a keyword's calculated opportunity score."""
    model_config = ConfigDict(from_attributes=True)

    score: float = Field(..., description="Calculated opportunity score")
    difficulty: Literal["Easy", "Medium", "Hard"] = Field(..., description="Difficulty classification level")
    mode: Literal["standard", "lightweight"] = Field(..., description="Calculation mode used")
    volume: float = Field(..., description="Input search volume")
    cpc: Optional[float] = Field(None, description="Input cost-per-click")
    competition: Optional[float] = Field(None, description="Input competition index")

    @field_validator("score")
    @classmethod
    def validate_score_range(cls, v: float) -> float:
        if v < 0.0:
            raise ValueError("score must be non-negative")
        return v


class IntelligenceFindings(BaseModel):
    """Aggregate search intelligence results for a seed keyword."""
    model_config = ConfigDict(from_attributes=True)

    seed_keyword: str = Field(..., description="Seed keyword utilized for search")
    keyword_findings: List[KeywordFinding] = Field(..., description="List of generated keywords and metrics")
    # competitor_gap, topic_clusters, trend_forecast, serp_analysis hold raw tool
    # output dicts aggregated before strategy synthesis. The corresponding *Result
    # schemas (CompetitorGapResult, TrendForecastResult, etc.) are the typed
    # contracts at the tool boundary. Typing these fields is a Phase 5 improvement.
    competitor_gap: Optional[Dict[str, Any]] = Field(None, description="Aggregated competitor gap analysis raw data")
    topic_clusters: Optional[Dict[str, Any]] = Field(None, description="Aggregated topic cluster analysis raw data")
    trend_forecast: Optional[Dict[str, Any]] = Field(None, description="Aggregated trends forecasting raw data")
    serp_analysis: Optional[Dict[str, Any]] = Field(None, description="Aggregated SERP analysis raw data")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when findings were generated")


class StrategyReport(BaseModel):
    """Top-level strategic marketing deliverable based on intelligence findings."""
    model_config = ConfigDict(from_attributes=True)

    seed_keyword: str = Field(..., description="Original seed keyword analyzed")
    executive_summary: str = Field(..., description="High-level markdown summary generated by AI agent")
    findings: IntelligenceFindings = Field(..., description="Underlying search intelligence findings data container")
    top_opportunities: List[KeywordFinding] = Field(..., description="Curated high-scoring keyword opportunities")
    recommendations: List[str] = Field(..., description="List of actionable strategic recommendations")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of report generation")
    version: str = Field("phase2c", description="Schema/platform version")


class ResearchPlan(BaseModel):
    """Strategic objectives and boundary configurations for a keyword research task."""
    model_config = ConfigDict(from_attributes=True)

    seed_keyword: str = Field(..., description="Seed keyword to analyze")
    objectives: List[str] = Field(..., description="Specific goal objectives for the research")
    requested_modules: List[Literal["keyword_discovery", "competitor_gap", "topic_clustering", "trend_forecasting", "serp_analysis"]] = Field(
        ..., description="List of components/modules requested for analysis"
    )
    max_keywords: int = Field(..., description="Maximum limit of keyword suggestions to generate")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of plan creation")

    @field_validator("max_keywords")
    @classmethod
    def validate_max_keywords_range(cls, v: int) -> int:
        if not (1 <= v <= 50):
            raise ValueError("max_keywords must be between 1 and 50")
        return v


class MarketState(BaseModel):
    """
    Foundation state model representing the shared context threaded between nodes.
    This is currently a model container only and does not contain graph execution behavior.
    """
    model_config = ConfigDict(from_attributes=True)

    research_plan: ResearchPlan = Field(..., description="The configured plan triggering state")
    findings: Optional[IntelligenceFindings] = Field(None, description="Aggregated keyword discovery outputs")
    report: Optional[StrategyReport] = Field(None, description="Constructed high-level marketing strategy report")
    status: Literal["pending", "in_progress", "completed", "failed"] = Field("pending", description="Overall state progress status")
    errors: List[str] = Field(default_factory=list, description="Collection of execution error details")


class KeywordSuggestion(BaseModel):
    """Lightweight suggestion before full scoring/intent/difficulty are determined."""
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    keyword: str = Field(..., description="The suggested keyword")
    volume: float = Field(0.0, description="Monthly search volume")
    cpc: Optional[float] = Field(None, description="CPC in USD")
    competition: Optional[float] = Field(None, description="Competition density index (0.0 to 1.0)")
    data_source: DataSource = Field(..., description="Data origin")


class OrganicResult(BaseModel):
    """A single organic search result from SERP."""
    model_config = ConfigDict(from_attributes=True)
    title: str = Field("", description="Page title")
    link: str = Field("", description="Page URL")
    snippet: str = Field("", description="Page snippet")
    displayed_link: Optional[str] = Field(None, description="Displayed URL")
    domain: Optional[str] = Field(None, description="Domain extracted from link")
    position: Optional[int] = Field(None, description="Organic rank position")

class SerpRawData(BaseModel):
    """Typed container for raw SERP response data."""
    model_config = ConfigDict(from_attributes=True)
    organic_results: List[OrganicResult] = Field(default_factory=list)
    people_also_ask: List[Dict[str, str]] = Field(default_factory=list)
    related_searches: List[Dict[str, str]] = Field(default_factory=list)
    featured_snippet: Dict[str, str] = Field(default_factory=dict)
    search_information: Dict[str, Any] = Field(default_factory=dict)

class SnippetOpportunity(BaseModel):
    """A single snippet optimization opportunity."""
    model_config = ConfigDict(from_attributes=True)
    type: str
    opportunity: str
    recommendation: str
    priority: Literal["high", "medium", "low"]

class SnippetAnalysis(BaseModel):
    """Analysis of snippet optimization opportunities."""
    model_config = ConfigDict(from_attributes=True)
    has_featured_snippet: bool = False
    snippet_opportunities: List[SnippetOpportunity] = Field(default_factory=list)

class PAAQuestion(BaseModel):
    """A People Also Ask question with content idea."""
    model_config = ConfigDict(from_attributes=True)
    question: str
    snippet: str
    content_idea: str
    opportunity_type: Optional[str] = None

class PAAData(BaseModel):
    """People Also Ask extraction results."""
    model_config = ConfigDict(from_attributes=True)
    questions: List[PAAQuestion] = Field(default_factory=list)
    opportunities: List[Dict[str, Any]] = Field(default_factory=list)

class SerpAnalysisResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    keyword: str = Field(..., description="The keyword analyzed")
    serp_data: SerpRawData = Field(default_factory=SerpRawData, description="Typed SERP response")
    snippet_analysis: SnippetAnalysis = Field(default_factory=SnippetAnalysis)
    paa_questions: PAAData = Field(default_factory=PAAData)
    ranking_analysis: Dict[str, Any] = Field(default_factory=dict, description="Top ranking page analysis")
    content_gaps: Dict[str, Any] = Field(default_factory=dict, description="Content format gaps")
    optimization_suggestions: List[SnippetOpportunity] = Field(default_factory=list)
    summary: str = Field("", description="Text summary of SERP findings")


# ---------------------------------------------------------------------------
# Typed sub-models for CompetitorGapResult
# ---------------------------------------------------------------------------

class CompetitorOpportunity(BaseModel):
    """A single keyword opportunity identified in competitor gap analysis."""
    model_config = ConfigDict(from_attributes=True)

    keyword: str = Field(..., description="The keyword representing the gap opportunity")
    opportunity_type: str = Field(..., description="Type of opportunity (e.g. 'keyword_gap', 'ranking_improvement')")
    gap_score: float = Field(..., description="Opportunity gap score (0–100; higher = better opportunity)")
    traffic_potential: Literal["high", "medium", "low"] = Field(..., description="Estimated traffic potential tier")
    reasoning: str = Field(..., description="Human-readable rationale for this opportunity")


class CompetitorGapResult(BaseModel):
    """Competitor keyword gap analysis results."""
    model_config = ConfigDict(from_attributes=True)

    competitors: List[CompetitorEntry] = Field(..., description="Analyzed competitors")
    opportunities: List[CompetitorOpportunity] = Field(..., description="Typed keyword opportunities found")
    summary: str = Field(..., description="Executive summary of the keyword gap")


# ---------------------------------------------------------------------------
# Typed sub-models for TrendForecastResult
# ---------------------------------------------------------------------------

class ForecastPoint(BaseModel):
    """A single monthly forecast data point."""
    model_config = ConfigDict(from_attributes=True)

    month: int = Field(..., description="Forecast month index (1 = next month, 6 = 6 months out)")
    score: float = Field(..., description="Predicted trend score (0–100)")
    confidence: float = Field(..., description="Forecast confidence percentage (0–100)")


class ForecastEntry(BaseModel):
    """Forecast data for a single keyword."""
    model_config = ConfigDict(from_attributes=True)

    forecast_scores: List[ForecastPoint] = Field(..., description="Month-by-month forecast points")
    predicted_growth: float = Field(..., description="Predicted growth rate as a percentage")
    trend_direction: str = Field(..., description="Direction label (e.g. 'strong_growth', 'stable')")
    recommendation: str = Field(..., description="Actionable recommendation based on forecast")


class SeasonalAnalysisEntry(BaseModel):
    """Seasonal pattern analysis for a single keyword."""
    model_config = ConfigDict(from_attributes=True)

    peak_season: Optional[int] = Field(None, description="Month number of peak interest (1–12)")
    low_season: Optional[int] = Field(None, description="Month number of lowest interest (1–12)")
    seasonality_strength: float = Field(..., description="Standard deviation of seasonal factors (higher = more seasonal)")
    growth_rate: Optional[float] = Field(None, description="Compound growth rate over the historical period")
    recommendation: Optional[str] = Field(None, description="Seasonal content calendar recommendation")


class TrendForecastResult(BaseModel):
    """Trend forecasting results."""
    model_config = ConfigDict(from_attributes=True)

    forecasts: Dict[str, ForecastEntry] = Field(..., description="Per-keyword typed forecast entries")
    seasonal_analysis: Dict[str, SeasonalAnalysisEntry] = Field(..., description="Per-keyword seasonal analysis")
    insights: List[str] = Field(..., description="Actionable insights from forecasting")
    summary: str = Field(..., description="Text summary of trends")


# ---------------------------------------------------------------------------
# Typed sub-models for TopicClusterResult
# ---------------------------------------------------------------------------

class ClusterMetrics(BaseModel):
    """Aggregated search metrics for a keyword cluster."""
    model_config = ConfigDict(from_attributes=True)

    avg_volume: float = Field(..., description="Average monthly search volume across cluster keywords")
    avg_competition: float = Field(..., description="Average competition density (0–1)")
    avg_cpc: float = Field(..., description="Average cost-per-click in USD")
    avg_score: float = Field(..., description="Average opportunity score")
    total_volume: float = Field(..., description="Total combined monthly search volume")


class TopicClusterEntry(BaseModel):
    """A single semantic topic cluster with enriched metrics."""
    model_config = ConfigDict(from_attributes=True)

    cluster_name: str = Field(..., description="Descriptive name for the cluster (e.g. 'AI Content Generation Tools')")
    description: str = Field(..., description="Brief description of what this cluster represents")
    keywords: List[str] = Field(..., description="Keywords belonging to this cluster")
    primary_intent: str = Field(..., description="Dominant search intent (commercial/informational/transactional/navigational)")
    industry_focus: str = Field(..., description="Main industry or use case")
    keyword_count: int = Field(..., description="Number of keywords in the cluster")
    opportunity_score: float = Field(..., description="Composite opportunity score for the cluster")
    metrics: ClusterMetrics = Field(..., description="Aggregated search metrics for the cluster")


class TopicClusterResult(BaseModel):
    """Semantic topic clustering results."""
    model_config = ConfigDict(from_attributes=True)

    clusters: List[TopicClusterEntry] = Field(..., description="Typed semantic cluster definitions")
    insights: List[str] = Field(..., description="Topic level insights")
    summary: str = Field(..., description="Executive summary of clusters")


class IntentClassification(BaseModel):
    """Intent classification result."""
    model_config = ConfigDict(from_attributes=True)

    keyword: str = Field(..., description="The keyword classified")
    intent: str = Field(..., description="The classified intent label")
    source: Literal["cache", "rule", "gemini"] = Field(..., description="Classification path source")


def schemas_to_legacy_dicts(findings: List[KeywordFinding]) -> List[dict]:
    """Convert KeywordFinding models to legacy dictionaries for Streamlit UI."""
    legacy_list = []
    for f in findings:
        d = f.model_dump(mode="json")
        # Map competitors back to legacy format
        legacy_comps = []
        for c in f.competitors:
            legacy_comps.append({
                "rank": c.rank,
                "title": c.title,
                "link": c.url,
                "domain": c.domain,
                "snippet": "No description available."
            })
        d["competitors"] = legacy_comps
        legacy_list.append(d)
    return legacy_list


# ---------------------------------------------------------------------------
# Phase 4 schemas — monitoring, diff, and evaluation
# ---------------------------------------------------------------------------

class MonitoringJob(BaseModel):
    """Configuration for a recurring keyword monitoring job."""
    model_config = ConfigDict(from_attributes=True)

    job_id: str = Field(..., description="Unique APScheduler job identifier")
    seed_keyword: str = Field(..., description="Keyword to monitor")
    interval_hours: int = Field(..., description="Run interval in hours")
    last_run: Optional[datetime] = Field(None, description="Timestamp of last execution")
    next_run: Optional[datetime] = Field(None, description="Scheduled next execution timestamp")
    status: Literal["active", "paused", "failed"] = Field(..., description="Current job status")


class KeywordDelta(BaseModel):
    """Change record for a single keyword between two consecutive reports."""
    model_config = ConfigDict(from_attributes=True)

    keyword: str = Field(..., description="The keyword")
    prev_score: Optional[float] = Field(None, description="Opportunity score in the previous report")
    curr_score: Optional[float] = Field(None, description="Opportunity score in the current report")
    delta: float = Field(..., description="curr_score - prev_score (or curr_score if new)")
    direction: Literal["improved", "declined", "new", "dropped"] = Field(
        ..., description="Change direction relative to prior report"
    )


class ReportDiff(BaseModel):
    """Diff between two consecutive StrategyReport runs for the same keyword."""
    model_config = ConfigDict(from_attributes=True)

    seed_keyword: str = Field(..., description="The monitored seed keyword")
    generated_at: datetime = Field(
        default_factory=datetime.utcnow, description="When this diff was computed"
    )
    keyword_deltas: List[KeywordDelta] = Field(
        default_factory=list, description="Per-keyword score changes"
    )
    new_recommendations: List[str] = Field(
        default_factory=list, description="Recommendations present in current report but not previous"
    )
    dropped_recommendations: List[str] = Field(
        default_factory=list, description="Recommendations present in previous report but not current"
    )
    confidence_delta: Dict[str, float] = Field(
        default_factory=dict, description="Per-tool confidence score change (curr - prev)"
    )
    summary: str = Field(..., description="Human-readable summary of the diff")


class EvalResult(BaseModel):
    """LLM-as-judge evaluation result for a single aspect of a research run."""
    model_config = ConfigDict(from_attributes=True)

    run_id: str = Field(..., description="Research run ID this evaluation belongs to")
    eval_type: Literal["plan_quality", "report_quality", "tool_reliability"] = Field(
        ..., description="Which aspect was evaluated"
    )
    score: float = Field(..., description="Normalised score 0.0–1.0")
    rationale: str = Field(..., description="LLM-generated rationale for the score")
    dimension_scores: Dict[str, float] = Field(
        default_factory=dict, description="Per-dimension breakdown scores"
    )
    evaluated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Evaluation timestamp"
    )


class TimelineEvent(BaseModel):
    event_type: str  # "node_start" | "node_end" | "tool_call" | "hitl_interrupt" | "error"
    node_name: str
    timestamp: str
    duration_ms: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    # For tool_call events: tool_name, success, result_keys
    # For hitl_interrupt: checkpoint_name
    # For errors: error_message

class ExecutionTimeline(BaseModel):
    run_id: str
    seed_keyword: str
    status: str
    total_duration_ms: Optional[float] = None
    events: List[TimelineEvent]
    confidence_scores: Dict[str, float] = Field(default_factory=dict)
    critic_verdict: Optional[str] = None
    eval_scores: Dict[str, float] = Field(default_factory=dict)


