"""Additional CLI tests for edge cases and auto-detection."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from aitx.cli import _detect_format, main


def test_detect_format_mcp():
    assert _detect_format({"name": "t", "inputSchema": {}}) == "mcp"


def test_detect_format_openai():
    assert _detect_format({"type": "function", "function": {"name": "t"}}) == "openai-chat"


def test_detect_format_anthropic():
    assert _detect_format({"name": "t", "input_schema": {}}) == "anthropic"


def test_detect_format_gemini():
    tool = {
        "name": "t",
        "parameters": {
            "type": "OBJECT",
            "properties": {"x": {"type": "STRING"}},
        },
    }
    assert _detect_format(tool) == "gemini"


def test_detect_format_unknown():
    assert _detect_format({"foo": "bar"}) is None


def test_cli_convert_invalid_json(tmp_path: Path):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("not json")
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "convert",
            str(bad_file),
            "--from",
            "mcp",
            "--to",
            "openai-chat",
        ],
    )
    assert result.exit_code != 0


def test_cli_convert_array_input(tmp_path: Path):
    """CLI should handle an array of tool definitions."""
    tools = [
        {
            "name": "tool_a",
            "inputSchema": {
                "type": "object",
                "properties": {"x": {"type": "string"}},
            },
        },
        {
            "name": "tool_b",
            "inputSchema": {
                "type": "object",
                "properties": {"y": {"type": "integer"}},
            },
        },
    ]
    input_file = tmp_path / "tools.json"
    input_file.write_text(json.dumps(tools))

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "convert",
            str(input_file),
            "--from",
            "mcp",
            "--to",
            "anthropic",
        ],
    )
    assert result.exit_code == 0
    output = json.loads(result.output)
    assert isinstance(output, list)
    assert len(output) == 2
    assert output[0]["name"] == "tool_a"


def test_cli_export_unknown_format(tmp_path: Path):
    """Export with undetectable format should fail gracefully."""
    input_file = tmp_path / "weird.json"
    input_file.write_text(json.dumps({"foo": "bar"}))

    runner = CliRunner()
    result = runner.invoke(main, ["export", str(input_file), "--to", "mcp"])
    assert result.exit_code != 0
