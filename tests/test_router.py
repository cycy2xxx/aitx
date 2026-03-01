import pytest
import asyncio
from aitx.mesh.router import MeshRouter

@pytest.mark.asyncio
async def test_mesh_router_init():
    router = MeshRouter()
    assert len(router.nodes) == 0
    
@pytest.mark.asyncio
async def test_mesh_router_start_stop():
    router = MeshRouter()
    await router.start()
    
    # Needs to run without exceptions
    assert router._browser is not None
    
    await router.stop()
    assert router._browser is None
