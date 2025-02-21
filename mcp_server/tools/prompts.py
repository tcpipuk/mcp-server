"""
Tools prompt definitions for the MCP fetch server.

Contains constant definitions that define available tools for fetching and linking content.
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
            "which may provide helpful context. You could then `fetch` URLs to see the content,"
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
]
