"""Test the MCP server initialization and configuration."""

from __future__ import annotations

from os import environ as os_environ
from typing import TYPE_CHECKING

import pytest
from yaml import dump as yaml_dump, safe_load as yaml_safe_load

from mcp_server.server import MCPServer
from mcp_server.tools import tool_python, tool_web

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path


@pytest.fixture
def mock_yaml_file(tmp_path: Path) -> Path:
    """Create a temporary tools.yaml file for testing.

    Args:
        tmp_path: Pytest fixture providing temporary directory

    Returns:
        Path to the temporary YAML file
    """
    yaml_content = {
        "tools": {
            "python": {
                "name": "python",
                "description": "Test Python tool",
                "inputSchema": {"type": "object", "properties": {"code": {"type": "string"}}},
            },
            "web": {
                "name": "web",
                "description": "Test Web tool",
                "inputSchema": {"type": "object", "properties": {"url": {"type": "string"}}},
            },
        }
    }

    yaml_path = tmp_path / "tools.yaml"
    yaml_path.write_text(yaml_dump(yaml_content), encoding="utf-8")
    return yaml_path


@pytest.fixture
def server_env() -> Generator[None]:
    """Set up server environment variables for testing."""
    os_environ["SSE_HOST"] = "127.0.0.1"
    os_environ["SSE_PORT"] = "3001"
    os_environ["USER_AGENT"] = "TestAgent/1.0"
    yield
    for key in ["SSE_HOST", "SSE_PORT", "USER_AGENT"]:
        if key in os_environ:
            del os_environ[key]


@pytest.fixture
async def server(mock_yaml_file: Path) -> MCPServer:
    """Create a test server instance.

    Args:
        mock_yaml_file: Path to test YAML configuration

    Returns:
        Configured MCPServer instance
    """
    config = yaml_safe_load(mock_yaml_file.read_text(encoding="utf-8"))
    config["tools"]["python"]["method"] = tool_python
    config["tools"]["web"]["method"] = tool_web
    return MCPServer(config)


def test_yaml_loading(mock_yaml_file: Path) -> None:
    """Test that the YAML configuration can be loaded correctly."""
    config = yaml_safe_load(mock_yaml_file.read_text(encoding="utf-8"))

    if "tools" not in config:
        pytest.fail("Missing 'tools' section in config")
    if "python" not in config["tools"]:
        pytest.fail("Missing 'python' tool in config")
    if "web" not in config["tools"]:
        pytest.fail("Missing 'web' tool in config")
    if config["tools"]["python"]["name"] != "python":
        pytest.fail(f"Incorrect python tool name: {config['tools']['python']['name']}")
    if config["tools"]["web"]["name"] != "web":
        pytest.fail(f"Incorrect web tool name: {config['tools']['web']['name']}")


def test_server_initialisation(server: MCPServer) -> None:
    """Test that the server initializes with the correct tools."""
    if not hasattr(server, "tools"):
        pytest.fail("Server missing tools attribute")
    if "python" not in server.tools:
        pytest.fail("Server missing python tool")
    if "web" not in server.tools:
        pytest.fail("Server missing web tool")

    python_tool = server.config["tools"]["python"]
    web_tool = server.config["tools"]["web"]

    if python_tool["method"] != tool_python:
        pytest.fail("Python tool has incorrect method")
    if web_tool["method"] != tool_web:
        pytest.fail("Web tool has incorrect method")


@pytest.mark.asyncio
async def test_server_environment(server_env: None) -> None:
    """Test that environment variables are correctly set."""
    if os_environ["SSE_HOST"] != "127.0.0.1":
        pytest.fail(f"Incorrect SSE_HOST: {os_environ['SSE_HOST']}")
    if os_environ["SSE_PORT"] != "3001":
        pytest.fail(f"Incorrect SSE_PORT: {os_environ['SSE_PORT']}")
    if os_environ["USER_AGENT"] != "TestAgent/1.0":
        pytest.fail(f"Incorrect USER_AGENT: {os_environ['USER_AGENT']}")
