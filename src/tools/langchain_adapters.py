"""
LangChain-compatible tool adapters for Keylytics.

Wraps every entry in TOOL_REGISTRY as a langchain_core.tools.StructuredTool
so that LangGraph agent graphs can invoke them uniformly via .invoke({...}).

All tools are backed by invoke_tool(), which guarantees:
  - Input validated against the tool's Pydantic input_model.
  - Errors returned as {"error": ..., "tool": name} — never raised.
  - Result is always a JSON-serialisable dict.

Usage
-----
    from src.tools.langchain_adapters import get_langchain_tools
    tools = get_langchain_tools()          # List[StructuredTool], one per registry entry
    result = tools[0].invoke({"seed_keyword": "coffee", "max_keywords": 10})
"""

from functools import partial
from typing import List

from langchain_core.tools import StructuredTool

from src.tools.registry import TOOL_REGISTRY, invoke_tool
from src.logger_config import get_logger

logger = get_logger(__name__)


def get_langchain_tools() -> List[StructuredTool]:
    """
    Build and return a StructuredTool for every registered Keylytics tool.

    Returns:
        List[StructuredTool] — one per TOOL_REGISTRY entry, in insertion order.
        Each tool's args_schema is the tool's Pydantic input_model so that
        LangGraph can introspect and validate arguments automatically.
    """
    tools: List[StructuredTool] = []
    for spec in TOOL_REGISTRY.values():
        tool = StructuredTool.from_function(
            # partial binds the tool name so invoke_tool knows which tool to call
            func=partial(invoke_tool, spec.name),
            name=spec.name,
            description=spec.description,
            args_schema=spec.input_model,
            # return_direct=False lets the agent loop process the result
            return_direct=False,
        )
        tools.append(tool)
        logger.debug(f"Registered LangChain tool: {spec.name}")

    logger.info(f"get_langchain_tools() returning {len(tools)} StructuredTool(s)")
    return tools
