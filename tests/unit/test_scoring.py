import pytest
import logging
from src.scoring import compute_score, classify_difficulty

@pytest.mark.unit
def test_compute_score_happy_path():
    # Standard mode
    metrics = {"volume": 100, "cpc": 2.0, "competition": 0.3}
    # (100 * 0.5 + 2.0 * 100 * 0.3 + (1 - 0.3) * 100 * 0.2) / 100
    # = (50 + 60 + 14) / 100 = 124 / 100 = 1.24
    score_standard = compute_score(metrics, mode="standard")
    assert score_standard.score == 1.24

    # Lightweight mode
    # (100 * 0.4 + 2.0 * 50 * 0.3 + (1 - 0.3) * 50 * 0.3) / 100
    # = (40 + 30 + 10.5) / 100 = 80.5 / 100 = 0.805
    score_light = compute_score(metrics, mode="lightweight")
    assert score_light.score == 0.805


@pytest.mark.unit
def test_compute_score_missing_competition():
    metrics = {"volume": 100, "cpc": 2.0, "competition": None}
    # competition defaults to 0.5
    # (100 * 0.5 + 60 + 0.5 * 100 * 0.2) / 100 = (50 + 60 + 10) / 100 = 1.2
    score = compute_score(metrics, mode="standard")
    assert score.score == 1.2


@pytest.mark.unit
def test_compute_score_missing_cpc_and_volume():
    metrics = {"volume": None, "cpc": None, "competition": 0.5}
    # treated as 0, competition = 0.5
    # (0 + 0 + 0.5 * 100 * 0.2) / 100 = 10 / 100 = 0.1
    score = compute_score(metrics, mode="standard")
    assert score.score == 0.1


@pytest.mark.unit
def test_compute_score_exception_path(caplog):
    # Pass non-numeric values to trigger TypeError/ValueError
    metrics = {"volume": "invalid", "cpc": 2.0, "competition": 0.3}
    import src.scoring
    src.scoring.logger.propagate = True
    with caplog.at_level(logging.ERROR):
        score = compute_score(metrics, mode="standard")
        assert score.score == 0.0
        assert "Score computation error" in caplog.text


@pytest.mark.unit
def test_classify_difficulty_boundaries():
    # Standard mode thresholds: >= 0.8 (Easy), >= 0.5 (Medium), < 0.5 (Hard)
    assert classify_difficulty(0.8, mode="standard") == "Easy"
    assert classify_difficulty(0.79, mode="standard") == "Medium"
    assert classify_difficulty(0.5, mode="standard") == "Medium"
    assert classify_difficulty(0.49, mode="standard") == "Hard"

    # Lightweight mode thresholds: >= 0.7 (Easy), >= 0.4 (Medium), < 0.4 (Hard)
    assert classify_difficulty(0.7, mode="lightweight") == "Easy"
    assert classify_difficulty(0.69, mode="lightweight") == "Medium"
    assert classify_difficulty(0.4, mode="lightweight") == "Medium"
    assert classify_difficulty(0.39, mode="lightweight") == "Hard"
