import pytest
from src.intent_classifier import rule_based_intent, classify_intent

@pytest.mark.unit
def test_rule_based_intent_classification():
    # Commercial Intent
    assert rule_based_intent("buy organic coffee") == "Commercial Intent"
    assert rule_based_intent("coffee price") == "Commercial Intent"

    # Transactional Intent
    assert rule_based_intent("hire seo specialist") == "Transactional Intent"
    assert rule_based_intent("seo careers") == "Transactional Intent"

    # Informational Intent
    assert rule_based_intent("what is organic coffee") == "Informational Intent"
    assert rule_based_intent("how to brew coffee") == "Informational Intent"

    # Navigational Intent
    assert rule_based_intent("starbucks vs peets") == "Navigational Intent"
    assert rule_based_intent("coffee alternatives") == "Navigational Intent"

    # Low-Intent (Bargain)
    assert rule_based_intent("cheap coffee beans") == "Low-Intent (Bargain)"
    assert rule_based_intent("free coffee sample") == "Low-Intent (Bargain)"

    # Uncertain
    assert rule_based_intent("coffee beans") == "Uncertain"


@pytest.mark.unit
def test_classify_intent_cache_hit(tmp_db_path, monkeypatch, mocker):
    # Setup cache hit in db
    mocker.patch("src.intent_classifier.get_cached_intent", return_value="Commercial")
    mock_gemini = mocker.patch("src.intent_classifier.generate_intent_gemini")

    intent = classify_intent("coffee beans")
    assert intent == "Commercial"
    mock_gemini.assert_not_called()


@pytest.mark.unit
def test_classify_intent_uncertain_fallback_to_gemini(tmp_db_path, monkeypatch, mocker):
    # Cache miss
    mocker.patch("src.intent_classifier.get_cached_intent", return_value=None)
    # Rule based returns "Uncertain"
    mocker.patch("src.intent_classifier.rule_based_intent", return_value="Uncertain")
    # Mock Gemini call
    mock_gemini = mocker.patch("src.intent_classifier.generate_intent_gemini", return_value="Transactional")
    mock_save = mocker.patch("src.intent_classifier.save_intent_to_db")

    intent = classify_intent("coffee beans")
    assert intent == "Transactional"
    mock_gemini.assert_called_once_with("coffee beans")
    mock_save.assert_called_once_with("coffee beans", "Transactional")
