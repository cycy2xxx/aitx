# Contributing to aitx

Thank you for your interest in contributing to aitx! This project aims to break down barriers between AI agent ecosystems, and every contribution helps.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/aitx.git`
3. Install dependencies: `uv sync --all-extras`
4. Create a branch: `git checkout -b my-feature`
5. Make your changes
6. Run checks: `uv run pytest && uv run mypy src/ && uv run ruff check src/`
7. Submit a pull request

## Development Setup

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all dependencies (including dev extras)
uv sync --all-extras

# Run tests
uv run pytest

# Type checking
uv run mypy src/

# Lint
uv run ruff check src/

# Format
uv run ruff format src/
```

## What Can I Contribute?

### New Format Adapters

The most impactful contributions are new format adapters. Each adapter extends the `FormatAdapter` base class:

```python
from aitx.adapters.base import FormatAdapter
from aitx.ir.types import UniversalTool, ConversionResult

class MyFormatAdapter(FormatAdapter[MyFormatType]):
    name = "my-format"

    def parse(self, source: MyFormatType) -> UniversalTool:
        ...

    def generate(self, tool: UniversalTool) -> ConversionResult[MyFormatType]:
        ...
```

See `src/aitx/adapters/mcp.py` for a reference implementation.

### Test Cases

Real-world tool definitions that exercise edge cases are extremely valuable. Add them to `tests/fixtures/` as JSON files with a descriptive name.

### Bug Fixes

If you find a conversion that produces incorrect output, please:
1. Add a failing test case first
2. Fix the bug
3. Verify the test passes

### Documentation

Improvements to docs, examples, and error messages are always welcome.

## Code Style

- Python 3.11+ with full type annotations
- Pydantic v2 for all data models
- `ruff` for linting and formatting
- `mypy --strict` must pass
- Named imports, no `from module import *`
- Every adapter must have corresponding tests

## Pull Request Guidelines

- Keep PRs focused — one feature or fix per PR
- Include tests for new functionality
- Update the README if adding a new format
- Run `uv run pytest && uv run mypy src/ && uv run ruff check src/` before submitting

## Adding a New Adapter

1. Create `src/aitx/adapters/your_format.py` extending `FormatAdapter`
2. Create `tests/adapters/test_your_format.py` with bidirectional conversion tests
3. Add fixture files in `tests/fixtures/`
4. Register the adapter in `src/aitx/adapters/__init__.py`
5. Update the README supported formats table

## Commit Messages

Use clear, descriptive commit messages:

```
feat: add Gemini adapter with type case conversion
fix: handle recursive $ref in schema inlining
test: add edge case for nullable union types
docs: update supported formats table
```

## Governance

This project uses a **maintainer delegation** model:
- The core maintainers have merge access
- Trusted contributors can be promoted to maintainer status
- All PRs require at least one maintainer review

## Code of Conduct

Be respectful and constructive. We're here to build something useful together.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
