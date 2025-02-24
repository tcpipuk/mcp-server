"""Provide tools to perform workspace operations.

Defines asynchronous functions to list, read, write files and run git commands within a persistent
workspace. The workspace is fixed at /workspace/ to ensure persistence when using Docker.
"""

from __future__ import annotations

from asyncio import (
    create_subprocess_exec as asyncio_create_subprocess_exec,
    subprocess as asyncio_subprocess,
)
from json import dumps as json_dumps
from pathlib import Path
from shlex import split as shlex_split

from mcp.shared.exceptions import McpError
from mcp.types import INTERNAL_ERROR, ErrorData


def get_workspace_dir() -> Path:
    """Return the base workspace directory and ensure it exists."""
    workspace = Path("/workspace")
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def sanitise_path(path: str | Path) -> Path:
    """Sanitise a path to ensure it cannot escape the workspace.

    Returns:
        Clean path relative to workspace root

    Raises:
        McpError: If path would escape workspace or contains hidden/special components.
    """
    try:
        # First check for obvious escape attempts
        path_str = str(path)
        if path_str.startswith(("..", "/")):
            raise McpError(
                ErrorData(code=INTERNAL_ERROR, message="Path cannot escape workspace root")
            )

        # Convert to Path and resolve against workspace
        workspace = get_workspace_dir()
        clean = (workspace / Path(path)).resolve()

        # Ensure path is within workspace
        if not clean.is_relative_to(workspace):
            raise McpError(
                ErrorData(code=INTERNAL_ERROR, message="Path cannot escape workspace root")
            )

        # Get relative path from workspace
        relative = clean.relative_to(workspace)

        # Block hidden files/directories
        if any(part.startswith(".") for part in relative.parts):
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR, message="Path cannot contain hidden/special components"
                )
            )
    except (ValueError, RuntimeError) as exc:
        raise McpError(
            ErrorData(code=INTERNAL_ERROR, message="Path cannot escape workspace root")
        ) from exc
    else:
        return relative


def ensure_parent_dirs(path: Path) -> None:
    """Create parent directories for a path if they don't exist.

    Raises:
        McpError: If directory creation fails.
    """
    try:
        parent = path.parent
        parent.mkdir(parents=True, exist_ok=True)

        # Test we can write to the directory
        test_file = parent / ".write_test"
        try:
            test_file.touch()
            test_file.unlink()
        except OSError as exc:
            raise McpError(
                ErrorData(code=INTERNAL_ERROR, message=f"Failed to create directories: {exc}")
            ) from exc
    except McpError:
        raise
    except OSError as exc:
        raise McpError(
            ErrorData(code=INTERNAL_ERROR, message=f"Failed to create directories: {exc}")
        ) from exc
    except Exception as exc:
        raise McpError(
            ErrorData(
                code=INTERNAL_ERROR,
                message=f"Unexpected error creating directories: {exc.__class__.__name__}: {exc}",
            )
        ) from exc


def format_output(stdout: bytes, stderr: bytes) -> str:
    """Format command outputs into a readable string.

    Returns:
        String of formatted outputs.
    """
    sections = []
    for section in {stdout, stderr}:
        if isinstance(section, bytes):
            section = section.decode(errors="replace")  # noqa: PLW2901
        if isinstance(section, str) and (section := section.strip()):
            sections.append(section)
    return "\n".join(sections)


async def run_command(
    args: list[str], *, cwd: str | Path, error_prefix: str, input_data: bytes | None = None
) -> str:
    """Run a command and handle errors consistently.

    Returns:
        Command output as a string.

    Raises:
        McpError: If the command fails or encounters filesystem errors.
    """
    try:
        process = await asyncio_create_subprocess_exec(
            *args, stdout=asyncio_subprocess.PIPE, stderr=asyncio_subprocess.PIPE, cwd=str(cwd)
        )
        stdout, stderr = await process.communicate(input=input_data)
        if process.returncode != 0:
            raise McpError(  # noqa: TRY301
                ErrorData(
                    code=INTERNAL_ERROR, message=f"{error_prefix}: {format_output(stdout, stderr)}"
                )
            )
    except McpError:
        raise
    except OSError as exc:
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"File system error: {exc}")) from exc
    except Exception as exc:
        raise McpError(
            ErrorData(
                code=INTERNAL_ERROR, message=f"Unexpected error: {exc.__class__.__name__}: {exc}"
            )
        ) from exc
    else:
        return format_output(stdout, stderr)


