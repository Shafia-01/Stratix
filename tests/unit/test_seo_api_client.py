import pytest
import requests
from datetime import datetime, timedelta
from src.seo_api_client import get_keyword_metrics, save_to_cache
from src.data_quality import DataSource
from src.db_client import connect_db
from sqlalchemy.orm import Session
from src.models import Keyword

@pytest.mark.unit
def test_seo_cache_hit_within_7_days(tmp_db_path, monkeypatch, mocker):
    # Setup a cached row in the DB with last_updated = now
    engine = connect_db()
    with Session(engine) as session:
        kw = Keyword(
            keyword="fresh coffee",
            volume=5000,
            competition=0.5,
            cpc=1.5,
            seed="coffee",
            last_updated=datetime.now()
        )
        session.add(kw)
        session.commit()

    # Mock requests.get and ensure it's not called
    mock_get = mocker.patch("requests.get")

    metrics = get_keyword_metrics("fresh coffee")
    assert metrics["volume"] == 5000
    assert metrics["data_source"] == DataSource.CACHED.value
    mock_get.assert_not_called()


@pytest.mark.unit
def test_seo_cache_expired_triggers_refresh(tmp_db_path, monkeypatch, mocker):
    # Setup a cached row with last_updated = 10 days ago
    engine = connect_db()
    with Session(engine) as session:
        kw = Keyword(
            keyword="old coffee",
            volume=5000,
            competition=0.5,
            cpc=1.5,
            seed="coffee",
            last_updated=datetime.now() - timedelta(days=10)
        )
        session.add(kw)
        session.commit()

    # Mock requests.get to return a valid search result
    class MockResponse:
        def json(self):
            return {"search_information": {"total_results": 10000000}} # volume = min(10000000/1000, 10000) = 10000
        def raise_for_status(self):
            pass

    mock_get = mocker.patch("requests.get", return_value=MockResponse())

    metrics = get_keyword_metrics("old coffee")
    assert metrics["volume"] == 10000
    assert metrics["data_source"] == DataSource.ESTIMATED.value
    mock_get.assert_called_once()


@pytest.mark.unit
def test_seo_api_exception_fallback(tmp_db_path, mocker):
    # Mock requests.get to raise an exception
    mocker.patch("requests.get", side_effect=requests.exceptions.RequestException("Timeout"))

    with pytest.raises(requests.exceptions.RequestException):
        get_keyword_metrics("timeout coffee")


@pytest.mark.unit
def test_save_to_cache_preserves_complete_row(tmp_db_path):
    engine = connect_db()
    # Save a complete row (has seed "coffee")
    with Session(engine) as session:
        kw = Keyword(
            keyword="complete coffee",
            volume=5000,
            competition=0.5,
            cpc=1.5,
            seed="coffee"
        )
        session.add(kw)
        session.commit()

    # Try saving new incomplete metrics to the cache
    save_to_cache("complete coffee", {"volume": 8000, "competition": 0.8, "cpc": 2.0})

    # Verify the row volume is still 5000 (not overwritten because row has seed)
    with Session(engine) as session:
        row = session.query(Keyword).filter(Keyword.keyword == "complete coffee").first()
        assert row.volume == 5000
        assert row.seed == "coffee"
