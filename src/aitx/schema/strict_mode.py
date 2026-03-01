"""OpenAI strict mode JSON Schema transformation.

When ``strict: true`` is set on an OpenAI function tool, the schema must
satisfy additional constraints that are recursively applied.
"""

from __future__ import annotations

from typing import Any


def ensure_strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Transform a JSON Schema to comply with OpenAI's strict mode requirements.

    Transformations:
    1. ``additionalProperties: false`` on ALL object types (recursive)
    2. ALL properties become ``required``
    3. ``oneOf`` → ``anyOf``
    4. Single-element ``allOf`` flattened
    5. ``$schema`` stripped
    6. ``null`` defaults stripped

    Note: This changes semantics — optional fields become required.
    The caller should record this in a ConversionWarning.
    """
    return _ensure_strict(dict(schema))


def _ensure_strict(schema: dict[str, Any]) -> dict[str, Any]:
    """Recursive implementation."""
    # Strip $schema
    schema.pop("$schema", None)

    typ = schema.get("type")

    # Object type: force additionalProperties and required
    if typ == "object":
        if "additionalProperties" not in schema:
            schema["additionalProperties"] = False

        if "properties" in schema:
            # Force all properties to be required
            schema["required"] = list(schema["properties"].keys())
            # Recurse into each property
            schema["properties"] = {
                k: _ensure_strict(dict(v)) for k, v in schema["properties"].items()
            }

    # Array type: recurse into items
    if isinstance(schema.get("items"), dict):
        schema["items"] = _ensure_strict(dict(schema["items"]))

    # additionalProperties as schema
    if isinstance(schema.get("additionalProperties"), dict):
        schema["additionalProperties"] = _ensure_strict(
            dict(schema["additionalProperties"])
        )

    # oneOf → anyOf
    if "oneOf" in schema:
        schema["anyOf"] = schema.pop("oneOf")

    # Single-element allOf → flatten
    if "allOf" in schema and len(schema["allOf"]) == 1:
        merged = dict(schema.pop("allOf")[0])
        schema.update(merged)

    # Recurse into anyOf / allOf
    for key in ("anyOf", "allOf"):
        if key in schema and isinstance(schema[key], list):
            schema[key] = [_ensure_strict(dict(s)) for s in schema[key]]

    # Strip null defaults
    if schema.get("default") is None and "default" in schema:
        del schema["default"]

    return schema
