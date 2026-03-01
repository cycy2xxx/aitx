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
results = aitx.handle_openai(response, [get_weather])  # auto-dispatch + format

# With Anthropic
tools = aitx.to_anthropic([get_weather])
response = client.messages.create(model="claude-sonnet-4-20250514", messages=msgs, tools=tools)
results = aitx.handle_anthropic(response, [get_weather])

# With Gemini
tools = aitx.to_gemini([get_weather])
results = aitx.handle_gemini(response, [get_weather])
```

**One function. Every platform. No boilerplate.**

## Why aitx?

Every AI platform has its own tool format. To use the same tool on OpenAI, Anthropic, and Gemini you currently write the schema 3 times and the dispatch logic 3 times. aitx eliminates all of it.

| Without aitx | With aitx |
|---|---|
| Write JSON schema per platform | `@aitx.tool()` on your function |
| Parse tool_calls manually | `aitx.handle_openai(response, tools)` |
| Format results per platform | Automatic |

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
     ┌─────┼──────┐
     ▼     ▼      ▼          ▼
  OpenAI Anthropic Gemini   Mesh
  schema  schema   schema  Network
     +      +       +
  dispatch dispatch dispatch
```

## Features

- **`@aitx.tool()` decorator** — Type hints become tool schemas. Docstrings become descriptions.
- **Schema generation** — `to_openai()`, `to_anthropic()`, `to_gemini()`
- **Runtime dispatch** — `handle_openai()`, `handle_anthropic()`, `handle_gemini()` parse tool calls, execute your function, format results
- **Async support** — `handle_openai_async()`, `handle_anthropic_async()`, `handle_gemini_async()` for async tools
- **P2P Mesh Network** — `MeshRouter` discovers and routes tools across machines via mDNS
- **Schema conversion** — `aitx convert` CLI for JSON-to-JSON format conversion with loss reporting
- **Zero boilerplate** — Your function is the single source of truth

## Installation

```bash
pip install aitx

# With platform-specific extras
pip install aitx[openai]      # OpenAI dispatch support
pip install aitx[anthropic]   # Anthropic dispatch support
pip install aitx[gemini]      # Gemini dispatch support
pip install aitx[swarm]       # P2P mesh networking
pip install aitx[all]         # Everything
```

## Quick Examples

### Multi-platform agent

```python
import aitx

@aitx.tool()
def search(query: str, limit: int = 5) -> list[dict]:
    """Search documents by keyword."""
    return [{"title": f"Result for '{query}'", "score": 0.95}]

tools = [search]

# Same tools, different platforms — zero extra work
openai_schemas = aitx.to_openai(tools)
anthropic_schemas = aitx.to_anthropic(tools)
gemini_schemas = aitx.to_gemini(tools)

# Parse + dispatch + format in one call
results = aitx.handle_openai(openai_response, tools)
results = aitx.handle_anthropic(anthropic_response, tools)
results = aitx.handle_gemini(gemini_response, tools)
```

### Async tools

```python
@aitx.tool()
async def fetch_data(url: str) -> dict:
    """Fetch data from a URL."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.json()

# Async dispatch handles both sync and async tools
results = await aitx.handle_openai_async(response, [fetch_data])
```

### JSON-to-JSON schema conversion (CLI)

```bash
# Convert MCP tool definition to OpenAI format
aitx convert tool.mcp.json --from mcp --to openai-chat

# See what information is lost in conversion
aitx convert tool.mcp.json --from mcp --to gemini --report
```

### P2P Mesh: Zero-Config Tool Sharing

Turn your tools into discoverable services across your local network.

```python
# Machine A: serve tools
from aitx.mesh import serve_mesh

@aitx.tool()
def translate(text: str, lang: str = "en") -> str:
    """Translate text."""
    return f"[{lang}] {text}"

serve_mesh(name="translator", tools=[translate])
```

```python
# Machine B: discover and use tools — routing is automatic
from aitx.mesh import MeshRouter

async with MeshRouter() as router:
    await asyncio.sleep(2)  # wait for discovery
    result = await router.execute("translate", {"text": "hello", "lang": "ja"})
    print(result)  # "[ja] hello"
```

## Supported Platforms

| Platform | Schema Gen | Runtime Dispatch | Status |
|---|---|---|---|
| OpenAI Chat Completions | `to_openai()` | `handle_openai()` | Implemented |
| Anthropic Claude | `to_anthropic()` | `handle_anthropic()` | Implemented |
| Google Gemini | `to_gemini()` | `handle_gemini()` | Implemented |
| P2P Mesh Network | `MeshRouter` | `router.execute()` | Implemented |
| Async tools | all `*_async()` variants | `dispatch_async()` | Implemented |
| MCP (Model Context Protocol) | — | — | Planned |
| OpenAI Responses API | — | — | Planned |

## Comparison

| | aitx | LangChain @tool | FastMCP | Composio |
|---|---|---|---|---|
| Multi-platform | **All platforms** | LangChain only | MCP only | All (hosted) |
| P2P Mesh | **Yes** | No | No | No |
| Framework-free | **Yes** | No | No | No |
| Async support | **Yes** | Yes | Yes | Yes |
| Schema conversion CLI | **Yes** | No | No | No |
| Open source | MIT | MIT | MIT | Freemium |
| Python-native | **Yes** | Yes | Yes | Yes |

## Roadmap

- **Phase 0**: `@aitx.tool()` + OpenAI + Anthropic + Gemini + P2P Mesh + async + CLI
- **Phase 1**: MCP server, OpenAI Responses API, streaming results
- **Phase 2**: Tool composition, middleware, OpenClaw integration

## Security

The P2P mesh network uses mDNS for discovery on the local network. Mesh endpoints have **no authentication** by default — any device on the LAN can list and execute tools. Use mesh networking only in trusted environments. Authentication support is planned for a future release.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines. We welcome contributions of all kinds — new adapters, bug fixes, documentation, and test cases.

## License

[MIT](LICENSE)
