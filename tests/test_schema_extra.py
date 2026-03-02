"""Extra schema utility tests for uncovered branches."""

from __future__ import annotations

import pytest

from aitx.schema.normalizer import normalize_schema
from aitx.schema.ref_resolver import inline_refs
from aitx.schema.strict_mode import ensure_strict_schema


def test_normalize_nested_items():
    schema = {
        "type": "array",
        "items": {"type": ["string", "null"]},
    }
    result = normalize_schema(schema)
    assert "anyOf" in result["items"]


def test_normalize_additional_properties():
    schema = {
        "type": "object",
        "additionalProperties": {"type": ["integer", "null"]},
    }
    result = normalize_schema(schema)
    assert "anyOf" in result["additionalProperties"]


def test_inline_refs_with_items():
    schema = {
        "type": "array",
        "$defs": {"Item": {"type": "string"}},
        "items": {"$ref": "#/$defs/Item"},
    }
    result = inline_refs(schema)
    assert result["items"]["type"] == "string"
    assert "$defs" not in result


def test_inline_refs_with_additional_properties():
    schema = {
        "type": "object",
        "$defs": {"Val": {"type": "integer"}},
        "additionalProperties": {"$ref": "#/$defs/Val"},
    }
    result = inline_refs(schema)
    assert result["additionalProperties"]["type"] == "integer"


def test_inline_refs_with_anyof():
    schema = {
        "$defs": {"Str": {"type": "string"}},
        "anyOf": [{"$ref": "#/$defs/Str"}, {"type": "null"}],
    }
    result = inline_refs(schema)
    assert result["anyOf"][0]["type"] == "string"


def test_inline_refs_with_prefix_items():
    schema = {
        "$defs": {"Num": {"type": "number"}},
        "type": "array",
        "prefixItems": [{"$ref": "#/$defs/Num"}, {"type": "string"}],
    }
    result = inline_refs(schema)
    assert result["prefixItems"][0]["type"] == "number"


def test_inline_refs_non_dict_raises():
    schema = {
        "$defs": {"bad": "not a dict"},
        "properties": {"x": {"$ref": "#/$defs/bad"}},
    }
    with pytest.raises(ValueError, match="non-dict"):
        inline_refs(schema)


def test_inline_refs_sibling_properties():
    """$ref with sibling fields should merge."""
    schema = {
        "$defs": {"Base": {"type": "string"}},
        "properties": {
            "x": {"$ref": "#/$defs/Base", "description": "Custom desc"},
        },
    }
    result = inline_refs(schema)
    assert result["properties"]["x"]["type"] == "string"
    assert result["properties"]["x"]["description"] == "Custom desc"


def test_strict_mode_nested_array_items():
    schema = {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                },
            },
        },
    }
    result = ensure_strict_schema(schema)
    inner = result["properties"]["items"]["items"]
    assert inner["additionalProperties"] is False
    assert inner["required"] == ["name"]


def test_strict_mode_additional_properties_schema():
    schema = {
        "type": "object",
        "additionalProperties": {
            "type": "object",
            "properties": {"val": {"type": "number"}},
        },
    }
    result = ensure_strict_schema(schema)
    assert result["additionalProperties"]["additionalProperties"] is False


def test_strict_mode_multi_allof():
    """allOf with 2+ elements should recurse into each."""
    schema = {
        "allOf": [
            {"type": "object", "properties": {"a": {"type": "string"}}},
            {"type": "object", "properties": {"b": {"type": "integer"}}},
        ]
    }
    result = ensure_strict_schema(schema)
    assert "allOf" in result
    assert result["allOf"][0]["additionalProperties"] is False
    assert result["allOf"][1]["additionalProperties"] is False
