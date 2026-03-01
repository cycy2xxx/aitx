"""MeshNode: Lightweight HTTP server exposing tools to the mesh network.

Provides ``create_app`` (the aiohttp application factory) and ``MeshNode``
which combines the HTTP server with mDNS advertisement.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from typing import TYPE_CHECKING, Any

from aiohttp import web

from ..ir.introspect import introspect as _introspect
from .discovery import MeshAdvertiser

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


# ── App factory ───────────────────────────────────────────────────────


def create_app(tools: list[Callable[..., Any]]) -> web.Application:
    """Create an aiohttp Application that exposes *tools* over HTTP.

    Endpoints
    ---------
    ``GET /tools``   — returns ``{"tools": {name: schema, ...}}``
    ``POST /execute`` — expects ``{"tool": "<name>", "arguments": {...}}``
    """
    app = web.Application()
    tools_by_name: dict[str, Callable[..., Any]] = {t.__name__: t for t in tools}
    # Pre-compute schemas once at startup using canonical IR
    schemas = {name: _introspect(t).model_dump(mode="json") for name, t in tools_by_name.items()}

    async def list_tools(_request: web.Request) -> web.Response:
        return web.json_response({"tools": schemas})

    async def execute_tool(request: web.Request) -> web.Response:
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON body"}, status=400)

        tool_name = data.get("tool")
        args = data.get("arguments", {})

        if not tool_name or tool_name not in tools_by_name:
            available = list(tools_by_name.keys())
            return web.json_response(
                {"error": f"Tool '{tool_name}' not found. Available: {available}"},
                status=404,
            )

        tool_func = tools_by_name[tool_name]
        try:
            if inspect.iscoroutinefunction(tool_func):
                result = await tool_func(**args)
            else:
                # Run sync functions in an executor to avoid blocking the loop
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(None, lambda: tool_func(**args))
            return web.json_response({"result": result})
        except TypeError as e:
            return web.json_response({"error": f"Bad arguments: {e}"}, status=400)
        except Exception as e:
            logger.exception(f"Error executing tool '{tool_name}'")
            return web.json_response({"error": str(e)}, status=500)

    app.router.add_get("/tools", list_tools)
    app.router.add_post("/execute", execute_tool)
    return app


# ── MeshNode ──────────────────────────────────────────────────────────


class MeshNode:
    """A mesh network node that serves tools over HTTP and advertises via mDNS.

    Usage::

        node = MeshNode("my_node", [my_tool], port=8080)
        await node.start()
        # ... node is now discoverable and serving tools ...
        await node.stop()

    Supports ``async with``::

        async with MeshNode("my_node", [my_tool]) as node:
            ...  # node is running
    """

    def __init__(
        self,
        name: str,
        tools: list[Callable[..., Any]],
        port: int = 8080,
    ) -> None:
        self.name = name
        self.tools = tools
        self.port = port
        self.app = create_app(tools)
        self.advertiser = MeshAdvertiser(name, port)
        self._runner: web.AppRunner | None = None

    async def start(self) -> None:
        """Start the HTTP server and begin mDNS advertisement."""
        self._runner = web.AppRunner(self.app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, "0.0.0.0", self.port)
        await site.start()
        await self.advertiser.start()
        logger.info(f"MeshNode '{self.name}' serving {len(self.tools)} tool(s) on port {self.port}")

    async def stop(self) -> None:
        """Stop advertisement and shut down the HTTP server."""
        await self.advertiser.stop()
        if self._runner:
            await self._runner.cleanup()
            self._runner = None

    async def __aenter__(self) -> MeshNode:
        await self.start()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.stop()
