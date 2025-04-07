"""Core MCPServer implementation for the MCP fetch service.

Provides a generic MCPServer class for serving MCP requests. Allows drop-in tool support by mapping
tool functions to configuration loaded from an external YAML file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from os import getenv as os_getenv
from pathlib import Path
from typing import TYPE_CHECKING, Any

from mcp.server import Server as BaseMCPServer
from mcp.server.sse import SseServerTransport
from mcp.server.stdio import stdio_server
from mcp.shared.exceptions import McpError
from mcp.types import INVALID_PARAMS, ErrorData, TextContent, Tool
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from uvicorn import Config as UvicornConfig, Server as UvicornServer

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response

# Default path for tool configuration YAML file
DEFAULT_TOOL_CONFIG_PATH = Path(__file__).parent / "tools.yaml"


@dataclass(slots=True)
class MCPServer:
    """Define a generic MCP server class with drop-in tool support."""

    config: dict[str, Any]
    server: BaseMCPServer = field(init=False)
    server_name: str = field(default="mcp-server")
    tools: list[Tool] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Initialise the MCPServer."""
        if self.config.get("server", {}).get("name"):
            self.server_name = self.config["server"]["name"]
        # Create MCP server instance
        self.server = BaseMCPServer(self.server_name)
        # Build the tool registry and tool list
        self.tools = [
            Tool(name=name, **{k: v for k, v in tool.items() if k != "method"})
            for name, tool in self.config["tools"].items()
        ]
        # Register the tool listing/calling methods
        self.server.list_tools()(self.list_tools)
        self.server.call_tool()(self.call_tool)

    async def list_tools(self) -> list[Tool]:
        """Return a list of available tools.

        Returns:
            A list of Tool objects representing the available tools.
        """
        return self.tools

    async def call_tool(self, name: str, arguments: dict) -> list[TextContent]:
        """Call the tool specified by name with provided arguments.

        Returns:
            A list of TextContent objects containing the tool's result

        Raises:
            McpError: If the tool is unknown or fails to execute
        """
        if name not in self.config["tools"]:
            raise McpError(
                ErrorData(
                    code=INVALID_PARAMS, message=f"Tool '{name}' isn't available on this server anymore"
                )
            )
        if "method" not in self.config["tools"][name]:
            raise McpError(
                ErrorData(
                    code=INVALID_PARAMS,
                    message=(
                        f"Tool '{name}' has no registered method: inform the user that their MCP "
                        "server requires configuration to provide a function for this tool."
                    ),
                )
            )
        try:
            result = await self.config["tools"][name]["method"](**arguments)
            return [TextContent(type="text", text=result)]
        except McpError as err:
            raise McpError(ErrorData(code=INVALID_PARAMS, message=str(err))) from err

    async def serve(self) -> None:
        """Run the MCP server, using either SSE or stdio mode."""
        options = self.server.create_initialization_options()
        sse_host, sse_port = os_getenv("SSE_HOST"), os_getenv("SSE_PORT")
        if sse_host and sse_port:
            sse = SseServerTransport("/messages/")

            async def _handle_sse(request: Request) -> Response | None:
                """Handle incoming SSE connection."""
                async with sse.connect_sse(
                    request.scope,
                    request.receive,
                    request._send,  # noqa: SLF001
                ) as streams:
                    await self.server.run(streams[0], streams[1], options, raise_exceptions=True)

            starlette_app = Starlette(
                debug=True,
                routes=[
                    Route("/sse", endpoint=_handle_sse),
                    Mount("/messages/", app=sse.handle_post_message),
                ],
            )

            config = UvicornConfig(app=starlette_app, host=sse_host, port=int(sse_port), log_level="info")
            server_instance = UvicornServer(config)
            await server_instance.serve()
        else:
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(read_stream, write_stream, options, raise_exceptions=True)
