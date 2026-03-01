"""Tool call dispatch engine.

Matches incoming tool calls from any platform to registered AITX tool
functions, executes them, and returns structured results.
"""

from __future__ import annotations

import inspect
import json
import logging
from typing import TYPE_CHECKING, Any

from ..adapters.anthropic import AnthropicAdapter
from ..adapters.openai_chat import OpenAIChatAdapter
from ..ir.introspect import introspect
from ..ir.types import ToolCall, ToolResult

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

# Singleton adapter instances
_openai_adapter = OpenAIChatAdapter()
_anthropic_adapter = AnthropicAdapter()


def _build_tool_map(
    tools: list[Callable[..., Any]],
) -> dict[str, Callable[..., Any]]:
    """Build a name → function mapping, respecting @aitx.tool() names."""
    mapping: dict[str, Callable[..., Any]] = {}
    for fn in tools:
        ir = getattr(fn, "__aitx_tool__", None)
        name = ir.name if ir else fn.__name__
        mapping[name] = fn
    return mapping


def dispatch(call: ToolCall, tools: list[Callable[..., Any]]) -> ToolResult:
    """Execute a single tool call against the given tool list.

    Returns a ``ToolResult`` with the serialised output or error.
    """
    tool_map = _build_tool_map(tools)
    func = tool_map.get(call.name)

    if func is None:
        return ToolResult(
            tool_call_id=call.id,
            name=call.name,
            content=json.dumps({"error": f"Tool '{call.name}' not found"}),
            is_error=True,
        )

    # Unwrap the decorator wrapper if present
    actual = getattr(func, "__wrapped__", func)

    try:
        if inspect.iscoroutinefunction(actual):
            raise TypeError(
                "Async tools must be dispatched with dispatch_async(). "
                f"'{call.name}' is a coroutine."
            )
        result = actual(**call.arguments)
        return ToolResult(
            tool_call_id=call.id,
            name=call.name,
            content=json.dumps(result, default=str),
        )
    except Exception as e:
        logger.exception("Error executing tool '%s'", call.name)
        return ToolResult(
            tool_call_id=call.id,
            name=call.name,
            content=json.dumps({"error": str(e)}),
            is_error=True,
        )


# ── Convenience functions for platform-specific dispatching ───────────


def to_openai(tools: list[Callable[..., Any]]) -> list[dict[str, Any]]:
    """Generate OpenAI Chat Completions tool schemas from functions.

    Usage::

        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            tools=aitx.to_openai([my_tool_a, my_tool_b]),
        )
    """
    return [
        _openai_adapter.to_schema(getattr(fn, "__aitx_tool__", None) or introspect(fn))
        for fn in tools
    ]


def to_anthropic(tools: list[Callable[..., Any]]) -> list[dict[str, Any]]:
    """Generate Anthropic Messages API tool schemas from functions.

    Usage::

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            messages=messages,
            tools=aitx.to_anthropic([my_tool_a, my_tool_b]),
        )
    """
    return [
        _anthropic_adapter.to_schema(getattr(fn, "__aitx_tool__", None) or introspect(fn))
        for fn in tools
    ]


def handle_openai(
    response: Any,
    tools: list[Callable[..., Any]],
) -> list[dict[str, Any]]:
    """Parse tool calls from an OpenAI response and execute them.

    Returns a list of message dicts ready to append to your conversation::

        results = aitx.handle_openai(response, [my_tool_a, my_tool_b])
        messages.extend(results)
    """
    calls = _openai_adapter.parse_tool_calls(response)
    return [_openai_adapter.format_result(dispatch(call, tools)) for call in calls]


def handle_anthropic(
    response: Any,
    tools: list[Callable[..., Any]],
) -> list[dict[str, Any]]:
    """Parse tool calls from an Anthropic response and execute them.

    Returns a list of tool_result dicts ready to use in follow-up::

        results = aitx.handle_anthropic(response, [my_tool_a, my_tool_b])
    """
    calls = _anthropic_adapter.parse_tool_calls(response)
    return [_anthropic_adapter.format_result(dispatch(call, tools)) for call in calls]
