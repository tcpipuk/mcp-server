"""Provide a tool to query a SearXNG instance.

Allows AI assistants to search the web using a configured SearXNG instance,
leveraging its API for targeted and filtered searches.
"""

from __future__ import annotations

from os import getenv as os_getenv
from typing import Any
from urllib.parse import urlencode

from mcp.shared.exceptions import McpError
from mcp.types import INTERNAL_ERROR, INVALID_PARAMS, ErrorData

from .helpers import get_request

# Allowed parameters for the SearXNG API, excluding 'q' which is handled separately.
ALLOWED_PARAMS: set[str] = {
    "categories",
    "engines",
    "language",
    "pageno",
    "time_range",
    "format",
    "safesearch",
}


async def tool_search(q: str, **kwargs: Any) -> str:
    """Query a SearXNG instance using its Search API.

    Args:
        q: The search query string.
        **kwargs: Additional optional parameters for the SearXNG API
                  (categories, engines, language, pageno, time_range, format, safesearch).

    Returns:
        The search results as a string (content depends on the 'format' parameter).

    Raises:
        McpError: If the SEARXNG_QUERY_URL environment variable is not set,
                  if invalid parameters are provided, or if the request fails.
    """
    searxng_url = os_getenv("SEARXNG_QUERY_URL")
    if not searxng_url:
        raise McpError(
            ErrorData(code=INTERNAL_ERROR, message="SearXNG query URL is not configured on the server.")
        )

    # Filter out any provided kwargs that are not valid SearXNG parameters
    search_params = {k: v for k, v in kwargs.items() if k in ALLOWED_PARAMS and v is not None}
    search_params["q"] = q  # Add the mandatory query

    # Default format to json if not specified, as it's often easiest for programmatic use
    if "format" not in search_params:
        search_params["format"] = "json"

    # Validate format if provided
    if search_params["format"] not in ("json", "csv", "rss"):
        raise McpError(
            ErrorData(
                code=INVALID_PARAMS,
                message=f"Invalid format '{search_params['format']}'. Must be 'json', 'csv', or 'rss'.",
            )
        )

    query_string = urlencode(search_params)
    full_url = f"{searxng_url}?{query_string}"

    try:
        # Use the existing get_request helper
        result = await get_request(full_url)
        # Simple check for empty result which might indicate no results found
        # depending on the format requested. SearXNG JSON format includes metadata even for no results.
        if not result and search_params["format"] != "json":
            return f"No results found for query '{q}' with specified parameters."
    except McpError as e:
        # Re-raise McpError to ensure it's handled correctly by the server
        raise McpError(ErrorData(code=e.data.code, message=f"SearXNG query failed: {e.data.message}")) from e
    except Exception as e:
        # Catch any other unexpected errors during the request
        raise McpError(
            ErrorData(code=INTERNAL_ERROR, message=f"Unexpected error during SearXNG query: {e!r}")
        ) from e
    else:
        return result
