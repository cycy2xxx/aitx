"""MeshNode: Lightweight HTTP server exposing tools to the mesh network.

Provides ``create_app`` (the aiohttp application factory) and ``MeshNode``
which combines the HTTP server with mDNS advertisement.
"""
from __future__ import annotations

import asyncio
import inspect
import logging
from typing import TYPE_CHECKING, Any, get_type_hints

from aiohttp import web

from .discovery import MeshAdvertiser

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

# ── Schema introspection ──────────────────────────────────────────────

# Maps Python types to JSON Schema type strings.
_TYPE_MAP: dict[type, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


def _python_type_to_json(tp: type | None) -> str:
    """Convert a Python type annotation to a JSON Schema type string."""
    if tp is None or tp is inspect.Parameter.empty:
        return "string"
    origin = getattr(tp, "__origin__", None)
    if origin is list:
        return "array"
    if origin is dict:
        return "object"
    return _TYPE_MAP.get(tp, "string")


def _parse_docstring_args(docstring: str | None) -> dict[str, str]:
    """Extract parameter descriptions from Google-style docstrings.

    Supports::

        Args:
            param_name: Description of the parameter.
            other_param: Another description.
    """
    if not docstring:
        return {}
    descriptions: dict[str, str] = {}
    in_args = False
    for line in docstring.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("args:"):
            in_args = True
            continue
        if in_args:
            if not stripped or (not line.startswith(" ") and not line.startswith("\t")):
                break
            if ":" in stripped:
                param, _, desc = stripped.partition(":")
                descriptions[param.strip()] = desc.strip()
    return descriptions


def introspect(func: Callable[..., Any]) -> dict[str, Any]:
    """Build a JSON Schema–style tool descriptor from a function's signature.

    Inspects type hints and docstring to produce a portable schema dict
    that can be used by any AI platform adapter.
    """
    sig = inspect.signature(func)
    try:
        hints = get_type_hints(func)
    except Exception:
        hints = {}
    doc = inspect.getdoc(func) or ""
    arg_docs = _parse_docstring_args(doc)
    # Strip the Args block from the main description
    desc_lines = []
    for line in doc.splitlines():
        if line.strip().lower().startswith("args:"):
            break
        desc_lines.append(line)
    description = "\n".join(desc_lines).strip()

    properties: dict[str, Any] = {}
    required: list[str] = []

    for name, param in sig.parameters.items():
        if name == "self":
            continue
        prop: dict[str, Any] = {"type": _python_type_to_json(hints.get(name))}
        if name in arg_docs:
            prop["description"] = arg_docs[name]
        if param.default is inspect.Parameter.empty:
            required.append(name)
        else:
            prop["default"] = param.default
        properties[name] = prop

    return {
        "name": func.__name__,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required,
        },
    }


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
    # Pre-compute schemas once at startup
    schemas = {name: introspect(t) for name, t in tools_by_name.items()}

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
                result = await loop.run_in_executor(
                    None, lambda: tool_func(**args)
                )
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
