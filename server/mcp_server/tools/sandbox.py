"""Provide tools to execute shell commands in a persistent sandbox environment.

Offers a secure environment for running Python code and shell commands with:

- Python 3.13 with pandas/numpy for data analysis
- Network tools (aiodns, aiohttp, beautifulsoup4, requests) for web tasks
- Development tools (git, ruff) for managing and checking code
- System tools (curl, dig, host, ping, screen, tree, wget) for investigation

Uses socat to connect to a bash process over a TCP connection defined by the SANDBOX
environment variable. Supports screen sessions that persist between requests for
long-running tasks.
"""

from __future__ import annotations

from asyncio import (
    StreamReader,
    StreamWriter,
    open_connection as asyncio_open_connection,
    wait_for as asyncio_wait_for,
)
from dataclasses import dataclass, field
from os import environ as os_environ
from typing import Final

from mcp.shared.exceptions import McpError
from mcp.types import INTERNAL_ERROR, ErrorData

# Constants for configuration and defaults
PROMPT_MARKER: Final[bytes] = b"$ "
SCREEN_LOG_PATH: Final[str] = "/tmp/mcp_screen.log"  # noqa: S108
DEFAULT_TIMEOUT: Final[int] = 5
SCREEN_PREFIX: Final[str] = "mcp_"
SCREEN_ID_LENGTH: Final[int] = 8


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Hold the result of a command execution."""

    stdout: str = field(default="")
    stderr: str = field(default="")

    @property
    def formatted_output(self) -> str:
        """Format the command result for display."""
        if stderr := self.stderr.strip():
            return f"Error:\n```\n{stderr}\n```"

        if stdout := self.stdout.strip():
            return f"Output:\n```\n{stdout}\n```"

        return "No output"


@dataclass(slots=True)
class ShellConnection:
    """Manage connection to sandbox shell via TCP."""

    reader: StreamReader
    writer: StreamWriter
    screen_session: str | None = None

    @classmethod
    async def connect(cls) -> ShellConnection:
        """Create new connection to sandbox shell using TCP.

        Returns:
            ShellConnection instance

        Raises:
            McpError: If SANDBOX is not set or malformed
        """
        if not (sandbox := os_environ.get("SANDBOX")):
            raise McpError(
                ErrorData(code=INTERNAL_ERROR, message="SANDBOX environment variable is not set")
            )

        try:
            host, port_str = sandbox.split(":", 1)
            reader, writer = await asyncio_open_connection(host, int(port_str))
        except (ValueError, OSError) as err:
            raise McpError(
                ErrorData(code=INTERNAL_ERROR, message=f"Failed to connect to sandbox: {err}")
            ) from err

        return cls(reader=reader, writer=writer)

    async def close(self) -> None:
        """Close the connection."""
        self.writer.close()
        await self.writer.wait_closed()

    async def run_command(self, command: str, time_limit: int = DEFAULT_TIMEOUT) -> CommandResult:
        """Run a command and return its output.

        Args:
            command: Shell command(s) to execute
            time_limit: Seconds to wait for output

        Returns:
            CommandResult containing stdout
        """
        try:
            # Wait for initial prompt
            await asyncio_wait_for(self._read_until_prompt(), timeout=1)

            # Send the command block
            await self._write_command(command)

            # Read all output until next prompt
            output = await asyncio_wait_for(self._read_until_prompt(), timeout=time_limit)

            return CommandResult(stdout=output)
        except TimeoutError:
            return CommandResult(stderr="Command timed out")
        except Exception as e:  # noqa: BLE001
            return CommandResult(stderr=str(e))

    async def _write_command(self, command: str) -> None:
        """Write a command to the shell and drain the buffer.

        Args:
            command: Command to write
        """
        self.writer.write(f"{command}\n".encode())
        await self.writer.drain()

    async def _read_until_prompt(self) -> str:
        """Read output until shell prompt is seen.

        Returns:
            Command output formatted as a string
        """
        buffer = []
        while True:
            if not (line := await self.reader.readline()):
                break
            if line.startswith(PROMPT_MARKER):
                break
            buffer.append(line.decode())
        return "".join(buffer)


async def tool_sandbox(commands: str, time_limit: int = DEFAULT_TIMEOUT) -> str:
    """Execute shell commands in the sandbox environment.

    Args:
        commands: Shell command(s) to execute
        time_limit: Seconds to wait for output

    Returns:
        Command output formatted as a string
    """
    conn = await ShellConnection.connect()
    try:
        result = await conn.run_command(commands, time_limit)
        return result.formatted_output
    finally:
        await conn.close()
