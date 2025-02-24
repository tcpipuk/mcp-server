"""Test the workspace operations tools."""

from __future__ import annotations

from json import loads as json_loads
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from mcp.shared.exceptions import McpError

from mcp_server.tools.workspace import (
    ensure_parent_dirs,
    sanitise_path,
    tool_workspace_git,
    tool_workspace_read,
    tool_workspace_tree,
    tool_workspace_write,
)


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a temporary workspace directory for testing.

    Returns:
        Path to temporary workspace
    """
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    monkeypatch.setattr("mcp_server.tools.workspace.get_workspace_dir", lambda: workspace_dir)
    return workspace_dir


@pytest.mark.asyncio
async def test_workspace_tree(workspace: Path) -> None:
    """Test the tree command functionality."""
    # Create some test files
    (workspace / "test.txt").touch()
    (workspace / "subdir").mkdir()
    (workspace / "subdir" / "file.txt").touch()

    # Test basic tree listing
    result = json_loads(await tool_workspace_tree())
    files = {
        item["name"]
        for directory in result
        if isinstance(directory, dict) and directory.get("type") == "directory"
        for item in directory.get("contents", [])
    }
    if not {"test.txt", "subdir"} <= files:
        pytest.fail(f"Expected files missing from tree output: {result}")

    # Test subdirectory listing
    result = json_loads(await tool_workspace_tree("subdir"))
    files = {
        item["name"]
        for directory in result
        if isinstance(directory, dict) and directory.get("type") == "directory"
        for item in directory.get("contents", [])
    }
    if "test.txt" in files:
        pytest.fail(f"Found root file in subdirectory listing: {result}")
    if "file.txt" not in files:
        pytest.fail(f"Subdirectory file missing from tree output: {result}")


@pytest.mark.asyncio
async def test_workspace_read(workspace: Path) -> None:
    """Test reading files from the workspace."""
    # Create test files
    test_content = "Hello, World!"
    (workspace / "test.txt").write_text(test_content)
    (workspace / "subdir").mkdir()
    (workspace / "subdir" / "file.txt").write_text("Test file")

    # Test reading multiple files
    result = await tool_workspace_read(["test.txt", "subdir/file.txt"])
    if test_content not in result:
        pytest.fail(f"Expected content missing from read output: {result}")

    # Test max length limit
    result = await tool_workspace_read(["test.txt"], max_length=5)
    if '"truncated": true' not in result:
        pytest.fail(f"Expected truncation flag in output: {result}")

    # Test reading non-existent file
    result = await tool_workspace_read(["missing.txt"])
    if "File not found" not in result:
        pytest.fail(f"Expected 'File not found' error in output: {result}")

    # Test reading outside workspace
    with pytest.raises(McpError, match="escape workspace"):
        await tool_workspace_read(["../outside.txt"])


@pytest.mark.asyncio
async def test_workspace_write(workspace: Path) -> None:
    """Test writing files to the workspace."""
    test_content = "Hello, World!"

    # Test overwrite mode
    result = await tool_workspace_write("test.txt", test_content)
    if "written successfully" not in result:
        pytest.fail(f"Expected success message in output: {result}")
    if (workspace / "test.txt").read_text() != test_content:
        pytest.fail("File content doesn't match written content")

    # Test patch mode
    patch_content = "@@ -1 +1 @@\n-Hello, World!\n+Hello, Test!\n"
    result = await tool_workspace_write("test.txt", patch_content, mode="patch")
    if "Patch applied successfully" not in result:
        pytest.fail(f"Expected patch success message in output: {result}")
    if (workspace / "test.txt").read_text() != "Hello, Test!":
        pytest.fail("Patch not applied correctly")

    # Test invalid mode
    with pytest.raises(McpError, match="Invalid mode"):
        await tool_workspace_write("test.txt", test_content, mode="invalid")

    # Test writing outside workspace
    with pytest.raises(McpError, match="escape workspace"):
        await tool_workspace_write("../outside.txt", test_content)


@pytest.mark.asyncio
async def test_workspace_git(workspace: Path) -> None:
    """Test git operations in the workspace."""
    # Test git init
    result = await tool_workspace_git("git init")
    if "Initialized empty Git repository" not in result:
        pytest.fail(f"Expected initialisation message in output: {result}")

    # Test git with custom working directory
    subdir = "repo"
    result = await tool_workspace_git("git init", cwd=subdir)
    if not (workspace / subdir / ".git").exists():
        pytest.fail("Git repository not initialized in subdirectory")

    # Test invalid git command
    result = await tool_workspace_git("git invalid-command")
    if "Git command failed" not in result:
        pytest.fail(f"Expected error message in output: {result}")

    # Test git command outside workspace
    with pytest.raises(McpError, match="escape workspace"):
        await tool_workspace_git("git status", cwd="../outside")


def test_sanitise_path() -> None:
    """Test path sanitisation."""
    # Test valid paths
    valid_paths = ["test.txt", "subdir/file.txt", "deeply/nested/path/file.txt"]
    for path in valid_paths:
        result = sanitise_path(path)
        if not isinstance(result, Path):
            pytest.fail(f"Expected Path object for {path}, got {type(result)}")

    # Test invalid paths
    invalid_paths = [
        "../outside.txt",  # Parent directory
        "/etc/passwd",  # Absolute path
        "subdir/../../../etc/passwd",  # Complex escape
        ".git/config",  # Hidden directory
        "test/.secret",  # Hidden file
    ]
    for path in invalid_paths:
        with pytest.raises(McpError):
            sanitise_path(path)


def test_ensure_parent_dirs(workspace: Path) -> None:
    """Test parent directory creation."""
    test_path = workspace / "deeply" / "nested" / "path" / "file.txt"

    # Test creating nested directories
    ensure_parent_dirs(test_path)
    if not test_path.parent.exists():
        pytest.fail("Parent directories not created")

    # Test with existing directories
    ensure_parent_dirs(test_path)  # Should not raise

    # Test with unwritable directory
    if not TYPE_CHECKING:  # Skip this test when type checking
        unwritable = workspace / "unwritable"
        unwritable.mkdir()
        unwritable.chmod(0o444)  # Read-only
        with pytest.raises(McpError, match="Failed to create directories"):
            ensure_parent_dirs(unwritable / "test.txt")
