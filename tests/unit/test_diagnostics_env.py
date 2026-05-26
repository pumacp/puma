"""Unit tests for puma env introspection (US-12.13)."""

from __future__ import annotations

from pathlib import Path

import pytest

from puma.diagnostics.env import EnvironmentInfo, collect_environment
from puma.ui.themes import get_theme


@pytest.mark.unit
def test_collect_environment_returns_populated():
    env = collect_environment(get_theme("amber"), "http://h:11434", Path("data/puma.db"))
    assert isinstance(env, EnvironmentInfo)
    assert env.puma_version
    assert env.python_version
    assert env.platform
    assert env.theme == "amber"
    assert env.profile  # a profile name or the "—" fallback
    assert env.ollama_endpoint == "http://h:11434"
    assert env.db_path == "data/puma.db"
    assert env.cache_dirs
