"""Pydantic v2 models for the AITX Internal Representation (IR).

These types form the universal superset schema that all platform-specific
formats are converted to and from.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ToolParameter(BaseModel):
    """A single parameter in a tool's input schema."""

    name: str
    type: str = "string"
    description: str = ""
    required: bool = True
    default: Any = None
    enum: list[Any] | None = None

    def to_json_schema_property(self) -> dict[str, Any]:
        """Convert to a JSON Schema property dict."""
        prop: dict[str, Any] = {"type": self.type}
        if self.description:
            prop["description"] = self.description
        if self.default is not None:
            prop["default"] = self.default
        if self.enum is not None:
            prop["enum"] = self.enum
        return prop


class UniversalTool(BaseModel):
    """Platform-agnostic representation of a tool (function).

    This is the IR that all adapters read from and write to.
    """

    name: str
    description: str = ""
    parameters: list[ToolParameter] = Field(default_factory=list)

    def to_json_schema(self) -> dict[str, Any]:
        """Convert to a standard JSON Schema ``object`` dict."""
        properties: dict[str, Any] = {}
        required: list[str] = []
        for p in self.parameters:
            properties[p.name] = p.to_json_schema_property()
            if p.required:
                required.append(p.name)

        schema: dict[str, Any] = {
            "type": "object",
            "properties": properties,
        }
        if required:
            schema["required"] = required
        return schema


class ToolCall(BaseModel):
    """A tool invocation request parsed from an LLM response."""

    id: str = ""
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """The result of executing a tool call."""

    tool_call_id: str = ""
    name: str
    content: str  # serialised JSON string
    is_error: bool = False
