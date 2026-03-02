"""Extra introspection tests for uncovered type branches."""

from __future__ import annotations

from aitx.ir.introspect import _python_type_to_json_schema, introspect


def test_none_type():
    assert _python_type_to_json_schema(None) == {"type": "string"}


def test_tuple_type():
    schema = _python_type_to_json_schema(tuple[str, int])
    assert schema["type"] == "array"
    assert schema["prefixItems"][0]["type"] == "string"
    assert schema["prefixItems"][1]["type"] == "integer"


def test_set_type():
    schema = _python_type_to_json_schema(set[str])
    assert schema["type"] == "array"
    assert schema["uniqueItems"] is True
    assert schema["items"]["type"] == "string"


def test_frozenset_type():
    schema = _python_type_to_json_schema(frozenset[int])
    assert schema["type"] == "array"
    assert schema["uniqueItems"] is True
    assert schema["items"]["type"] == "integer"


def test_multi_union():
    """str | int | None should produce anyOf with 3 variants."""
    schema = _python_type_to_json_schema(str | int | None)
    assert "anyOf" in schema
    types = [s.get("type") for s in schema["anyOf"]]
    assert "string" in types
    assert "integer" in types
    assert "null" in types


def test_bare_list_no_args():
    schema = _python_type_to_json_schema(list)
    assert schema == {"type": "array"}


def test_bare_dict_no_args():
    schema = _python_type_to_json_schema(dict)
    assert schema == {"type": "object"}


def test_unknown_type_defaults_to_string():
    """Custom class should fall back to string."""

    class MyCustom:
        pass

    schema = _python_type_to_json_schema(MyCustom)
    assert schema == {"type": "string"}


def test_docstring_param_with_type_annotation():
    """Handles 'param (type): desc' pattern in docstrings."""

    def fn(x: int) -> int:
        """Do something.

        Args:
            x (int): The value.
        """
        return x

    ir = introspect(fn)
    assert ir.parameters[0].description == "The value."


def test_no_docstring():
    def fn(x: int) -> int:
        return x

    ir = introspect(fn)
    assert ir.description == ""
    assert ir.parameters[0].description == ""


def test_no_type_hints():
    def fn(x):  # type: ignore[no-untyped-def]
        """Untyped function.

        Args:
            x: Some value.
        """
        return x

    ir = introspect(fn)
    assert ir.parameters[0].type == "string"  # default
