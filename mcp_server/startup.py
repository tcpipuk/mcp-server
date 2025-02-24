"""Handle secure startup configuration for the MCP server.

Sets up Git configuration and SSH keys safely before any tools are available.
"""

from __future__ import annotations

from logging import getLogger
from os import environ as os_environ
from pathlib import Path
from re import MULTILINE, compile as re_compile
from shutil import which
from subprocess import CalledProcessError, run as subprocess_run  # noqa: S404
from tempfile import NamedTemporaryFile

from mcp.shared.exceptions import McpError
from mcp.types import INTERNAL_ERROR, ErrorData

# Get logger for this module
logger = getLogger(__name__)

# SSH agent exit codes
SSH_AGENT_NOT_RUNNING = 2

# Validation patterns
GIT_NAME_PATTERN = re_compile(r"^[a-zA-Z0-9\s._-]+$")
GIT_EMAIL_PATTERN = re_compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
SSH_KEY_PATTERN = re_compile(
    r"^-----BEGIN [A-Z\s]+ PRIVATE KEY-----[\r\n]+"
    r"[A-Za-z0-9+/=\s]+[\r\n]+"
    r"-----END [A-Z\s]+ PRIVATE KEY-----[\r\n]*$",
    MULTILINE,
)


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
        McpError: If key format is invalid
    """
    # Normalize line endings and remove any double newlines
    normalised_key = "\n".join(line.strip() for line in key.splitlines())

    # Add final newline if missing
    if not normalised_key.endswith("\n"):
        normalised_key += "\n"

    if not SSH_KEY_PATTERN.match(normalised_key):
        raise McpError(
            ErrorData(
                code=INTERNAL_ERROR,
                message="Invalid SSH key format - must be a PEM formatted private key",
            )
        )


def setup_git_config() -> None:
    """Configure git with user details from environment if provided.

    Raises:
        McpError: If git configuration fails
    """
    git_name = os_environ.get("GIT_USER_NAME")
    git_email = os_environ.get("GIT_USER_EMAIL")
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

    If the SSH key is invalid or setup fails, logs a warning but continues.
    """
    ssh_key = os_environ.get("GIT_SSH_KEY")
    if not ssh_key:
        return

    try:
        # Validate key format
        try:
            normalised_key = "\n".join(line.strip() for line in ssh_key.splitlines())
            if not normalised_key.endswith("\n"):
                normalised_key += "\n"
            if not SSH_KEY_PATTERN.match(normalised_key):
                logger.warning("Invalid SSH key format - SSH authentication will be unavailable")
                return
        except Exception as exc:
            logger.warning("Failed to validate SSH key: %s", exc)
            return

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
                    os_environ[key] = value

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
        del os_environ["GIT_SSH_KEY"]

    except (CalledProcessError, OSError) as exc:
        logger.warning("Failed to setup SSH agent: %s", exc)
        return


def secure_startup() -> None:
    """Perform secure startup configuration.

    This must be called before any tools are made available.
    """
    try:
        setup_git_config()
    except McpError as exc:
        logger.warning("Failed to configure git: %s", exc)

    # SSH setup already handles its own errors
    setup_ssh_agent()
