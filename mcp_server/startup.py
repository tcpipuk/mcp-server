"""Handle secure startup configuration for the MCP server.

Sets up Git configuration and SSH keys safely before any tools are available.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from shutil import which
from subprocess import CalledProcessError, run as subprocess_run  # noqa: S404
from tempfile import NamedTemporaryFile

from mcp.shared.exceptions import McpError
from mcp.types import INTERNAL_ERROR, ErrorData

# SSH agent exit codes
SSH_AGENT_NOT_RUNNING = 2

# Validation patterns
GIT_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9\s._-]+$")
GIT_EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
SSH_KEY_PATTERN = re.compile(r"^[-A-Za-z0-9+/=\s]+$")  # Base64 + whitespace


def _get_command_path(command: str) -> str:
    """Get full path to a command, raising if not found or not executable.

    Returns:
        Full path to the command

    Raises:
        McpError: If command is not found or not executable
    """
    path = which(command)
    if not path:
        raise McpError(
            ErrorData(code=INTERNAL_ERROR, message=f"Required command not found: {command}")
        )
    return path


def _validate_git_name(name: str) -> None:
    """Validate git user name format.

    Raises:
        McpError: If name contains invalid characters
    """
    if not GIT_NAME_PATTERN.match(name):
        raise McpError(
            ErrorData(
                code=INTERNAL_ERROR,
                message=(
                    "Git user name can only contain alphanumeric characters, spaces, dots, "
                    "underscores and hyphens"
                ),
            )
        )


def _validate_git_email(email: str) -> None:
    """Validate git email format.

    Raises:
        McpError: If email format is invalid
    """
    if not GIT_EMAIL_PATTERN.match(email):
        raise McpError(ErrorData(code=INTERNAL_ERROR, message="Invalid git email address format"))


def _validate_ssh_key(key: str) -> None:
    """Validate SSH key format.

    Raises:
        McpError: If key contains invalid characters
    """
    if not SSH_KEY_PATTERN.match(key):
        raise McpError(
            ErrorData(code=INTERNAL_ERROR, message="SSH key contains invalid characters")
        )


def setup_git_config() -> None:
    """Configure git with user details from environment if provided.

    Raises:
        McpError: If git configuration fails
    """
    git_name = os.environ.get("GIT_USER_NAME")
    git_email = os.environ.get("GIT_USER_EMAIL")
    git_path = _get_command_path("git")

    try:
        # Ensure config directory exists
        config_dir = Path.home() / ".config" / "git"
        config_dir.mkdir(parents=True, exist_ok=True)

        if git_name:
            _validate_git_name(git_name)
            subprocess_run(  # noqa: S603
                [git_path, "config", "--file", str(config_dir / "config"), "user.name", git_name],
                check=True,
                capture_output=True,
            )
        if git_email:
            _validate_git_email(git_email)
            subprocess_run(  # noqa: S603
                [git_path, "config", "--file", str(config_dir / "config"), "user.email", git_email],
                check=True,
                capture_output=True,
            )
    except CalledProcessError as exc:
        raise McpError(
            ErrorData(
                code=INTERNAL_ERROR,
                message=f"Failed to configure git: {exc.stderr.decode(errors='replace')}",
            )
        ) from exc


def setup_ssh_agent() -> None:
    """Start SSH agent if not running and add provided key.

    Raises:
        McpError: If SSH key setup fails
    """
    ssh_key = os.environ.get("GIT_SSH_KEY")
    if not ssh_key:
        return

    try:
        _validate_ssh_key(ssh_key)
        ssh_add_path = _get_command_path("ssh-add")
        ssh_agent_path = _get_command_path("ssh-agent")

        # Check if agent is running - using full path so safe
        result = subprocess_run(  # noqa: S603
            [ssh_add_path, "-l"], capture_output=True, text=True, check=False
        )
        agent_running = result.returncode != SSH_AGENT_NOT_RUNNING

        if not agent_running:
            # Start agent and get its environment - using full path so safe
            result = subprocess_run(  # noqa: S603
                [ssh_agent_path, "-s"], capture_output=True, text=True, check=True
            )
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
            # Add key to agent - using full path and validated key file so safe
            subprocess_run([ssh_add_path, str(key_path)], check=True, capture_output=True)  # noqa: S603
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
