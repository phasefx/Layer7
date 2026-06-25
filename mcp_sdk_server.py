import json
import asyncio
import threading
from typing import Any
import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

class SDKMCPServer:
    """
    Adapter for running Layer7 via the official Anthropic MCP SDK.
    Uses asyncio threads to run the synchronous Layer7 engine.
    """
    def __init__(self, registry):
        self.registry = registry
        self.app = Server("Layer7")
        self._lock = threading.Lock()

        @self.app.list_tools()
        async def list_tools() -> list[types.Tool]:
            mcp_tools = []
            for tool_def in self.registry.get_tools():
                mcp_tools.append(
                    types.Tool(
                        name=tool_def["name"],
                        description=tool_def.get("description", ""),
                        inputSchema=tool_def.get("inputSchema", {})
                    )
                )
            return mcp_tools

        @self.app.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
            # Run the synchronous tool execution in a background thread
            # so we don't block the asyncio event loop handling MCP messages.
            def _run():
                with self._lock:
                    try:
                        return self.registry.call_tool(name, arguments)
                    except Exception as e:
                        return {"error": str(e)}

            res = await asyncio.to_thread(_run)
            return [types.TextContent(type="text", text=json.dumps(res, indent=2))]

    def serve_stdio(self):
        """
        Runs the MCP SDK stdio server using asyncio.run.
        """
        async def _run_server():
            async with stdio_server() as (read_stream, write_stream):
                await self.app.run(
                    read_stream,
                    write_stream,
                    self.app.create_initialization_options()
                )

        asyncio.run(_run_server())

    def serve_sse(self, host: str, port: int):
        """
        Runs the MCP SDK SSE server over HTTP using Starlette and Uvicorn.
        """
        try:
            from mcp.server.sse import SseServerTransport
            from starlette.applications import Starlette
            from starlette.routing import Route
            from starlette.middleware import Middleware
            from starlette.middleware.cors import CORSMiddleware
            import uvicorn
        except ImportError:
            print("Error: starlette and uvicorn are required for SSE support.")
            print("Please install them with: pip install starlette uvicorn")
            import sys
            sys.exit(1)

        sse = SseServerTransport("/sse")

        async def handle_sse(request):
            async with sse.connect_sse(
                request.scope, request.receive, request._send
            ) as streams:
                await self.app.run(
                    streams[0],
                    streams[1],
                    self.app.create_initialization_options()
                )

        async def handle_messages(request):
            await sse.handle_post_message(request.scope, request.receive, request._send)

        middleware = [
            Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
        ]

        starlette_app = Starlette(
            debug=True,
            routes=[
                Route("/sse", endpoint=handle_sse, methods=["GET"]),
                Route("/sse", endpoint=handle_messages, methods=["POST"]),
            ],
            middleware=middleware,
        )

        print(f"Starting Layer7 MCP server on http://{host}:{port}/sse")
        uvicorn.run(starlette_app, host=host, port=port)
