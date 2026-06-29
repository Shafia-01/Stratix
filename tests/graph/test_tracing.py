"""Tests for LangSmith tracing utilities."""
from src.graph.tracing import (
    get_run_id,
    get_run_config,
    build_initial_metadata,
    finalise_metadata,
    extract_tool_call_counts,
)


def test_get_run_id_is_uuid():
    import uuid
    run_id = get_run_id()
    # Should be parseable as UUID without raising
    uuid.UUID(run_id)


def test_get_run_config_structure():
    config = get_run_config("AI tools", "test-run-123")
    assert config["recursion_limit"] == 12
    assert config["configurable"]["thread_id"] == "test-run-123"
    assert "keylytics" in config["tags"]
    assert config["metadata"]["seed_keyword"] == "AI tools"


def test_build_initial_metadata():
    meta = build_initial_metadata("run-abc")
    assert meta["run_id"] == "run-abc"
    assert meta["total_tool_calls"] == 0
    assert meta["tool_call_counts"] == {}
    assert meta["end_ts"] is None


def test_finalise_metadata():
    meta = build_initial_metadata("run-abc")
    meta["tool_call_counts"] = {"keyword_research": 1, "serp_analysis": 1}
    finalised = finalise_metadata(meta)
    assert finalised["total_tool_calls"] == 2
    assert finalised["end_ts"] is not None


def test_extract_tool_call_counts():
    class FakeMsg:
        def __init__(self, name):
            self.name = name

    messages = [
        FakeMsg("keyword_research"),
        FakeMsg("serp_analysis"),
        FakeMsg("keyword_research"),
        FakeMsg(None),
    ]
    counts = extract_tool_call_counts(messages)
    assert counts["keyword_research"] == 2
    assert counts["serp_analysis"] == 1
    assert None not in counts
