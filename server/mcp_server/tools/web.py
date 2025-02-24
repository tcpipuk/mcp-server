"""Provide tools to retrieve and process web content.

Defines classes and functions to fetch web content and process it in various modes:
markdown, raw text, or link extraction.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Final
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag
from bs4.filter import SoupStrainer
from mcp.shared.exceptions import McpError
from mcp.types import INTERNAL_ERROR, ErrorData
from trafilatura import extract as trafilatura_extract

from .helpers import add_error, get_request


class ProcessingMode(Enum):
    """Define valid content processing modes."""

    MARKDOWN = "markdown"
    RAW = "raw"
    LINKS = "links"

    @classmethod
    def from_str(cls, mode: str) -> ProcessingMode:
        """Create ProcessingMode from string, defaulting to RAW if invalid.

        Args:
            mode: String representation of the processing mode

        Returns:
            ProcessingMode enum value
        """
        try:
            return cls(mode.lower())
        except ValueError:
            return cls.RAW


SKIP_HREF_PREFIXES: Final = ("#", "javascript:")


@dataclass(slots=True)
class WebProcessor:
    """Handle web content retrieval and processing."""

    url: str
    mode: ProcessingMode | str = field(default=ProcessingMode.MARKDOWN)
    max_length: int = field(default=0)

    def __post_init__(self) -> None:
        """Validate and correct inputs as needed."""
        if isinstance(self.mode, str):
            self.mode = ProcessingMode.from_str(self.mode)
        self.max_length = max(self.max_length, 0)

    async def process(self) -> str:
        """Fetch and process the content according to the specified mode.

        Returns:
            Processed content as a string
        """
        content = await get_request(self.url)

        match self.mode:
            case ProcessingMode.LINKS:
                return self._format_links(self._extract_links(content))

            case ProcessingMode.MARKDOWN:
                extracted = trafilatura_extract(
                    content,
                    output_format="markdown",
                    include_formatting=True,
                    include_images=True,
                    include_links=True,
                    include_tables=True,
                    with_metadata=True,
                ) or add_error(
                    content, "Extraction to markdown failed; returning raw content", append=False
                )

            case ProcessingMode.RAW:
                extracted = content

        if self.max_length > 0 and len(extracted) > self.max_length:
            extracted = add_error(
                extracted[: self.max_length],
                f"Content truncated to {self.max_length} characters",
                append=True,
            )

        return f"Contents of {self.url}:\n\n{extracted}"

    def _get_absolute_url(self, href: str) -> str | None:
        """Get the absolute URL from a relative or absolute href.

        Returns:
            Absolute URL or None if invalid
        """
        stripped = href.strip()
        if not stripped or any(stripped.startswith(prefix) for prefix in SKIP_HREF_PREFIXES):
            return None
        return (
            stripped
            if stripped.startswith(("http://", "https://"))
            else urljoin(self.url, stripped)
        )

    def _extract_links(self, content: str) -> dict[str, str]:
        """Extract all valid links with their anchor text.

        Returns:
            Dictionary mapping each unique absolute URL to its first-found anchor text
        """
        soup = BeautifulSoup(content, "html.parser", parse_only=SoupStrainer("a", href=True))

        anchors = [a for a in soup.find_all("a", href=True) if isinstance(a, Tag)]
        valid_anchors = [
            (a, url)
            for a in anchors
            if (href := a.get("href"))
            and isinstance(href, str)
            and (url := self._get_absolute_url(href))
        ]

        url_counts = Counter(url for _, url in valid_anchors)

        return dict(
            sorted(
                {
                    url: next(
                        a.get_text(strip=True)
                        for a, anchor_url in valid_anchors
                        if anchor_url == url
                    )
                    for url in url_counts
                }.items(),
                key=lambda x: (-url_counts[x[0]], x[0]),
            )
        )

    def _format_links(self, links: dict[str, str]) -> str:
        """Format extracted links into a readable string.

        Args:
            links: Dictionary of URLs and their titles

        Returns:
            Formatted string of links

        Raises:
            McpError: If no links are found
        """
        if not links:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"No links found on {self.url} - it may require JavaScript or auth.",
                )
            )

        total_links = len(links)
        formatted_links = []
        length = 0

        for url, title in links.items():
            link_text = f"- {title}: {url}" if title else f"- {url}"
            new_length = length + len(link_text) + 1

            if self.max_length > 0 and new_length > self.max_length:
                break

            formatted_links.append(link_text)
            length = new_length

        added_count = len(formatted_links)
        header = (
            f"{added_count} of {total_links} links found on {self.url}"
            if added_count < total_links
            else f"All {total_links} links found on {self.url}"
        )

        return f"{header}\n" + "\n".join(formatted_links)


async def tool_web(url: str, mode: str = "markdown", max_length: int = 0) -> str:
    """Access and process web content from a given URL.

    Returns:
        Processed content as a string
    """
    processor = WebProcessor(url=url, mode=mode, max_length=max_length)
    return await processor.process()
