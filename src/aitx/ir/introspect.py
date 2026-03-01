"""Introspect Python functions into AITX Internal Representation.

The ``introspect`` function is the canonical way to convert any callable
into a ``UniversalTool`` IR object.
"""

from __future__ import annotations

import inspect
from typing import Any, get_type_hints

from .types import ToolParameter, UniversalTool

# Maps Python types → JSON Schema type strings
_TYPE_MAP: dict[type, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


def _python_type_to_json(tp: type | None) -> str:
    """Convert a Python type annotation to a JSON Schema type string."""
    if tp is None or tp is inspect.Parameter.empty:
        return "string"
    origin = getattr(tp, "__origin__", None)
    if origin is list:
        return "array"
    if origin is dict:
        return "object"
    return _TYPE_MAP.get(tp, "string")


def _parse_docstring_params(docstring: str | None) -> dict[str, str]:
    """Extract parameter descriptions from a Google-style docstring.

    Supports::

        Args:
            param_name: Description of the parameter.
            other_param: Another description.
    """
    if not docstring:
        return {}
    descriptions: dict[str, str] = {}
    in_args = False
    for line in docstring.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("args:"):
            in_args = True
            continue
        if in_args:
            if not stripped or (not line.startswith(" ") and not line.startswith("\t")):
                break
            if ":" in stripped:
                param, _, desc = stripped.partition(":")
                descriptions[param.strip()] = desc.strip()
    return descriptions


def _extract_description(docstring: str | None) -> str:
    """Return the description portion of a docstring (everything before Args)."""
    if not docstring:
        return ""
    lines: list[str] = []
    for line in docstring.splitlines():
        if line.strip().lower().startswith(("args:", "returns:", "raises:")):
            break
        lines.append(line)
    return "\n".join(lines).strip()


def introspect(func: Any) -> UniversalTool:
    """Convert a Python callable into a ``UniversalTool`` IR object.

    Parses:
    - Function name
    - Docstring description + per-parameter descriptions (Google style)
    - Type hints → JSON Schema types
    - Default values → optional parameters
    """
    # Handle wrapped functions (e.g. from @aitx.tool())
    actual = getattr(func, "__wrapped__", func)

    sig = inspect.signature(actual)
    try:
        hints = get_type_hints(actual)
    except Exception:
        hints = {}

    doc = inspect.getdoc(actual) or ""
    param_docs = _parse_docstring_params(doc)

    parameters: list[ToolParameter] = []
    for name, param in sig.parameters.items():
        if name == "self":
            continue
        tp = _python_type_to_json(hints.get(name))
        is_required = param.default is inspect.Parameter.empty
        default = None if is_required else param.default

        parameters.append(
            ToolParameter(
                name=name,
                type=tp,
                description=param_docs.get(name, ""),
                required=is_required,
                default=default,
            )
        )

    return UniversalTool(
        name=actual.__name__,
        description=_extract_description(doc),
        parameters=parameters,
    )
