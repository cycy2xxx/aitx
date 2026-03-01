# aitx — AI Tool eXchange

## Overview
Universal tool runtime for AI agents.
Decorate a Python function once, use it as a tool on any AI platform.
What FastAPI did for REST APIs, aitx does for AI tools.

## Core Concept
```python
@aitx.tool()
def my_func(param: str) -> dict:
    """Description from docstring."""
    return {"result": param}

# Works on every platform
aitx.to_openai([my_func])       # Schema generation
aitx.handle_openai(resp, tools)  # Runtime dispatch
aitx.serve_mcp([my_func])       # MCP server
```

## Tech Stack
- Python 3.11+
- Pydantic v2 (IR models + validation)
- Click (CLI)
- pytest (testing)
- ruff (lint + format)
- mypy strict (type checking)
- uv (package management)
- hatchling (build backend)

## Commands
```bash
uv run pytest              # Run tests
uv run pytest -x           # Stop on first failure
uv run mypy src/           # Type check
uv run ruff check src/     # Lint
uv run ruff format src/    # Format
uv run aitx                # CLI
```

## Architecture

Three layers:
```
Layer 3: Runtime Bridges     handle_openai(), handle_anthropic(), serve_mcp()
Layer 2: Schema Generation   to_openai(), to_anthropic(), to_gemini() (auto)
Layer 1: Tool Registration   @aitx.tool() decorator + introspection
```

### Directory Structure
```
src/aitx/
  __init__.py          — Public API
  decorator.py         — @aitx.tool()
  convert.py           — JSON-to-JSON conversion (schema export)
  ir/
    types.py           — UniversalTool, ToolCall, ToolResult
    introspect.py      — Function signature → IR
  adapters/
    base.py            — FormatAdapter ABC
    openai_chat.py     — OpenAI Chat Completions
    anthropic.py       — Anthropic Claude
    mcp.py             — MCP server
    gemini.py          — Gemini (Phase 1)
  schema/
    normalizer.py      — JSON Schema normalization
    ref_resolver.py    — $ref inlining
    strict_mode.py     — OpenAI strict mode
  bridge/
    dispatcher.py      — Tool call dispatch engine
    validation.py      — Argument validation
  cli/
    __init__.py        — CLI entry point
```

## Design Principles
- Type hints + docstrings = tool schemas (zero manual schema writing)
- IR-centric pipeline: Function → IR → Platform Schema
- Each adapter: schema generation + tool call parsing + result formatting
- Explicit loss reporting on schema conversion
- No vendor lock-in: works with raw API calls, not a framework

## Conversion Matrix (Schema Transforms)
```
Target          Key Transforms
────────────────────────────────────────────────
OpenAI          Wrap in {function: {name, parameters}}
(strict)        + recursive additionalProperties: false
                + force all properties required

Anthropic       input_schema key, minimal transforms

Gemini          UPPERCASE type names, inline $ref,
                strip oneOf/allOf/default, nullable flag

MCP             Canonical form (no transforms)
```

## Dependencies
- Runtime: pydantic (required)
- Optional: click (CLI), openai, anthropic, mcp (platform-specific extras)

## Phase Plan
- Phase 0: @tool + OpenAI + Anthropic + MCP + dispatch + CLI
- Phase 1: Gemini, OpenAI Responses API, async tools
- Phase 2: OpenClaw, tool composition, middleware
