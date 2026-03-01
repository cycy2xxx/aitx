"""aitx CLI — command-line interface for tool schema conversion.

Commands:
    aitx convert <file> --from <format> --to <format>   Convert tool schemas
    aitx export <file> --to <format>                    Alias for convert
    aitx formats                                        List supported formats
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from ..convert import convert

FORMATS = ["mcp", "openai-chat", "anthropic", "gemini"]


@click.group()
@click.version_option(package_name="aitx")
def main() -> None:
    """aitx — AI Tool eXchange. Universal transpiler for AI tool definitions."""


@main.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option("--from", "source", required=True, type=click.Choice(FORMATS), help="Source format")
@click.option("--to", "target", required=True, type=click.Choice(FORMATS), help="Target format")
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Output file")
@click.option("--report", is_flag=True, help="Show conversion warnings")
@click.option("--pretty", is_flag=True, default=True, help="Pretty-print JSON output")
def convert_cmd(
    file: Path,
    source: str,
    target: str,
    output: Path | None,
    report: bool,
    pretty: bool,
) -> None:
    """Convert tool definitions between AI platform formats."""
    try:
        data = json.loads(file.read_text())
    except json.JSONDecodeError as e:
        click.echo(f"Error: Invalid JSON in {file}: {e}", err=True)
        sys.exit(1)

    # Handle single tool or array of tools
    tools = data if isinstance(data, list) else [data]
    results = []

    for tool in tools:
        result = convert(tool, source=source, target=target)  # type: ignore[arg-type]
        results.append(result)

        if report and result.warnings:
            click.echo(f"\n--- Warnings for '{tool.get('name', 'unknown')}' ---", err=True)
            for w in result.warnings:
                icon = {"info": "ℹ", "warning": "⚠", "error": "✗"}.get(w.severity, "?")
                click.echo(f"  {icon} [{w.field}] {w.message}", err=True)

    # Output
    outputs = [r.output for r in results]
    json_out = outputs[0] if len(outputs) == 1 else outputs
    indent = 2 if pretty else None
    json_str = json.dumps(json_out, indent=indent, ensure_ascii=False)

    if output:
        output.write_text(json_str + "\n")
        click.echo(f"Written to {output}", err=True)
    else:
        click.echo(json_str)


@main.command("export")
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option("--to", "target", required=True, type=click.Choice(FORMATS), help="Target format")
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Output file")
@click.option("--report", is_flag=True, help="Show conversion warnings")
@click.pass_context
def export_cmd(
    ctx: click.Context,
    file: Path,
    target: str,
    output: Path | None,
    report: bool,
) -> None:
    """Export tool definitions to a target format (auto-detects source)."""
    # Try to auto-detect source format from the JSON structure
    try:
        data = json.loads(file.read_text())
    except json.JSONDecodeError as e:
        click.echo(f"Error: Invalid JSON in {file}: {e}", err=True)
        sys.exit(1)

    tool = data[0] if isinstance(data, list) else data
    source = _detect_format(tool)

    if source is None:
        click.echo(
            "Error: Could not auto-detect source format. Use 'aitx convert' with --from.",
            err=True,
        )
        sys.exit(1)

    click.echo(f"Detected source format: {source}", err=True)
    ctx.invoke(
        convert_cmd,
        file=file,
        source=source,
        target=target,
        output=output,
        report=report,
        pretty=True,
    )


@main.command("formats")
def formats_cmd() -> None:
    """List all supported tool definition formats."""
    click.echo("Supported formats:\n")
    descriptions = {
        "mcp": "Model Context Protocol (Anthropic/AAIF)",
        "openai-chat": "OpenAI Chat Completions API",
        "anthropic": "Anthropic Messages API",
        "gemini": "Google Gemini FunctionDeclaration",
    }
    for fmt, desc in descriptions.items():
        click.echo(f"  {fmt:20s} {desc}")


def _detect_format(tool: dict) -> str | None:  # type: ignore[type-arg]
    """Auto-detect the format of a tool definition dict."""
    if "inputSchema" in tool:
        return "mcp"
    if "type" in tool and "function" in tool:
        return "openai-chat"
    if "input_schema" in tool:
        return "anthropic"
    if "parameters" in tool:
        params = tool["parameters"]
        if isinstance(params, dict):
            # Gemini uses UPPERCASE types
            props = params.get("properties", {})
            if any(p.get("type", "").isupper() for p in props.values() if isinstance(p, dict)):
                return "gemini"
    return None
