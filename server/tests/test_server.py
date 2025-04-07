"""Test the MCP server initialization and configuration."""

from __future__ import annotations

from os import environ as os_environ
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import pytest_asyncio
from yaml import dump as yaml_dump, safe_load as yaml_safe_load

from mcp_server.server import MCPServer
from mcp_server.tools import tool_search, tool_web

if TYPE_CHECKING:
    from collections.abc import Generator

# Constants for testing
MAX_DESCRIPTION_LENGTH = 1024


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
            "search": {
                "description": "Test Search tool",
                "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}},
            },
            "web": {
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
    os_environ["SANDBOX"] = "127.0.0.1:8080"
    os_environ["SSE_HOST"] = "127.0.0.1"
    os_environ["SSE_PORT"] = "3001"
    os_environ["USER_AGENT"] = "TestAgent/1.0"
    yield
    for key in ["SANDBOX", "SSE_HOST", "SSE_PORT", "USER_AGENT"]:
        if key in os_environ:
            del os_environ[key]


@pytest_asyncio.fixture
async def server(mock_yaml_file: Path) -> MCPServer:
    """Create a test server instance.

    Args:
        mock_yaml_file: Path to test YAML configuration

    Returns:
        Configured MCPServer instance
    """
    config = yaml_safe_load(mock_yaml_file.read_text(encoding="utf-8"))
    config["tools"]["search"]["method"] = tool_search
    config["tools"]["web"]["method"] = tool_web
    return MCPServer(config)


def test_yaml_loading(mock_yaml_file: Path) -> None:
    """Test that the YAML configuration can be loaded correctly."""
    config = yaml_safe_load(mock_yaml_file.read_text(encoding="utf-8"))

    if "tools" not in config:
        pytest.fail("Missing 'tools' section in config")
    if "search" not in config["tools"]:
        pytest.fail("Missing 'search' tool in config")
    if "web" not in config["tools"]:
        pytest.fail("Missing 'web' tool in config")

    for tool_name in ("search", "web"):
        if "description" not in config["tools"][tool_name]:
            pytest.fail(f"Missing 'description' in {tool_name} tool config")

        description_length = len(config["tools"][tool_name]["description"])
        if description_length > MAX_DESCRIPTION_LENGTH:
            pytest.fail(
                f"Description for tool '{tool_name}' is too long: "
                f"{description_length} characters (max {MAX_DESCRIPTION_LENGTH})"
            )


def test_server_initialisation(server: MCPServer) -> None:
    """Test that the server initializes with the correct tools."""
    if not hasattr(server, "tools"):
        pytest.fail("Server missing tools attribute")
    tool_names = {tool.name for tool in server.tools}
    if "search" not in tool_names:
        pytest.fail("Server missing search tool")
    if "web" not in tool_names:
        pytest.fail("Server missing web tool")

    search_tool_config = server.config["tools"]["search"]
    web_tool_config = server.config["tools"]["web"]

    if search_tool_config.get("method") != tool_search:
        pytest.fail("Search tool has incorrect method")
    if web_tool_config.get("method") != tool_web:
        pytest.fail("Web tool has incorrect method")


@pytest.mark.asyncio
@pytest.mark.usefixtures("server_env")
async def test_server_environment() -> None:
    """Test that environment variables are correctly set."""
    if os_environ["SANDBOX"] != "127.0.0.1:8080":
        pytest.fail(f"Incorrect SANDBOX: {os_environ['SANDBOX']}")
    if os_environ["SSE_HOST"] != "127.0.0.1":
        pytest.fail(f"Incorrect SSE_HOST: {os_environ['SSE_HOST']}")
    if os_environ["SSE_PORT"] != "3001":
        pytest.fail(f"Incorrect SSE_PORT: {os_environ['SSE_PORT']}")
    if os_environ["USER_AGENT"] != "TestAgent/1.0":
        pytest.fail(f"Incorrect USER_AGENT: {os_environ['USER_AGENT']}")


def test_live_tools_yaml_file() -> None:
    """Test that the live tools.yaml file is readable and contains required keys."""
    # Determine the project root (assumed one level above the tests directory)
    project_root = Path(__file__).parent.parent
    tools_yaml_path = project_root / "tools.yaml"
    if not tools_yaml_path.exists():
        pytest.fail(f"tools.yaml file not found at {tools_yaml_path}")

    config = yaml_safe_load(tools_yaml_path.read_text(encoding="utf-8"))

    if "tools" not in config:
        pytest.fail("Missing 'tools' section in live tools.yaml")

    for tool in ("search", "web"):
        if tool not in config["tools"]:
            pytest.fail(f"Missing '{tool}' configuration in live tools.yaml")
        if "inputSchema" not in config["tools"][tool]:
            pytest.fail(f"Missing 'inputSchema' for tool '{tool}' in live tools.yaml")


def test_tool_description_length() -> None:
    """Test that tool descriptions don't exceed the OpenAI API limit of 1024 characters."""
    # Determine the project root (assumed one level above the tests directory)
    project_root = Path(__file__).parent.parent
    tools_yaml_path = project_root / "tools.yaml"
    if not tools_yaml_path.exists():
        pytest.fail(f"tools.yaml file not found at {tools_yaml_path}")

    config = yaml_safe_load(tools_yaml_path.read_text(encoding="utf-8"))

    if "tools" not in config:
        pytest.fail("Missing 'tools' section in tools.yaml")

    for tool_name, tool_config in config["tools"].items():
        if "description" not in tool_config:
            pytest.fail(f"Missing 'description' for tool '{tool_name}' in tools.yaml")

        description_length = len(tool_config["description"])
        if description_length > MAX_DESCRIPTION_LENGTH:
            pytest.fail(
                f"Description for tool '{tool_name}' is too long: "
                f"{description_length} characters (max {MAX_DESCRIPTION_LENGTH})"
            )
