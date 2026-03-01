"""JSON-to-JSON schema conversion API.

Converts raw tool definition dicts between formats with loss reporting.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from .ir.types import ToolParameter, UniversalTool

FormatName = Literal["mcp", "openai-chat", "gemini", "anthropic"]


class ConversionWarning(BaseModel):
    """A warning about information lost during conversion."""

    field: str
    message: str
    severity: Literal["info", "warning", "error"] = "warning"


class ConversionResult(BaseModel):
    """Result of a format conversion, including the output and any warnings."""

    output: dict[str, Any]
    source: FormatName
    target: FormatName
    warnings: list[ConversionWarning] = Field(default_factory=list)


def _parse_mcp(tool: dict[str, Any]) -> tuple[UniversalTool, list[ConversionWarning]]:
    """Parse an MCP tool definition to IR."""
    warnings: list[ConversionWarning] = []
    schema = tool.get("inputSchema", {})
    props = schema.get("properties", {})
    required = set(schema.get("required", []))

    parameters = []
    for name, prop in props.items():
        parameters.append(
            ToolParameter(
                name=name,
                type=prop.get("type", "string"),
                description=prop.get("description", ""),
                required=name in required,
                default=prop.get("default"),
                enum=prop.get("enum"),
            )
        )

    ir = UniversalTool(
        name=tool.get("name", ""),
        description=tool.get("description", ""),
        parameters=parameters,
    )

    # Record what MCP-specific fields will be lost
    if tool.get("title"):
        warnings.append(
            ConversionWarning(
                field="title",
                message="MCP title has no equivalent in most formats",
            )
        )
    if tool.get("outputSchema"):
        warnings.append(
            ConversionWarning(
                field="outputSchema",
                message="Output schema not supported in target format",
            )
        )
    if tool.get("annotations"):
        warnings.append(
            ConversionWarning(
                field="annotations",
                message="MCP annotations (readOnlyHint, destructiveHint, etc.) dropped",
            )
        )

    return ir, warnings


def _parse_openai_chat(tool: dict[str, Any]) -> tuple[UniversalTool, list[ConversionWarning]]:
    """Parse an OpenAI Chat Completions tool definition to IR."""
    warnings: list[ConversionWarning] = []
    func = tool.get("function", {})
    schema = func.get("parameters", {})
    props = schema.get("properties", {})
    required = set(schema.get("required", []))

    parameters = []
    for name, prop in props.items():
        parameters.append(
            ToolParameter(
                name=name,
                type=prop.get("type", "string"),
                description=prop.get("description", ""),
                required=name in required,
                default=prop.get("default"),
                enum=prop.get("enum"),
            )
        )

    ir = UniversalTool(
        name=func.get("name", ""),
        description=func.get("description", ""),
        parameters=parameters,
    )

    if func.get("strict"):
        warnings.append(
            ConversionWarning(
                field="strict",
                message="OpenAI strict mode has no equivalent; schema constraints may differ",
                severity="info",
            )
        )

    return ir, warnings


def _parse_anthropic(tool: dict[str, Any]) -> tuple[UniversalTool, list[ConversionWarning]]:
    """Parse an Anthropic tool definition to IR."""
    schema = tool.get("input_schema", {})
    props = schema.get("properties", {})
    required = set(schema.get("required", []))

    parameters = []
    for name, prop in props.items():
        parameters.append(
            ToolParameter(
                name=name,
                type=prop.get("type", "string"),
                description=prop.get("description", ""),
                required=name in required,
                default=prop.get("default"),
                enum=prop.get("enum"),
            )
        )

    return UniversalTool(
        name=tool.get("name", ""),
        description=tool.get("description", ""),
        parameters=parameters,
    ), []


def _parse_gemini(tool: dict[str, Any]) -> tuple[UniversalTool, list[ConversionWarning]]:
    """Parse a Gemini FunctionDeclaration to IR."""
    schema = tool.get("parameters", {})
    props = schema.get("properties", {})
    required = set(schema.get("required", []))

    parameters = []
    for name, prop in props.items():
        # Gemini uses UPPERCASE types → lowercase
        typ = prop.get("type", "STRING").lower()
        parameters.append(
            ToolParameter(
                name=name,
                type=typ,
                description=prop.get("description", ""),
                required=name in required,
            )
        )

    return UniversalTool(
        name=tool.get("name", ""),
        description=tool.get("description", ""),
        parameters=parameters,
    ), []


# ── Generators ────────────────────────────────────────────────────────


def _generate_mcp(ir: UniversalTool) -> tuple[dict[str, Any], list[ConversionWarning]]:
    return {
        "name": ir.name,
        "description": ir.description,
        "inputSchema": ir.to_json_schema(),
    }, []


def _generate_openai_chat(ir: UniversalTool) -> tuple[dict[str, Any], list[ConversionWarning]]:
    return {
        "type": "function",
        "function": {
            "name": ir.name,
            "description": ir.description,
            "parameters": ir.to_json_schema(),
        },
    }, []


def _generate_anthropic(ir: UniversalTool) -> tuple[dict[str, Any], list[ConversionWarning]]:
    return {
        "name": ir.name,
        "description": ir.description,
        "input_schema": ir.to_json_schema(),
    }, []


def _generate_gemini(ir: UniversalTool) -> tuple[dict[str, Any], list[ConversionWarning]]:
    from .adapters.gemini import GeminiAdapter

    warnings: list[ConversionWarning] = []
    adapter = GeminiAdapter()
    output = adapter.to_schema(ir)

    # Record potential losses
    schema = ir.to_json_schema()
    if "$ref" in str(schema) or "$defs" in str(schema):
        warnings.append(
            ConversionWarning(
                field="$ref/$defs",
                message="Gemini does not support $ref; references were inlined",
            )
        )

    return output, warnings


# ── Registries ────────────────────────────────────────────────────────

_PARSERS = {
    "mcp": _parse_mcp,
    "openai-chat": _parse_openai_chat,
    "anthropic": _parse_anthropic,
    "gemini": _parse_gemini,
}

_GENERATORS = {
    "mcp": _generate_mcp,
    "openai-chat": _generate_openai_chat,
    "anthropic": _generate_anthropic,
    "gemini": _generate_gemini,
}


def convert(
    tool: dict[str, Any],
    *,
    source: FormatName,
    target: FormatName,
) -> ConversionResult:
    """Convert a raw tool definition dict from one format to another.

    Returns a ``ConversionResult`` with the converted schema and any
    warnings about information lost in the conversion.

    Example::

        result = convert(mcp_tool, source="mcp", target="openai-chat")
        print(result.output)     # OpenAI-compatible dict
        print(result.warnings)   # What was lost
    """
    parser = _PARSERS.get(source)
    generator = _GENERATORS.get(target)

    if parser is None:
        raise ValueError(f"Unknown source format: {source!r}")
    if generator is None:
        raise ValueError(f"Unknown target format: {target!r}")

    ir, parse_warnings = parser(tool)
    output, gen_warnings = generator(ir)

    return ConversionResult(
        output=output,
        source=source,
        target=target,
        warnings=parse_warnings + gen_warnings,
    )
