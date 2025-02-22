"""Tool for retrieving and processing web content."""

from __future__ import annotations
from collections import Counter
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag, SoupStrainer
from trafilatura import extract as trafilatura_extract

from mcp.shared.exceptions import McpError
from mcp.types import INTERNAL_ERROR, ErrorData
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

        absolute_url = parse_link(a.get("href", ""), base_url, base_netloc, base_scheme)
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
    Access and process web content from a URL.

    The processing behavior depends on the mode:
      - "markdown": Fetch the URL and extract content formatted as markdown.
      - "raw": Fetch the URL and return the raw content.
      - "links": Fetch the URL and extract internal links along with their anchor text.

    Args:
        url: The URL to process.
        mode: The content processing mode ("markdown", "raw", or "links").
        max_length: Maximum characters to return (0 means unlimited).

    Returns:
        A string representation of the processed content.

    Raises:
        ValueError: If an invalid mode is specified.
        McpError: If link extraction fails due to lack of detectable links.
    """
    if mode in ("raw", "markdown"):
        downloaded = await get_request(url)

        if mode == "raw":
            extracted = downloaded
        else:  # mode == "markdown"
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

    elif mode == "links":
        html = await get_request(url)
        links = parse_links(html, url)

        if not links:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"No links read on {url} - it may require JavaScript or authentication.",
                )
            )

        total_links = len(links)
        summary_line = f"All {total_links} links found on {url}\n"
        lines = [summary_line]

        for link_url, title in links.items():
            if title:
                lines.append(f"- {title}: {link_url}")
            else:
                lines.append(f"- {link_url}")

        result = "\n".join(lines)

        if max_length > 0 and len(result) > max_length:
            result = add_error(
                result[:max_length],
                f"Content truncated. The output has been limited to {max_length} characters",
                append=True,
            )

        return result

    else:
        raise ValueError(
            f"Invalid mode '{mode}'. Expected one of: 'markdown', 'raw', or 'links'."
        )
