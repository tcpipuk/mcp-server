"""
Tools prompt definitions for the MCP fetch server.

Contains constant definitions that define available tools for fetching, linking, executing and
linting Python code.
"""

from typing import Final

from mcp.types import Tool

TOOLS: Final[list[Tool]] = [
    Tool(
        name="web",
        description=(
            "Use to access the internet when up-to-date information may help. You can navigate "
            "documentation, or fetch code and data from the web, so use it whenever fresh "
            "information from the internet could potentially improve the accuracy of your answer "
            "to the user."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": (
                        "The URL to access. This can be any public web address, an API GET "
                        "endpoint, or even a location of a text/code file on GitHub, etc."
                    ),
                },
                "mode": {
                    "type": "string",
                    "enum": ["markdown", "raw", "links"],
                    "default": "markdown",
                    "description": (
                        "Determines how to process the content:\n"
                        "'markdown' formats a HTML page into efficient markdown, removing headers, "
                        "navigation, ads, etc, so ideal for normal web pages;\n"
                        "'raw' returns the unprocessed content, if you need to see raw HTML, or "
                        "code, XML, JSON, etc.;\n"
                        "'links' extracts a list of hyperlinks (with anchor text) from a HTML "
                        "page, which can help you understand site structure or navigate "
                        "documentation."
                    ),
                },
                "max_length": {
                    "type": "integer",
                    "default": 0,
                    "description": (
                        "Limits the number of characters returned. A value of 0 means no limit. "
                        "You could use this if you're only interested in the start of a file, but "
                        "it's better to err on the side of having more context."
                    ),
                },
            },
            "required": ["url", "mode"],
        },
    ),
    Tool(
        name="python",
        description=(
            "Execute or lint Python code in a resource-limited sandbox.\n"
            "It has internet access, with aiodns, aiohttp, bs4, numpy, pandas, and requests "
            "installed, so you can now test and solve a number of problems without needing to "
            "directly calculate it yourself.\n"
            "Depending on your input parameters, this tool either runs the code or lints with "
            "Ruff, so you can test code before running, or use Ruff to help debugging if you get "
            "errors. The user can see the code you've submitted and the raw returned response, but "
            "it's good etiquette to briefly summarise after using this tool what you asked for and "
            "got back."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to use",
                },
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
