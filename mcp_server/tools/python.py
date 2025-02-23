"""Provide tools to execute or lint Python code in a sandboxed environment.

Defines classes and functions to write code to a temporary file, then either run it or lint it
using Ruff, with appropriate resource limits and isolation.
"""

from __future__ import annotations

import resource
from asyncio import create_subprocess_exec, subprocess, timeout as asyncio_timeout
from dataclasses import dataclass, field
from os import environ as os_environ
from pathlib import Path
from shutil import rmtree as shutil_rmtree
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from collections.abc import Mapping

# Allowed environment variables to expose to sandboxed code
ALLOWED_ENV_VARS = frozenset({
    "LANG",
    "OPENBLAS_NUM_THREADS",
    "PYTHON_VERSION",
    "PYTHONPATH",
    "SANDBOX_PYTHON",
    "SANDBOX_RUFF",
    "TZ",
    "USER_AGENT",
})


# Resource limits as class constants
@dataclass(slots=True, frozen=True)
class ResourceLimits:
    """Define resource limits for sandboxed execution."""

    MEMORY: ClassVar[int] = 2 * 1024 * 1024 * 1024  # 2GB
    CPU_TIME: ClassVar[int] = 600  # seconds
    PROCESS_COUNT: ClassVar[int] = 50
    FILE_SIZE: ClassVar[int] = 50 * 1024 * 1024  # 50MB

    LIMITS: ClassVar[Mapping[int, int]] = {
        resource.RLIMIT_AS: MEMORY,
        resource.RLIMIT_CPU: CPU_TIME,
        resource.RLIMIT_NPROC: PROCESS_COUNT,
        resource.RLIMIT_FSIZE: FILE_SIZE,
        resource.RLIMIT_CORE: 0,
    }


@dataclass(slots=True)
class SandboxedPython:
    """Handle execution of Python code in a sandboxed environment."""

    code: str
    time_limit: int | None = None
    lint: bool = False
    _temp_dir: Path = field(init=False)
    _script_path: Path = field(init=False)

    def __post_init__(self) -> None:
        """Set up the sandbox environment on instantiation."""
        self._temp_dir = Path(TemporaryDirectory().name)
        self._script_path = self._temp_dir / "run" / "usercode.py"
        self._script_path.parent.mkdir(parents=True)
        self._script_path.write_text(self.code)

    def __del__(self) -> None:
        """Clean up temporary files on object destruction."""
        if self._temp_dir.exists():
            shutil_rmtree(self._temp_dir)

    @staticmethod
    def setup_sandbox() -> None:
        """Set up sandbox environment and resource limits."""
        # Set resource limits
        for res, limit in ResourceLimits.LIMITS.items():
            resource.setrlimit(res, (limit, limit))

        # Preserve necessary environment variables.
        original_env = {k: v for k, v in os_environ.items() if k in ALLOWED_ENV_VARS}
        os_environ.clear()
        os_environ.update(original_env)

    async def execute(self) -> tuple[bytes, bytes, str]:
        """Execute the code in the sandbox and return raw outputs.

        Returns:
            Tuple of stdout, stderr, and error message
        """
        stdout = stderr = b""
        errmsg = ""

        try:
            proc = await create_subprocess_exec(
                *(
                    [os_environ["SANDBOX_RUFF"], "check", "--output-format", "json"]
                    if self.lint
                    else [os_environ["SANDBOX_PYTHON"]]
                ),
                str(self._script_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=self.setup_sandbox,
                cwd=self._script_path.parent,
            )

            if self.time_limit:
                try:
                    async with asyncio_timeout(self.time_limit):
                        stdout, stderr = await proc.communicate()
                except TimeoutError:
                    proc.kill()
                    stdout, stderr = await proc.communicate()
                    errmsg = f"Execution terminated after {self.time_limit} seconds"
            else:
                stdout, stderr = await proc.communicate()

            if proc.returncode and not errmsg:
                errmsg = f"Process exited with code {proc.returncode}"

        except OSError as exc:
            errmsg = f"File system error: {exc}"
        except Exception as exc:  # noqa: BLE001
            errmsg = f"Unexpected error: {exc.__class__.__name__}: {exc}"

        return stdout, stderr, errmsg

    @staticmethod
    def format_output(stdout: bytes, stderr: bytes, errmsg: str) -> str:
        """Format execution outputs into a readable string.

        Returns:
            String of formatted outputs
        """
        sections = []
        for section in {stdout, stderr, errmsg}:
            if isinstance(section, bytes):
                section = section.decode(errors="replace")  # noqa: PLW2901
            if section := section.strip():
                sections.append(f"{section}:\n```\n{section}\n```")
        return "\n\n".join(sections)


async def tool_python(code: str, time_limit: int = 5, lint: bool = False) -> str:
    """Execute or lint Python code in a sandboxed environment.

    Returns:
        The output of code execution or the linting result
    """
    sandbox = SandboxedPython(code=code, time_limit=time_limit if not lint else None, lint=lint)
    stdout, stderr, errmsg = await sandbox.execute()
    return sandbox.format_output(stdout, stderr, errmsg)
