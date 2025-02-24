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


def format_output(stdout: bytes, stderr: bytes) -> str:
    """Format command outputs into a readable string.

    Args:
        stdout: Raw stdout bytes from the command
        stderr: Raw stderr bytes from the command

    Returns:
        String of formatted outputs
    """
    sections = []
    for section in {stdout, stderr}:
        if isinstance(section, bytes):
            section = section.decode(errors="replace")  # noqa: PLW2901
        if section := section.strip():
            sections.append(section)
    return "\n".join(sections)


async def run_command(
    args: list[str], *, cwd: str | Path, error_prefix: str, input_data: bytes | None = None
) -> tuple[str, str]:
    """Run a command and handle errors consistently.

    Args:
        args: Command and arguments to execute
        cwd: Working directory for the command
        error_prefix: Prefix for error messages if the command fails
        input_data: Optional bytes to write to stdin

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

        return stdout.decode(errors="replace"), stderr.decode(errors="replace")

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


async def tool_workspace_tree(path: str = ".") -> str:
    """Execute a tree command in the workspace to list files and directories.

    Args:
        path: Optional subdirectory relative to workspace root (defaults to ".").

    Returns:
        JSON formatted string of the directory tree output.
    """
    workspace = get_workspace_dir()
    stdout, _ = await run_command(
        ["tree", "-aiJ", "-I", ".git", "--gitignore", path],
        cwd=workspace,
        error_prefix="Tree command failed",
    )
    return stdout


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
            file_path = workspace / file
            try:
                if not file_path.exists():
                    results["files"][file] = {"error": f"File not found: {file}"}
                else:
                    with file_path.open("rb") as f:
                        data = f.read(max_length) if max_length > 0 else f.read()
                    results["files"][file] = {
                        "content": data.decode("utf-8", errors="replace"),
                        "truncated": max_length > 0 and len(data) >= max_length,
                    }
            except OSError as exc:
                results["files"][file] = {"error": f"Error reading file: {exc}"}

        if all("error" in info for info in results["files"].values()):
            raise McpError(  # noqa: TRY301
                ErrorData(code=INTERNAL_ERROR, message="Failed to read any of the requested files")
            )

        return json_dumps(results, indent=2)

    except McpError:
        raise
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
    file_path = workspace / path

    try:
        if mode == "overwrite":
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            return f"File '{path}' written successfully."

        if mode == "patch":
            if not file_path.exists():
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.touch()

            stdout, stderr = await run_command(
                ["patch", str(file_path)],
                cwd=file_path.parent,
                error_prefix="Patch failed",
                input_data=content.encode("utf-8"),
            )
            return format_output(stdout.encode(), stderr.encode()) or "Patch applied successfully."

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
    work_dir = workspace / cwd
    work_dir.mkdir(parents=True, exist_ok=True)

    stdout, stderr = await run_command(
        shlex_split(command), cwd=work_dir, error_prefix="Git command failed"
    )
    return format_output(stdout.encode(), stderr.encode()) or "Git command completed successfully."
