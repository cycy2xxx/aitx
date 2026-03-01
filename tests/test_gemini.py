"""Tests for Gemini adapter."""

from __future__ import annotations

import aitx
from aitx.adapters.gemini import GeminiAdapter
from aitx.ir.introspect import introspect


@aitx.tool()
def summarize(text: str, max_length: int = 100) -> str:
    """Summarize text to a maximum length.

    Args:
        text: The text to summarize
        max_length: Maximum output length
    """
    return text[:max_length]


def test_gemini_schema_uppercase_types():
    adapter = GeminiAdapter()
    ir = introspect(summarize)
    schema = adapter.to_schema(ir)

    assert schema["name"] == "summarize"
    assert schema["description"] == "Summarize text to a maximum length."
    params = schema["parameters"]
    assert params["type"] == "OBJECT"
    assert params["properties"]["text"]["type"] == "STRING"
    assert params["properties"]["max_length"]["type"] == "INTEGER"


def test_to_gemini():
    schemas = aitx.to_gemini([summarize])
    assert len(schemas) == 1
    assert schemas[0]["parameters"]["properties"]["text"]["type"] == "STRING"


def test_gemini_parse_tool_calls_dict():
    adapter = GeminiAdapter()
    response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "functionCall": {
                                "name": "summarize",
                                "args": {"text": "hello world", "max_length": 5},
                            }
                        }
                    ]
                }
            }
        ]
    }
    calls = adapter.parse_tool_calls(response)
    assert len(calls) == 1
    assert calls[0].name == "summarize"
    assert calls[0].arguments == {"text": "hello world", "max_length": 5}


def test_gemini_format_result():
    from aitx.ir.types import ToolResult

    adapter = GeminiAdapter()
    result = ToolResult(
        tool_call_id="1",
        name="summarize",
        content='{"summary": "hello"}',
    )
    formatted = adapter.format_result(result)
    assert formatted["functionResponse"]["name"] == "summarize"
    assert formatted["functionResponse"]["response"]["summary"] == "hello"


def test_handle_gemini():
    response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "functionCall": {
                                "name": "summarize",
                                "args": {"text": "hello world", "max_length": 5},
                            }
                        }
                    ]
                }
            }
        ]
    }
    results = aitx.handle_gemini(response, [summarize])
    assert len(results) == 1
    assert results[0]["functionResponse"]["name"] == "summarize"
