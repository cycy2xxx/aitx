"""Tests for schema normalization, ref resolution, and strict mode."""

from __future__ import annotations

from aitx.schema import ensure_strict_schema, inline_refs, normalize_schema


def test_normalize_definitions_to_defs():
    schema = {
        "type": "object",
        "definitions": {
            "Address": {"type": "object", "properties": {"city": {"type": "string"}}},
        },
    }
    result = normalize_schema(schema)
    assert "$defs" in result
    assert "definitions" not in result


def test_normalize_type_array():
    schema = {"type": ["string", "null"]}
    result = normalize_schema(schema)
    assert "anyOf" in result
    assert {"type": "string"} in result["anyOf"]
    assert {"type": "null"} in result["anyOf"]


def test_normalize_strip_schema():
    schema = {"$schema": "http://json-schema.org/draft-07/schema#", "type": "object"}
    result = normalize_schema(schema)
    assert "$schema" not in result


def test_inline_refs_basic():
    schema = {
        "type": "object",
        "$defs": {
            "Address": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
            },
        },
        "properties": {
            "home": {"$ref": "#/$defs/Address"},
            "work": {"$ref": "#/$defs/Address"},
        },
    }
    result = inline_refs(schema)

    assert "$defs" not in result
    assert result["properties"]["home"]["type"] == "object"
    assert "city" in result["properties"]["home"]["properties"]
    assert result["properties"]["work"]["type"] == "object"


def test_inline_refs_recursive_guard():
    """Recursive schemas should be truncated, not infinite-loop."""
    schema = {
        "type": "object",
        "$defs": {
            "Node": {
                "type": "object",
                "properties": {
                    "value": {"type": "string"},
                    "child": {"$ref": "#/$defs/Node"},
                },
            },
        },
        "properties": {
            "root": {"$ref": "#/$defs/Node"},
        },
    }
    result = inline_refs(schema, max_depth=5)

    # Should not raise, should eventually truncate
    assert result["properties"]["root"]["type"] == "object"


def test_strict_mode_adds_additional_properties():
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
        },
        "required": ["name"],
    }
    result = ensure_strict_schema(schema)

    assert result["additionalProperties"] is False
    # All properties should now be required
    assert set(result["required"]) == {"name", "age"}


def test_strict_mode_recursive():
    schema = {
        "type": "object",
        "properties": {
            "address": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                    "zip": {"type": "string"},
                },
            },
        },
    }
    result = ensure_strict_schema(schema)

    # Nested object should also have additionalProperties: false
    assert result["properties"]["address"]["additionalProperties"] is False
    assert set(result["properties"]["address"]["required"]) == {"city", "zip"}


def test_strict_mode_oneof_to_anyof():
    schema = {"oneOf": [{"type": "string"}, {"type": "integer"}]}
    result = ensure_strict_schema(schema)

    assert "anyOf" in result
    assert "oneOf" not in result


def test_strict_mode_flatten_single_allof():
    schema = {"allOf": [{"type": "string", "description": "A name"}]}
    result = ensure_strict_schema(schema)

    assert "allOf" not in result
    assert result["type"] == "string"
