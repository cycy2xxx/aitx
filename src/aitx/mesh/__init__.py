import asyncio
from typing import Callable, Any
from zeroconf import Zeroconf, ServiceBrowser, ServiceStateChange, ServiceInfo

from .node import MeshNode
from .client import MeshClient

__all__ = ["MeshNode", "MeshClient", "serve_mesh", "discover_tools"]

def serve_mesh(name: str, tools: list[Callable[..., Any]], port: int = 8080) -> None:
    """Serve a list of tools over the AITX mesh synchronously."""
    node = MeshNode(name, tools, port)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(node.start())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(node.stop())

class _DiscoverListener:
    def __init__(self):
        self.nodes = {}

    def remove_service(self, zeroconf, type, name):
        if name in self.nodes:
            del self.nodes[name]

    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        if info and info.addresses:
            import socket
            ip = socket.inet_ntoa(info.addresses[0])
            port = info.port
            self.nodes[name] = {"host": ip, "port": port}

    def update_service(self, zeroconf, type, name):
        pass

async def discover_tools(timeout: float = 3.0) -> list[dict[str, Any]]:
    """Discover available AITX mesh nodes on the local network."""
    loop = asyncio.get_running_loop()
    zeroconf = await loop.run_in_executor(None, Zeroconf)
    listener = _DiscoverListener()
    browser = await loop.run_in_executor(None, ServiceBrowser, zeroconf, "_aitx._tcp.local.", listener)
    
    await asyncio.sleep(timeout)
    
    await loop.run_in_executor(None, browser.cancel)
    await loop.run_in_executor(None, zeroconf.close)
    
    results = []
    for node_name, info in listener.nodes.items():
        try:
            async with MeshClient(info["host"], info["port"]) as client:
                tools = await client.list_tools()
                results.append({
                    "node": node_name.replace("._aitx._tcp.local.", ""),
                    "host": info["host"],
                    "port": info["port"],
                    "tools": tools
                })
        except Exception:
            pass
            
    return results
