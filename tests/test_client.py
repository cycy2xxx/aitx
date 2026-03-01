import pytest
from aioresponses import aioresponses
from aitx.mesh.client import MeshClient

@pytest.fixture
def mock_aioresponse():
    with aioresponses() as m:
        yield m

@pytest.mark.asyncio
async def test_mesh_client_list_tools(mock_aioresponse):
    mock_aioresponse.get('http://127.0.0.1:8080/tools', payload={'tools': ['test_tool']})
    
    async with MeshClient("127.0.0.1", 8080) as client:
        tools = await client.list_tools()
        assert "test_tool" in tools

@pytest.mark.asyncio
async def test_mesh_client_execute_tool(mock_aioresponse):
    mock_aioresponse.post('http://127.0.0.1:8080/execute', payload={'result': 'success'})
    
    async with MeshClient("127.0.0.1", 8080) as client:
        result = await client.execute("test_tool")
        assert result == "success"
