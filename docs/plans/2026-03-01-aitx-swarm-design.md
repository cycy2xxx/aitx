# AITX Swarm/Mesh Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement `aitx.mesh`, a zero-config peer-to-peer network layer allowing `@aitx.tool()` functions to be dynamically discovered and executed across processes and machines using mDNS and HTTP.

**Architecture:** We use `zeroconf` to advertise local `aitx` instances over mDNS (`_aitx._tcp.local.`). A local instance spins up a lightweight `aiohttp` web server exposing a `/tools` endpoint to list available tools, and a `/execute` endpoint to run them. The client can automatically resolve nodes and call tools.

**Tech Stack:** Python 3.11+, `zeroconf` for discovery, `aiohttp` for the local server/client.

---

### Task 1: Update Dependencies

**Files:**
- Modify: `pyproject.toml`

**Step 1: Write the changes**

```toml
# In [project.optional-dependencies] add:
swarm = ["zeroconf>=0.131.0", "aiohttp>=3.9.0"]

# Change all to include swarm:
all = ["aitx[openai,anthropic,mcp,gemini,cli,swarm]"]
```

**Step 2: Install and verify**

Run: `uv pip install -e ".[all]"`
Expected: Installs successfully with zeroconf and aiohttp.

**Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "build: add optional swarm dependencies"
```

---

### Task 2: Create Mesh Package Structure

**Files:**
- Create: `src/aitx/mesh/__init__.py`
- Create: `src/aitx/mesh/node.py`
- Create: `src/aitx/mesh/discovery.py`
- Create: `tests/test_mesh.py`

**Step 1: Write the failing test**

```python
# in tests/test_mesh.py
def test_mesh_imports():
    import aitx.mesh
    assert hasattr(aitx.mesh, "MeshNode")
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_mesh.py -v`
Expected: FAIL with "No module named 'aitx.mesh'" or "MeshNode" not found.

**Step 3: Write minimal implementation**

```python
# in src/aitx/mesh/__init__.py
from .node import MeshNode
__all__ = ["MeshNode"]

# in src/aitx/mesh/node.py
class MeshNode:
    pass

# in src/aitx/mesh/discovery.py
# (empty file for now)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_mesh.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/aitx/mesh/ tests/test_mesh.py
git commit -m "feat: scaffold mesh package"
```

---

### Task 3: Implement Web Server Router

**Files:**
- Modify: `src/aitx/mesh/node.py`
- Modify: `tests/test_mesh.py`

**Step 1: Write the failing test**

```python
# in tests/test_mesh.py
import pytest
from aiohttp import web
from aitx.mesh.node import create_app

@pytest.mark.asyncio
async def test_mesh_app_creation():
    app = create_app([])
    assert isinstance(app, web.Application)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_mesh.py::test_mesh_app_creation -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# in src/aitx/mesh/node.py
from typing import Callable, Any
from aiohttp import web

def create_app(tools: list[Callable[..., Any]]) -> web.Application:
    app = web.Application()
    
    async def list_tools(request: web.Request) -> web.Response:
        return web.json_response({"tools": [t.__name__ for t in tools]})
        
    app.router.add_get('/tools', list_tools)
    return app

class MeshNode:
    def __init__(self, tools: list[Callable[..., Any]], port: int = 0):
        self.tools = tools
        self.port = port
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_mesh.py::test_mesh_app_creation -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/aitx/mesh/node.py tests/test_mesh.py
git commit -m "feat(mesh): basic aiohttp app creation"
```

(Further tasks will be created dynamically as the execution agent iterates during the next phase. This plan establishes the pattern for Claude Code).
