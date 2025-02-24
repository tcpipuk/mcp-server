"""Test the sandbox tool for executing shell commands over TCP.

Tests include:
- Connection error when SANDBOX_HOST is not set.
- Successful command execution.
- Handling of command timeouts.
- Execution using a screen session.
"""

from collections.abc import Callable

import pytest
from mcp.shared.exceptions import McpError

from mcp_server.tools.sandbox import ShellConnection, tool_sandbox


class DummyStreamReader:
    """Dummy stream reader simulating a preset list of output lines."""

    def __init__(self, lines: list[bytes]) -> None:
        """Initialise with a list of bytes lines."""
        self._lines = iter(lines)

    async def readline(self) -> bytes:
        """Return the next line from the preset list."""
        try:
            return next(self._lines)
        except StopIteration:
            return b""


class DummyStreamWriter:
    """Dummy stream writer that captures written data."""

    def __init__(self) -> None:
        """Initialise with an empty buffer."""
        self.buffer = b""

    def write(self, data: bytes) -> None:
        """Append written data to the buffer."""
        self.buffer += data

    async def drain(self) -> None:
        """Simulate drain (no-op)."""

    def close(self) -> None:
        """Simulate closing the writer."""
        self.closed = True

    async def wait_closed(self) -> None:
        """Simulate waiting for the writer to close."""


def make_fake_open_connection(lines: list[bytes]) -> tuple[Callable, DummyStreamWriter]:
    """Return a fake open_connection function along with its DummyStreamWriter.

    Args:
        lines: List of bytes lines to initialise the DummyStreamReader.

    Returns:
        A tuple of (fake_open_connection, dummy_writer)
    """
    dummy_writer = DummyStreamWriter()

    async def fake_open_connection(
        host: str, port: int
    ) -> tuple[DummyStreamReader, DummyStreamWriter]:
        reader = DummyStreamReader(lines)
        return reader, dummy_writer

    return fake_open_connection, dummy_writer


@pytest.mark.asyncio
async def test_connect_without_sandbox_host(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that connection fails when SANDBOX_HOST is not set."""
    monkeypatch.delenv("SANDBOX_HOST", raising=False)
    with pytest.raises(McpError) as excinfo:
        await ShellConnection.connect()
    if "SANDBOX_HOST environment variable is not set" not in str(excinfo.value):
        pytest.fail(
            "Expected error message about missing SANDBOX_HOST, but got: " + str(excinfo.value)
        )


@pytest.mark.asyncio
async def test_tool_sandbox_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test a successful command execution using tool_sandbox."""
    # Set the environment variable for connection.
    monkeypatch.setenv("SANDBOX_HOST", "127.0.0.1:1234")

    async def fake_open_connection(
        host: str, port: int
    ) -> tuple[DummyStreamReader, DummyStreamWriter]:
        # Simulate output lines ending with a prompt.
        lines = [b"output line 1\n", b"output line 2\n", b"$ "]
        return DummyStreamReader(lines), DummyStreamWriter()

    monkeypatch.setattr("mcp_server.tools.sandbox.asyncio_open_connection", fake_open_connection)
    result = await tool_sandbox("echo hello", time_limit=2)
    if "Exit code: 0" not in result:
        pytest.fail("Expected exit code 0 in result, got: " + result)
    if "output line 1" not in result:
        pytest.fail("Expected 'output line 1' in result, got: " + result)
    if "output line 2" not in result:
        pytest.fail("Expected 'output line 2' in result, got: " + result)


@pytest.mark.asyncio
async def test_run_command_timeout(
    monkeypatch: pytest.MonkeyPatch, sandbox_server: tuple[str, int]
) -> None:
    """Test that a command timing out produces the expected timeout output."""
    host, port = sandbox_server
    monkeypatch.setenv("SANDBOX_HOST", f"{host}:{port}")

    # Use a real command that will timeout
    result = await tool_sandbox("sleep 10", time_limit=1)
    if "Command timed out" not in result:
        pytest.fail("Expected 'Command timed out' in result, got: " + result)
    if "Exit code: 1" not in result:
        pytest.fail("Expected 'Exit code: 1' in result, got: " + result)


@pytest.mark.asyncio
async def test_run_command_with_screen(monkeypatch: pytest.MonkeyPatch, sandbox_server) -> None:
    """Test that running a command with a screen session works correctly."""
    host, port = sandbox_server
    monkeypatch.setenv("SANDBOX_HOST", f"{host}:{port}")

    # Test creating and using a screen session
    shell = await ShellConnection.connect()
    result = await shell.run_command(
        "screen -S test_screen -dm bash -c 'echo testing screen'", time_limit=2
    )
    if result.exit_code != 0:
        pytest.fail(f"Expected exit code 0, got: {result.exit_code}")

    # Verify we can read the screen output
    result = await shell.run_command(
        "screen -S test_screen -X hardcopy /tmp/screen.log", time_limit=2
    )
    result = await shell.run_command("cat /tmp/screen.log", time_limit=2)
    if "testing screen" not in result.stdout:
        pytest.fail(f"Expected 'testing screen' in output, got: {result.stdout}")
