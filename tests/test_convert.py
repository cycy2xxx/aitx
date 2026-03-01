"""Tests for JSON-to-JSON conversion API."""

from __future__ import annotations

import json
from pathlib import Path

from aitx.convert import convert

FIXTURES = Path(__file__).parent / "fixtures"


def test_mcp_to_openai():
    tool = json.loads((FIXTURES / "weather_mcp.json").read_text())
    result = convert(tool, source="mcp", target="openai-chat")

    assert result.output["type"] == "function"
    assert result.output["function"]["name"] == "get_weather"
    assert "city" in result.output["function"]["parameters"]["properties"]


def test_mcp_to_anthropic():
    tool = json.loads((FIXTURES / "weather_mcp.json").read_text())
    result = convert(tool, source="mcp", target="anthropic")

    assert result.output["name"] == "get_weather"
    assert "input_schema" in result.output
    assert "city" in result.output["input_schema"]["properties"]


def test_mcp_to_gemini():
    tool = json.loads((FIXTURES / "weather_mcp.json").read_text())
    result = convert(tool, source="mcp", target="gemini")

    assert result.output["name"] == "get_weather"
    assert result.output["parameters"]["type"] == "OBJECT"
    assert result.output["parameters"]["properties"]["city"]["type"] == "STRING"


def test_openai_to_mcp():
    openai_tool = {
        "type": "function",
        "function": {
            "name": "search",
            "description": "Search docs",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
                "required": ["query"],
            },
        },
    }
    result = convert(openai_tool, source="openai-chat", target="mcp")

    assert result.output["name"] == "search"
    assert "inputSchema" in result.output
    assert "query" in result.output["inputSchema"]["properties"]


def test_mcp_warnings_for_lost_fields():
    tool = json.loads((FIXTURES / "weather_mcp.json").read_text())
    result = convert(tool, source="mcp", target="openai-chat")

    # MCP has title and annotations that OpenAI doesn't support
    warning_fields = [w.field for w in result.warnings]
    assert "title" in warning_fields
    assert "annotations" in warning_fields


def test_roundtrip_mcp_openai_mcp():
    """Converting MCP → OpenAI → MCP should preserve core fields."""
    original = json.loads((FIXTURES / "weather_mcp.json").read_text())

    to_openai = convert(original, source="mcp", target="openai-chat")
    back_to_mcp = convert(to_openai.output, source="openai-chat", target="mcp")

    assert back_to_mcp.output["name"] == "get_weather"
    assert "city" in back_to_mcp.output["inputSchema"]["properties"]


def test_convert_invalid_source():
    import pytest

    with pytest.raises(ValueError, match="Unknown source format"):
        convert({}, source="invalid", target="mcp")  # type: ignore[arg-type]
