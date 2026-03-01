"""Introspect Python functions into AITX Internal Representation.

The ``introspect`` function is the canonical way to convert any callable
into a ``UniversalTool`` IR object.
"""

from __future__ import annotations

import inspect
import types
from typing import Any, Union, get_args, get_origin, get_type_hints

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


def _python_type_to_json_schema(tp: Any) -> dict[str, Any]:
    """Convert a Python type annotation to a JSON Schema property dict.

    Handles generics like ``list[str]``, ``dict[str, int]``,
    ``Optional[str]``, and ``str | None``.
    """
    if tp is None or tp is inspect.Parameter.empty:
        return {"type": "string"}

    origin = get_origin(tp)
    args = get_args(tp)

    # Handle Union types (Optional[X] = Union[X, None], X | None)
    if origin is Union or origin is types.UnionType:
        non_none = [a for a in args if a is not type(None)]
        has_none = len(non_none) < len(args)
        if len(non_none) == 1:
            inner = _python_type_to_json_schema(non_none[0])
            if has_none:
                return {"anyOf": [inner, {"type": "null"}]}
            return inner
        # Multi-type union
        variants = [_python_type_to_json_schema(a) for a in non_none]
        if has_none:
            variants.append({"type": "null"})
        return {"anyOf": variants}

    # list[X] → {"type": "array", "items": X}
    if origin is list:
        out: dict[str, Any] = {"type": "array"}
        if args:
            out["items"] = _python_type_to_json_schema(args[0])
        return out

    # dict[K, V] → {"type": "object", "additionalProperties": V}
    if origin is dict:
        out = {"type": "object"}
        if len(args) >= 2:
            out["additionalProperties"] = _python_type_to_json_schema(args[1])
        return out

    # tuple[X, Y, ...] → {"type": "array", "prefixItems": [...]}
    if origin is tuple:
        out = {"type": "array"}
        if args:
            out["prefixItems"] = [_python_type_to_json_schema(a) for a in args]
        return out

    # set[X] → {"type": "array", "items": X, "uniqueItems": true}
    if origin is set or origin is frozenset:
        out = {"type": "array", "uniqueItems": True}
        if args:
            out["items"] = _python_type_to_json_schema(args[0])
        return out

    # Plain types
    json_type = _TYPE_MAP.get(tp, "string")
    return {"type": json_type}


def _python_type_to_json(tp: type | None) -> str:
    """Convert a Python type annotation to a simple JSON Schema type string.

    For backward compat: returns the top-level type string only.
    """
    result = _python_type_to_json_schema(tp)
    return str(result.get("type", "string"))


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
                # Handle "param (type): desc" pattern
                param_name = param.strip().split("(")[0].strip()
                descriptions[param_name] = desc.strip()
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
    - Type hints → JSON Schema types (including generics)
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
        tp = hints.get(name)
        json_type = _python_type_to_json(tp)
        json_schema = _python_type_to_json_schema(tp)
        is_required = param.default is inspect.Parameter.empty
        default = None if is_required else param.default

        parameters.append(
            ToolParameter(
                name=name,
                type=json_type,
                description=param_docs.get(name, ""),
                required=is_required,
                default=default,
                enum=None,
                json_schema_override=(
                    json_schema
                    if json_schema.get("type") != json_type or len(json_schema) > 1
                    else None
                ),
            )
        )

    return UniversalTool(
        name=actual.__name__,
        description=_extract_description(doc),
        parameters=parameters,
    )
