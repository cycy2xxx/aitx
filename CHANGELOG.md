# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-03-02

### Added

- `@aitx.tool()` decorator with function introspection (type hints + docstrings)
- OpenAI Chat Completions adapter (`to_openai()`, `handle_openai()`)
- Anthropic Messages API adapter (`to_anthropic()`, `handle_anthropic()`)
- Google Gemini adapter (`to_gemini()`, `handle_gemini()`)
- Async dispatch support (`handle_openai_async()`, `handle_anthropic_async()`, `handle_gemini_async()`)
- P2P Mesh Network with mDNS discovery (`MeshNode`, `MeshRouter`, `MeshClient`)
- JSON-to-JSON schema conversion with loss reporting (`convert()`)
- CLI commands: `aitx convert`, `aitx export`, `aitx formats`
- JSON Schema utilities: normalization, `$ref` inlining, OpenAI strict mode
- Generic type introspection (`list[str]`, `dict[str, int]`, `Optional[X]`)
- GitHub Actions CI (ruff, mypy, pytest across Python 3.11/3.12/3.13)

[0.1.0]: https://github.com/cycy2xxx/aitx/releases/tag/v0.1.0
