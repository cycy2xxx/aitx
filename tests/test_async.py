"""Tests for async tool dispatch."""

from __future__ import annotations

import pytest

import aitx
from aitx.bridge.dispatcher import dispatch, dispatch_async
from aitx.ir.types import ToolCall


@aitx.tool()
async def async_lookup(key: str) -> dict:
    """Look up a value by key.

    Args:
        key: The key to look up
    """
    return {"key": key, "value": f"result_for_{key}"}


@aitx.tool()
def sync_add(a: int, b: int) -> int:
    """Add two numbers.

    Args:
        a: First number
        b: Second number
    """
    return a + b


@pytest.mark.asyncio
async def test_dispatch_async_with_async_tool():
    call = ToolCall(id="1", name="async_lookup", arguments={"key": "test"})
    result = await dispatch_async(call, [async_lookup])

    assert not result.is_error
    assert "result_for_test" in result.content


@pytest.mark.asyncio
async def test_dispatch_async_with_sync_tool():
    """dispatch_async should handle sync tools via executor."""
    call = ToolCall(id="2", name="sync_add", arguments={"a": 3, "b": 4})
    result = await dispatch_async(call, [sync_add])

    assert not result.is_error
    assert "7" in result.content


def test_dispatch_sync_rejects_async_tool():
    """Sync dispatch should error on async tools."""
    call = ToolCall(id="3", name="async_lookup", arguments={"key": "test"})
    result = dispatch(call, [async_lookup])

    assert result.is_error
    assert "dispatch_async" in result.content.lower() or "async" in result.content.lower()


@pytest.mark.asyncio
async def test_handle_openai_async():
    response = {
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "async_lookup",
                                "arguments": '{"key": "hello"}',
                            },
                        }
                    ]
                }
            }
        ]
    }
    results = await aitx.handle_openai_async(response, [async_lookup])
    assert len(results) == 1
    assert results[0]["role"] == "tool"
    assert "result_for_hello" in results[0]["content"]


@pytest.mark.asyncio
async def test_handle_gemini_async():
    response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "functionCall": {
                                "name": "sync_add",
                                "args": {"a": 10, "b": 20},
                            }
                        }
                    ]
                }
            }
        ]
    }
    results = await aitx.handle_gemini_async(response, [sync_add])
    assert len(results) == 1
    assert results[0]["functionResponse"]["response"] == 30
