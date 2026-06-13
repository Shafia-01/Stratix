"""
Tests for src/tools/intent_classifier_tool.py and src/tools/keyword_research_tool.py.
All external API/Gemini calls are mocked.
"""

import pytest
from unittest.mock import patch
from pydantic import ValidationError


class TestIntentClassifierTool:
    def test_run_returns_intent_classification(self):
        from src.tools.intent_classifier_tool import IntentClassifierInput, run
        from src.schemas import IntentClassification

        mock_result = ("commercial", "rule")
        with patch("src.tools.intent_classifier_tool.classify_intent_with_source", return_value=mock_result):
            inp = IntentClassifierInput(keyword="best coffee maker")
            result = run(inp)

        assert isinstance(result, IntentClassification)
        assert result.keyword == "best coffee maker"
        assert result.intent == "commercial"

    def test_run_wraps_exception_in_keylytics_error(self):
        from src.tools.intent_classifier_tool import IntentClassifierInput, run
        from src.exceptions import KeylyticsAPIError

        with patch("src.tools.intent_classifier_tool.classify_intent_with_source", side_effect=RuntimeError("API down")):
            with pytest.raises(KeylyticsAPIError, match="Intent classification tool failed"):
                run(IntentClassifierInput(keyword="coffee"))

    def test_input_model_validates_keyword_required(self):
        from src.tools.intent_classifier_tool import IntentClassifierInput
        with pytest.raises(ValidationError):
            IntentClassifierInput()  # Missing required 'keyword'


class TestKeywordResearchTool:
    def test_run_returns_list_of_keyword_suggestions(self):
        from src.tools.keyword_research_tool import KeywordResearchInput, run
        from src.schemas import KeywordSuggestion
        from src.data_quality import DataSource

        mock_keywords = [
            {"keyword": "coffee beans", "volume": 5000, "cpc": 1.2, "competition": 0.3,
             "data_source": DataSource.ESTIMATED.value}
        ]
        with patch("src.tools.keyword_research_tool.get_enhanced_keywords", return_value=mock_keywords):
            result = run(KeywordResearchInput(seed_keyword="coffee", max_keywords=5))

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], KeywordSuggestion)

    def test_run_returns_empty_list_on_no_results(self):
        from src.tools.keyword_research_tool import KeywordResearchInput, run

        with patch("src.tools.keyword_research_tool.get_enhanced_keywords", return_value=[]):
            result = run(KeywordResearchInput(seed_keyword="xyzabc", max_keywords=5))

        assert result == []

    def test_input_validates_max_keywords_range(self):
        from src.tools.keyword_research_tool import KeywordResearchInput
        # Valid
        inp = KeywordResearchInput(seed_keyword="coffee", max_keywords=5)
        assert inp.max_keywords == 5


class TestCompetitorGapTool:
    def test_run_returns_competitor_gap_result(self):
        from src.tools.competitor_gap_tool import CompetitorGapInput, run
        from src.schemas import CompetitorGapResult

        mock_response = {
            "competitors": [{"domain": "example.com", "rank": 1, "title": "Example", "link": "https://example.com"}],
            "opportunities": [
                {
                    "keyword": "best coffee",
                    "opportunity_type": "keyword_gap",
                    "gap_score": 80.0,
                    "traffic_potential": "high",
                    "reasoning": "Competitor ranks, you don't.",
                }
            ],
            "summary": "One gap found.",
        }
        with patch("src.tools.competitor_gap_tool.analyze_competitor_keyword_gap", return_value=mock_response):
            result = run(CompetitorGapInput(seed_keyword="coffee", top_competitors=3))

        assert isinstance(result, CompetitorGapResult)
        assert len(result.opportunities) == 1
        assert result.opportunities[0].traffic_potential == "high"

    def test_invoke_tool_error_returned_as_dict(self):
        """invoke_tool must return error dict, never raise, on tool failure."""
        from src.tools.registry import invoke_tool
        from src.exceptions import KeylyticsAPIError

        with patch("src.tools.competitor_gap_tool.analyze_competitor_keyword_gap", side_effect=KeylyticsAPIError("quota exceeded")):
            result = invoke_tool("competitor_gap", {"seed_keyword": "coffee", "top_competitors": 3})

        assert "error" in result
        assert result["tool"] == "competitor_gap"
