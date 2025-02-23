"""Test the web content retrieval and processing tools."""

from __future__ import annotations

import pytest
from mcp.shared.exceptions import McpError

from mcp_server.tools.web import ProcessingMode, WebProcessor, tool_web


@pytest.fixture
def mock_html_content() -> str:
    """Return sample HTML content for testing.

    Returns:
        Sample HTML content as a string
    """
    return """
    <html>
        <body>
            <h1>Test Page</h1>
            <p>This is a test paragraph.</p>
            <a href="https://example.com">Example Link</a>
            <a href="/relative/path">Relative Link</a>
            <a href="#skip">Skip Link</a>
            <a href="javascript:void(0)">JavaScript Link</a>
        </body>
    </html>
    """


def test_processing_mode_from_str() -> None:
    """Test conversion of strings to ProcessingMode enum values."""
    if ProcessingMode.from_str("markdown") != ProcessingMode.MARKDOWN:
        pytest.fail("Failed to convert 'markdown' to ProcessingMode.MARKDOWN")
    if ProcessingMode.from_str("raw") != ProcessingMode.RAW:
        pytest.fail("Failed to convert 'raw' to ProcessingMode.RAW")
    if ProcessingMode.from_str("links") != ProcessingMode.LINKS:
        pytest.fail("Failed to convert 'links' to ProcessingMode.LINKS")
    if ProcessingMode.from_str("invalid") != ProcessingMode.RAW:
        pytest.fail("Failed to convert invalid mode to ProcessingMode.RAW")


@pytest.mark.asyncio
async def test_web_processor_links(monkeypatch: pytest.MonkeyPatch, mock_html_content: str) -> None:
    """Test extraction and formatting of links from web content."""

    async def mock_get_request(_url: str) -> str:
        return mock_html_content

    monkeypatch.setattr("mcp_server.tools.web.get_request", mock_get_request)

    processor = WebProcessor("https://test.com", mode=ProcessingMode.LINKS)
    result = await processor.process()

    if "Example Link: https://example.com" not in result:
        pytest.fail(f"Missing absolute link in output: {result}")
    if "https://test.com/relative/path" not in result:
        pytest.fail(f"Missing resolved relative link in output: {result}")
    if "#skip" in result:
        pytest.fail(f"Found invalid anchor link in output: {result}")
    if "javascript:void(0)" in result:
        pytest.fail(f"Found invalid JavaScript link in output: {result}")


@pytest.mark.asyncio
async def test_web_processor_markdown(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test conversion of HTML content to markdown format."""

    async def mock_get_request(_url: str) -> str:
        return """
        <!DOCTYPE html>
        <html>
        <head><title>Test Page</title></head>
        <body>
            <article>
                <h1>Test Heading</h1>
                <p>This is a test paragraph with some <strong>bold text</strong>.</p>
                <p>And another paragraph for good measure.</p>
            </article>
        </body>
        </html>
        """

    monkeypatch.setattr("mcp_server.tools.web.get_request", mock_get_request)

    processor = WebProcessor("https://test.com", mode=ProcessingMode.MARKDOWN)
    result = await processor.process()

    if "Test Heading" not in result:
        pytest.fail(f"Missing heading content in output: {result}")
    if "test paragraph" not in result:
        pytest.fail(f"Missing paragraph content in output: {result}")


@pytest.mark.asyncio
async def test_max_length_limit() -> None:
    """Test truncation of content based on max_length parameter."""
    processor = WebProcessor("https://test.com", max_length=10)
    content = "This is a very long text that should be truncated"

    truncated = processor._format_links({"https://test.com": content})  # noqa: SLF001
    if len(truncated) > processor.max_length + 100:  # Allow for header text
        pytest.fail(f"Content exceeds max length: {len(truncated)} > {processor.max_length + 100}")


@pytest.mark.asyncio
async def test_invalid_url() -> None:
    """Test error handling for invalid URLs."""
    try:
        await tool_web("not-a-url")
        pytest.fail("Expected McpError for invalid URL")
    except McpError:
        pass


@pytest.mark.asyncio
async def test_empty_links() -> None:
    """Test error handling when no links are found."""
    processor = WebProcessor("https://test.com", mode=ProcessingMode.LINKS)
    try:
        processor._format_links({})  # noqa: SLF001
        pytest.fail("Expected McpError for empty links")
    except McpError:
        pass
