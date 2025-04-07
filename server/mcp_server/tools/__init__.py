"""Tools submodule package for mcp_server.

Provides tools that let AI assistants safely interact with external systems:

- search: Use SearXNG's search API to find information on the web
- web: Access and process web content with support for markdown conversion and link extraction

Each tool is designed to handle errors gracefully and provide clear feedback to help AI
assistants solve problems independently.
"""

from __future__ import annotations

from .search import tool_search
from .web import tool_web

__all__ = ["tool_search", "tool_web"]
