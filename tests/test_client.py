"""Tests for MeshClient."""

import pytest
from aioresponses import aioresponses

from aitx.mesh.client import MeshClient


@pytest.fixture
def mock_aioresponse():
    with aioresponses() as m:
        yield m


MOCK_TOOLS = {
    "tools": {
        "test_tool": {
            "name": "test_tool",
            "description": "A dummy tool",
            "parameters": {
                "type": "object",
                "properties": {"x": {"type": "integer"}},
                "required": ["x"],
            },
        }
    }
}


@pytest.mark.asyncio
async def test_list_tools(mock_aioresponse):
    mock_aioresponse.get("http://127.0.0.1:8080/tools", payload=MOCK_TOOLS)

    async with MeshClient("127.0.0.1", 8080) as client:
        tools = await client.list_tools()
        assert "test_tool" in tools
        assert tools["test_tool"]["name"] == "test_tool"


@pytest.mark.asyncio
async def test_execute(mock_aioresponse):
    mock_aioresponse.post("http://127.0.0.1:8080/execute", payload={"result": 42})

    async with MeshClient("127.0.0.1", 8080) as client:
        result = await client.execute("test_tool", {"x": 10})
        assert result == 42


@pytest.mark.asyncio
async def test_execute_no_args(mock_aioresponse):
    mock_aioresponse.post("http://127.0.0.1:8080/execute", payload={"result": "ok"})

    async with MeshClient("127.0.0.1", 8080) as client:
        result = await client.execute("test_tool")
        assert result == "ok"


@pytest.mark.asyncio
async def test_execute_remote_error(mock_aioresponse):
    mock_aioresponse.post(
        "http://127.0.0.1:8080/execute",
        payload={"error": "boom"},
        status=500,
    )

    async with MeshClient("127.0.0.1", 8080) as client:
        with pytest.raises(RuntimeError, match="boom"):
            await client.execute("test_tool")
