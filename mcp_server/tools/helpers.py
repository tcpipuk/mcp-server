"""Helper functions for the MCP fetch server tools.

Provides common utilities for fetching and processing web content.
"""

from __future__ import annotations

from os import getenv as os_getenv

from aiohttp import (
    ClientConnectionError,
    ClientError,
    ClientResponseError,
    ClientSession as AiohttpClientSession,
    ServerTimeoutError,
    TooManyRedirects,
)
from mcp.shared.exceptions import McpError
from mcp.types import INTERNAL_ERROR, ErrorData


def add_error(text: str, error: str, append: bool = True) -> str:
    """Append an error message to the string.

    Args:
        text: The string to append the error to.
        error: The error message to append.
        append: Whether to append or prepend the error.

    Returns:
        The string with the error message appended.

    """
    return f"{text}\n\n<error>{error}</error>" if append else f"<error>{error}</error>\n\n{text}"


async def get_request(url: str) -> str:
    """Fetch content from a URL asynchronously.

    Args:
        url: The URL to fetch.

    Returns:
        The fetched content as a string.

    Raises:
        McpError: If fetching or processing fails.

    """
    errmsg: str = ""
    try:
        async with AiohttpClientSession(
            headers={
                "User-Agent": os_getenv("USER_AGENT")
                or "Mozilla/5.0 (X11; Linux i686; rv:135.0) Gecko/20100101 Firefox/135.0"
            }
        ) as session:
            response = await session.get(url)
            response_text = (await response.text()).strip()
            if response.ok:
                if response_text:
                    return response_text
                errmsg = f"Failed to fetch {url}: HTTP {response.status} with empty body"
            else:
                errmsg = f"Failed to fetch {url}: HTTP {response.status} ({response.reason})"
    except ServerTimeoutError as err:
        errmsg = f"Timeout while fetching {url}: {str(err)!r}"
    except ClientConnectionError as err:
        errmsg = f"Failed to connect to {url}: {str(err)!r}"
    except TooManyRedirects as err:
        errmsg = f"Too many redirects while fetching {url}: {str(err)!r}"
    except ClientResponseError as err:
        errmsg = f"HTTP error while fetching {url}: {err.status} - {err.message}"
    except ClientError as err:
        errmsg = f"Network error while fetching {url}: {str(err)!r}"
    except Exception as err:
        errmsg = f"Unexpected error while fetching {url}: {str(err)!r}"

    raise McpError(ErrorData(code=INTERNAL_ERROR, message=errmsg))
