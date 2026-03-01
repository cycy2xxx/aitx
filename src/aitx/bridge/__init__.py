"""Bridge — tool call dispatch engine."""

from .dispatcher import (
    dispatch,
    handle_anthropic,
    handle_openai,
    to_anthropic,
    to_openai,
)

__all__ = [
    "dispatch",
    "handle_anthropic",
    "handle_openai",
    "to_anthropic",
    "to_openai",
]
