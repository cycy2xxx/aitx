"""Example: JSON-to-JSON schema conversion with loss reporting.

Demonstrates converting tool definitions between formats using the
convert() API and CLI-equivalent functionality.
"""

import json

from aitx.convert import convert

# An MCP tool definition with MCP-specific fields
mcp_tool = {
    "name": "create_issue",
    "title": "GitHub Issue Creator",
    "description": "Create a new issue in a GitHub repository",
    "inputSchema": {
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "Repository (owner/name)"},
            "title": {"type": "string", "description": "Issue title"},
            "body": {"type": "string", "description": "Issue body (markdown)"},
            "labels": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Labels to apply",
            },
        },
        "required": ["repo", "title"],
    },
    "annotations": {
        "readOnlyHint": False,
        "destructiveHint": False,
        "openWorldHint": True,
    },
}

print("=" * 60)
print("AITX Schema Conversion Demo")
print("=" * 60)

# Convert to each format and show what's lost
for target in ["openai-chat", "anthropic", "gemini"]:
    result = convert(mcp_tool, source="mcp", target=target)  # type: ignore[arg-type]
    print(f"\n--- MCP -> {target} ---")
    print(json.dumps(result.output, indent=2))

    if result.warnings:
        print(f"\n  Warnings ({len(result.warnings)}):")
        for w in result.warnings:
            print(f"    [{w.severity}] {w.field}: {w.message}")
    else:
        print("\n  No information lost.")

# Roundtrip: MCP -> OpenAI -> MCP
print("\n--- Roundtrip: MCP -> OpenAI -> MCP ---")
to_openai = convert(mcp_tool, source="mcp", target="openai-chat")
back_to_mcp = convert(to_openai.output, source="openai-chat", target="mcp")
print(json.dumps(back_to_mcp.output, indent=2))
print(f"  Core fields preserved: name='{back_to_mcp.output['name']}'")
