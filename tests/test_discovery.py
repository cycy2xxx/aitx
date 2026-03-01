import pytest

from aitx.mesh.discovery import MeshAdvertiser


def test_mesh_advertiser_init():
    advertiser = MeshAdvertiser("test_node", 8080)
    assert advertiser.name == "test_node"
    assert advertiser.port == 8080
    assert not advertiser.is_running


@pytest.mark.asyncio
async def test_mesh_advertiser_lifecycle():
    # We don't want to actually blast MDNS on the network during unit tests,
    # so we'll mock zeroconf in a real implementation.
    # For now, let's just make sure start() and stop() don't crash and update state.
    advertiser = MeshAdvertiser("test_node_lifecycle", 8080)
    await advertiser.start()
    assert advertiser.is_running
    await advertiser.stop()
    assert not advertiser.is_running
