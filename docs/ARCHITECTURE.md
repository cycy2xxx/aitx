# aitx Architecture

## Design Philosophy

aitx follows the same pattern that made FastAPI and FastMCP successful:
**type hints + docstrings = infrastructure**.

Write a Python function with proper annotations. aitx generates tool schemas
for every AI platform and handles the runtime dispatch loop.

## Three Layers

```
Layer 3: Runtime Bridges
         handle_openai(), handle_anthropic(), serve_mcp()
         Parse tool calls → validate args → execute function → format results

Layer 2: Schema Generation
         to_openai(), to_anthropic(), to_gemini(), to_mcp()
         IR → platform-specific JSON schema

Layer 1: Tool Registration
         @aitx.tool() decorator
         Introspect function → build Universal IR
```

Most users only interact with Layer 1 (decorator) and Layer 3 (dispatch).
Layer 2 runs automatically behind the scenes.

## Internal Representation (IR)

The IR is a Pydantic model that captures the superset of all tool formats.

```python
class UniversalTool(BaseModel):
    """The internal representation — superset of all formats."""
    name: str
    title: str | None = None
    description: str | None = None
    input_schema: dict[str, Any]         # JSON Schema draft 2020-12
    output_schema: dict[str, Any] | None = None
    annotations: ToolAnnotations | None = None
    fn: Callable[..., Any] | None = None  # The actual Python function

class ToolAnnotations(BaseModel):
    read_only: bool = False
    destructive: bool = False
    idempotent: bool = False
    open_world: bool = False

class UniversalToolCall(BaseModel):
    """Normalized tool call from any platform."""
    id: str
    name: str
    arguments: dict[str, Any]

class UniversalToolResult(BaseModel):
    """Normalized tool result for any platform."""
    call_id: str
    content: list[ContentItem]
    is_error: bool = False

class ContentItem(BaseModel):
    type: Literal["text", "image", "audio", "resource"]
    text: str | None = None
    mime_type: str | None = None
    data: str | None = None  # base64 for binary
    uri: str | None = None

class ConversionWarning(BaseModel):
    field: str
    message: str
    severity: Literal["info", "warning", "error"]

class ConversionResult(BaseModel, Generic[T]):
    output: T
    warnings: list[ConversionWarning]
```

## Introspection Engine

The `@aitx.tool()` decorator introspects the function to build the IR:

```
def get_weather(city: str, units: str = "celsius") -> dict:
    """Get current weather for a city.

    Args:
        city: City name (e.g. "Tokyo")
        units: Temperature units
    """

Introspection extracts:
├── name: "get_weather"          (from function.__name__)
├── description: "Get current..."(from docstring first line)
├── input_schema:
│   ├── city: str, required      (from type hints + no default)
│   │   └── description: "City name..." (from docstring Args section)
│   └── units: str, default "celsius"   (from type hints + default value)
├── output type: dict            (from return annotation)
└── fn: <function reference>     (for runtime dispatch)
```

### Docstring Parsing

Supports Google-style, NumPy-style, and Sphinx-style docstrings:

```python
# Google style (preferred)
"""Summary line.

Args:
    param: Description of param
"""

# NumPy style
"""Summary line.

Parameters
----------
param : str
    Description of param
"""
```

## Adapter Interface

Each platform adapter implements:

```python
class FormatAdapter(ABC, Generic[T]):
    """Base class for platform-specific adapters."""
    name: str

    @abstractmethod
    def generate_schema(self, tool: UniversalTool) -> ConversionResult[T]:
        """IR → platform schema (for API calls)."""
        ...

    @abstractmethod
    def parse_tool_calls(self, response: Any) -> list[UniversalToolCall]:
        """Platform response → normalized tool calls."""
        ...

    @abstractmethod
    def format_results(self, results: list[UniversalToolResult]) -> Any:
        """Normalized results → platform-specific format."""
        ...
```

### Adapter Implementations

```
adapters/
  openai_chat.py       # OpenAI Chat Completions
    - generate_schema: IR → {"type": "function", "function": {name, parameters}}
    - parse_tool_calls: response.choices[0].message.tool_calls → UniversalToolCall[]
    - format_results:   UniversalToolResult → {"role": "tool", "tool_call_id", "content"}

  anthropic.py         # Anthropic Claude
    - generate_schema: IR → {"name", "input_schema"}
    - parse_tool_calls: response.content[tool_use blocks] → UniversalToolCall[]
    - format_results:   UniversalToolResult → {"type": "tool_result", "tool_use_id"}

  gemini.py            # Google Gemini
    - generate_schema: IR → {"name", "parameters": {UPPERCASE types}}
    - parse_tool_calls: response.candidates[0].content.parts[functionCall] → UniversalToolCall[]
    - format_results:   UniversalToolResult → {"functionResponse": {name, response}}

  mcp.py               # MCP Server
    - generate_schema: IR → MCP Tool definition
    - serve:            Start stdio/HTTP MCP server with tools/list + tools/call handlers
```

