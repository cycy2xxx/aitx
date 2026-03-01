"""Tests for the AITX core pipeline: IR, decorator, adapters, dispatcher."""

import json

import aitx
from aitx.adapters import AnthropicAdapter, OpenAIChatAdapter
from aitx.bridge.dispatcher import dispatch
from aitx.ir import ToolCall, ToolResult, UniversalTool, introspect

# ── Sample tools ──────────────────────────────────────────────────────


def get_weather(city: str, units: str = "celsius") -> dict:
    """Get the current weather for a city.

    Args:
        city: Name of the city.
        units: Temperature units (celsius or fahrenheit).
    """
    return {"city": city, "temp": 22, "units": units}


@aitx.tool()
def add(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b


@aitx.tool(name="greet_user")
def greet(name: str) -> str:
    """Say hello to someone."""
    return f"Hello, {name}!"


# ── IR Tests ──────────────────────────────────────────────────────────


def test_introspect_basic():
    ir = introspect(get_weather)
    assert ir.name == "get_weather"
    assert ir.description == "Get the current weather for a city."
    assert len(ir.parameters) == 2

    city = ir.parameters[0]
    assert city.name == "city"
    assert city.type == "string"
    assert city.required is True
    assert city.description == "Name of the city."

    units = ir.parameters[1]
    assert units.name == "units"
    assert units.required is False
    assert units.default == "celsius"


def test_introspect_to_json_schema():
    ir = introspect(get_weather)
    schema = ir.to_json_schema()
    assert schema["type"] == "object"
    assert "city" in schema["properties"]
    assert schema["properties"]["city"]["type"] == "string"
    assert "city" in schema["required"]
    assert "units" not in schema["required"]


def test_universal_tool_model_dump():
    ir = introspect(get_weather)
    data = ir.model_dump(mode="json")
    assert data["name"] == "get_weather"
    assert isinstance(data["parameters"], list)


# ── Decorator Tests ───────────────────────────────────────────────────


def test_tool_decorator_attaches_ir():
    ir = aitx.get_ir(add)
    assert isinstance(ir, UniversalTool)
    assert ir.name == "add"


def test_tool_decorator_custom_name():
    ir = aitx.get_ir(greet)
    assert ir.name == "greet_user"


def test_tool_decorator_preserves_function():
    assert add(3, 5) == 8
    assert greet("World") == "Hello, World!"


# ── OpenAI Adapter Tests ─────────────────────────────────────────────


def test_openai_schema():
    schemas = aitx.to_openai([get_weather])
    assert len(schemas) == 1
    s = schemas[0]
    assert s["type"] == "function"
    assert s["function"]["name"] == "get_weather"
    assert "city" in s["function"]["parameters"]["properties"]


def test_openai_parse_tool_calls():
    adapter = OpenAIChatAdapter()
    response = {
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {
                            "id": "call_123",
                            "type": "function",
                            "function": {
                                "name": "get_weather",
                                "arguments": json.dumps({"city": "Tokyo"}),
                            },
                        }
                    ]
                }
            }
        ]
    }
    calls = adapter.parse_tool_calls(response)
    assert len(calls) == 1
    assert calls[0].name == "get_weather"
    assert calls[0].arguments == {"city": "Tokyo"}


def test_openai_format_result():
    adapter = OpenAIChatAdapter()
    result = ToolResult(
        tool_call_id="call_123",
        name="get_weather",
        content='{"temp": 22}',
    )
    formatted = adapter.format_result(result)
    assert formatted["role"] == "tool"
    assert formatted["tool_call_id"] == "call_123"


# ── Anthropic Adapter Tests ──────────────────────────────────────────


def test_anthropic_schema():
    schemas = aitx.to_anthropic([get_weather])
    assert len(schemas) == 1
    s = schemas[0]
    assert s["name"] == "get_weather"
    assert "input_schema" in s
    assert "city" in s["input_schema"]["properties"]


def test_anthropic_parse_tool_calls():
    adapter = AnthropicAdapter()
    response = {
        "content": [
            {"type": "text", "text": "Let me check"},
            {
                "type": "tool_use",
                "id": "toolu_123",
                "name": "get_weather",
                "input": {"city": "Osaka"},
            },
        ]
    }
    calls = adapter.parse_tool_calls(response)
    assert len(calls) == 1
    assert calls[0].name == "get_weather"
    assert calls[0].arguments == {"city": "Osaka"}


def test_anthropic_format_result():
    adapter = AnthropicAdapter()
    result = ToolResult(
        tool_call_id="toolu_123",
        name="get_weather",
        content='{"temp": 22}',
    )
    formatted = adapter.format_result(result)
    assert formatted["type"] == "tool_result"
    assert formatted["tool_use_id"] == "toolu_123"


# ── Dispatcher Tests ─────────────────────────────────────────────────


def test_dispatch_basic():
    call = ToolCall(id="c1", name="get_weather", arguments={"city": "Tokyo"})
    result = dispatch(call, [get_weather])
    assert not result.is_error
    data = json.loads(result.content)
    assert data["city"] == "Tokyo"
    assert data["temp"] == 22


def test_dispatch_decorated_tool():
    call = ToolCall(id="c2", name="add", arguments={"a": 10, "b": 20})
    result = dispatch(call, [add])
    assert not result.is_error
    assert json.loads(result.content) == 30


def test_dispatch_not_found():
    call = ToolCall(id="c3", name="nonexistent", arguments={})
    result = dispatch(call, [get_weather])
    assert result.is_error


def test_handle_openai():
    response = {
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "get_weather",
                                "arguments": json.dumps({"city": "NYC"}),
                            },
                        }
                    ]
                }
            }
        ]
    }
    results = aitx.handle_openai(response, [get_weather])
    assert len(results) == 1
    assert results[0]["role"] == "tool"
    data = json.loads(results[0]["content"])
    assert data["city"] == "NYC"


def test_handle_anthropic():
    response = {
        "content": [
            {
                "type": "tool_use",
                "id": "toolu_1",
                "name": "get_weather",
                "input": {"city": "London"},
            }
        ]
    }
    results = aitx.handle_anthropic(response, [get_weather])
    assert len(results) == 1
    assert results[0]["type"] == "tool_result"
    data = json.loads(results[0]["content"])
    assert data["city"] == "London"
