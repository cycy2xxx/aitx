"""Edge case tests for all adapters — SDK objects, nullable, empty responses."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

from aitx.adapters.anthropic import AnthropicAdapter
from aitx.adapters.gemini import GeminiAdapter, _schema_to_gemini
from aitx.adapters.openai_chat import OpenAIChatAdapter
from aitx.ir.introspect import introspect

# ── OpenAI SDK object parsing ────────────────────────────────────────


def _make_openai_sdk_response(tool_calls: list[dict[str, Any]] | None) -> Any:
    """Build a fake OpenAI SDK ChatCompletion-like object."""
    calls = None
    if tool_calls:
        calls = [
            SimpleNamespace(
                id=tc["id"],
                function=SimpleNamespace(
                    name=tc["name"],
                    arguments=json.dumps(tc["arguments"]),
                ),
            )
            for tc in tool_calls
        ]
    message = SimpleNamespace(tool_calls=calls)
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice])


def test_openai_parse_sdk_object():
    adapter = OpenAIChatAdapter()
    resp = _make_openai_sdk_response(
        [
            {"id": "call_1", "name": "test_fn", "arguments": {"x": 1}},
        ]
    )
    calls = adapter.parse_tool_calls(resp)
    assert len(calls) == 1
    assert calls[0].name == "test_fn"
    assert calls[0].arguments == {"x": 1}


def test_openai_parse_sdk_no_tool_calls():
    adapter = OpenAIChatAdapter()
    resp = _make_openai_sdk_response(None)
    calls = adapter.parse_tool_calls(resp)
    assert calls == []


# ── Anthropic SDK object parsing ─────────────────────────────────────


def _make_anthropic_sdk_response(blocks: list[dict[str, Any]]) -> Any:
    """Build a fake Anthropic Message-like object."""
    content = []
    for b in blocks:
        if b["type"] == "tool_use":
            content.append(
                SimpleNamespace(
                    type="tool_use",
                    id=b["id"],
                    name=b["name"],
                    input=b["input"],
                )
            )
        else:
            content.append(SimpleNamespace(type=b["type"]))
    return SimpleNamespace(content=content)


def test_anthropic_parse_sdk_object():
    adapter = AnthropicAdapter()
    resp = _make_anthropic_sdk_response(
        [
            {"type": "text"},
            {"type": "tool_use", "id": "tu_1", "name": "greet", "input": {"name": "World"}},
        ]
    )
    calls = adapter.parse_tool_calls(resp)
    assert len(calls) == 1
    assert calls[0].name == "greet"
    assert calls[0].arguments == {"name": "World"}


def test_anthropic_parse_sdk_no_tool_use():
    adapter = AnthropicAdapter()
    resp = _make_anthropic_sdk_response([{"type": "text"}])
    calls = adapter.parse_tool_calls(resp)
    assert calls == []


# ── Gemini edge cases ────────────────────────────────────────────────


def test_gemini_nullable_type():
    """anyOf with null should produce nullable: true."""
    schema = {"anyOf": [{"type": "string"}, {"type": "null"}]}
    result = _schema_to_gemini(schema)
    assert result.get("nullable") is True
    assert result["type"] == "STRING"


def test_gemini_enum_preserved():
    schema = {"type": "string", "enum": ["a", "b", "c"]}
    result = _schema_to_gemini(schema)
    assert result["type"] == "STRING"
    assert result["enum"] == ["a", "b", "c"]


def test_gemini_nested_object():
    schema = {
        "type": "object",
        "properties": {
            "addr": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
            }
        },
    }
    result = _schema_to_gemini(schema)
    assert result["properties"]["addr"]["type"] == "OBJECT"
    assert result["properties"]["addr"]["properties"]["city"]["type"] == "STRING"


def test_gemini_array_items():
    schema = {"type": "array", "items": {"type": "integer"}}
    result = _schema_to_gemini(schema)
    assert result["type"] == "ARRAY"
    assert result["items"]["type"] == "INTEGER"


def test_gemini_parse_empty_candidates():
    adapter = GeminiAdapter()
    calls = adapter.parse_tool_calls({"candidates": []})
    assert calls == []


def test_gemini_parse_no_function_call():
    adapter = GeminiAdapter()
    resp = {"candidates": [{"content": {"parts": [{"text": "hello"}]}}]}
    calls = adapter.parse_tool_calls(resp)
    assert calls == []


def test_gemini_format_result_plain_string():
    from aitx.ir.types import ToolResult

    adapter = GeminiAdapter()
    result = ToolResult(tool_call_id="1", name="fn", content="plain text")
    formatted = adapter.format_result(result)
    assert formatted["functionResponse"]["response"] == {"result": "plain text"}


# ── Gemini SDK-like object ───────────────────────────────────────────


def test_gemini_parse_sdk_object():
    adapter = GeminiAdapter()

    fc = SimpleNamespace(name="calc", args={"a": 1, "b": 2})
    part = SimpleNamespace(function_call=fc)
    content = SimpleNamespace(parts=[part])
    candidate = SimpleNamespace(content=content)
    resp = SimpleNamespace(candidates=[candidate])

    calls = adapter.parse_tool_calls(resp)
    assert len(calls) == 1
    assert calls[0].name == "calc"
    assert calls[0].arguments == {"a": 1, "b": 2}


# ── Schema generation with generic types ─────────────────────────────


def func_with_nullable(name: str, tag: str | None = None) -> str:
    """Test function.

    Args:
        name: Name
        tag: Optional tag
    """
    return name


def test_openai_schema_with_nullable():
    ir = introspect(func_with_nullable)
    adapter = OpenAIChatAdapter()
    schema = adapter.to_schema(ir)
    props = schema["function"]["parameters"]["properties"]
    assert "anyOf" in props["tag"]


def test_gemini_schema_with_nullable():
    ir = introspect(func_with_nullable)
    adapter = GeminiAdapter()
    schema = adapter.to_schema(ir)
    # Gemini should handle nullable via the nullable flag
    tag_prop = schema["parameters"]["properties"]["tag"]
    assert tag_prop.get("nullable") is True or "anyOf" not in tag_prop
