"""
Define the fetch tool for retrieving and processing web content.

Provides a function to fetch content from a URL and optionally extract and clean it to markdown.
"""

from trafilatura import extract as trafilatura_extract

from .helpers import add_error, get_request


async def tool_fetch(url: str, max_length: int = 0, raw: bool = False) -> str:
    """
    Fetch and process content from a URL.

    Args:
        url: The URL to fetch.
        max_length: Maximum characters to return (0 for unlimited).
        raw: Return raw content instead of cleaning/extracting to markdown.

    Returns:
        A formatted string containing the fetched content.
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