async def read_file(path: Path, max_length: int = 0) -> dict[str, str | bool]:
    """Read a file with optional length limit.

    Returns:
        Dict with content and truncation status.

    Raises:
        McpError: If file cannot be read.
    """
    try:
        with path.open("rb") as f:
            data = f.read(max_length) if max_length > 0 else f.read()
        return {
            "content": data.decode("utf-8", errors="replace"),
            "truncated": max_length > 0 and len(data) >= max_length,
        }
    except OSError as exc:
        raise McpError(
            ErrorData(code=INTERNAL_ERROR, message=f"Error reading file: {exc}")
        ) from exc


def apply_patch(current: str, patch: str) -> str:
    """Apply a minimal unified diff patch to current content.

    This simple implementation only supports a single hunk replacing the entire text.

    Args:
        current: The current file content.
        patch: The patch diff text.

    Returns:
        The new file content.

    Raises:
        McpError: If the patch does not match current file content.
    """
    lines = patch.splitlines()
    old_lines = []
    new_lines = []
    in_hunk = False
    for line in lines:
        if line.startswith("@@"):
            in_hunk = True
        elif in_hunk:
            if line.startswith("-"):
                old_lines.append(line[1:])
            elif line.startswith("+"):
                new_lines.append(line[1:])
            else:
                new_lines.append(line)
    if current.strip() == "\n".join(old_lines).strip():
        return "\n".join(new_lines)
    raise McpError(ErrorData(code=INTERNAL_ERROR, message="Patch did not match file content"))


async def tool_workspace_tree(path: str = ".") -> str:
    """Execute a tree command in the workspace to list files and directories.

    Args:
        path: Optional subdirectory relative to workspace root (defaults to ".").

    Returns:
        JSON formatted string of the directory tree output.
    """
    workspace = get_workspace_dir()
    return await run_command(
        ["tree", "-aiJ", "-I", ".git", "--gitignore", str(sanitise_path(path))],
        cwd=workspace,
        error_prefix="Tree command failed",
    )


async def tool_workspace_read(files: list[str], max_length: int = 65535) -> str:
    """Read the contents of specified files from the workspace.

    Args:
        files: List of file paths relative to workspace root.
        max_length: Maximum bytes to read per file (default 64KiB; 0 means no limit).

    Returns:
        JSON string mapping file paths to their contents.
    """
    workspace = get_workspace_dir()
    results = {"files": {}}

    for file in files:
        # Note: propagates McpError if sanitisation fails.
        file_path = workspace / sanitise_path(file)
        if not file_path.exists():
            results["files"][file] = {"error": f"File not found: {file}"}
        else:
            results["files"][file] = await read_file(file_path, max_length)

    return json_dumps(results)


async def tool_workspace_write(path: str, content: str, mode: str = "overwrite") -> str:
    """Write or update a file in the workspace.

    Args:
        path: File path relative to workspace root.
        content: New file content or a diff patch to apply.
        mode: Either "overwrite" to replace the file entirely, or "patch" to apply a diff patch
            (default "overwrite").

    Returns:
        Success message.

    Raises:
        McpError: If the write operation fails or if mode is invalid.
    """
    workspace = get_workspace_dir()
    file_path = workspace / sanitise_path(path)

    if mode == "overwrite":
        ensure_parent_dirs(file_path)
        file_path.write_text(content, encoding="utf-8")
        return f"File '{path}' written successfully."

    if mode == "patch":
        ensure_parent_dirs(file_path)
        if not file_path.exists():
            file_path.touch()
        current = file_path.read_text(encoding="utf-8")
        new_content = apply_patch(current, content)
        file_path.write_text(new_content, encoding="utf-8")
        return "Patch applied successfully."

    raise McpError(
        ErrorData(
            code=INTERNAL_ERROR, message=f"Invalid mode '{mode}'. Use 'overwrite' or 'patch'."
        )
    )


async def tool_workspace_git(command: str, cwd: str = ".") -> str:
    """Execute a git command within the workspace.

    Args:
        command: Full git command to execute (e.g. "git clone git@github.com:user/repo.git")
        cwd: Working directory relative to workspace root (defaults to ".")

    Returns:
        Output of the git command

    Raises:
        McpError: If the git command fails or if the working directory cannot be sanitised
    """
    workspace = get_workspace_dir()
    work_dir = workspace / sanitise_path(cwd)
    # Ensure the working directory exists
    work_dir.mkdir(parents=True, exist_ok=True)
    try:
        return await run_command(
            shlex_split(command), cwd=work_dir, error_prefix="Git command failed"
        )
    except McpError as err:
        # Allow sanitisation errors to propagate.
        if "escape workspace" in str(err):
            raise
        # Otherwise, return the error message as a string.
        return str(err)
