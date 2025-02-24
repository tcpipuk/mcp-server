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
        McpError: If path would escape workspace
    """
    # Convert to Path and normalise
    clean = Path(path).parts

    # Handle empty paths (e.g. "." or "")
    if not clean:
        return Path()

    # Block absolute paths and parent directory traversal
    if clean[0] == "/" or ".." in clean:
        raise McpError(
            ErrorData(
                code=INTERNAL_ERROR, message="Path cannot be absolute or contain parent traversal"
            )
        )

    # Ensure no parts start with dots/hidden
    if any(part.startswith(".") for part in clean):
        raise McpError(
            ErrorData(code=INTERNAL_ERROR, message="Path cannot contain hidden/special components")
        )

    # Join parts to create clean relative path
    return Path(*clean)


def ensure_parent_dirs(path: Path) -> None:
    """Create parent directories for a path if they don't exist.

    Raises:
        McpError: If directory creation fails
    """
    try:
        parent = path.parent
        parent.mkdir(parents=True, exist_ok=True)
        # Test we can actually write to the directory
        test_file = parent / ".write_test"
        test_file.touch()
        test_file.unlink()
    except OSError as exc:
        raise McpError(
            ErrorData(code=INTERNAL_ERROR, message=f"Failed to create directories: {exc}")
        ) from exc


def format_output(stdout: bytes, stderr: bytes) -> str:
    """Format command outputs into a readable string.

    Returns:
        String of formatted outputs
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
        Tuple of (stdout string, stderr string)

    Raises:
        McpError: If the command fails or encounters filesystem errors
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
        Dict with content and truncation status

    Raises:
        McpError: If file cannot be read
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

    Raises:
        McpError: If no files are found or if there are filesystem errors.
    """
    workspace = get_workspace_dir()
    results = {"files": {}}

    try:
        for file in files:
            try:
                file_path = workspace / sanitise_path(file)
                if not file_path.exists():
                    results["files"][file] = {"error": f"File not found: {file}"}
                else:
                    results["files"][file] = await read_file(file_path, max_length)
            except McpError as exc:
                results["files"][file] = {"error": str(exc)}

        return json_dumps(results)

    except Exception as exc:
        raise McpError(
            ErrorData(
                code=INTERNAL_ERROR, message=f"Unexpected error: {exc.__class__.__name__}: {exc}"
            )
        ) from exc


async def tool_workspace_write(path: str, content: str, mode: str = "overwrite") -> str:
    """Write or update a file in the workspace.

    Args:
        path: File path relative to workspace root
        content: New file content or a diff patch to apply
        mode: Either "overwrite" to replace the file entirely, or "patch" to apply a diff patch
            (default "overwrite")

    Returns:
        Success message.

    Raises:
        McpError: If the write operation fails or if mode is invalid.
    """
    workspace = get_workspace_dir()
    file_path = workspace / sanitise_path(path)

    try:
        if mode == "overwrite":
            ensure_parent_dirs(file_path)
            file_path.write_text(content, encoding="utf-8")
            return f"File '{path}' written successfully."

        if mode == "patch":
            ensure_parent_dirs(file_path)
            if not file_path.exists():
                file_path.touch()

            return (
                await run_command(
                    ["patch", "-p0", str(file_path)],
                    cwd=file_path.parent,
                    error_prefix="Patch failed",
                    input_data=content.encode("utf-8"),
                )
                or "Patch applied successfully."
            )

        raise McpError(  # noqa: TRY301
            ErrorData(
                code=INTERNAL_ERROR, message=f"Invalid mode '{mode}'. Use 'overwrite' or 'patch'."
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


async def tool_workspace_git(command: str, cwd: str = ".") -> str:
    """Execute a git command within the workspace.

    Args:
        command: Full git command to execute (e.g. "git clone git@github.com:user/repo.git")
        cwd: Working directory relative to workspace root (defaults to ".")

    Returns:
        Output of the git command.
    """
    workspace = get_workspace_dir()
    work_dir = workspace / sanitise_path(cwd)
    ensure_parent_dirs(work_dir)

    return (
        await run_command(shlex_split(command), cwd=work_dir, error_prefix="Git command failed")
        or "Git command completed successfully."
    )
