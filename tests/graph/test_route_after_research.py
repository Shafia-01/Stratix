"""
Tests for the fixed route_after_research function (Phase 10-PRE).

Covers:
  A. Empty keyword research items -> routes to aggregator_node (not __end__)
  B. Keyword research error dict -> routes to aggregator_node (not __end__)
  C. Missing keyword_research key -> routes to aggregator_node (not __end__)
  D. Successful result -> still routes to aggregator_node
  E. quality_gate and critic retry budgets remain bounded (no infinite loop)
  F. _reconcile_terminal_db_status safety net
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch
from src.graph.nodes import route_after_research


def _make_state(collected_data=None, execution_metadata=None):
    return {
        "collected_data": collected_data,
        "execution_metadata": execution_metadata or {},
        "errors": [],
        "status": "in_progress",
    }


class TestRouteAfterResearchEmpty:
    def test_empty_items_routes_to_aggregator(self):
        state = _make_state(collected_data={"keyword_research": {"items": []}})
        result = route_after_research(state)
        assert result == "aggregator_node"

    def test_empty_items_does_not_end(self):
        state = _make_state(collected_data={"keyword_research": {"items": []}})
        assert route_after_research(state) != "__end__"


class TestRouteAfterResearchError:
    def test_error_dict_routes_to_aggregator(self):
        state = _make_state(collected_data={"keyword_research": {"error": "API rate limit exceeded"}})
        result = route_after_research(state)
        assert result == "aggregator_node"

    def test_error_dict_does_not_end(self):
        state = _make_state(collected_data={"keyword_research": {"error": "timeout"}})
        assert route_after_research(state) != "__end__"


class TestRouteAfterResearchMissing:
    def test_missing_key_routes_to_aggregator(self):
        state = _make_state(collected_data={})
        assert route_after_research(state) == "aggregator_node"

    def test_none_collected_data_routes_to_aggregator(self):
        state = _make_state(collected_data=None)
        assert route_after_research(state) == "aggregator_node"

    def test_missing_does_not_end(self):
        state = _make_state(collected_data={})
        assert route_after_research(state) != "__end__"


class TestRouteAfterResearchSuccess:
    def test_good_result_routes_to_aggregator(self):
        state = _make_state(collected_data={"keyword_research": {"items": [
            {"keyword": "seo tools", "volume": 1000, "score": 0.8},
            {"keyword": "keyword research", "volume": 800, "score": 0.7},
        ]}})
        assert route_after_research(state) == "aggregator_node"

    def test_route_never_returns_end_on_success(self):
        state = _make_state(collected_data={"keyword_research": {"items": [
            {"keyword": "test", "volume": 100}
        ]}})
        assert route_after_research(state) != "__end__"


class TestQualityGateRetryBudget:
    def test_gate_retries_bounded(self):
        from src.graph.nodes import quality_gate_node, route_after_quality_gate
        state = {
            "confidence_scores": {"keyword_research": 0.0},
            "intelligence_findings": {"keyword_findings": []},
            "execution_metadata": {"gate_retries": 1},
            "errors": [],
            "research_plan": {"requested_modules": ["keyword_discovery"], "max_keywords": 5},
            "collected_data": {},
            "human_feedback": None,
            "retry_target_tools": None,
        }
        new_state = quality_gate_node(state)
        route = route_after_quality_gate(new_state)
        assert route == "critic_node"

    def test_gate_retries_first_pass_allows_retry(self):
        from src.graph.nodes import quality_gate_node, route_after_quality_gate
        state = {
            "confidence_scores": {"keyword_research": 0.0},
            "intelligence_findings": {"keyword_findings": []},
            "execution_metadata": {"gate_retries": 0},
            "errors": [],
            "research_plan": {"requested_modules": ["keyword_discovery"], "max_keywords": 5},
            "collected_data": {},
            "human_feedback": None,
            "retry_target_tools": None,
        }
        new_state = quality_gate_node(state)
        route = route_after_quality_gate(new_state)
        assert route == "research_agent_node"

    def test_critic_retries_bounded(self):
        from src.graph.nodes import route_after_critic
        state = {
            "critic_feedback": {"overall_verdict": "REVISE"},
            "execution_metadata": {"critic_retries": 2},
        }
        assert route_after_critic(state) == "strategy_generation_node"

    def test_critic_first_revise_retries(self):
        from src.graph.nodes import route_after_critic
        state = {
            "critic_feedback": {"overall_verdict": "REVISE"},
            "execution_metadata": {"critic_retries": 1},
        }
        assert route_after_critic(state) == "research_agent_node"


class TestReconcileTerminalDbStatus:
    def _fn(self):
        from api.routes.agent import _reconcile_terminal_db_status
        return _reconcile_terminal_db_status

    def test_no_op_for_pending_status(self):
        with patch("src.db_client.connect_db") as mock_db:
            self._fn()("run-123", "pending")
            mock_db.assert_not_called()

    def test_no_op_for_completed_status(self):
        with patch("src.db_client.connect_db") as mock_db:
            self._fn()("run-123", "completed")
            mock_db.assert_not_called()

    def test_marks_pending_row_as_failed(self):
        mock_row = MagicMock()
        mock_row.status = "pending"
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.filter.return_value.first.return_value = mock_row
        mock_engine = MagicMock()
        with patch("src.db_client.connect_db", return_value=mock_engine), \
             patch("sqlalchemy.orm.Session", return_value=mock_session):
            self._fn()("run-abc", "failed")
        assert mock_row.status == "failed"
        mock_session.commit.assert_called_once()

    def test_does_not_overwrite_already_failed_row(self):
        mock_row = MagicMock()
        mock_row.status = "failed"
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.filter.return_value.first.return_value = mock_row
        mock_engine = MagicMock()
        with patch("src.db_client.connect_db", return_value=mock_engine), \
             patch("sqlalchemy.orm.Session", return_value=mock_session):
            self._fn()("run-xyz", "failed")
        assert mock_row.status == "failed"
        mock_session.commit.assert_not_called()
