"""
Web content retrieval tools for the MCP fetch server.

Provides tools for retrieving and processing web content:
- fetch: Get content from a URL with markdown conversion
- crawl: Extract internal links from a URL with frequency and anchor text
"""

from __future__ import annotations

from collections import Counter
from os import getenv as os_getenv
from typing import Final
from urllib.parse import urljoin, urlparse

from aiohttp import (
    ClientConnectionError,
    ClientError,
    ClientResponseError,
    ServerTimeoutError,
    TooManyRedirects,
)
from aiohttp import ClientSession as AiohttpClientSession
from bs4 import BeautifulSoup, Tag
from bs4.filter import SoupStrainer
from mcp.shared.exceptions import McpError
from mcp.types import INTERNAL_ERROR, ErrorData, Tool
from trafilatura import extract as trafilatura_extract

########################################################
# Constants
########################################################


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


########################################################
# Helpers
########################################################


def add_error(text: str, error: str, append: bool = True) -> str:
    """
    Append an error message to the end of a string.

    Args:
        text: The string to append the error to
        error: The error message to append
        append: Whether to append or prepend the error (default: True for append)

    Returns:
        The string with the error message appended
    """
    return f"{text}\n\n<error>{error}</error>" if append else f"<error>{error}</error>\n\n{text}"


async def get_request(url: str) -> str:
    """
    Extract and sort internal links from a URL.

    Fetch content asynchronously and return internal links sorted by frequency and appearance order.
    Each link includes its frequency and optionally its anchor text from first occurrence.

    Args:
        url: The URL to crawl
        max_urls: Maximum number of URLs to return (default: 10)
        include_text: Include the anchor text for each link (default: True)

    Returns:
        Formatted string listing the detected internal links

    Raises:
        McpError: If fetching or processing fails
    """
    errmsg: str = ""
    try:
        async with AiohttpClientSession(
            headers={
                "User-Agent": os_getenv("USER_AGENT")
                or "Mozilla/5.0 (X11; Linux i686; rv:135.0) Gecko/20100101 Firefox/135.0",
            },
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


def parse_link(href: str, base_url: str, base_netloc: str, base_scheme: str) -> str | None:
    """
    Parse and validate a link URL.

    Args:
        href: Raw href attribute from anchor tag
        base_url: Original URL being crawled
        base_netloc: Parsed network location of base URL
        base_scheme: Parsed scheme of base URL

    Returns:
        Absolute URL if valid internal link, None otherwise
    """
    href = str(href).strip()
    if not href or href.startswith(("#", "javascript:")):
        return None

    try:
        if href.startswith("/"):
            return f"{base_scheme}://{base_netloc}{href}"
        if href.startswith(("http://", "https://")):
            parsed_link = urlparse(href)
            if parsed_link.netloc != base_netloc:
                return None
            return href
        return urljoin(base_url, href)
    except (ValueError, TypeError):
        return None


def parse_links(html: str, base_url: str) -> dict[str, str]:
    """
    Parse HTML content and extract sorted internal links with their anchor text.

    Args:
        html: Raw HTML content to parse
        base_url: Original URL being crawled

    Returns:
        Dictionary mapping unique URLs to their first seen anchor text,
            sorted by frequency and appearance order
    """
    # Parse base URL components once
    parsed_base = urlparse(base_url)
    base_netloc = parsed_base.netloc
    base_scheme = parsed_base.scheme

    # Track all occurrences for frequency counting
    all_urls = []
    # Track first occurrence of each URL with its title
    url_to_first_title = {}

    # Process links efficiently using SoupStrainer
    for a in BeautifulSoup(html, "html.parser", parse_only=SoupStrainer("a", href=True)):
        if not isinstance(a, Tag):
            continue

        absolute_url = parse_link(str(a.get("href", "")), base_url, base_netloc, base_scheme)
        if not absolute_url:
            continue

        # Add to frequency counter
        all_urls.append(absolute_url)

        # Keep only first title for each unique URL
        if not url_to_first_title.get(absolute_url):
            url_to_first_title[absolute_url] = a.get_text(strip=True)

    if not url_to_first_title:
        return {}

    # Count all occurrences
    url_counts = Counter(all_urls)

    # Create list of (url, title) sorted by frequency and original order
    sorted_urls = sorted(
        url_to_first_title.items(),
        key=lambda x: (-url_counts[x[0]], all_urls.index(x[0])),
    )

    return dict(sorted_urls)


########################################################
# Tools
########################################################


async def tool_fetch(
    url: str,
    max_length: int = 0,
    raw: bool = False,
) -> str:
    """
    Fetch and process content from a URL.

    Args:
        url: The URL to fetch
        max_length: Maximum characters to return (0 is unlimited)
        raw: Return raw content instead of cleaning/extracting to markdown

    Returns:
        Formatted string containing the fetched content
    """
    downloaded = await get_request(url)

    if raw:
        extracted = downloaded
    else:
        extracted = trafilatura_extract(
            downloaded,
            output_format="markdown",
            include_formatting=True,
            include_images=True,
            include_links=True,
            include_tables=True,
            with_metadata=True,
        )
        if extracted is None:
            extracted = add_error(
                downloaded,
                "Extraction to markdown failed; returning raw content",
                append=False,
            )

    if max_length > 0 and len(extracted) > max_length:
        extracted = add_error(
            extracted[:max_length],
            f"Content truncated. The output has been limited to {max_length} characters",
            append=True,
        )

    return f"Contents of {url}:\n\n{extracted}"


async def tool_links(url: str, max_links: int = 100, titles: bool = True) -> str:
    """
    Extract and sort links from a URL.

    Fetch content asynchronously and return links sorted by frequency and appearance order.
    Each link includes its frequency and optionally its anchor text from first occurrence.

    Args:
        url: The URL to scrape for links
        max_links: Maximum number of URLs to process (default: 20)
        titles: Include the anchor text for each link (default: True)

    Returns:
        Formatted string listing the detected links, including count of shown vs total links

    Raises:
        McpError: If fetching or processing fails
    """
    html = await get_request(url)
    links = parse_links(html, url)

    # Raise an error if no links are found
    if not links:
        raise McpError(
            ErrorData(
                code=INTERNAL_ERROR,
                message=f"No links read on {url} - it may require JavaScript or authentication.",
            ),
        )

    total_links = len(links)
    shown_links = min(max_links, total_links)

    if shown_links < total_links:
        shown_links_str = f"{shown_links} of the {total_links} links found on {url}"
    else:
        shown_links_str = f"All {total_links} links found on {url}"

    # Format the output
    return "\n".join(
        [f"{shown_links_str}\n"]
        + [
            f"- {text}: {link_url}" if titles else f"- {link_url}"
            for link_url, text in list(links.items())[:max_links]
        ],
    )
