"""
Define the links tool for extracting and formatting webpage links.

Provides a function to scrape and process links from a URL.
"""

from __future__ import annotations

from collections import Counter
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag
from bs4.filter import SoupStrainer
from mcp.shared.exceptions import McpError
from mcp.types import INTERNAL_ERROR, ErrorData

from .helpers import get_request


def parse_link(href: str, base_url: str, base_netloc: str, base_scheme: str) -> str | None:
    """
    Parse and validate an anchor tag's href attribute.

    Args:
        href: Raw href attribute from an anchor tag.
        base_url: Original URL being crawled.
        base_netloc: Network location of the base URL.
        base_scheme: Scheme of the base URL.

    Returns:
        An absolute URL if valid and internal; otherwise, None.
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
    Parse HTML content and extract internal links with their anchor text.

    Args:
        html: Raw HTML content to parse.
        base_url: Original URL being crawled.

    Returns:
        A dictionary mapping unique URLs to their first seen anchor text.
    """
    parsed_base = urlparse(base_url)
    base_netloc = parsed_base.netloc
    base_scheme = parsed_base.scheme

    all_urls = []
    url_to_first_title = {}

    for a in BeautifulSoup(html, "html.parser", parse_only=SoupStrainer("a", href=True)):
        if not isinstance(a, Tag):
            continue

        absolute_url = parse_link(str(a.get("href", "")), base_url, base_netloc, base_scheme)
        if not absolute_url:
            continue

        all_urls.append(absolute_url)

        if not url_to_first_title.get(absolute_url):
            url_to_first_title[absolute_url] = a.get_text(strip=True)

    if not url_to_first_title:
        return {}

    url_counts = Counter(all_urls)

    sorted_urls = sorted(
        url_to_first_title.items(),
        key=lambda x: (-url_counts[x[0]], all_urls.index(x[0])),
    )

    return dict(sorted_urls)


async def tool_links(url: str, max_links: int = 100, titles: bool = True) -> str:
    """
    Extract and sort links from a URL.

    Args:
        url: The URL to scrape for links.
        max_links: Maximum number of URLs to return (default is 100).
        titles: Include the anchor text for each link (default is True).

    Returns:
        A formatted string listing the detected links, including a count summary.

    Raises:
        McpError: If fetching or processing fails.
    """
    html = await get_request(url)
    links = parse_links(html, url)

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

    return "\n".join(
        [f"{shown_links_str}\n"]
        + [
            f"- {text}: {link_url}" if titles else f"- {link_url}"
            for link_url, text in list(links.items())[:max_links]
        ],
    )
