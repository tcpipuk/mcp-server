"""Tools prompt definitions for the MCP fetch server.

Contains constant definitions that define available tools for fetching, linking, executing and
linting Python code.
"""

from typing import Final

from mcp.types import Tool

TOOLS: Final[list[Tool]] = [
    Tool(
        name="web",
        description=(
            "Your knowledge is out of date and potentially flawed. This tool lets you access and "
            "process web content to enhance your responses. Use this tool to:\n"
            "- Check current documentation when answering questions\n"
            "- Fetch example code or data to demonstrate solutions\n"
            "- Navigate through documentation using extracted links\n"
            "- Verify information before making recommendations"
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": (
                        "URL to access - could be a web page, API endpoint, or a file on GitHub, "
                        "etc."
                    ),
                },
                "mode": {
                    "type": "string",
                    "enum": ["markdown", "raw", "links"],
                    "default": "markdown",
                    "description": (
                        "How to process the content:\n"
                        "'markdown': Convert HTML to clean markdown (best for reading)\n"
                        "'raw': Get unprocessed content (for non-HTML such as code, JSON, etc)\n"
                        "'links': Extract hyperlinks from a webpage with anchor text, which can be "
                        "combined with the markdown mode for navigation around a website, e.g. to "
                        "locate details in a repository or documentation site."
                    ),
                },
                "max_length": {
                    "type": "integer",
                    "default": 0,
                    "description": "Limit response length in characters (zero means no limit)",
                },
            },
            "required": ["url"],
        },
    ),
    Tool(
        name="python",
        description=(
            "Execute code in a Python 3.13 sandbox to demonstrate concepts and calculate results. "
            "Instead of writing example code for users to run, use this tool directly to:\n"
            "- Show pandas/numpy operations with real data\n"
            "- Calculate results that would be tedious manually\n"
            "- Demonstrate and verify working code examples\n\n"
            "Includes: numpy, pandas, requests, bs4, aiodns, aiohttp. Can either run code or lint "
            "with Ruff. The user can see your code and its output, but it's not well-formatted, so "
            "it's good practice to briefly explain what you did and what the results show."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python code to use"},
                "timeout": {
                    "type": "integer",
                    "default": 10,
                    "description": "Timeout in seconds for execution (ignored when linting)",
                },
                "lint": {
                    "type": "boolean",
                    "default": False,
                    "description": "Lint the code using Ruff instead of executing it",
                },
            },
            "required": ["code"],
        },
    ),
]
