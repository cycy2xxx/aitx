"""Tests for MeshNode and its aiohttp web app."""

import pytest
from aiohttp import web

from aitx.ir.introspect import introspect
from aitx.mesh.node import create_app


def sample_tool(text: str) -> str:
    """A dummy tool for testing."""
    return f"echo: {text}"


def test_mesh_imports():
    import aitx.mesh

    assert hasattr(aitx.mesh, "MeshNode")
    assert hasattr(aitx.mesh, "MeshRouter")


def test_introspect_produces_valid_schema():
    ir = introspect(sample_tool)
    assert ir.name == "sample_tool"
    assert ir.description == "A dummy tool for testing."
    assert len(ir.parameters) == 1
    assert ir.parameters[0].name == "text"
    assert ir.parameters[0].type == "string"


@pytest.mark.asyncio
async def test_mesh_app_creation():
    app = create_app([sample_tool])
    assert isinstance(app, web.Application)


@pytest.mark.asyncio
async def test_mesh_tools_endpoint_schemas(aiohttp_client):
    app = create_app([sample_tool])
    client = await aiohttp_client(app)

    resp = await client.get("/tools")
    assert resp.status == 200
    data = await resp.json()
    assert "tools" in data
    tool = data["tools"]["sample_tool"]
    assert tool["name"] == "sample_tool"
    assert len(tool["parameters"]) >= 1  # list of ToolParameter dicts


@pytest.mark.asyncio
async def test_mesh_execute_endpoint(aiohttp_client):
    app = create_app([sample_tool])
    client = await aiohttp_client(app)

    resp = await client.post(
        "/execute", json={"tool": "sample_tool", "arguments": {"text": "hello"}}
    )
    assert resp.status == 200
    data = await resp.json()
    assert data["result"] == "echo: hello"


@pytest.mark.asyncio
async def test_mesh_execute_not_found(aiohttp_client):
    app = create_app([sample_tool])
    client = await aiohttp_client(app)

    resp = await client.post("/execute", json={"tool": "unknown", "arguments": {}})
    assert resp.status == 404


@pytest.mark.asyncio
async def test_mesh_execute_bad_arguments(aiohttp_client):
    app = create_app([sample_tool])
    client = await aiohttp_client(app)

    resp = await client.post("/execute", json={"tool": "sample_tool", "arguments": {"wrong": 1}})
    assert resp.status == 400
