"""Additional convert() tests for edge cases and all format combinations."""

from __future__ import annotations

import pytest

from aitx.convert import convert


def _mcp_tool(name: str = "test") -> dict:
    return {
        "name": name,
        "description": "A test tool",
        "inputSchema": {
            "type": "object",
            "properties": {"x": {"type": "string"}},
            "required": ["x"],
        },
    }


def _openai_tool(name: str = "test") -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": "A test tool",
            "parameters": {
                "type": "object",
                "properties": {"x": {"type": "string"}},
                "required": ["x"],
            },
        },
    }


def _anthropic_tool(name: str = "test") -> dict:
    return {
        "name": name,
        "description": "A test tool",
        "input_schema": {
            "type": "object",
            "properties": {"x": {"type": "string"}},
            "required": ["x"],
        },
    }


def _gemini_tool(name: str = "test") -> dict:
    return {
        "name": name,
        "description": "A test tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {"x": {"type": "STRING"}},
            "required": ["x"],
        },
    }


# ── All format combinations ──────────────────────────────────────────


@pytest.mark.parametrize(
    "source,target,make_tool",
    [
        ("mcp", "openai-chat", _mcp_tool),
        ("mcp", "anthropic", _mcp_tool),
        ("mcp", "gemini", _mcp_tool),
        ("openai-chat", "mcp", _openai_tool),
        ("openai-chat", "anthropic", _openai_tool),
        ("openai-chat", "gemini", _openai_tool),
        ("anthropic", "mcp", _anthropic_tool),
        ("anthropic", "openai-chat", _anthropic_tool),
        ("anthropic", "gemini", _anthropic_tool),
        ("gemini", "mcp", _gemini_tool),
        ("gemini", "openai-chat", _gemini_tool),
        ("gemini", "anthropic", _gemini_tool),
    ],
)
def test_all_format_combinations(source: str, target: str, make_tool):
    """Every source->target pair should produce valid output."""
    result = convert(make_tool(), source=source, target=target)  # type: ignore[arg-type]
    assert result.output is not None
    assert result.source == source
    assert result.target == target


def test_convert_invalid_target():
    with pytest.raises(ValueError, match="Unknown target format"):
        convert({}, source="mcp", target="invalid")  # type: ignore[arg-type]


def test_openai_strict_warning():
    tool = {
        "type": "function",
        "function": {
            "name": "strict_fn",
            "description": "Has strict",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {"x": {"type": "string"}},
                "required": ["x"],
                "additionalProperties": False,
            },
        },
    }
    result = convert(tool, source="openai-chat", target="mcp")
    fields = [w.field for w in result.warnings]
    assert "strict" in fields


def test_mcp_all_warnings():
    tool = {
        "name": "full",
        "title": "Full Tool",
        "description": "Has all MCP fields",
        "inputSchema": {"type": "object", "properties": {}},
        "outputSchema": {"type": "object"},
        "annotations": {"readOnlyHint": True},
    }
    result = convert(tool, source="mcp", target="openai-chat")
    fields = [w.field for w in result.warnings]
    assert "title" in fields
    assert "outputSchema" in fields
    assert "annotations" in fields
