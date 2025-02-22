"""
Core server implementation for the MCP fetch service.

Implements a Model Context Protocol server that fetches and processes web content.
Supports both standard I/O and Server-Sent Events (SSE) transport modes, with
content extraction powered by trafilatura for efficient web scraping.
"""

from __future__ import annotations

from os import getenv as os_getenv
from typing import TYPE_CHECKING

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.server.stdio import stdio_server
from mcp.shared.exceptions import McpError
from mcp.types import INVALID_PARAMS, ErrorData, TextContent, Tool
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from uvicorn import Config as UvicornConfig
from uvicorn import Server as UvicornServer

from .tools import TOOLS, tool_fetch, tool_links, tool_python

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response


async def serve() -> None:
    """
    Run the fetch MCP server.
    """
    server = Server("mcp-fetch")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """
        Return a list of available tools.

        Returns:
            A list of Tool objects representing the available tools.
        """
        return TOOLS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        """
        Call the specified tool with provided arguments.

        Args:
            name: The name of the tool to call.
            arguments: A dictionary of arguments for the tool.

        Returns:
            A list of TextContent objects containing the fetched results.

        Raises:
            McpError: If the tool is unknown or fails to execute.
        """
        for tool_name, tool_func in {"fetch": tool_fetch, "links": tool_links, "python": tool_python}.items():
            if name == tool_name:
                try:
                    return [TextContent(type="text", text=await tool_func(**arguments))]
                except McpError as err:
                    raise McpError(ErrorData(code=INVALID_PARAMS, message=str(err))) from err
        # Otherwise, the tool is unknown
        raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Unknown tool: {name}"))

    options = server.create_initialization_options()
    sse_host, sse_port = os_getenv("SSE_HOST"), os_getenv("SSE_PORT")
    if sse_host and sse_port:
        sse = SseServerTransport("/messages/")

        async def handle_sse(request: Request) -> Response | None:
            """
            Handle the Server-Sent Events (SSE) connection.

            Args:
                request: The incoming HTTP request.
            """
            async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
                await server.run(streams[0], streams[1], options, raise_exceptions=True)

        starlette_app = Starlette(
            debug=True,
            routes=[
                Route("/sse", endpoint=handle_sse),
                Mount("/messages/", app=sse.handle_post_message),
            ],
        )

        config = UvicornConfig(
            app=starlette_app,
            host=sse_host,
            port=int(sse_port),
            log_level="info",
        )
        server_instance = UvicornServer(config)
        await server_instance.serve()
    else:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, options, raise_exceptions=True)
