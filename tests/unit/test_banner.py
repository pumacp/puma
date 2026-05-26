"""Unit tests for the retro mainframe banner (US-12.11)."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError

import pytest
from rich.console import Console
from rich.panel import Panel

from puma.ui import banner


def _render_to_text() -> str:
    console = Console(width=120, force_terminal=False)
    with console.capture() as cap:
        console.print(banner.render_banner())
    return cap.get()


@pytest.mark.unit
class TestBanner:
    def test_render_banner_returns_panel(self):
        assert isinstance(banner.render_banner(), Panel)

    def test_render_banner_contains_puma_text(self):
        out = _render_to_text()
        # The block figlet font spells PUMA in glyph rows (the literal
        # "PUMA" string is not present), so assert non-trivial rendered
        # content plus the human-readable tagline.
        assert len(out) > 100
        assert "Local LLM benchmarks for project management" in out

    def test_render_banner_contains_version(self):
        out = _render_to_text()
        assert banner._resolve_puma_version() in out

    def test_resolve_puma_version_fallback(self, monkeypatch):
        def _raise(_name: str) -> str:
            raise PackageNotFoundError(_name)

        monkeypatch.setattr("puma.ui.banner.version", _raise)
        assert banner._resolve_puma_version() == "0.0.0-unknown"

    def test_print_banner_writes_to_console(self):
        console = Console(width=120, force_terminal=False)
        with console.capture() as cap:
            banner.print_banner(console)
        assert cap.get().strip()
