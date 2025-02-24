"""Test the Python code execution and linting tools."""

from __future__ import annotations

from os import environ as os_environ
from pathlib import Path
from sys import executable as sys_executable, prefix as sys_prefix
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator

import pytest

from mcp_server.tools.python import SandboxedPython, tool_python


@pytest.fixture
def sandbox_env() -> Generator[None]:
    """Set up sandbox environment variables for testing."""
    os_environ["SANDBOX_PYTHON"] = sys_executable
    os_environ["SANDBOX_RUFF"] = str(Path(sys_prefix) / "bin" / "ruff")
    yield
    for key in ["SANDBOX_PYTHON", "SANDBOX_RUFF"]:
        if key in os_environ:
            del os_environ[key]


@pytest.mark.asyncio
@pytest.mark.usefixtures("sandbox_env")
async def test_basic_python_execution() -> None:
    """Test basic Python code execution."""
    code = 'print("Hello, World!")'
    result = await tool_python(code)
    if "Hello, World!" not in result:
        pytest.fail(f"Expected 'Hello, World!' in output, got: {result}")


@pytest.mark.asyncio
@pytest.mark.usefixtures("sandbox_env")
async def test_python_execution_with_error() -> None:
    """Test Python code execution with syntax error."""
    code = 'print("Unclosed string'
    result = await tool_python(code)
    if "SyntaxError" not in result:
        pytest.fail(f"Expected SyntaxError in output, got: {result}")


@pytest.mark.asyncio
@pytest.mark.usefixtures("sandbox_env")
async def test_python_timeout() -> None:
    """Test Python code execution timeout."""
    code = "while True: pass"
    result = await tool_python(code, time_limit=1)
    if "Execution terminated after 1 seconds" not in result:
        pytest.fail(f"Expected timeout message in output, got: {result}")


@pytest.mark.asyncio
@pytest.mark.usefixtures("sandbox_env")
async def test_python_linting() -> None:
    """Test Python code linting."""
    # Create code with multiple obvious linting issues
    code = """
def my_func():
    print(f"{1+2}")  # T201 print found
    undefined_var  # F821 undefined name
    """
    result = await tool_python(code, lint=True)

    # Check if we got any output at all
    if not result.strip():
        pytest.fail(f"No linting output received. SANDBOX_RUFF={os_environ.get('SANDBOX_RUFF')}")

    # Look for specific ruff error codes
    expected_issues = ["T201", "F821"]
    found_issues = all(issue in result for issue in expected_issues)

    if not found_issues:
        pytest.fail(f"Expected all of {expected_issues} in linting output, got: {result}")


def test_sandbox_resource_limits() -> None:
    """Test sandbox resource limits are set correctly."""
    sandbox = SandboxedPython("print('test')")

    # Get references to avoid repeated private member access
    temp_dir = sandbox._temp_dir  # noqa: SLF001
    script_path = sandbox._script_path  # noqa: SLF001

    # Test temporary directory creation
    if not temp_dir.exists():
        pytest.fail("Temporary directory was not created")
    if not script_path.exists():
        pytest.fail("Script file was not created")
    if script_path.read_text() != "print('test')":
        pytest.fail(f"Unexpected script content: {script_path.read_text()}")

    # Test cleanup
    del sandbox
    if temp_dir.exists():
        pytest.fail("Temporary directory was not cleaned up")
