"""Command-line entry point for the MCP fetch server.

Provides configuration options for running the fetch server, including customisation
of the User-Agent string for HTTP requests. The server runs asynchronously to handle
concurrent requests efficiently.
"""

from __future__ import annotations

from argparse import ArgumentParser
from asyncio import CancelledError, run as asyncio_run
from contextlib import suppress as contextlib_suppress
from os import environ as os_environ
from pathlib import Path

from yaml import safe_load as yaml_safe_load

from .server import MCPServer
from .tools import tool_sandbox, tool_web


def main() -> None:
    """Provide command-line entrypoint for the MCP fetch server."""
    parser = ArgumentParser(description="Give your LLM access to external tools")
    parser.add_argument("--sandbox", type=str, help="TCP host:port pair (e.g. mcp-sandbox:8080)")
    parser.add_argument("--sse-host", type=str, help="SSE listening address (e.g. 0.0.0.0)")
    parser.add_argument("--sse-port", type=int, help="SSE listening port (e.g. 3001)")
    parser.add_argument("--user-agent", type=str, help="Custom User-Agent string")
    args = parser.parse_args()

    if args.sandbox:
        os_environ["SANDBOX"] = args.sandbox
    if args.sse_host:
        os_environ["SSE_HOST"] = args.sse_host
    if args.sse_port:
        os_environ["SSE_PORT"] = str(args.sse_port)
    if args.user_agent:
        os_environ["USER_AGENT"] = args.user_agent

    config = yaml_safe_load(Path("tools.yaml").read_text(encoding="utf-8"))
    config["tools"]["web"]["method"] = tool_web
    config["tools"]["sandbox"]["method"] = tool_sandbox
    # Remove the sandbox tool if there's no sandbox
    if not os_environ.get("SANDBOX") and "sandbox" in config["tools"]:
        del config["tools"]["sandbox"]
    server = MCPServer(config)
    with contextlib_suppress(KeyboardInterrupt, CancelledError):
        asyncio_run(server.serve())


if __name__ == "__main__":
    main()
