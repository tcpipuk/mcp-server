"""
Provide tools to execute or lint Python code in a sandboxed environment.

Defines a function to write code to a temporary file, then either run it or lint it using Ruff,
depending on the provided parameters.
"""

from __future__ import annotations

from asyncio import TimeoutError as AsyncioTimeoutError
from asyncio import create_subprocess_exec, subprocess, wait_for
from os import environ as os_environ
from pathlib import Path
from tempfile import TemporaryDirectory


async def run_sandboxed(code: str, cmd: list[str], timeout: int | None = None) -> str:
    """
    Run a command on a temporary file containing the provided code.

    Args:
        code: The Python code to write to a file.
        cmd: The command to run (will be passed the temp file path).
        timeout: Optional timeout in seconds.

    Returns:
        The command output, with any errors appended.
    """
    with TemporaryDirectory() as tmpdir:
        script_path = Path(tmpdir) / "script.py"
        script_path.write_text(code)

        try:
            proc = await create_subprocess_exec(
                *cmd,
                str(script_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                stdout, stderr = await wait_for(proc.communicate(), timeout=timeout)
                output = stdout.decode()
                if stderr:
                    error = stderr.decode()
                    output = f"{output}\nErrors:\n{error}" if output else error
            except AsyncioTimeoutError:
                proc.kill()
                return "Execution timed out"
            else:
                return output

        except Exception as e:
            return f"Execution failed: {str(e)!r}"


async def tool_python(code: str, timeout: int = 5, lint: bool = False) -> str:
    """
    Execute or lint Python code in a sandboxed environment.

    Args:
        code: The Python code to execute or lint.
        timeout: Timeout in seconds (default is 5) - only used when executing code.
        lint: If True, lint the code using Ruff instead of executing it.

    Returns:
        The output of code execution or the linting result.
    """
    if lint:
        cmd = [os_environ["SANDBOX_RUFF"], "check", "--output-format", "text"]
        result = await run_sandboxed(code, cmd)
        return result or "No issues found!"

    # Chain unshare with setpriv to isolate Python before execution
    cmd = [
        "unshare",
        "--net",  # New network namespace
        "--ipc",  # New IPC namespace
        "--pid",  # New PID namespace
        "--mount",  # New mount namespace
        "--uts",  # New UTS namespace
        "--fork",  # Fork before executing
        "setpriv",
        "--no-new-privileges",  # Prevent gaining new privileges via setuid, etc
        "--clear-groups",  # Remove any supplementary groups
        "--inh-caps=-all",  # Drop all Linux capabilities
        "--uid=nobody",  # Run as unprivileged 'nobody' user
        "--regid=nogroup",  # Run as unprivileged 'nogroup' group
        os_environ["SANDBOX_PYTHON"],  # Use sandbox Python
    ]
    return await run_sandboxed(code, cmd, timeout)
