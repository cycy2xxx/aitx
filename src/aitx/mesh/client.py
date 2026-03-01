"""MeshClient: HTTP client for interacting with remote AITX mesh nodes."""
from __future__ import annotations

from typing import Any

import aiohttp


class MeshClient:
    """Async HTTP client for listing and executing tools on a remote mesh node.

    Must be used as an async context manager::

        async with MeshClient("192.168.1.10", 8080) as client:
            tools = await client.list_tools()
            result = await client.execute("my_tool", {"arg": "val"})
    """

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> MeshClient:
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            raise RuntimeError(
                "Client session not initialised. "
                "Use 'async with MeshClient(...) as client:'"
            )
        return self._session

    async def list_tools(self) -> dict[str, Any]:
        """Fetch available tools and their schemas from the remote node.

        Returns a dict mapping tool names to their IR schema dicts.
        """
        session = self._ensure_session()
        async with session.get(f"{self.base_url}/tools") as resp:
            if resp.status != 200:
                raise RuntimeError(f"Failed to fetch tools (HTTP {resp.status})")
            data = await resp.json()
            return data.get("tools", {})

    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> Any:
        """Execute a tool on the remote node and return its result.

        Parameters
        ----------
        tool_name:
            Name of the tool to execute.
        arguments:
            Keyword arguments to pass to the tool. Optional for tools
            that take no parameters.

        Raises
        ------
        RuntimeError
            If the remote node returns a non-200 status.
        """
        session = self._ensure_session()
        payload = {"tool": tool_name, "arguments": arguments or {}}
        async with session.post(f"{self.base_url}/execute", json=payload) as resp:
            data = await resp.json()
            if resp.status != 200:
                raise RuntimeError(
                    f"Remote execution failed: {data.get('error', 'unknown')}"
                )
            return data.get("result")
