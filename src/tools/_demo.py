# This is a small demo script to verify that tool schemas are auto-generated
# in the format expected by the Anthropic Messages API.
# Note: This output is what Phase 4's agent orchestrator will consume directly.

import json
from src.tools.registry import get_tool_schemas

def main():
    schemas = get_tool_schemas()
    print(json.dumps(schemas, indent=2))

if __name__ == "__main__":
    main()
