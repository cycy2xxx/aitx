"""JSON Schema $ref resolution and inlining.

Required for Gemini (no $ref support) and OpenAI strict mode.
"""

from __future__ import annotations

import copy
from typing import Any


def _resolve_ref(ref: str, root: dict[str, Any]) -> dict[str, Any]:
    """Resolve a JSON Pointer $ref string against the root schema."""
    if not ref.startswith("#/"):
        raise ValueError(f"Only local $ref is supported, got: {ref}")

    parts = ref[2:].split("/")
    node: Any = root
    for part in parts:
        # Unescape JSON Pointer encoding
        part = part.replace("~1", "/").replace("~0", "~")
        if isinstance(node, dict):
            node = node[part]
        else:
            raise ValueError(f"Cannot resolve $ref path: {ref}")
    if not isinstance(node, dict):
        raise ValueError(f"$ref resolved to non-dict: {ref}")
    return dict(node)


def inline_refs(
    schema: dict[str, Any],
    root: dict[str, Any] | None = None,
    max_depth: int = 20,
    _depth: int = 0,
) -> dict[str, Any]:
    """Recursively inline all ``$ref`` references in a JSON Schema.

    Parameters
    ----------
    schema:
        The schema (or sub-schema) to process.
    root:
        The root schema used to resolve ``$ref``. Defaults to *schema*.
    max_depth:
        Guard against infinite recursion from recursive schemas.

    Returns a new schema dict with all ``$ref`` resolved and ``$defs`` removed.
    """
    if _depth > max_depth:
        return {"type": "object", "description": "(recursive schema truncated)"}

    if root is None:
        root = schema

    result = dict(schema)

    # Resolve $ref
    if "$ref" in result:
        ref = result.pop("$ref")
        resolved = copy.deepcopy(_resolve_ref(ref, root))
        # Merge: resolved fields first, then any siblings (except $ref)
        merged = inline_refs(resolved, root, max_depth, _depth + 1)
        for k, v in result.items():
            if k != "$ref":
                merged[k] = v
        result = merged

    # Recurse into properties
    if "properties" in result:
        result["properties"] = {
            k: inline_refs(v, root, max_depth, _depth + 1)
            for k, v in result["properties"].items()
        }

    # Recurse into items
    if isinstance(result.get("items"), dict):
        result["items"] = inline_refs(result["items"], root, max_depth, _depth + 1)

    # Recurse into additionalProperties
    if isinstance(result.get("additionalProperties"), dict):
        result["additionalProperties"] = inline_refs(
            result["additionalProperties"], root, max_depth, _depth + 1
        )

    # Recurse into combinators
    for key in ("anyOf", "oneOf", "allOf"):
        if key in result and isinstance(result[key], list):
            result[key] = [
                inline_refs(s, root, max_depth, _depth + 1) for s in result[key]
            ]

    # Recurse into prefixItems (tuple)
    if "prefixItems" in result and isinstance(result["prefixItems"], list):
        result["prefixItems"] = [
            inline_refs(s, root, max_depth, _depth + 1) for s in result["prefixItems"]
        ]

    # Strip $defs / definitions at root level
    if _depth == 0:
        result.pop("$defs", None)
        result.pop("definitions", None)

    return result
