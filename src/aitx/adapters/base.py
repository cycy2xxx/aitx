"""Base class for all platform format adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..ir.types import ToolCall, ToolResult, UniversalTool


class FormatAdapter(ABC):
    """Abstract base class that every platform adapter must implement.

    An adapter handles three responsibilities:

    1. **Schema generation** — convert a ``UniversalTool`` IR to the
       platform's native tool definition format.
    2. **Tool call parsing** — extract ``ToolCall`` objects from the
       platform's raw LLM response.
    3. **Result formatting** — convert a ``ToolResult`` back into the
       format the platform expects when returning tool output.
    """

    @abstractmethod
    def to_schema(self, tool: UniversalTool) -> dict[str, Any]:
        """Convert an IR tool to the platform's schema format."""

    @abstractmethod
    def parse_tool_calls(self, response: Any) -> list[ToolCall]:
        """Extract tool calls from a raw LLM response."""

    @abstractmethod
    def format_result(self, result: ToolResult) -> dict[str, Any]:
        """Format a tool result for the platform's expected response."""
