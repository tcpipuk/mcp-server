"""
Provide tools to execute or lint Python code in a sandboxed environment.
"""

from __future__ import annotations

import resource
from asyncio import TimeoutError as AsyncioTimeoutError
from asyncio import create_subprocess_exec, subprocess, wait_for
from os import environ as os_environ
from pathlib import Path
from tempfile import TemporaryDirectory

# Resource limits in bytes
MEMORY_LIMIT = 500 * 1024 * 1024  # 500MB
CPU_TIME_LIMIT = 60  # seconds

def limit_resources() -> None:
    """Set resource limits for the child process."""
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT, MEMORY_LIMIT))
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_TIME_LIMIT, CPU_TIME_LIMIT))
    resource.setrlimit(resource.RLIMIT_NPROC, (1, 1))
    resource.setrlimit(resource.RLIMIT_FSIZE, (50 * 1024 * 1024, 50 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

async def run_sandboxed(code: str, cmd: list[str], timeout: int | None = None) -> str:
    """
    Run a command on a temporary file containing the provided code.
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
                preexec_fn=limit_resources,  # Apply limits before exec
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
    """
    if lint:
        cmd = [os_environ["SANDBOX_RUFF"], "check", "--output-format", "json"]
        result = await run_sandboxed(code, cmd)
        return result or "No issues found!"

    # Run sandboxed Python
    cmd = [os_environ["SANDBOX_PYTHON"]]
    return await run_sandboxed(code, cmd, timeout)
