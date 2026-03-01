import pytest
from aiohttp import web
from aitx.mesh.node import create_app

def test_mesh_imports():
    import aitx.mesh
    assert hasattr(aitx.mesh, "MeshNode")

def sample_tool(text: str) -> str:
    """A dummy tool."""
    return f"echo: {text}"

@pytest.mark.asyncio
async def test_mesh_app_creation():
    app = create_app([sample_tool])
    assert isinstance(app, web.Application)

@pytest.mark.asyncio
async def test_mesh_tools_endpoint(aiohttp_client):
    app = create_app([sample_tool])
    client = await aiohttp_client(app)
    
    resp = await client.get('/tools')
    assert resp.status == 200
    data = await resp.json()
    assert "tools" in data
    assert "sample_tool" in data["tools"]

@pytest.mark.asyncio
async def test_mesh_execute_endpoint(aiohttp_client):
    app = create_app([sample_tool])
    client = await aiohttp_client(app)
    
    resp = await client.post('/execute', json={"tool": "sample_tool", "arguments": {"text": "hello"}})
    assert resp.status == 200
    data = await resp.json()
    assert data["result"] == "echo: hello"

@pytest.mark.asyncio
async def test_mesh_execute_not_found(aiohttp_client):
    app = create_app([sample_tool])
    client = await aiohttp_client(app)
    
    resp = await client.post('/execute', json={"tool": "unknown", "arguments": {}})
    assert resp.status == 404
