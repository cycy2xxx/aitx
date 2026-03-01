import asyncio
import inspect
from typing import Callable, Any
from aiohttp import web
from .discovery import MeshAdvertiser

# Fallback simple schema introspection since aitx.ir doesn't exist yet
def _simple_introspect(func: Callable[..., Any]) -> dict[str, Any]:
    return {
        "name": func.__name__,
        "description": inspect.getdoc(func) or "",
        "parameters": {
            "type": "object",
            "properties": {}, # Basic mock, real IR would parse annotations
        }
    }

def create_app(tools: list[Callable[..., Any]]) -> web.Application:
    app = web.Application()
    tools_by_name = {t.__name__: t for t in tools}
    
    async def list_tools(request: web.Request) -> web.Response:
        tools_info = {}
        for name, t in tools_by_name.items():
            tools_info[name] = _simple_introspect(t)
        return web.json_response({"tools": tools_info})
        
    async def execute_tool(request: web.Request) -> web.Response:
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON"}, status=400)
            
        tool_name = data.get("tool")
        args = data.get("arguments", {})
        
        if not tool_name or tool_name not in tools_by_name:
            return web.json_response({"error": f"Tool '{tool_name}' not found"}, status=404)
            
        tool_func = tools_by_name[tool_name]
        try:
            if inspect.iscoroutinefunction(tool_func):
                result = await tool_func(**args)
            else:
                result = tool_func(**args)
            return web.json_response({"result": result})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
        
    app.router.add_get('/tools', list_tools)
    app.router.add_post('/execute', execute_tool)
    return app

class MeshNode:
    def __init__(self, name: str, tools: list[Callable[..., Any]], port: int = 8080):
        self.name = name
        self.tools = tools
        self.port = port
        self.app = create_app(tools)
        self.advertiser = MeshAdvertiser(name, port)
        self.runner: web.AppRunner | None = None
        self.site: web.TCPSite | None = None

    async def start(self) -> None:
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, '0.0.0.0', self.port)
        await self.site.start()
        # Start advertiser once server is running
        await self.advertiser.start()

    async def stop(self) -> None:
        await self.advertiser.stop()
        if self.runner:
            await self.runner.cleanup()
