"""Handle secure startup configuration for the MCP server.

Sets up Git configuration and SSH keys safely before any tools are available.
"""

from __future__ import annotations

import os
from pathlib import Path
from subprocess import CalledProcessError, run as subprocess_run  # noqa: S404
from tempfile import NamedTemporaryFile

from mcp.shared.exceptions import McpError
from mcp.types import INTERNAL_ERROR, ErrorData


def setup_git_config() -> None:
    """Configure git with user details from environment if provided."""
    git_name = os.environ.get("GIT_USER_NAME")
    git_email = os.environ.get("GIT_USER_EMAIL")

    if git_name:
        subprocess_run(
            ["git", "config", "--global", "user.name", git_name], check=True, capture_output=True
        )
    if git_email:
        subprocess_run(
            ["git", "config", "--global", "user.email", git_email], check=True, capture_output=True
        )


def setup_ssh_agent() -> None:
    """Start SSH agent if not running and add provided key.

    Raises:
        McpError: If SSH key setup fails
    """
    ssh_key = os.environ.get("GIT_SSH_KEY")
    if not ssh_key:
        return

    try:
        # Check if agent is running
        result = subprocess_run(["ssh-add", "-l"], capture_output=True, text=True, check=False)
        agent_running = result.returncode != 2  # Exit code 2 means no agent

        if not agent_running:
            # Start agent and get its environment
            result = subprocess_run(["ssh-agent", "-s"], capture_output=True, text=True, check=True)
            # Parse and set agent environment variables
            for line in result.stdout.splitlines():
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip().upper()
                    value = value.rstrip(";").strip('"')
                    os.environ[key] = value

        # Write key to temporary file
        with NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as temp:
            temp.write(ssh_key)
            key_path = Path(temp.name)

        try:
            # Set correct permissions
            key_path.chmod(0o600)
            # Add key to agent
            subprocess_run(["ssh-add", str(key_path)], check=True, capture_output=True)
        finally:
            # Securely delete the key file
            key_path.write_bytes(b"\0" * len(ssh_key))  # Overwrite with zeros
            key_path.unlink()

        # Remove key from environment
        del os.environ["GIT_SSH_KEY"]

    except (CalledProcessError, OSError) as exc:
        raise McpError(
            ErrorData(code=INTERNAL_ERROR, message=f"Failed to setup SSH key: {exc}")
        ) from exc


def secure_startup() -> None:
    """Perform secure startup configuration.

    This must be called before any tools are made available.
    """
    setup_git_config()
    setup_ssh_agent()
