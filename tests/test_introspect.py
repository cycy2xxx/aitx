"""Tests for enhanced introspection (generic types)."""

from __future__ import annotations

from aitx.ir.introspect import introspect


def func_list_str(items: list[str]) -> list[str]:
    """Process items.

    Args:
        items: List of strings to process
    """
    return items


def func_dict_str_int(data: dict[str, int]) -> dict[str, int]:
    """Process data.

    Args:
        data: Mapping of names to values
    """
    return data


def func_optional(name: str, tag: str | None = None) -> str:
    """Greet someone.

    Args:
        name: Person's name
        tag: Optional tag
    """
    return f"hello {name}"


def func_complex(
    queries: list[dict[str, str]],
    limit: int = 10,
) -> list[dict]:
    """Run queries.

    Args:
        queries: List of query objects
        limit: Max results
    """
    return []


def test_list_str_produces_array_with_items():
    ir = introspect(func_list_str)
    schema = ir.to_json_schema()
    prop = schema["properties"]["items"]
    assert prop["type"] == "array"
    assert prop["items"]["type"] == "string"


def test_dict_str_int_produces_object_with_additional():
    ir = introspect(func_dict_str_int)
    schema = ir.to_json_schema()
    prop = schema["properties"]["data"]
    assert prop["type"] == "object"
    assert prop["additionalProperties"]["type"] == "integer"


def test_optional_produces_anyof():
    ir = introspect(func_optional)
    schema = ir.to_json_schema()
    prop = schema["properties"]["tag"]
    assert "anyOf" in prop
    types = [s.get("type") for s in prop["anyOf"]]
    assert "string" in types
    assert "null" in types


def test_complex_nested_generics():
    ir = introspect(func_complex)
    schema = ir.to_json_schema()
    prop = schema["properties"]["queries"]
    assert prop["type"] == "array"
    # list[dict[str, str]] → items should be object with additionalProperties
    assert prop["items"]["type"] == "object"
    assert prop["items"]["additionalProperties"]["type"] == "string"
