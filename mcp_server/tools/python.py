"""
Provide tools to execute or lint Python code in a sandboxed environment.

Defines functions to write code to a temporary file, then either run it or lint it using Ruff,
with appropriate resource limits and isolation.
"""

from __future__ import annotations

import os
import resource
from asyncio import TimeoutError as AsyncioTimeoutError
from asyncio import create_subprocess_exec, subprocess, wait_for
from os import environ as os_environ
from pathlib import Path
from tempfile import TemporaryDirectory

# Resource limits
MEMORY_LIMIT = 1 * 1024 * 1024 * 1024  # 1G
CPU_TIME_LIMIT = 600  # seconds

# Safe environment variables to expose to sandboxed code
SAFE_ENV_VARS = {
    "LANG",
    "PYTHON_VERSION",
    "PYTHONPATH",
    "TZ",
    "USER_AGENT",
}

def create_safe_env() -> dict[str, str]:
    """Create a minimal environment with only safe variables."""
    return {
        k: v for k, v in os_environ.items() 
        if k in SAFE_ENV_VARS
    }

def setup_sandbox() -> None:
    """Set up sandbox environment and resource limits."""
    # Set resource limits
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT, MEMORY_LIMIT))
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_TIME_LIMIT, CPU_TIME_LIMIT))
    resource.setrlimit(resource.RLIMIT_NPROC, (20, 20))
    resource.setrlimit(resource.RLIMIT_FSIZE, (50 * 1024 * 1024, 50 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    
    # Clear environment variables
    os.environ.clear()
    os.environ.update(create_safe_env())

async def run_sandboxed(code: str, cmd: list[str], timeout: int | None = None) -> str:
    """
    Run a command on a temporary file containing the provided code.

    Args:
        code: The Python code to write to a file
        cmd: The command to run (will be passed the temp file path)
        timeout: Optional timeout in seconds

    Returns:
        The command output, with any errors appended
    """
    with TemporaryDirectory(dir="/tmp") as tmpdir:
        script_path = Path(tmpdir) / "script.py"
        script_path.write_text(code)

        try:
            proc = await create_subprocess_exec(
                *cmd,
                str(script_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=setup_sandbox,
                env=create_safe_env(),
                cwd=tmpdir,
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
        code: The Python code to execute or lint
        timeout: Timeout in seconds (default is 5) - only used when executing code
        lint: If True, lint the code using Ruff instead of executing it

    Returns:
        The output of code execution or the linting result
    """
    if lint:
        cmd = [os_environ["SANDBOX_RUFF"], "check", "--output-format", "json"]
        result = await run_sandboxed(code, cmd)
        return result or "No issues found!"

    cmd = [os_environ["SANDBOX_PYTHON"]]
    return await run_sandboxed(code, cmd, timeout)