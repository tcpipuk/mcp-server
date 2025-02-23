"""Test the Python code execution and linting tools."""

from __future__ import annotations

import os

import pytest

from mcp_server.tools.python import SandboxedPython, tool_python


@pytest.fixture
def sandbox_env():
    """Set up sandbox environment variables for testing."""
    os.environ["SANDBOX_PYTHON"] = "/usr/bin/python3"
    os.environ["SANDBOX_RUFF"] = "/usr/local/bin/ruff"
    yield
    for key in ["SANDBOX_PYTHON", "SANDBOX_RUFF"]:
        if key in os.environ:
            del os.environ[key]


@pytest.mark.asyncio
async def test_basic_python_execution(sandbox_env) -> None:
    """Test basic Python code execution."""
    code = 'print("Hello, World!")'
    result = await tool_python(code)
    if "Hello, World!" not in result:
        pytest.fail(f"Expected 'Hello, World!' in output, got: {result}")


@pytest.mark.asyncio
async def test_python_execution_with_error(sandbox_env) -> None:
    """Test Python code execution with syntax error."""
    code = 'print("Unclosed string'
    result = await tool_python(code)
    if "SyntaxError" not in result:
        pytest.fail(f"Expected SyntaxError in output, got: {result}")


@pytest.mark.asyncio
async def test_python_timeout(sandbox_env) -> None:
    """Test Python code execution timeout."""
    code = "while True: pass"
    result = await tool_python(code, time_limit=1)
    if "Execution terminated after 1 seconds" not in result:
        pytest.fail(f"Expected timeout message in output, got: {result}")


@pytest.mark.asyncio
async def test_python_linting(sandbox_env) -> None:
    """Test Python code linting."""
    code = "x=1\ny =2\nprint(x+y)"  # Contains formatting issues
    result = await tool_python(code, lint=True)
    if not any(issue in result.lower() for issue in ["style", "format", "lint"]):
        pytest.fail(f"Expected linting issues in output, got: {result}")


def test_sandbox_resource_limits() -> None:
    """Test sandbox resource limits are set correctly."""
    sandbox = SandboxedPython("print('test')")

    # Test temporary directory creation
    if not sandbox._temp_dir.exists():
        pytest.fail("Temporary directory was not created")
    if not sandbox._script_path.exists():
        pytest.fail("Script file was not created")
    if sandbox._script_path.read_text() != "print('test')":
        pytest.fail(f"Unexpected script content: {sandbox._script_path.read_text()}")

    # Test cleanup
    temp_dir = sandbox._temp_dir
    del sandbox
    if temp_dir.exists():
        pytest.fail("Temporary directory was not cleaned up")
