"""aitx — AI Tool eXchange.

Write a Python function, use it as a tool on any AI platform.

Public API
----------
Decorator:
    ``@aitx.tool()`` — register a function as a tool

Schema Generation:
    ``aitx.to_openai(tools)`` — generate OpenAI tool schemas
    ``aitx.to_anthropic(tools)`` — generate Anthropic tool schemas

Runtime Dispatch:
    ``aitx.handle_openai(response, tools)`` — dispatch OpenAI tool calls
    ``aitx.handle_anthropic(response, tools)`` — dispatch Anthropic tool calls
"""

__version__ = "0.1.0"

from .bridge.dispatcher import (
    dispatch,
    handle_anthropic,
    handle_openai,
    to_anthropic,
    to_openai,
)
from .decorator import get_ir, get_tools, tool

__all__ = [
    "tool",
    "get_ir",
    "get_tools",
    "to_openai",
    "to_anthropic",
    "handle_openai",
    "handle_anthropic",
    "dispatch",
]
