from src.tools.registry import get_tool_schemas

def test_get_tool_schemas():
    schemas = get_tool_schemas()

    # We registered 6 tools
    assert len(schemas) == 6

    for s in schemas:
        assert "name" in s
        assert "description" in s
        assert "input_schema" in s

        assert s["name"] != ""
        assert s["description"] != ""

        schema = s["input_schema"]
        assert schema.get("type") == "object"
