"""Shared pytest fixtures."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Make src/puma importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def ollama_client_mock():
    """Mock Ollama client for tests that do not require a real Ollama server."""
    mock = MagicMock()
    mock.chat.return_value = {"message": {"content": "Critical"}}
    return mock
