"""Test the web content retrieval and processing tools."""

from __future__ import annotations

import pytest
from mcp.shared.exceptions import McpError

from mcp_server.tools.web import ProcessingMode, WebProcessor, tool_web


@pytest.fixture
def mock_html_content() -> str:
    """Provide sample HTML content for testing.

    Returns:
        str: Sample HTML content.
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
    """Test ProcessingMode string conversion."""
    if ProcessingMode.from_str("markdown") != ProcessingMode.MARKDOWN:
        pytest.fail("Failed to convert 'markdown' to ProcessingMode.MARKDOWN")
    if ProcessingMode.from_str("raw") != ProcessingMode.RAW:
        pytest.fail("Failed to convert 'raw' to ProcessingMode.RAW")
    if ProcessingMode.from_str("links") != ProcessingMode.LINKS:
        pytest.fail("Failed to convert 'links' to ProcessingMode.LINKS")
    if ProcessingMode.from_str("invalid") != ProcessingMode.RAW:
        pytest.fail("Failed to convert invalid mode to ProcessingMode.RAW")


@pytest.mark.asyncio
async def test_web_processor_links(monkeypatch, mock_html_content) -> None:
    """Test link extraction from web content."""

    async def mock_get_request(_url):
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
async def test_web_processor_markdown(monkeypatch) -> None:
    """Test markdown processing of web content."""

    async def mock_get_request(_url):
        return "<h1>Test</h1><p>Content</p>"

    monkeypatch.setattr("mcp_server.tools.web.get_request", mock_get_request)

    processor = WebProcessor("https://test.com", mode=ProcessingMode.MARKDOWN)
    result = await processor.process()

    if "Test" not in result:
        pytest.fail(f"Missing heading content in output: {result}")
    if "Content" not in result:
        pytest.fail(f"Missing paragraph content in output: {result}")


@pytest.mark.asyncio
async def test_max_length_limit() -> None:
    """Test content length limiting."""
    processor = WebProcessor("https://test.com", max_length=10)
    content = "This is a very long text that should be truncated"

    truncated = processor._format_links({"https://test.com": content})
    if len(truncated) > processor.max_length + 100:  # Allow for header text
        pytest.fail(f"Content exceeds max length: {len(truncated)} > {processor.max_length + 100}")


@pytest.mark.asyncio
async def test_invalid_url() -> None:
    """Test handling of invalid URLs."""
    try:
        await tool_web("not-a-url")
        pytest.fail("Expected McpError for invalid URL")
    except McpError:
        pass


@pytest.mark.asyncio
async def test_empty_links() -> None:
    """Test handling of pages with no links."""
    processor = WebProcessor("https://test.com", mode=ProcessingMode.LINKS)
    try:
        processor._format_links({})
        pytest.fail("Expected McpError for empty links")
    except McpError:
        pass
