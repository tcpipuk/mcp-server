"""Configure pytest for the test suite."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _setup_test_env() -> None:
    """Set up test environment variables and cleanup."""
