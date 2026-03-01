"""MeshRouter: Automatic tool discovery and transparent execution routing.

Discovers AITX mesh nodes on the local network via mDNS, indexes every
tool they expose, and routes ``execute()`` calls to the right node
without the caller needing to know anything about the network topology.
"""
from __future__ import annotations

import asyncio
import logging
import socket
from typing import Any

from zeroconf import ServiceBrowser, Zeroconf

from .client import MeshClient

logger = logging.getLogger(__name__)


# ── Internal zeroconf listener ────────────────────────────────────────


class _RouterListener:
    """Zeroconf callback handler — called from a *background thread*."""

    def __init__(self, router: MeshRouter) -> None:
        self._router = router

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        if info and info.addresses:
            host = socket.inet_ntoa(info.addresses[0])
            node_name = name.replace("._aitx._tcp.local.", "")
            self._router._register_node(node_name, host, info.port)

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        node_name = name.replace("._aitx._tcp.local.", "")
        self._router._unregister_node(node_name)

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass


# ── MeshRouter ────────────────────────────────────────────────────────


class MeshRouter:
    """Zero-config tool router for the AITX mesh network.

    Continuously discovers nodes, indexes their tools, and lets you call
    any tool by name — routing is fully automatic.

    Usage::

        async with MeshRouter() as router:
            await asyncio.sleep(2)            # allow discovery
            result = await router.execute("analyze_text", {"text": "hi"})

    Or manually::

        router = MeshRouter()
        await router.start()
        ...
        await router.stop()
    """

    SERVICE_TYPE = "_aitx._tcp.local."

    def __init__(self) -> None:
        self.nodes: dict[str, dict[str, Any]] = {}
        self._tool_index: dict[str, str] = {}  # tool_name → node_name
        self._zeroconf: Zeroconf | None = None
        self._browser: ServiceBrowser | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    # ── async context manager ─────────────────────────────────────────

    async def __aenter__(self) -> MeshRouter:
        await self.start()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.stop()

    # ── lifecycle ─────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start the mDNS browser and begin discovering nodes."""
        self._loop = asyncio.get_running_loop()
        self._zeroconf = await self._loop.run_in_executor(None, Zeroconf)
        listener = _RouterListener(self)
        self._browser = await self._loop.run_in_executor(
            None, ServiceBrowser, self._zeroconf, self.SERVICE_TYPE, listener,
        )
        logger.info("MeshRouter started — listening for AITX nodes")

    async def stop(self) -> None:
        """Stop the mDNS browser and release resources."""
        loop = asyncio.get_running_loop()
        if self._browser:
            await loop.run_in_executor(None, self._browser.cancel)
            self._browser = None
        if self._zeroconf:
            await loop.run_in_executor(None, self._zeroconf.close)
            self._zeroconf = None
        self.nodes.clear()
        self._tool_index.clear()
        self._loop = None
        logger.info("MeshRouter stopped")

    # ── internal registry (called from background thread) ─────────────

    def _register_node(self, name: str, host: str, port: int) -> None:
        self.nodes[name] = {"host": host, "port": port, "tools": {}}
        logger.info("Discovered mesh node '%s' at %s:%d", name, host, port)
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._fetch_tools(name), self._loop)

    def _unregister_node(self, name: str) -> None:
        if name not in self.nodes:
            return
        stale = [t for t, n in self._tool_index.items() if n == name]
        for t in stale:
            del self._tool_index[t]
        del self.nodes[name]
        logger.info("Lost mesh node '%s'", name)

    async def _fetch_tools(self, node_name: str) -> None:
        """Fetch tool schemas from a discovered node and build the index."""
        node = self.nodes.get(node_name)
        if not node:
            return
        try:
            async with MeshClient(node["host"], node["port"]) as client:
                tools = await client.list_tools()
                node["tools"] = tools
                for tool_name in tools:
                    self._tool_index[tool_name] = node_name
                logger.info(
                    "Indexed %d tool(s) from '%s': %s",
                    len(tools), node_name, ", ".join(tools.keys()),
                )
        except Exception:
            logger.warning("Failed to fetch tools from '%s'", node_name, exc_info=True)

    # ── public API ────────────────────────────────────────────────────

    @property
    def available_tools(self) -> list[str]:
        """Names of all tools currently known across the mesh."""
        return list(self._tool_index.keys())

    def get_tool_schema(self, tool_name: str) -> dict[str, Any] | None:
        """Return the schema dict for a tool, or ``None`` if unknown."""
        node_name = self._tool_index.get(tool_name)
        if not node_name or node_name not in self.nodes:
            return None
        return self.nodes[node_name]["tools"].get(tool_name)

    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> Any:
        """Execute a tool by name — routing is automatic.

        Raises
        ------
        KeyError
            If the tool is not found on any discovered node.
        """
        node_name = self._tool_index.get(tool_name)
        if not node_name or node_name not in self.nodes:
            raise KeyError(
                f"Tool '{tool_name}' not found on any mesh node. "
                f"Available: {self.available_tools}"
            )
        node = self.nodes[node_name]
        async with MeshClient(node["host"], node["port"]) as client:
            return await client.execute(tool_name, arguments)
