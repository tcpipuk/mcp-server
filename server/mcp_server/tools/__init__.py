"""Tools submodule package for mcp_server.

Provides tools that let AI assistants safely interact with external systems:

- sandbox: Run Python code and shell commands in an isolated environment
- web: Access and process web content with support for markdown conversion and link extraction

Each tool is designed to handle errors gracefully and provide clear feedback to help AI
assistants solve problems independently.
"""

from .sandbox import tool_sandbox
from .web import tool_web

__all__ = ["tool_sandbox", "tool_web"]
