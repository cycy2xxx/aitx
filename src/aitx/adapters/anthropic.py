"""Anthropic Claude Messages API adapter.

Converts between AITX IR and Anthropic's tool format used in the
Messages API (``tools`` parameter).
"""

from __future__ import annotations

import json
from typing import Any

from ..ir.types import ToolCall, ToolResult, UniversalTool
from .base import FormatAdapter


class AnthropicAdapter(FormatAdapter):
    """Adapter for the Anthropic Messages API.

    Schema format::

        {
            "name": "...",
            "description": "...",
            "input_schema": { JSON Schema }
        }
    """

    def to_schema(self, tool: UniversalTool) -> dict[str, Any]:
        return {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.to_json_schema(),
        }

    def parse_tool_calls(self, response: Any) -> list[ToolCall]:
        """Parse tool calls from an Anthropic Messages response.

        Accepts either:
        - A raw dict with ``content`` blocks of type ``tool_use``
        - An Anthropic ``Message`` object (from the anthropic SDK)
        """
        calls: list[ToolCall] = []

        # Handle dict responses
        if isinstance(response, dict):
            for block in response.get("content", []):
                if block.get("type") == "tool_use":
                    calls.append(
                        ToolCall(
                            id=block.get("id", ""),
                            name=block.get("name", ""),
                            arguments=block.get("input", {}),
                        )
                    )
            return calls

        # Handle Anthropic SDK objects
        for block in response.content:
            if block.type == "tool_use":
                calls.append(
                    ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=block.input
                        if isinstance(block.input, dict)
                        else json.loads(block.input),
                    )
                )
        return calls

    def format_result(self, result: ToolResult) -> dict[str, Any]:
        return {
            "type": "tool_result",
            "tool_use_id": result.tool_call_id,
            "content": result.content,
            **({"is_error": True} if result.is_error else {}),
        }
