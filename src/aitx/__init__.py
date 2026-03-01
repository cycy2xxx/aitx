"""aitx — AI Tool eXchange.

Write a Python function, use it as a tool on any AI platform.

Public API
----------
Decorator:
    ``@aitx.tool()`` — register a function as a tool

Schema Generation:
    ``aitx.to_openai(tools)`` — generate OpenAI tool schemas
    ``aitx.to_anthropic(tools)`` — generate Anthropic tool schemas
    ``aitx.to_gemini(tools)`` — generate Gemini tool schemas

Runtime Dispatch (sync):
    ``aitx.handle_openai(response, tools)`` — dispatch OpenAI tool calls
    ``aitx.handle_anthropic(response, tools)`` — dispatch Anthropic tool calls
    ``aitx.handle_gemini(response, tools)`` — dispatch Gemini tool calls

Runtime Dispatch (async):
    ``aitx.handle_openai_async(response, tools)``
    ``aitx.handle_anthropic_async(response, tools)``
    ``aitx.handle_gemini_async(response, tools)``

JSON-to-JSON Conversion:
    ``aitx.convert(tool_dict, source=..., target=...)``
"""

__version__ = "0.1.0"

from .bridge.dispatcher import (
    dispatch,
    dispatch_async,
    handle_anthropic,
    handle_anthropic_async,
    handle_gemini,
    handle_gemini_async,
    handle_openai,
    handle_openai_async,
    to_anthropic,
    to_gemini,
    to_openai,
)
from .convert import convert
from .decorator import get_ir, get_tools, tool

__all__ = [
    # Decorator
    "tool",
    "get_ir",
    "get_tools",
    # Schema generation
    "to_openai",
    "to_anthropic",
    "to_gemini",
    # Sync dispatch
    "handle_openai",
    "handle_anthropic",
    "handle_gemini",
    "dispatch",
    # Async dispatch
    "handle_openai_async",
    "handle_anthropic_async",
    "handle_gemini_async",
    "dispatch_async",
    # JSON-to-JSON conversion
    "convert",
]
