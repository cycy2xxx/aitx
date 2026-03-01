"""JSON Schema normalization utilities.

Normalizes JSON Schema drafts to a canonical form for consistent conversion.
"""

from __future__ import annotations

from typing import Any


def normalize_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Normalize a JSON Schema to canonical draft 2020-12 form.

    Transformations applied:
    - ``definitions`` → ``$defs`` (draft-07 compat)
    - Strips ``$schema`` keyword
    - Type arrays ``["string", "null"]`` → ``anyOf`` normalization
    """
    result = dict(schema)

    # Strip $schema
    result.pop("$schema", None)

    # definitions → $defs
    if "definitions" in result and "$defs" not in result:
        result["$defs"] = result.pop("definitions")

    # Type array → anyOf
    if isinstance(result.get("type"), list):
        types = result.pop("type")
        result["anyOf"] = [{"type": t} for t in types]

    # Recurse into properties
    if "properties" in result:
        result["properties"] = {
            k: normalize_schema(v) for k, v in result["properties"].items()
        }

    # Recurse into items
    if isinstance(result.get("items"), dict):
        result["items"] = normalize_schema(result["items"])

    # Recurse into additionalProperties
    if isinstance(result.get("additionalProperties"), dict):
        result["additionalProperties"] = normalize_schema(result["additionalProperties"])

    # Recurse into anyOf / oneOf / allOf
    for key in ("anyOf", "oneOf", "allOf"):
        if key in result and isinstance(result[key], list):
            result[key] = [normalize_schema(s) for s in result[key]]

    # Recurse into $defs
    if "$defs" in result:
        result["$defs"] = {
            k: normalize_schema(v) for k, v in result["$defs"].items()
        }

    return result
