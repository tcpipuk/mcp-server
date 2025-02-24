"""Test the MCP server initialization and configuration."""

from __future__ import annotations

from os import environ as os_environ
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from yaml import dump as yaml_dump, safe_load as yaml_safe_load

from mcp_server.server import MCPServer
from mcp_server.tools import tool_sandbox, tool_web

if TYPE_CHECKING:
    from collections.abc import Generator


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
                "description": "Test Python tool",
                "inputSchema": {"type": "object", "properties": {"code": {"type": "string"}}},
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


@pytest.fixture
async def server(mock_yaml_file: Path) -> MCPServer:
    """Create a test server instance.

    Args:
        mock_yaml_file: Path to test YAML configuration

    Returns:
        Configured MCPServer instance
    """
    config = yaml_safe_load(mock_yaml_file.read_text(encoding="utf-8"))
    config["tools"]["sandbox"]["method"] = tool_sandbox
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
    if "description" not in config["tools"]["python"]:
        pytest.fail("Missing 'description' in python tool config")
    if "description" not in config["tools"]["web"]:
        pytest.fail("Missing 'description' in web tool config")


def test_server_initialisation(server: MCPServer) -> None:
    """Test that the server initializes with the correct tools."""
    if not hasattr(server, "tools"):
        pytest.fail("Server missing tools attribute")
    tool_names = {tool.name for tool in server.tools}
    if "sandbox" not in tool_names:
        pytest.fail("Server missing sandbox tool")
    if "web" not in tool_names:
        pytest.fail("Server missing web tool")

    sandbox_tool_config = server.config["tools"]["sandbox"]
    web_tool_config = server.config["tools"]["web"]

    if sandbox_tool_config.get("method") != tool_sandbox:
        pytest.fail("Sandbox tool has incorrect method")
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

    for tool in ("python", "web"):
        if tool not in config["tools"]:
            pytest.fail(f"Missing '{tool}' configuration in live tools.yaml")
        if "inputSchema" not in config["tools"][tool]:
            pytest.fail(f"Missing 'inputSchema' for tool '{tool}' in live tools.yaml")
