"""MCP Fetch Server module for handling web content retrieval.

This module provides HTTP fetching capabilities for the Model Context Protocol (MCP) framework,
allowing models to retrieve and process web content in a controlled manner.
"""

from .__main__ import main
from .server import MCPServer

__all__ = ["MCPServer", "main"]
