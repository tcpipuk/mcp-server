"""
Tools prompt definitions for the MCP fetch server.

Contains constant definitions that define available tools for fetching,
linking, executing and linting Python code.
"""

from typing import Final

from mcp.types import Tool

TOOLS: Final[list[Tool]] = [
    Tool(
        name="fetch",
        description=(
            "Read content from a real internet URL. By default, this tool attempts to clean pages "
            "and format in markdown for efficiency, removing non-content like navigation or ads to "
            "make your job easier. If asked to find something on a website, you can combine with "
            "the `links` tool to explore a website to find the content you need."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to fetch"},
                "max_length": {
                    "type": "integer",
                    "default": 0,
                    "description": "Max characters to return (0 is unlimited)",
                },
                "raw": {
                    "type": "boolean",
                    "default": False,
                    "description": "Get raw content instead of cleaning/extracting to markdown",
                },
            },
            "required": ["url"],
        },
    ),
    Tool(
        name="links",
        description=(
            "Fetch a list of links from a webpage. Useful to discover related pages and understand "
            "the structure when exploring a website. By default, includes the text from the link, "
            "which may provide helpful context. You could then `fetch` URLs to see the content, "
            "as you're not limited in how many tools you can use."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to scrape for links"},
                "max_links": {
                    "type": "integer",
                    "default": 100,
                    "description": "Maximum number of URLs to return",
                },
                "titles": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include the anchor text for each link",
                },
            },
            "required": ["url"],
        },
    ),
    Tool(
        name="python",
        description=(
            "Execute or lint Python code in a resource-limited sandbox. "
            "It has internet access, with aiodns, aiohttp, bs4, numpy, pandas, and "
            "requests installed, so you can now test and solve a number of problems "
            "without needing to directly calculate it yourself. Depending on "
            "your input parameters, this tool either runs the code or lints with Ruff, "
            "so you can test code before running, or use Ruff to help debugging if "
            "you get errors. The user can see the code you've submitted and the "
            "raw returned response, but it's good etiquette to briefly summarise after "
            "using this tool what you asked for and got back."
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
