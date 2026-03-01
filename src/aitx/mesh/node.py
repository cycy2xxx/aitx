from typing import Callable, Any
from aiohttp import web

def create_app(tools: list[Callable[..., Any]]) -> web.Application:
    app = web.Application()
    
    async def list_tools(request: web.Request) -> web.Response:
        return web.json_response({"tools": [t.__name__ for t in tools]})
        
    app.router.add_get('/tools', list_tools)
    return app

class MeshNode:
    def __init__(self, tools: list[Callable[..., Any]], port: int = 0):
        self.tools = tools
        self.port = port
