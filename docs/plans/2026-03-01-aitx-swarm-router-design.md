# AITX Swarm Mesh Next Level: Schema Cast & MeshRouter

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement Universal Schema Cast (nodes broadcast tool IR schemas) and `MeshRouter` (abstracts discovery and automatically routes executions).

**Architecture:** 
1. **Schema Cast:** Modify `MeshNode`'s `/tools` endpoint to generate and return AITX `UniversalTool` IR JSON for each registered function instead of just the name. `MeshClient` caches this IR.
2. **MeshRouter:** A new class that holds a reference to a `Zeroconf` browser (using the existing `MeshAdvertiser` listener logic, extracted if necessary). It maintains a real-time dict of `tool_name -> MeshClient`. Exposes `router.execute(tool_name, args)`.

**Tech Stack:** Python 3.11+, `zeroconf`, `aiohttp`, `aitx.ir.introspect`.

---

### Task 1: Refactor MeshNode to serve schemas

**Files:**
- Modify: `src/aitx/mesh/node.py`
- Modify: `tests/test_mesh.py`

**Step 1: Write the failing test**

```python
# in tests/test_mesh.py
@pytest.mark.asyncio
async def test_mesh_tools_endpoint_schemas(aiohttp_client):
    app = create_app([sample_tool])
    client = await aiohttp_client(app)
    
    resp = await client.get('/tools')
    data = await resp.json()
    assert "tools" in data
    # Now it should be a dict of name -> ir schema
    assert "sample_tool" in data["tools"]
    assert "description" in data["tools"]["sample_tool"]
```

**Step 2: Write minimal implementation**

```python
# in src/aitx/mesh/node.py
from aitx.ir.introspect import introspect

def create_app(tools: list[Callable[..., Any]]) -> web.Application:
    # ...
    async def list_tools(request: web.Request) -> web.Response:
        tools_info = {}
        for name, t in tools_by_name.items():
            ir = introspect(t)
            tools_info[name] = ir.model_dump()
        return web.json_response({"tools": tools_info})
    # ...
```

**Step 3: Commit**

```bash
git add src/aitx/mesh/node.py tests/test_mesh.py
git commit -m "feat(mesh): node serves tool IR schemas"
```

---

### Task 2: Enhance MeshClient to support schemas

**Files:**
- Modify: `src/aitx/mesh/client.py`
- Modify: `tests/test_client.py`

**Step 1: Write implementation**

```python
# in src/aitx/mesh/client.py
from aitx.ir.types import UniversalTool

class MeshClient:
    async def list_tools(self) -> dict[str, UniversalTool]:
        # fetch and parse response into UniversalTool objects
        # return dict of name -> UniversalTool
```

**Step 2: Commit**

```bash
git add src/aitx/mesh/client.py tests/test_client.py
git commit -m "feat(mesh): client parses tool schemas into IR objects"
```

---

### Task 3: Implement MeshRouter

**Files:**
- Create: `src/aitx/mesh/router.py`
- Modify: `src/aitx/mesh/__init__.py`
- Create: `tests/test_router.py`

**Step 1: Write implementation**

```python
# in router.py
class MeshRouter:
    async def start(self) -> None:
        # start zeroconf browser
        
    async def stop(self) -> None:
        # stop discovery
        
    async def execute(self, tool_name: str, arguments: dict[str, Any] | None = None) -> Any:
        # find node hosting this tool, create client, execute, return
        
    async def get_tool(self, tool_name: str) -> UniversalTool:
        # return the IR schema for a tool 
```

**Step 2: Commit**

```bash
git add src/aitx/mesh/router.py tests/test_router.py src/aitx/mesh/__init__.py
git commit -m "feat(mesh): add MeshRouter for dynamic tool routing"
```

---

### Task 4: Update Examples

**Files:**
- Modify: `examples/mesh_consumer.py`

**Step 1: Simplify consumer**

```python
# examples/mesh_consumer.py
import asyncio
from aitx.mesh.router import MeshRouter

async def main():
    router = MeshRouter()
    await router.start()
    
    # Wait a bit for discovery
    await asyncio.sleep(2)
    
    result = await router.execute("analyze_text", {"text": "Hello Router!"})
    print(result)
    
    await router.stop()
```

**Step 2: Commit**

```bash
git add examples/mesh_consumer.py
git commit -m "docs: update consumer example to use MeshRouter"
```
