"""OpenAI Chat Completions adapter.

Converts between AITX IR and OpenAI's tool format used in the
Chat Completions API (``tools`` parameter).
"""

from __future__ import annotations

import json
from typing import Any

from ..ir.types import ToolCall, ToolResult, UniversalTool
from .base import FormatAdapter


class OpenAIChatAdapter(FormatAdapter):
    """Adapter for the OpenAI Chat Completions API.

    Schema format::

        {
            "type": "function",
            "function": {
                "name": "...",
                "description": "...",
                "parameters": { JSON Schema }
            }
        }
    """

    def to_schema(self, tool: UniversalTool) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.to_json_schema(),
            },
        }

    def parse_tool_calls(self, response: Any) -> list[ToolCall]:
        """Parse tool calls from an OpenAI ChatCompletion response.

        Accepts either:
        - A raw dict with ``choices[0].message.tool_calls``
        - An OpenAI ``ChatCompletion`` object (from the openai SDK)
        """
        calls: list[ToolCall] = []

        # Handle dict responses
        if isinstance(response, dict):
            message = response.get("choices", [{}])[0].get("message", {})
            tool_calls = message.get("tool_calls", [])
            for tc in tool_calls:
                fn = tc.get("function", {})
                calls.append(
                    ToolCall(
                        id=tc.get("id", ""),
                        name=fn.get("name", ""),
                        arguments=json.loads(fn.get("arguments", "{}")),
                    )
                )
            return calls

        # Handle OpenAI SDK objects
        message = response.choices[0].message
        if not message.tool_calls:
            return []
        for tc in message.tool_calls:
            calls.append(
                ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=json.loads(tc.function.arguments),
                )
            )
        return calls

    def format_result(self, result: ToolResult) -> dict[str, Any]:
        return {
            "role": "tool",
            "tool_call_id": result.tool_call_id,
            "content": result.content,
        }
