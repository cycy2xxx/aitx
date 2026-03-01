"""Google Gemini FunctionDeclaration adapter.

Converts between AITX IR and Gemini's tool format. Gemini uses an
OpenAPI 3.0 subset with UPPERCASE type names and several limitations
compared to full JSON Schema.
"""

from __future__ import annotations

import json
from typing import Any

from ..ir.types import ToolCall, ToolResult, UniversalTool
from .base import FormatAdapter

# JSON Schema type → Gemini UPPERCASE type
_TYPE_MAP: dict[str, str] = {
    "string": "STRING",
    "number": "NUMBER",
    "integer": "INTEGER",
    "boolean": "BOOLEAN",
    "array": "ARRAY",
    "object": "OBJECT",
}


def _schema_to_gemini(schema: dict[str, Any]) -> dict[str, Any]:
    """Recursively convert a JSON Schema dict to Gemini's OpenAPI subset."""
    result: dict[str, Any] = {}

    typ = schema.get("type", "string")

    # Handle anyOf (nullable unions)
    if "anyOf" in schema:
        variants = schema["anyOf"]
        non_null = [v for v in variants if v.get("type") != "null"]
        has_null = len(non_null) < len(variants)
        if has_null:
            result["nullable"] = True
        if len(non_null) == 1:
            result.update(_schema_to_gemini(non_null[0]))
            return result
        # Multiple non-null: pick first (Gemini cannot represent unions)
        if non_null:
            result.update(_schema_to_gemini(non_null[0]))
        return result

    result["type"] = _TYPE_MAP.get(typ, "STRING")

    if "description" in schema:
        result["description"] = schema["description"]
    if "enum" in schema:
        result["enum"] = schema["enum"]
    if "minimum" in schema:
        result["minimum"] = schema["minimum"]
    if "maximum" in schema:
        result["maximum"] = schema["maximum"]

    # Recurse into properties
    if "properties" in schema:
        result["properties"] = {k: _schema_to_gemini(v) for k, v in schema["properties"].items()}
    if "required" in schema:
        result["required"] = schema["required"]

    # Array items
    if "items" in schema:
        result["items"] = _schema_to_gemini(schema["items"])

    # additionalProperties
    if "additionalProperties" in schema and isinstance(schema["additionalProperties"], dict):
        result["additionalProperties"] = _schema_to_gemini(schema["additionalProperties"])

    return result


class GeminiAdapter(FormatAdapter):
    """Adapter for Google Gemini's function calling API.

    Schema format::

        {
            "name": "...",
            "description": "...",
            "parameters": { OpenAPI-style with UPPERCASE types }
        }

    Known limitations vs full JSON Schema:
    - Type names must be UPPERCASE
    - No $ref/$defs support (must inline)
    - No oneOf/allOf (limited anyOf)
    - No default, examples, pattern keywords
    - null type → nullable: true flag
    """

    def to_schema(self, tool: UniversalTool) -> dict[str, Any]:
        json_schema = tool.to_json_schema()
        return {
            "name": tool.name,
            "description": tool.description or tool.name,
            "parameters": _schema_to_gemini(json_schema),
        }

    def parse_tool_calls(self, response: Any) -> list[ToolCall]:
        """Parse tool calls from a Gemini response.

        Accepts either:
        - A raw dict with candidates[0].content.parts[].functionCall
        - A google-genai SDK GenerateContentResponse
        """
        calls: list[ToolCall] = []

        if isinstance(response, dict):
            candidates = response.get("candidates", [])
            if not candidates:
                return []
            parts = candidates[0].get("content", {}).get("parts", [])
            for i, part in enumerate(parts):
                fc = part.get("functionCall") or part.get("function_call")
                if fc:
                    calls.append(
                        ToolCall(
                            id=f"gemini_call_{i}",
                            name=fc.get("name", ""),
                            arguments=fc.get("args", {}),
                        )
                    )
            return calls

        # Handle SDK objects
        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            parts = candidate.content.parts if hasattr(candidate, "content") else []
            for i, part in enumerate(parts):
                if hasattr(part, "function_call") and part.function_call:
                    fc = part.function_call
                    calls.append(
                        ToolCall(
                            id=f"gemini_call_{i}",
                            name=fc.name,
                            arguments=dict(fc.args) if hasattr(fc.args, "items") else {},
                        )
                    )
        return calls

    def format_result(self, result: ToolResult) -> dict[str, Any]:
        """Format as a Gemini functionResponse part."""
        try:
            content = json.loads(result.content)
        except (json.JSONDecodeError, TypeError):
            content = {"result": result.content}

        return {
            "functionResponse": {
                "name": result.name,
                "response": content,
            }
        }
