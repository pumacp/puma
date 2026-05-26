"""Unit tests for the themed progress factory (US-12.12)."""

from __future__ import annotations

from io import StringIO

import pytest
from rich.console import Console
from rich.progress import BarColumn, SpinnerColumn

from puma.ui.progress import make_progress
from puma.ui.themes import get_theme


def _spinner(progress) -> SpinnerColumn:
    return next(c for c in progress.columns if isinstance(c, SpinnerColumn))


def _bar(progress) -> BarColumn:
    return next(c for c in progress.columns if isinstance(c, BarColumn))


@pytest.mark.unit
class TestProgress:
    def test_make_progress_returns_disabled_when_enabled_false(self):
        # Force a terminal so only `enabled=False` drives the disable.
        p = make_progress(get_theme("amber"), console=Console(force_terminal=True), enabled=False)
        assert p.disable is True

    def test_make_progress_returns_disabled_when_console_not_terminal(self):
        non_tty = Console(file=StringIO())
        assert non_tty.is_terminal is False
        p = make_progress(get_theme("amber"), console=non_tty, enabled=True)
        assert p.disable is True

    def test_make_progress_columns_use_amber_when_theme_amber(self):
        p = make_progress(get_theme("amber"), console=Console(force_terminal=True), enabled=True)
        assert p.disable is False
        assert _spinner(p).spinner.style == "orange3"
        assert _bar(p).complete_style == "orange3"
        assert _bar(p).finished_style == "green3"

    def test_make_progress_columns_use_green_when_theme_green(self):
        p = make_progress(get_theme("green"), console=Console(force_terminal=True), enabled=True)
        assert _spinner(p).spinner.style == "green3"
        assert _bar(p).complete_style == "green3"
        assert _bar(p).finished_style == "bright_green"

    def test_make_progress_writes_to_stderr_console_by_default(self):
        p = make_progress(get_theme("amber"))
        assert p.console.stderr is True
