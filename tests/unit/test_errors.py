"""Unit tests for themed error rendering (US-12.12)."""

from __future__ import annotations

import sys
from io import StringIO

import pytest
from rich.console import Console
from rich.panel import Panel

from puma.ui.errors import (
    _is_expected,
    format_error_panel,
    install_themed_traceback,
    print_error,
)
from puma.ui.themes import get_theme


def _span_styles(panel: Panel) -> list[str]:
    return [str(s.style) for s in panel.renderable.spans]


@pytest.mark.unit
class TestErrors:
    def test_format_error_panel_uses_theme_error_border(self):
        for name in ("amber", "green"):
            panel = format_error_panel(get_theme(name), "Oops", "it broke")
            assert isinstance(panel, Panel)
            assert panel.border_style == "red3"  # both baseline themes use red3

    def test_format_error_panel_includes_hint_when_provided(self):
        panel = format_error_panel(get_theme("amber"), "T", "msg", hint="try X")
        assert "grey50" in _span_styles(panel)  # muted hint span

    def test_format_error_panel_omits_hint_when_none(self):
        panel = format_error_panel(get_theme("amber"), "T", "msg")
        assert "grey50" not in _span_styles(panel)

    def test_install_themed_traceback_idempotent(self):
        orig = sys.excepthook
        try:
            install_themed_traceback(get_theme("amber"))
            h1 = sys.excepthook
            install_themed_traceback(get_theme("green"))
            h2 = sys.excepthook
            # Both installs leave a Rich excepthook in place (not a stacked
            # wrapper of a wrapper).
            assert "rich" in getattr(h1, "__module__", "")
            assert "rich" in getattr(h2, "__module__", "")
        finally:
            sys.excepthook = orig

    def test_print_error_writes_to_stderr_console(self):
        console = Console(file=StringIO(), stderr=True, force_terminal=True, width=100)
        try:
            raise ValueError("bad value")
        except ValueError as exc:
            print_error(console, get_theme("amber"), exc, show_traceback=False)
        out = console.file.getvalue()
        assert "bad value" in out
        assert "ValueError" in out

    def test_print_error_shows_traceback_when_flag_true(self):
        console = Console(file=StringIO(), force_terminal=True, width=100)
        try:
            raise RuntimeError("boom")
        except RuntimeError as exc:
            print_error(console, get_theme("amber"), exc, show_traceback=True)
        assert "Traceback" in console.file.getvalue()

    def test_print_error_hides_traceback_when_flag_false(self):
        console = Console(file=StringIO(), force_terminal=True, width=100)
        try:
            raise RuntimeError("boom")
        except RuntimeError as exc:
            print_error(console, get_theme("amber"), exc, show_traceback=False)
        assert "Traceback" not in console.file.getvalue()

    def test_is_expected_classifies_filenotfound_as_expected(self):
        assert _is_expected(FileNotFoundError("x")) is True

    def test_is_expected_classifies_runtimeerror_as_unexpected(self):
        assert _is_expected(RuntimeError("x")) is False
