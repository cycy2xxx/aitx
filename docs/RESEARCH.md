# aitx Research Report

## 1. Competitive Landscape

### Existing Projects

| Project | Stars | Direction | IR | Language | Limitation |
|---|---|---|---|---|---|
| LiteLLM | ~27k | OpenAI→providers (embedded) | OpenAI format | Python | Conversion not usable standalone |
| Vercel AI SDK | ~22k | Zod→providers (embedded) | Zod | TS | Cannot convert from existing schemas |
| ToolRegistry | 16 | N→OpenAI (one-way) | OpenAI format | Python | Output is OpenAI only |
| mcphero | small | MCP→OpenAI/Gemini | none | Python | Streamable HTTP only |
| mcp-llm-bridge | 277 | MCP→OpenAI-compat | none | Python | Runtime bridge |
| OpenAI Agents SDK | 19k | MCP→OpenAI (internal) | none | Python | Coupled to SDK |
| LangChain | 100k+ | N→OpenAI (internal) | OpenAI format | Python | Inside bind_tools() |

### aitx Unique Value

1. **Standalone library** — not embedded in an SDK
2. **N-to-N conversion** — many-to-many, bidirectional
3. **Formal IR** — superset of all formats
4. **Loss reporting** — explicit report of what's lost in each conversion
5. **TypeScript-first** — immediate npm ecosystem availability
6. **CLI** — batch conversion support

---

## 2. Format Comparison

### Tool Definition Schemas

```
                  MCP              OpenAI Chat       OpenAI Responses    Gemini           Anthropic
──────────────────────────────────────────────────────────────────────────────────────────────────────
Name field       name             function.name      name (flat)         name              name
Desc field       description      function.desc      description (flat)  description(req)  description
Schema key       inputSchema      function.params    parameters (flat)   parameters        input_schema
Output schema    outputSchema     none               none                none              none
Annotations      annotations      none               none                none              none
Strict mode      none             function.strict    strict (flat)       none              none
Type casing      lowercase        lowercase          lowercase           UPPERCASE         lowercase
Schema spec      JSON Schema      JSON Schema subset JSON Schema subset  OpenAPI subset    JSON Schema
                 draft-07/2020-12                                                          draft-07/2020-12
```

### Tool Call Flow

```
                  MCP              OpenAI Chat       OpenAI Responses    Gemini           Anthropic
──────────────────────────────────────────────────────────────────────────────────────────────────────
Call ID          none (JSON-RPC)  tool_call_id       call_id             none (by name)    tool_use id
Args format      parsed object    JSON string        JSON string         parsed object     parsed object
Result format    content[] array  string             string              object            content[] array
Error signal     isError: true    error string       error string        exception/string  is_error
Parallel calls   separate reqs    tool_calls[] array function_call[]     functionCall[]    tool_use[]
```

---

## 3. Hard Conversion Problems

### 3.1 OpenAI strict: true Deep Transformation

Strict mode recursively mutates the entire schema tree:
- Injects `additionalProperties: false` on ALL objects
- Forces ALL properties to be `required`
- Converts `oneOf` → `anyOf`
- Flattens single-element `allOf`
- Inlines `$ref` with sibling properties
- Strips `null` defaults

This changes semantics: optional fields become required, altering tool behavior.

### 3.2 Gemini Limitations

The most lossy conversion target:
- Type names uppercased (`string` → `STRING`)
- `$ref` / `$defs` not supported → must inline all references
- `oneOf` / `allOf` not supported → must flatten
- `default`, `examples`, `pattern` not supported → must strip
- No `null` type → use `nullable: true` flag
- Recursive schemas → impossible to convert (depth-limited unrolling only)

### 3.3 Multi-Content Result Conversion

MCP results: array of text, image, audio, resource items
OpenAI results: single string
Gemini results: object

The transpiler needs content-type-specific conversion strategies.

### 3.4 JSON Schema Draft Differences

- draft-07: `definitions` keyword
- draft 2020-12: `$defs` keyword
- OpenAPI 3.0 (Gemini): neither supported

Must detect and inline both variants.

---

## 4. Protocol Ecosystem

### Layer Stack

```
Layer 4: AG-UI        Agent ↔ User UI (CopilotKit)
Layer 3: A2A          Agent ↔ Agent (Google → Linux Foundation)
Layer 2: MCP          Agent ↔ Tools/Data (Anthropic → Linux Foundation)
Layer 1: AGNTCY       Infrastructure: identity, discovery, messaging (Cisco → LF)
Layer 0: HTTP/SSE     Transport
```

### aitx Positioning

aitx is a **Layer 2 horizontal integration tool**.
Centered on MCP while bridging other Layer 2 tool definition formats
(OpenAI function calling, Gemini FunctionDeclaration, Anthropic tool_use).

---

## 5. Governance Bodies

### Agentic AI Foundation (AAIF) — Linux Foundation
- Founded December 2025
- Projects: MCP, goose, AGENTS.md
- Platinum: AWS, Anthropic, Block, Bloomberg, Cloudflare, Google, Microsoft, OpenAI

### NIST AI Agent Standards Initiative
- Announced February 2026
- Focused on interoperable agent protocol barriers
