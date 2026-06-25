import json
import asyncio
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
