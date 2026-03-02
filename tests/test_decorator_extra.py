"""Extra decorator tests for uncovered branches."""

from __future__ import annotations

import pytest

import aitx
from aitx.decorator import get_ir, get_tools


def test_tool_bare_decorator():
    """@aitx.tool without parentheses."""

    @aitx.tool
    def bare_fn(x: int) -> int:
        """Bare decorated.

        Args:
            x: Value.
        """
        return x

    assert hasattr(bare_fn, "__aitx_tool__")
    assert bare_fn(5) == 5


def test_tool_with_custom_description():
    @aitx.tool(description="Custom desc")
    def custom_desc_fn(x: int) -> int:
        """Original desc.

        Args:
            x: Value.
        """
        return x

    ir = get_ir(custom_desc_fn)
    assert ir.description == "Custom desc"


def test_get_ir_raises_for_undecorated():
    def plain_fn() -> None:
        pass

    with pytest.raises(AttributeError, match="not an AITX tool"):
        get_ir(plain_fn)


def test_get_tools_returns_registry():
    tools = get_tools()
    assert isinstance(tools, dict)
    # Should contain at least tools registered in this module
    assert len(tools) > 0
