"""MeshRouter: Automatic tool discovery and execution routing.

Discovers AITX mesh nodes on the local network and routes tool execution
requests to the correct node transparently.
"""
import asyncio
import socket
import logging
from typing import Any

from zeroconf import Zeroconf, ServiceBrowser, ServiceInfo

from .client import MeshClient

logger = logging.getLogger(__name__)


class _RouterListener:
    """Internal zeroconf listener that tracks discovered mesh nodes."""

    def __init__(self, router: "MeshRouter") -> None:
        self._router = router

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        if info and info.addresses:
            host = socket.inet_ntoa(info.addresses[0])
            port = info.port
            node_name = name.replace("._aitx._tcp.local.", "")
            self._router._register_node(node_name, host, port)
            logger.info(f"Discovered mesh node '{node_name}' at {host}:{port}")

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        node_name = name.replace("._aitx._tcp.local.", "")
        self._router._unregister_node(node_name)
        logger.info(f"Lost mesh node '{node_name}'")

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass


class MeshRouter:
    """Routes tool execution to the appropriate mesh node automatically.

    Usage::

        router = MeshRouter()
        await router.start()

        # Wait a moment for discovery
        await asyncio.sleep(2)

        # Execute any tool on any node — routing is automatic
        result = await router.execute("analyze_text", {"text": "hello"})

        await router.stop()
    """

    SERVICE_TYPE = "_aitx._tcp.local."

    def __init__(self) -> None:
        self.nodes: dict[str, dict[str, Any]] = {}
        # Maps tool_name -> node_name for fast routing
        self._tool_index: dict[str, str] = {}
        self._zeroconf: Zeroconf | None = None
        self._browser: ServiceBrowser | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    # ── lifecycle ──────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start discovering mesh nodes on the local network."""
        self._loop = asyncio.get_running_loop()
        self._zeroconf = await self._loop.run_in_executor(None, Zeroconf)
        listener = _RouterListener(self)
        self._browser = await self._loop.run_in_executor(
            None, ServiceBrowser, self._zeroconf, self.SERVICE_TYPE, listener
        )
        logger.info("MeshRouter started — listening for AITX nodes")

    async def stop(self) -> None:
        """Stop discovery and clean up."""
        if self._browser:
            await asyncio.get_running_loop().run_in_executor(
                None, self._browser.cancel
            )
            self._browser = None
        if self._zeroconf:
            await asyncio.get_running_loop().run_in_executor(
                None, self._zeroconf.close
            )
            self._zeroconf = None
        self.nodes.clear()
        self._tool_index.clear()
        logger.info("MeshRouter stopped")

    # ── internal registry ─────────────────────────────────────────────

    def _register_node(self, name: str, host: str, port: int) -> None:
        self.nodes[name] = {"host": host, "port": port, "tools": {}}
        # Schedule async tool fetching back on the main event loop
        # (this method is called from zeroconf's background thread)
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._fetch_tools(name), self._loop)

    def _unregister_node(self, name: str) -> None:
        if name in self.nodes:
            # Remove tool index entries pointing to this node
            stale = [t for t, n in self._tool_index.items() if n == name]
            for t in stale:
                del self._tool_index[t]
            del self.nodes[name]

    async def _fetch_tools(self, node_name: str) -> None:
        """Fetch the tool list from a discovered node and index them."""
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
                    f"Indexed {len(tools)} tool(s) from '{node_name}': "
                    f"{', '.join(tools.keys())}"
                )
        except Exception as e:
            logger.warning(f"Failed to fetch tools from '{node_name}': {e}")

    # ── public API ────────────────────────────────────────────────────

    @property
    def available_tools(self) -> list[str]:
        """Return the names of all tools currently known across the mesh."""
        return list(self._tool_index.keys())

    def get_tool_schema(self, tool_name: str) -> dict[str, Any] | None:
        """Return the IR schema dict for a tool, or None if unknown."""
        node_name = self._tool_index.get(tool_name)
        if not node_name or node_name not in self.nodes:
            return None
        return self.nodes[node_name]["tools"].get(tool_name)

    async def execute(
        self, tool_name: str, arguments: dict[str, Any] | None = None
    ) -> Any:
        """Execute a tool by name — the router finds the right node.

        Raises ``KeyError`` if the tool is not found on any node.
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
