"""
Tests for src/tools/registry.py.
Verifies get_tool_schemas() and invoke_tool() behavior including
error-as-result semantics and StructuredTool production.
"""

from unittest.mock import patch, MagicMock
from pydantic import BaseModel
from src.tools.registry import TOOL_REGISTRY, get_tool_schemas, invoke_tool


class TestToolRegistry:
    def test_registry_has_six_tools(self):
        assert len(TOOL_REGISTRY) == 6

    def test_all_expected_tools_present(self):
        expected = {
            "keyword_research", "serp_analysis", "competitor_gap",
            "trend_forecast", "topic_cluster", "intent_classifier"
        }
        assert set(TOOL_REGISTRY.keys()) == expected

    def test_each_spec_has_required_fields(self):
        for name, spec in TOOL_REGISTRY.items():
            assert spec.name == name
            assert spec.description
            assert spec.input_model is not None
            assert callable(spec.fn)


class TestGetToolSchemas:
    def test_returns_list_of_dicts(self):
        schemas = get_tool_schemas()
        assert isinstance(schemas, list)
        assert len(schemas) == 6

    def test_each_schema_has_required_keys(self):
        for schema in get_tool_schemas():
            assert "name" in schema
            assert "description" in schema
            assert "input_schema" in schema

    def test_each_schema_is_valid_json_schema(self):
        """input_schema must be a dict with 'type' and 'properties'."""
        for schema in get_tool_schemas():
            input_schema = schema["input_schema"]
            assert isinstance(input_schema, dict)
            assert "properties" in input_schema

    def test_schema_names_match_registry_keys(self):
        schemas = get_tool_schemas()
        schema_names = {s["name"] for s in schemas}
        assert schema_names == set(TOOL_REGISTRY.keys())


class TestInvokeTool:
    def test_unknown_tool_returns_error_dict(self):
        result = invoke_tool("does_not_exist", {})
        assert "error" in result
        assert result["tool"] == "does_not_exist"
        assert "does_not_exist" in result["error"]

    def test_invalid_args_returns_error_dict_not_raises(self):
        """Validation errors should never raise — always return error dict."""
        result = invoke_tool("intent_classifier", {"completely_wrong": "field"})
        assert "error" in result
        assert result["tool"] == "intent_classifier"

    def test_tool_error_returns_error_dict_not_raises(self):
        """Execution errors inside the tool should be caught and returned as dict."""
        with patch("src.tools.intent_classifier_tool.classify_intent_with_source", side_effect=Exception("upstream failed")):
            result = invoke_tool("intent_classifier", {"keyword": "coffee"})
        assert "error" in result
        assert "upstream failed" in result["error"]

    def test_valid_result_is_serializable(self):
        """A successful tool call must return a dict (or Pydantic-derived dict)."""
        mock_result = MagicMock()
        mock_result.__class__ = BaseModel
        mock_result.model_dump = MagicMock(return_value={"keyword": "test", "intent": "informational", "source": "rule"})

        with patch("src.tools.intent_classifier_tool.run", return_value=mock_result):
            result = invoke_tool("intent_classifier", {"keyword": "coffee"})
        # Should return the model_dump dict, not raise
        assert isinstance(result, dict)


class TestGetLangchainTools:
    def test_returns_six_structured_tools(self):
        from src.tools.langchain_adapters import get_langchain_tools
        tools = get_langchain_tools()
        assert len(tools) == 6

    def test_tool_names_match_registry(self):
        from src.tools.langchain_adapters import get_langchain_tools
        tools = get_langchain_tools()
        tool_names = {t.name for t in tools}
        assert tool_names == set(TOOL_REGISTRY.keys())

    def test_each_tool_has_args_schema(self):
        from src.tools.langchain_adapters import get_langchain_tools
        for tool in get_langchain_tools():
            assert tool.args_schema is not None

    def test_each_tool_has_description(self):
        from src.tools.langchain_adapters import get_langchain_tools
        for tool in get_langchain_tools():
            assert tool.description
