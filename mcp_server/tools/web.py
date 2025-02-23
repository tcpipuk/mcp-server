"""Tool for retrieving and processing web content."""

from __future__ import annotations

from collections import Counter
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag
from bs4.filter import SoupStrainer
from mcp.shared.exceptions import McpError
from mcp.types import INTERNAL_ERROR, ErrorData
from trafilatura import extract as trafilatura_extract

from .helpers import add_error, get_request


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
    Parse HTML content and extract internal links along with their anchor text.

    Args:
        html: Raw HTML content to parse.
        base_url: Original URL being crawled.

    Returns:
        A dictionary mapping each unique absolute URL to its first-found anchor text.
    """
    parsed_base = urlparse(base_url)
    base_netloc = parsed_base.netloc
    base_scheme = parsed_base.scheme

    all_urls: list[str] = []
    url_to_first_title: dict[str, str] = {}

    for a in BeautifulSoup(html, "html.parser", parse_only=SoupStrainer("a", href=True)):
        if not isinstance(a, Tag):
            continue

        absolute_url = parse_link(str(a.get("href", "")), base_url, base_netloc, base_scheme)
        if not absolute_url:
            continue

        all_urls.append(absolute_url)

        if absolute_url not in url_to_first_title:
            url_to_first_title[absolute_url] = a.get_text(strip=True)

    if not url_to_first_title:
        return {}

    url_counts = Counter(all_urls)
    sorted_urls = sorted(
        url_to_first_title.items(),
        key=lambda x: (-url_counts[x[0]], all_urls.index(x[0])),
    )

    return dict(sorted_urls)


async def tool_web(url: str, mode: str = "markdown", max_length: int = 0) -> str:
    """
    Access and process web content from a given URL.

    The processing behavior depends on the mode:
      - "markdown": Fetch the URL and extract content formatted as markdown.
      - "raw": Fetch the URL and return the raw content.
      - "links": Fetch the URL and extract internal links along with their anchor text,
         making sure not to break a line in the middle if a character limit is set.

    Args:
        url: The URL to process.
        mode: The content processing mode ("markdown", "raw", or "links").
        max_length: Maximum number of characters to return (0 means unlimited).

    Returns:
        A string representation of the processed content.

    Raises:
        McpError: If an invalid mode is specified or if link extraction fails.
    """
    downloaded = await get_request(url)

    if mode == "raw":
        extracted = downloaded

    elif mode == "markdown":
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

    if mode in {"raw", "markdown"}:
        if max_length > 0 and len(extracted) > max_length:
            extracted = add_error(
                extracted[:max_length],
                f"Content truncated. The output has been limited to {max_length} characters",
                append=True,
            )

        return f"Contents of {url}:\n\n{extracted}"

    if mode == "links":
        links = parse_links(downloaded, url)
        total_links = len(links)
        if not links:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"No links found on {url} - it may require JavaScript or auth.",
                ),
            )

        # Prepare link lines.
        link_lines = []
        for link_url, title in links.items():
            link_lines.append(f"- {title}: {link_url}" if title else f"- {link_url}")

        # Build output with header.
        output_lines = []
        cumulative_length = 0

        # We'll decide how many full lines can be added without exceeding max_length.
        added_count = 0
        for line in link_lines:
            # If adding this line (and a newline) would exceed max_length, stop.
            # Note: if max_length == 0 then there's no limit.
            projected_length = cumulative_length + len(line) + 1  # +1 for the newline.
            if max_length > 0 and projected_length > max_length:
                break
            output_lines.append(line)
            cumulative_length = projected_length
            added_count += 1

        # Set an appropriate header.
        header = (
            f"{added_count} of {total_links} links returned on {url}"
            if added_count < total_links
            else f"All {total_links} links found on {url}"
        )

        return f"{header}\n" + "\n".join(output_lines)

    # Catch unexpected mode
    raise McpError(
        ErrorData(
            code=INTERNAL_ERROR,
            message=(f"Invalid mode '{mode}'. Expected one of: 'markdown', 'raw', or 'links'."),
        ),
    )
