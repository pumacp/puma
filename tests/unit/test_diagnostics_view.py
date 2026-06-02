"""Unit tests for the diagnostics table renderers (US-12.13)."""

from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console
from rich.panel import Panel

from puma.diagnostics.checks import CheckResult
from puma.diagnostics.env import collect_environment
from puma.ui.diagnostics_view import _status_cell, render_doctor_table, render_env_table
from puma.ui.themes import get_theme


@pytest.mark.unit
class TestDiagnosticsView:
    def test_render_doctor_table_styles_ok_with_success_color(self):
        assert _status_cell(get_theme("amber"), "ok").style == "green3"

    def test_render_doctor_table_styles_warn_with_warning_color(self):
        assert _status_cell(get_theme("amber"), "warn").style == "yellow3"

    def test_render_doctor_table_styles_fail_with_error_color(self):
        assert _status_cell(get_theme("amber"), "fail").style == "red3"

    def test_render_doctor_table_omits_hint_column_when_no_hints(self):
        no_hint = render_doctor_table(get_theme("amber"), [CheckResult("X", "ok", "d")])
        with_hint = render_doctor_table(
            get_theme("amber"), [CheckResult("X", "fail", "d", hint="h")]
        )
        assert isinstance(no_hint, Panel)
        assert len(no_hint.renderable.columns) == 3
        assert len(with_hint.renderable.columns) == 4

    def test_render_env_table_includes_all_fields(self):
        env = collect_environment(get_theme("amber"), "http://h:11434", Path("data/puma.db"))
        console = Console(file=StringIO(), force_terminal=False, width=140)
        console.print(render_env_table(get_theme("amber"), env))
        out = console.file.getvalue()
        for label in (
            "PUMA version",
            "Python",
            "Platform",
            "Theme",
            "Profile",
            "Ollama endpoint",
            "Database",
            "Cache dirs",
        ):
            assert label in out
