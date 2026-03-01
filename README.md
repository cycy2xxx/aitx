# aitx — AI Tool eXchange

> Write a Python function. Use it as a tool on **any** AI platform. Zero schema writing.

```python
import aitx

@aitx.tool()
def get_weather(city: str, units: str = "celsius") -> dict:
    """Get current weather for a city.

    Args:
        city: City name (e.g. "Tokyo")
        units: Temperature units, "celsius" or "fahrenheit"
    """
    return {"temp": 22, "condition": "sunny", "city": city}
```

That's it. Now use it everywhere:

```python
# With OpenAI
tools = aitx.to_openai([get_weather])
response = client.chat.completions.create(model="gpt-4o", messages=msgs, tools=tools)
result = aitx.handle_openai(response, [get_weather])  # auto-dispatch + format

# With Anthropic
tools = aitx.to_anthropic([get_weather])
response = client.messages.create(model="claude-sonnet-4-20250514", messages=msgs, tools=tools)
result = aitx.handle_anthropic(response, [get_weather])

# With Gemini
tools = aitx.to_gemini([get_weather])

# As an MCP server
aitx.serve_mcp([get_weather])  # stdio or HTTP, zero config

# Export raw schemas
schema = aitx.export("openai-chat", [get_weather])
```

**One function. Every platform. No boilerplate.**

## Why aitx?

Every AI platform has its own tool format. To use the same tool on OpenAI, Anthropic, Gemini, and MCP, you currently write the schema 4 times and the dispatch logic 4 times. aitx eliminates all of it.

| Without aitx | With aitx |
|---|---|
| Write JSON schema per platform | `@aitx.tool()` on your function |
| Parse tool_calls manually | `aitx.handle_openai(response, tools)` |
| Format results per platform | Automatic |
| Separate MCP server code | `aitx.serve_mcp(tools)` |

## How It Works

aitx inspects your function's **type hints and docstring** to generate tool schemas — the same approach that made FastAPI and FastMCP successful.

```
@aitx.tool()
     │
     ▼
┌─────────────────────┐
│  Introspect function │  type hints + docstring + defaults
│  Build Universal IR  │
└──────────┬──────────┘
           │
     ┌─────┴──────┐
     ▼            ▼            ▼            ▼
  OpenAI      Anthropic     Gemini        MCP
  schema       schema       schema       server
     +            +            +
  dispatch     dispatch     dispatch
  handler      handler      handler
```

## Features

- **`@aitx.tool()` decorator** — Type hints become tool schemas. Docstrings become descriptions.
- **Schema generation** — `to_openai()`, `to_anthropic()`, `to_gemini()`, `to_mcp()`
- **Runtime dispatch** — `handle_openai()`, `handle_anthropic()`, `handle_gemini()` parse tool calls, execute your function, format results
- **MCP server** — `serve_mcp()` turns any decorated function into a full MCP server
- **Loss reporting** — Know what's lost when converting between formats
- **Schema export** — `export()` for raw schema conversion (JSON in, JSON out)
- **CLI** — `aitx export`, `aitx convert`, `aitx serve` commands

## Installation

```bash
pip install aitx

# With platform-specific extras
pip install aitx[openai]      # OpenAI dispatch support
pip install aitx[anthropic]   # Anthropic dispatch support
pip install aitx[mcp]         # MCP server support
pip install aitx[all]         # Everything
```

## Quick Examples

### Multi-platform agent

```python
import aitx
from openai import OpenAI
from anthropic import Anthropic

@aitx.tool()
def search(query: str, limit: int = 5) -> list[dict]:
    """Search documents by keyword."""
    return [{"title": f"Result for '{query}'", "score": 0.95}]

@aitx.tool()
def calculate(expression: str) -> float:
    """Evaluate a math expression."""
    return float(eval(expression))

tools = [search, calculate]

# Same tools, different platforms
openai_response = OpenAI().chat.completions.create(
    model="gpt-4o", messages=msgs, tools=aitx.to_openai(tools)
)
result = aitx.handle_openai(openai_response, tools)

anthropic_response = Anthropic().messages.create(
    model="claude-sonnet-4-20250514", messages=msgs, tools=aitx.to_anthropic(tools)
)
result = aitx.handle_anthropic(anthropic_response, tools)
```

### Instant MCP server

```python
import aitx

@aitx.tool()
def read_file(path: str) -> str:
    """Read a file and return its contents."""
    return open(path).read()

@aitx.tool()
def list_files(directory: str = ".") -> list[str]:
    """List files in a directory."""
    import os
    return os.listdir(directory)

# One line: full MCP server over stdio
aitx.serve_mcp([read_file, list_files])
```

### AITX Swarm: Zero-Config P2P Mesh

Turn your tools into discoverable node services on your local network.

```python
# On Machine A (Provider)
from aitx.mesh import serve_mesh

@aitx.tool()
def calculate(expression: str) -> float:
    return float(eval(expression))

serve_mesh(name="calculator_node", tools=[calculate])

# On Machine B (Consumer)
import asyncio
from aitx.mesh import discover_tools, MeshClient

async def run():
    # Automatically finds calculator_node via mDNS
    nodes = await discover_tools()
    
    async with MeshClient(nodes[0]["host"], nodes[0]["port"]) as client:
        result = await client.execute("calculate", {"expression": "100 / 4"})
        print(result) # 25.0

asyncio.run(run())
```

### Schema conversion (JSON to JSON)

```python
from aitx import convert

# Convert existing MCP tool definition to OpenAI format
result = convert(mcp_tool_json, source="mcp", target="openai-chat")
print(result.output)     # OpenAI-compatible schema
print(result.warnings)   # What was lost
```

## Supported Platforms

| Platform | Schema Gen | Runtime Dispatch | Status |
|---|---|---|---|
| OpenAI Chat Completions | `to_openai()` | `handle_openai()` | Phase 0 |
| Anthropic Claude | `to_anthropic()` | `handle_anthropic()` | Phase 0 |
| MCP (Model Context Protocol) | `to_mcp()` | `serve_mcp()` | Phase 0 |
| OpenAI Responses API | `to_openai_responses()` | `handle_openai_responses()` | Phase 1 |
| Google Gemini | `to_gemini()` | `handle_gemini()` | Phase 1 |
| OpenClaw | `to_openclaw()` | — | Phase 2 |

## Comparison

| | aitx | LangChain @tool | FastMCP | Composio |
|---|---|---|---|---|
| Multi-platform | **All platforms** | LangChain only | MCP only | All (hosted) |
| Open source | MIT | MIT | MIT | Freemium |
| Framework-free | **Yes** | No (requires LangChain) | No (MCP only) | No (their SDK) |
| Runtime dispatch | **Yes** | Yes (within LC) | Yes (MCP) | Yes |
| Schema export | **Yes** | Limited | No | No |
| Python-native | **Yes** | Yes | Yes | Yes |

## Roadmap

- **Phase 0**: `@aitx.tool()` + OpenAI + Anthropic + MCP (core platforms)
- **Phase 1**: Gemini, OpenAI Responses API, async tools
- **Phase 2**: OpenClaw, tool composition, middleware
- **Phase 3**: Proxy server mode, TypeScript port

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[MIT](LICENSE)
