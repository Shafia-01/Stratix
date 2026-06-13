"""
Tests for src/scoring.py.
Verifies compute_score() returns an OpportunityScore and classify_difficulty() works
in both standard and lightweight modes, including edge cases.
"""

from src.scoring import compute_score, classify_difficulty
from src.schemas import OpportunityScore


class TestComputeScore:
    def test_returns_opportunity_score_instance(self):
        result = compute_score({"volume": 1000, "cpc": 1.5, "competition": 0.4})
        assert isinstance(result, OpportunityScore)

    def test_standard_mode_fields_populated(self):
        result = compute_score({"volume": 2000, "cpc": 2.0, "competition": 0.3}, mode="standard")
        assert result.mode == "standard"
        assert result.volume == 2000.0
        assert result.cpc == 2.0
        assert result.competition == 0.3
        assert result.score >= 0.0

    def test_lightweight_mode(self):
        result = compute_score({"volume": 500, "cpc": 0.5, "competition": 0.6}, mode="lightweight")
        assert result.mode == "lightweight"
        assert isinstance(result.score, float)

    def test_zero_volume_returns_zero_score(self):
        result = compute_score({"volume": 0, "cpc": 0, "competition": 1.0})
        assert result.score == 0.0

    def test_missing_competition_defaults_to_neutral(self):
        """Missing competition should default to 0.5 (neutral)."""
        result_with_none = compute_score({"volume": 1000, "cpc": 1.0, "competition": None})
        result_with_half = compute_score({"volume": 1000, "cpc": 1.0, "competition": 0.5})
        assert result_with_none.score == result_with_half.score

    def test_missing_cpc_defaults_to_zero(self):
        result = compute_score({"volume": 1000, "competition": 0.5})
        assert result.cpc is None
        assert result.score >= 0.0

    def test_score_is_non_negative(self):
        """Score must never be negative even with extreme inputs."""
        result = compute_score({"volume": 0, "cpc": 0, "competition": 1.0})
        assert result.score >= 0.0

    def test_difficulty_is_valid_literal(self):
        result = compute_score({"volume": 1000, "cpc": 1.5, "competition": 0.4})
        assert result.difficulty in ("Easy", "Medium", "Hard")

    def test_high_volume_low_competition_is_easy(self):
        """High volume + very low competition + decent CPC should yield Easy difficulty."""
        result = compute_score({"volume": 100000, "cpc": 5.0, "competition": 0.0})
        assert result.difficulty == "Easy"

    def test_zero_everything_returns_hard(self):
        result = compute_score({"volume": 0, "cpc": 0, "competition": 1.0})
        assert result.difficulty == "Hard"


class TestClassifyDifficulty:
    def test_standard_easy_threshold(self):
        assert classify_difficulty(0.85) == "Easy"

    def test_standard_medium_threshold(self):
        assert classify_difficulty(0.6) == "Medium"

    def test_standard_hard_threshold(self):
        assert classify_difficulty(0.3) == "Hard"

    def test_lightweight_easy_threshold(self):
        assert classify_difficulty(0.75, mode="lightweight") == "Easy"

    def test_lightweight_medium_threshold(self):
        assert classify_difficulty(0.5, mode="lightweight") == "Medium"

    def test_lightweight_hard_threshold(self):
        assert classify_difficulty(0.2, mode="lightweight") == "Hard"

    def test_accepts_opportunity_score_instance(self):
        """classify_difficulty should transparently accept an OpportunityScore."""
        opp = compute_score({"volume": 1000, "cpc": 2.0, "competition": 0.2})
        # Should not raise; result should match calling with the numeric score directly
        assert classify_difficulty(opp) == classify_difficulty(opp.score)
