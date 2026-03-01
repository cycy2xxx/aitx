"""The ``@aitx.tool()`` decorator.

Tags a function as an AITX tool and attaches its ``UniversalTool`` IR
for later use by adapters and the mesh network.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any, TypeVar, overload

from .ir import UniversalTool, introspect

F = TypeVar("F", bound=Callable[..., Any])

# Module-level registry of all decorated tools
_registry: dict[str, Callable[..., Any]] = {}


@overload
def tool(func: F) -> F: ...


@overload
def tool(
    *,
    name: str | None = None,
    description: str | None = None,
) -> Callable[[F], F]: ...


def tool(
    func: F | None = None,
    *,
    name: str | None = None,
    description: str | None = None,
) -> F | Callable[[F], F]:
    """Decorator that registers a function as an AITX tool.

    Can be used with or without arguments::

        @aitx.tool
        def my_tool(x: int) -> int: ...

        @aitx.tool()
        def my_tool(x: int) -> int: ...

        @aitx.tool(name="custom_name")
        def my_tool(x: int) -> int: ...

    The decorated function gets an ``__aitx_tool__`` attribute containing
    its ``UniversalTool`` IR representation.
    """

    def decorator(fn: F) -> F:
        ir = introspect(fn)
        if name:
            ir.name = name
        if description:
            ir.description = description

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return fn(*args, **kwargs)

        wrapper.__aitx_tool__ = ir  # type: ignore[attr-defined]
        _registry[ir.name] = wrapper
        return wrapper  # type: ignore[return-value]

    if func is not None:
        # Called as @tool without parentheses
        return decorator(func)
    # Called as @tool() or @tool(name=...)
    return decorator


def get_tools() -> dict[str, Callable[..., Any]]:
    """Return all registered tools."""
    return dict(_registry)


def get_ir(func: Callable[..., Any]) -> UniversalTool:
    """Get the UniversalTool IR for a decorated function.

    Raises ``AttributeError`` if the function is not decorated with ``@tool``.
    """
    ir: UniversalTool | None = getattr(func, "__aitx_tool__", None)
    if ir is None:
        raise AttributeError(
            f"Function '{func.__name__}' is not an AITX tool. "
            "Decorate it with @aitx.tool()."
        )
    return ir
