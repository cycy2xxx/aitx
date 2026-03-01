import pytest
from aiohttp import web
from aitx.mesh.node import create_app

def test_mesh_imports():
    import aitx.mesh
    assert hasattr(aitx.mesh, "MeshNode")

@pytest.mark.asyncio
async def test_mesh_app_creation():
    app = create_app([])
    assert isinstance(app, web.Application)
