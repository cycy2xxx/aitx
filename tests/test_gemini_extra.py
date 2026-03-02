"""Extra Gemini adapter tests for uncovered branches."""

from __future__ import annotations

from aitx.adapters.gemini import _schema_to_gemini


def test_multi_non_null_anyof():
    """Multiple non-null variants: Gemini picks first."""
    schema = {"anyOf": [{"type": "string"}, {"type": "integer"}]}
    result = _schema_to_gemini(schema)
    assert result["type"] == "STRING"


def test_multi_non_null_anyof_with_null():
    """Multiple non-null + null: nullable + first type."""
    schema = {"anyOf": [{"type": "string"}, {"type": "integer"}, {"type": "null"}]}
    result = _schema_to_gemini(schema)
    assert result.get("nullable") is True
    assert result["type"] == "STRING"


def test_minimum_maximum():
    schema = {"type": "integer", "minimum": 0, "maximum": 100}
    result = _schema_to_gemini(schema)
    assert result["minimum"] == 0
    assert result["maximum"] == 100


def test_additional_properties():
    schema = {
        "type": "object",
        "additionalProperties": {"type": "string"},
    }
    result = _schema_to_gemini(schema)
    assert result["additionalProperties"]["type"] == "STRING"


def test_unknown_type_defaults_to_string():
    schema = {"type": "custom_weird_type"}
    result = _schema_to_gemini(schema)
    assert result["type"] == "STRING"
