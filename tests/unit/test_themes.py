"""Unit tests for the CLI color theme registry (US-12.12)."""

from __future__ import annotations

import pytest

from puma.ui.themes import THEMES, Theme, get_theme


@pytest.mark.unit
class TestThemes:
    def test_registry_has_amber_and_green(self):
        assert set(THEMES) == {"amber", "green"}
        assert isinstance(THEMES["amber"], Theme)
        assert isinstance(THEMES["green"], Theme)

    def test_get_theme_default_returns_amber(self, monkeypatch):
        monkeypatch.delenv("PUMA_THEME", raising=False)
        assert get_theme().name == "amber"

    def test_get_theme_env_var_green(self, monkeypatch):
        monkeypatch.setenv("PUMA_THEME", "green")
        assert get_theme().name == "green"

    def test_get_theme_explicit_overrides_env(self, monkeypatch):
        monkeypatch.setenv("PUMA_THEME", "green")
        assert get_theme("amber").name == "amber"

    def test_get_theme_unknown_name_raises(self, monkeypatch):
        monkeypatch.delenv("PUMA_THEME", raising=False)
        with pytest.raises(ValueError, match="Unknown theme 'purple'") as exc:
            get_theme("purple")
        assert "amber" in str(exc.value)
        assert "green" in str(exc.value)

    def test_get_theme_unknown_env_raises(self, monkeypatch):
        monkeypatch.setenv("PUMA_THEME", "purple")
        with pytest.raises(ValueError, match="Unknown theme 'purple'"):
            get_theme()
