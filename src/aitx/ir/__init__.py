"""Internal Representation — the superset schema for all tool formats."""

from .introspect import introspect
from .types import ToolCall, ToolParameter, ToolResult, UniversalTool

__all__ = [
    "ToolCall",
    "ToolParameter",
    "ToolResult",
    "UniversalTool",
    "introspect",
]
