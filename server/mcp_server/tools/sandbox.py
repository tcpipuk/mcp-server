"""Provide tools to execute shell commands in a persistent sandbox environment.

Uses socat to connect to a bash process over a TCP connection defined by the SANDBOX_HOST
environment variable, with support for running commands in screen sessions that persist between
requests.
"""

from __future__ import annotations

from asyncio import (
    StreamReader,
    StreamWriter,
    open_connection as asyncio_open_connection,
    sleep as asyncio_sleep,
    wait_for as asyncio_wait_for,
)
from dataclasses import dataclass
from os import environ as os_environ
from shlex import quote as shlex_quote
from uuid import uuid4

from mcp.shared.exceptions import McpError
from mcp.types import INTERNAL_ERROR, ErrorData


@dataclass(slots=True)
class ShellConnection:
    """Manage connection to sandbox shell via TCP."""

    reader: StreamReader
    writer: StreamWriter

    @classmethod
    async def connect(cls) -> ShellConnection:
        """Create new connection to sandbox shell using TCP.

        Returns:
            ShellConnection instance

        Raises:
            McpError: If SANDBOX_HOST is not set.
        """
        sandbox = os_environ.get("SANDBOX_HOST")
        if not sandbox:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR, message="SANDBOX_HOST environment variable is not set"
                )
            )
        host, port_str = sandbox.split(":", 1)
        reader, writer = await asyncio_open_connection(host, int(port_str))
        return cls(reader=reader, writer=writer)

    async def close(self) -> None:
        """Close the connection."""
        self.writer.close()
        await self.writer.wait_closed()

    async def run_command(
        self, command: str, time_limit: int = 10, screen: str | None = None
    ) -> tuple[str, str, int]:
        """Run a command and return its output.

        Args:
            command: Shell command(s) to execute
            time_limit: Seconds to wait for output
            screen: Optional screen session name

        Returns:
            Tuple of (stdout, stderr, exit_code)
        """
        if screen:
            # Generate random session name if not provided
            screen = screen or f"mcp_{uuid4().hex[:8]}"

            # Create new screen session or reconnect to existing one
            self.writer.write(
                f"screen -dmS {screen} 2>/dev/null || screen -S {screen} -X stuff $'\n'".encode()
            )
            await self.writer.drain()

            # Send command to screen session
            self.writer.write(
                f"screen -S {screen} -X stuff {shlex_quote(command + '\n')}\n".encode()
            )
            await self.writer.drain()

            # Wait briefly then get output since last detach
            await asyncio_sleep(0.1)
            self.writer.write(f"screen -S {screen} -X hardcopy /tmp/mcp_screen.log\n".encode())
            await self.writer.drain()

            # Detach from session
            self.writer.write(f"screen -S {screen} -X detach\n".encode())
            await self.writer.drain()

            # Read the output file
            self.writer.write(b"cat /tmp/mcp_screen.log\n")

        else:
            # Run command directly
            self.writer.write(f"{command}\n".encode())

        await self.writer.drain()

        try:
            output = await asyncio_wait_for(self._read_until_prompt(), timeout=time_limit)
        except TimeoutError:
            return "", "Command timed out", 1
        else:
            return output, "", 0  # TODO: capture exit code and stderr

    async def _read_until_prompt(self) -> str:
        """Read output until shell prompt is seen.

        Returns:
            Command output formatted as a string
        """
        buffer = []
        while True:
            line = await self.reader.readline()
            if not line:
                break
            if line.startswith(b"$ "):  # Basic prompt detection
                break
            buffer.append(line.decode())
        return "".join(buffer)


async def tool_sandbox(command: str, time_limit: int = 5) -> str:
    """Execute shell commands in the sandbox environment.

    Args:
        command: Shell command(s) to execute
        time_limit: Seconds to wait for output

    Returns:
        Command output formatted as a string
    """
    conn = await ShellConnection.connect()
    try:
        # Execute the provided command directly (cwd and screen options removed to match tools.yaml)
        stdout, stderr, exit_code = await conn.run_command(command, time_limit)

        # Format output
        sections = []
        sections.append(f"Exit code: {exit_code}")
        if stdout := stdout.strip():
            sections.append(f"Output:\n```\n{stdout}\n```")
        if stderr := stderr.strip():
            sections.append(f"Error:\n```\n{stderr}\n```")
        return "\n\n".join(sections)

    finally:
        await conn.close()
