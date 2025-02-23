"""Configure pytest for the test suite."""

from __future__ import annotations

from asyncio import AbstractEventLoop, get_event_loop_policy
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture(autouse=True)
def _setup_test_env() -> None:
    """Set up test environment variables and cleanup."""


@pytest.fixture(scope="session")
def event_loop() -> Generator[AbstractEventLoop]:
    """Create an instance of the default event loop for the test session.

    Yields:
        asyncio.AbstractEventLoop: The default event loop.
    """
    policy = get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()
