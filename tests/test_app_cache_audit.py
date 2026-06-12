import ast
import pytest
import app

def test_static_cache_audit():
    with open("app.py", "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())
        
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            func_name = node.name
            if func_name.startswith("save_") or "save_to_db" in func_name:
                # Check decorators
                for decorator in node.decorator_list:
                    # check if decorator is st.cache_data
                    if isinstance(decorator, ast.Call):
                        func = decorator.func
                        if isinstance(func, ast.Attribute) and func.attr == "cache_data":
                            pytest.fail(f"Function {func_name} has @st.cache_data decorator!")
                    elif isinstance(decorator, ast.Attribute) and decorator.attr == "cache_data":
                        pytest.fail(f"Function {func_name} has @st.cache_data decorator!")

def test_save_keyword_results_no_cache(monkeypatch):
    call_count = 0
    def mock_save_to_db(data):
        nonlocal call_count
        call_count += 1
        return None
        
    monkeypatch.setattr("src.db_client.save_to_db", mock_save_to_db)
    
    test_data = [{"keyword": "test"}]
    
    # Call save_keyword_results twice
    app.save_keyword_results(test_data)
    app.save_keyword_results(test_data)
    
    # Assert it was called twice (without caching)
    assert call_count == 2
