"""Configure pytest for the test suite."""

from __future__ import annotations

from asyncio import create_subprocess_exec, sleep as asyncio_sleep
from os import setsid as os_setsid
from typing import TYPE_CHECKING

import pytest
import pytest_asyncio

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@pytest.fixture(autouse=True)
def _setup_test_env() -> None:
    """Set up test environment variables and cleanup."""


@pytest_asyncio.fixture
async def sandbox_server(unused_tcp_port: int) -> AsyncGenerator[tuple[str, int]]:
    """Create a socat-based TCP server for sandbox testing.

    Yields:
        Tuple of (host, port) for the test server
    """
    # Start socat in the background, echoing input back
    process = await create_subprocess_exec(
        "/usr/bin/socat",
        f"TCP-LISTEN:{unused_tcp_port},reuseaddr,fork",
        "EXEC:'bash -i',pty,stderr,setsid,sigint,sane",
        preexec_fn=os_setsid,
    )

    # Give socat a moment to start up
    await asyncio_sleep(0.2)

    try:
        yield "127.0.0.1", unused_tcp_port
    finally:
        process.terminate()
        await process.wait()
