"""aitx.mesh — Zero-config peer-to-peer tool mesh for AI agents.

Provides the public API for the AITX Swarm Mesh feature:

- :class:`MeshNode`   — serve tools over HTTP + advertise via mDNS
- :class:`MeshClient` — call tools on a known remote node
- :class:`MeshRouter` — auto-discover nodes and route tool calls
- :func:`serve_mesh`  — one-liner to start a node (blocking)
- :func:`discover_tools` — one-shot discovery of all nodes on the LAN
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import socket
from typing import TYPE_CHECKING, Any

from zeroconf import ServiceBrowser, Zeroconf

from .client import MeshClient
from .node import MeshNode
from .router import MeshRouter

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = [
    "MeshNode",
    "MeshClient",
    "MeshRouter",
    "serve_mesh",
    "discover_tools",
]

logger = logging.getLogger(__name__)


# ── Convenience helpers ───────────────────────────────────────────────


def serve_mesh(
    name: str,
    tools: list[Callable[..., Any]],
    port: int = 8080,
) -> None:
    """Start a mesh node and serve tools until interrupted (blocking).

    This is the simplest way to expose tools to the mesh::

        serve_mesh("my_node", [my_tool_a, my_tool_b])
    """

    async def _run() -> None:
        async with MeshNode(name, tools, port):
            # Block until cancelled (Ctrl-C)
            await asyncio.Event().wait()

    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(_run())


class _DiscoverListener:
    """Internal zeroconf listener for one-shot discovery."""

    def __init__(self) -> None:
        self.nodes: dict[str, dict[str, Any]] = {}

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        if info and info.addresses:
            ip = socket.inet_ntoa(info.addresses[0])
            self.nodes[name] = {"host": ip, "port": info.port}

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        self.nodes.pop(name, None)

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass


async def discover_tools(timeout: float = 3.0) -> list[dict[str, Any]]:
    """One-shot discovery of all AITX mesh nodes on the local network.

    Waits *timeout* seconds for mDNS responses, then returns a list of
    dicts, each containing ``node``, ``host``, ``port``, and ``tools``.
    """
    loop = asyncio.get_running_loop()
    zc = await loop.run_in_executor(None, Zeroconf)
    listener = _DiscoverListener()
    browser = await loop.run_in_executor(
        None, ServiceBrowser, zc, "_aitx._tcp.local.", listener,
    )

    await asyncio.sleep(timeout)

    await loop.run_in_executor(None, browser.cancel)
    await loop.run_in_executor(None, zc.close)

    results: list[dict[str, Any]] = []
    for node_name, info in listener.nodes.items():
        try:
            async with MeshClient(info["host"], info["port"]) as client:
                tools = await client.list_tools()
                results.append({
                    "node": node_name.replace("._aitx._tcp.local.", ""),
                    "host": info["host"],
                    "port": info["port"],
                    "tools": tools,
                })
        except Exception:
            logger.debug("Skipping unreachable node '%s'", node_name)

    return results