## Dispatch Engine

The core dispatch loop (shared across all platforms):

```python
def dispatch(
    tool_calls: list[UniversalToolCall],
    tools: list[UniversalTool],
) -> list[UniversalToolResult]:
    """Execute tool calls against registered functions."""
    results = []
    tool_map = {t.name: t for t in tools}

    for call in tool_calls:
        tool = tool_map.get(call.name)
        if tool is None or tool.fn is None:
            results.append(UniversalToolResult(
                call_id=call.id, is_error=True,
                content=[ContentItem(type="text", text=f"Unknown tool: {call.name}")]
            ))
            continue

        try:
            # Validate arguments against schema
            validated = validate_args(call.arguments, tool.input_schema)
            # Execute the function
            output = tool.fn(**validated)
            # Normalize output to content items
            content = normalize_output(output)
            results.append(UniversalToolResult(
                call_id=call.id, content=content
            ))
        except Exception as e:
            results.append(UniversalToolResult(
                call_id=call.id, is_error=True,
                content=[ContentItem(type="text", text=str(e))]
            ))

    return results
```

## Schema Normalization

### JSON Schema transforms per target

```
Target          Required Transforms
─────────────────────────────────────────────────────────
OpenAI          Strip $schema
(non-strict)    Ensure "properties" exists

OpenAI          All of above, plus:
(strict)        additionalProperties: false (recursive)
                All properties → required
                oneOf → anyOf
                Inline $ref
                Strip null defaults

Gemini          All type names → UPPERCASE
                Inline all $ref/$defs
                Strip: oneOf, allOf, default, examples, pattern
                null type → nullable: true
                const → single-element enum

Anthropic       Rename inputSchema → input_schema
                (otherwise minimal transforms)

MCP             Canonical form (no transforms needed)
```

## Directory Structure

```
src/aitx/
├── __init__.py              # Public API: tool(), to_openai(), handle_openai(), etc.
├── decorator.py             # @aitx.tool() implementation
├── convert.py               # JSON-to-JSON conversion API (schema export)
├── ir/
│   ├── __init__.py
│   ├── types.py             # UniversalTool, ToolCall, ToolResult (Pydantic)
│   └── introspect.py        # Function → IR (type hints, docstring parsing)
├── adapters/
│   ├── __init__.py          # Adapter registry
│   ├── base.py              # FormatAdapter ABC
│   ├── openai_chat.py       # OpenAI Chat Completions
│   ├── anthropic.py         # Anthropic Claude
│   └── gemini.py            # Google Gemini
├── schema/
│   ├── __init__.py
│   ├── normalizer.py        # JSON Schema normalization
│   ├── ref_resolver.py      # $ref resolution and inlining
│   └── strict_mode.py       # OpenAI strict mode compliance
├── bridge/
│   ├── __init__.py
│   └── dispatcher.py        # Universal tool call dispatch engine
├── mesh/
│   ├── __init__.py          # serve_mesh(), discover_tools()
│   ├── node.py              # MeshNode: HTTP server + mDNS
│   ├── client.py            # MeshClient: async HTTP client
│   ├── router.py            # MeshRouter: auto-discovery + routing
│   └── discovery.py         # MeshAdvertiser: mDNS registration
└── cli/
    └── __init__.py          # CLI: aitx convert, aitx export, aitx formats
```

## Phase Plan

### Phase 0 (Complete)
- `@aitx.tool()` decorator with introspection
- `to_openai()` + `handle_openai()`
- `to_anthropic()` + `handle_anthropic()`
- `to_gemini()` + `handle_gemini()`
- Async dispatch (`handle_*_async()`, `dispatch_async()`)
- P2P Mesh Network (MeshNode, MeshRouter, MeshClient)
- Dispatch engine
- JSON-to-JSON `convert()` with loss reporting
- Schema normalization, $ref inlining, strict mode
- CLI: `aitx convert`, `aitx export`, `aitx formats`

### Phase 1
- MCP server adapter (`to_mcp()`, `serve_mcp()`)
- OpenAI Responses API adapter
- Streaming results
- Pydantic model return types

### Phase 2
- OpenClaw skill adapter
- Tool composition (tools that call tools)
- Middleware (logging, rate limiting, auth)
- Proxy server mode

### Phase 3
- TypeScript port consideration
- Plugin system for custom adapters
- Tool testing framework
