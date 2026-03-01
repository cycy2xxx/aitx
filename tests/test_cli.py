"""Tests for the aitx CLI."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from aitx.cli import main

FIXTURES = Path(__file__).parent / "fixtures"


def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_cli_formats():
    runner = CliRunner()
    result = runner.invoke(main, ["formats"])
    assert result.exit_code == 0
    assert "mcp" in result.output
    assert "openai-chat" in result.output
    assert "anthropic" in result.output
    assert "gemini" in result.output


def test_cli_convert_mcp_to_openai():
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "convert",
            str(FIXTURES / "weather_mcp.json"),
            "--from",
            "mcp",
            "--to",
            "openai-chat",
        ],
    )
    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["type"] == "function"
    assert output["function"]["name"] == "get_weather"


def test_cli_convert_with_report():
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "convert",
            str(FIXTURES / "weather_mcp.json"),
            "--from",
            "mcp",
            "--to",
            "openai-chat",
            "--report",
        ],
    )
    assert result.exit_code == 0
    # Warnings go to stderr
    assert "title" in (result.output + (result.stderr or ""))


def test_cli_convert_to_file(tmp_path: Path):
    output_file = tmp_path / "output.json"
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "convert",
            str(FIXTURES / "weather_mcp.json"),
            "--from",
            "mcp",
            "--to",
            "anthropic",
            "-o",
            str(output_file),
        ],
    )
    assert result.exit_code == 0
    assert output_file.exists()
    data = json.loads(output_file.read_text())
    assert data["name"] == "get_weather"
    assert "input_schema" in data


def test_cli_export_auto_detect(tmp_path: Path):
    output_file = tmp_path / "out.json"
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "export",
            str(FIXTURES / "weather_mcp.json"),
            "--to",
            "gemini",
            "-o",
            str(output_file),
        ],
    )
    assert result.exit_code == 0
    data = json.loads(output_file.read_text())
    assert data["parameters"]["type"] == "OBJECT"
