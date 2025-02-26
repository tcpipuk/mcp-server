"""Configure pytest for the test suite."""

from __future__ import annotations

from asyncio import create_subprocess_exec, sleep as asyncio_sleep
from json import dump as json_dump
from logging import getLogger
from os import environ, setsid as os_setsid
from pathlib import Path
from time import time as time_time
from typing import TYPE_CHECKING

import pytest
import pytest_asyncio

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# Store memory snapshots for different test phases if psutil is available
memory_data = {"start": {}, "tests": {}, "peak": {}, "end": {}}


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    """Record initial memory usage when pytest starts."""
    if not HAS_PSUTIL:
        return

    process = psutil.Process()
    memory = process.memory_info()

    memory_data["start"] = {
        "rss": memory.rss / (1024 * 1024),  # Convert to MB
        "vms": memory.vms / (1024 * 1024),
        "optimization_level": environ.get("PYTHONOPTIMIZE", "0"),
        "timestamp": time_time(),
    }


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Record final memory usage when pytest finishes."""
    if not HAS_PSUTIL:
        return

    process = psutil.Process()
    memory = process.memory_info()

    memory_data["end"] = {
        "rss": memory.rss / (1024 * 1024),
        "vms": memory.vms / (1024 * 1024),
        "timestamp": time_time(),
    }

    # Add summary data
    summary = {
        "duration_seconds": memory_data["end"]["timestamp"] - memory_data["start"]["timestamp"],
        "peak_rss_mb": memory_data["peak"].get("rss", 0),
        "final_rss_mb": memory_data["end"]["rss"],
        "rss_difference_mb": memory_data["end"]["rss"] - memory_data["start"]["rss"],
        "optimization_level": memory_data["start"]["optimization_level"],
    }

    # Use the dedicated directory with proper permissions
    memory_dir = Path("/app/memory_profiles")
    output_file = memory_dir / f"memory_profile_O{summary['optimization_level']}.json"

    try:
        logger = getLogger(__name__)
        with Path(output_file).open("w", encoding="utf-8") as f:
            json_dump({"raw": memory_data, "summary": summary}, f, indent=2)
        logger.info("Memory profile saved to %s", output_file)

        # Verify the file was created
        if not output_file.exists():
            logger.error("ERROR: Memory profile file was not created")
    except Exception:
        logger.exception("Memory profile could not be written")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item: pytest.Item, nextitem: pytest.Item) -> Generator[None]:
    """Track memory usage before and after each test."""
    if not HAS_PSUTIL:
        yield
        return

    # Gather memory data before and after test
    process = psutil.Process()
    pre_memory = process.memory_info()

    yield

    # Store memory data after test
    post_memory = process.memory_info()
    test_id = item.nodeid
    memory_data["tests"][test_id] = {
        "pre_rss": pre_memory.rss / (1024 * 1024),
        "post_rss": post_memory.rss / (1024 * 1024),
        "diff_rss": (post_memory.rss - pre_memory.rss) / (1024 * 1024),
    }

    # Update peak memory if needed
    current_rss = post_memory.rss / (1024 * 1024)
    if current_rss > memory_data.get("peak", {}).get("rss", 0):
        memory_data["peak"] = {"rss": current_rss, "test": test_id, "timestamp": time_time()}


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
