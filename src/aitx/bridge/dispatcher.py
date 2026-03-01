"""Tool call dispatch engine.

Matches incoming tool calls from any platform to registered AITX tool
functions, executes them, and returns structured results.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
from typing import TYPE_CHECKING, Any

from ..adapters.anthropic import AnthropicAdapter
from ..adapters.gemini import GeminiAdapter
from ..adapters.openai_chat import OpenAIChatAdapter
from ..ir.introspect import introspect
from ..ir.types import ToolCall, ToolResult

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

# Singleton adapter instances
_openai_adapter = OpenAIChatAdapter()
_anthropic_adapter = AnthropicAdapter()
_gemini_adapter = GeminiAdapter()


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
    """Execute a single tool call against the given tool list (sync).

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
                f"Async tool '{call.name}' cannot be dispatched synchronously. "
                "Use dispatch_async() or handle_openai_async() instead."
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


async def dispatch_async(call: ToolCall, tools: list[Callable[..., Any]]) -> ToolResult:
    """Execute a single tool call, supporting both sync and async tools."""
    tool_map = _build_tool_map(tools)
    func = tool_map.get(call.name)

    if func is None:
        return ToolResult(
            tool_call_id=call.id,
            name=call.name,
            content=json.dumps({"error": f"Tool '{call.name}' not found"}),
            is_error=True,
        )

    actual = getattr(func, "__wrapped__", func)

    try:
        if inspect.iscoroutinefunction(actual):
            result = await actual(**call.arguments)
        else:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, lambda: actual(**call.arguments))
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


# ── Schema generation helpers ─────────────────────────────────────────


def _get_ir(fn: Callable[..., Any]) -> Any:
    """Get or build IR for a function."""
    return getattr(fn, "__aitx_tool__", None) or introspect(fn)


def to_openai(tools: list[Callable[..., Any]]) -> list[dict[str, Any]]:
    """Generate OpenAI Chat Completions tool schemas from functions."""
    return [_openai_adapter.to_schema(_get_ir(fn)) for fn in tools]


def to_anthropic(tools: list[Callable[..., Any]]) -> list[dict[str, Any]]:
    """Generate Anthropic Messages API tool schemas from functions."""
    return [_anthropic_adapter.to_schema(_get_ir(fn)) for fn in tools]


def to_gemini(tools: list[Callable[..., Any]]) -> list[dict[str, Any]]:
    """Generate Gemini FunctionDeclaration schemas from functions."""
    return [_gemini_adapter.to_schema(_get_ir(fn)) for fn in tools]


# ── Sync dispatch handlers ────────────────────────────────────────────


def handle_openai(
    response: Any,
    tools: list[Callable[..., Any]],
) -> list[dict[str, Any]]:
    """Parse tool calls from an OpenAI response and execute them (sync)."""
    calls = _openai_adapter.parse_tool_calls(response)
    return [_openai_adapter.format_result(dispatch(call, tools)) for call in calls]


def handle_anthropic(
    response: Any,
    tools: list[Callable[..., Any]],
) -> list[dict[str, Any]]:
    """Parse tool calls from an Anthropic response and execute them (sync)."""
    calls = _anthropic_adapter.parse_tool_calls(response)
    return [_anthropic_adapter.format_result(dispatch(call, tools)) for call in calls]


def handle_gemini(
    response: Any,
    tools: list[Callable[..., Any]],
) -> list[dict[str, Any]]:
    """Parse tool calls from a Gemini response and execute them (sync)."""
    calls = _gemini_adapter.parse_tool_calls(response)
    return [_gemini_adapter.format_result(dispatch(call, tools)) for call in calls]


# ── Async dispatch handlers ───────────────────────────────────────────


async def handle_openai_async(
    response: Any,
    tools: list[Callable[..., Any]],
) -> list[dict[str, Any]]:
    """Parse tool calls from an OpenAI response and execute them (async)."""
    calls = _openai_adapter.parse_tool_calls(response)
    results = [await dispatch_async(call, tools) for call in calls]
    return [_openai_adapter.format_result(r) for r in results]


async def handle_anthropic_async(
    response: Any,
    tools: list[Callable[..., Any]],
) -> list[dict[str, Any]]:
    """Parse tool calls from an Anthropic response and execute them (async)."""
    calls = _anthropic_adapter.parse_tool_calls(response)
    results = [await dispatch_async(call, tools) for call in calls]
    return [_anthropic_adapter.format_result(r) for r in results]


async def handle_gemini_async(
    response: Any,
    tools: list[Callable[..., Any]],
) -> list[dict[str, Any]]:
    """Parse tool calls from a Gemini response and execute them (async)."""
    calls = _gemini_adapter.parse_tool_calls(response)
    results = [await dispatch_async(call, tools) for call in calls]
    return [_gemini_adapter.format_result(r) for r in results]
