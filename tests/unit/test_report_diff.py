import pytest
from src.report_diff import compute_report_diff
from src.schemas import ReportDiff

@pytest.mark.unit
def test_compute_report_diff():
    # Mock two strategy reports
    prev_report = {
        "seed_keyword": "coffee maker",
        "top_opportunities": [
            {"keyword": "best coffee maker", "score": 85.0},
            {"keyword": "espresso guide", "score": 70.0}
        ],
        "recommendations": [
            "Write an espresso machine guide",
            "Optimize coffee maker product pages"
        ]
    }

    curr_report = {
        "seed_keyword": "coffee maker",
        "top_opportunities": [
            {"keyword": "best coffee maker", "score": 90.0},
            {"keyword": "cold brew guide", "score": 75.0}
        ],
        "recommendations": [
            "Write an espresso machine guide",
            "Target cold brew keywords"
        ]
    }

    prev_conf = {"keyword_research": 0.8, "serp_analysis": 0.6}
    curr_conf = {"keyword_research": 0.9, "serp_analysis": 0.4}

    diff = compute_report_diff(prev_report, curr_report, prev_conf, curr_conf)

    assert isinstance(diff, ReportDiff)
    assert diff.seed_keyword == "coffee maker"

    deltas = {d.keyword: d for d in diff.keyword_deltas}
    assert deltas["best coffee maker"].delta == 5.0
    assert deltas["best coffee maker"].direction == "improved"
    assert deltas["cold brew guide"].direction == "new"
    assert deltas["espresso guide"].direction == "dropped"

    assert "Target cold brew keywords" in diff.new_recommendations
    assert "Optimize coffee maker product pages" in diff.dropped_recommendations

    assert diff.confidence_delta["keyword_research"] == pytest.approx(0.1)
    assert diff.confidence_delta["serp_analysis"] == pytest.approx(-0.2)
