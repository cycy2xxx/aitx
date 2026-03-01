import aiohttp
from typing import Any

class MeshClient:
    """Client for interacting with AITX mesh nodes."""
    
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> "MeshClient":
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.session:
            await self.session.close()

    async def list_tools(self) -> list[str]:
        """Fetch the list of tools available on the node."""
        if not self.session:
            raise RuntimeError("Client session not initialized. Use 'async with MeshClient(...):'")
        
        async with self.session.get(f"{self.base_url}/tools") as response:
            if response.status != 200:
                raise RuntimeError(f"Failed to fetch tools: {response.status}")
            data = await response.json()
            return data.get("tools", [])

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Execute a tool on the remote node."""
        if not self.session:
            raise RuntimeError("Client session not initialized. Use 'async with MeshClient(...):'")
            
        payload = {"tool": tool_name, "arguments": object}
        payload["arguments"] = arguments
        
        async with self.session.post(f"{self.base_url}/execute", json=payload) as response:
            data = await response.json()
            if response.status != 200:
                raise RuntimeError(data.get("error", "Unknown error"))
            return data.get("result")
