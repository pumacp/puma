"""Unit tests for the themed run-summary renderer (US-12.12)."""

from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console
from rich.panel import Panel

from puma.ui.summary import _samples_cell, print_run_summary, render_run_summary
from puma.ui.themes import get_theme

_BASE: dict = {
    "run_id": "run-1",
    "task": "triage_jira",
    "model": "qwen2.5:3b",
    "profile": "gpu-entry",
    "samples_total": 10,
    "samples_succeeded": 10,
    "samples_failed": 0,
    "primary_metric_name": "f1_macro",
    "primary_metric_value": 0.5831,
    "runtime_seconds": 42.3,
    "emissions_g_co2": 0.1131,
    "predictions_path": Path("/tmp/x.predictions.jsonl"),
}


def _to_text(renderable) -> str:
    console = Console(file=StringIO(), force_terminal=False, width=120)
    console.print(renderable)
    return console.file.getvalue()


@pytest.mark.unit
class TestSummary:
    def test_render_run_summary_amber_uses_orange3_border(self):
        panel = render_run_summary(get_theme("amber"), **_BASE)
        assert isinstance(panel, Panel)
        assert panel.border_style == "orange3"

    def test_render_run_summary_green_uses_green3_border(self):
        panel = render_run_summary(get_theme("green"), **_BASE)
        assert panel.border_style == "green3"

    def test_render_run_summary_failed_samples_styled_error_when_failures_present(self):
        cell = _samples_cell(get_theme("amber"), 8, 2, 10)
        assert "red3" in [str(s.style) for s in cell.spans]

    def test_render_run_summary_failed_samples_styled_muted_when_zero_failures(self):
        styles = [str(s.style) for s in _samples_cell(get_theme("amber"), 10, 0, 10).spans]
        assert "red3" not in styles
        assert "grey50" in styles

    def test_render_run_summary_emissions_dash_when_none(self):
        out = _to_text(render_run_summary(get_theme("amber"), **{**_BASE, "emissions_g_co2": None}))
        assert "gCO2eq" not in out
        assert "—" in out

    def test_render_run_summary_predictions_dash_when_none(self):
        out = _to_text(
            render_run_summary(get_theme("amber"), **{**_BASE, "predictions_path": None})
        )
        assert "—" in out

    def test_render_run_summary_does_not_raise_on_none_fields(self):
        panel = render_run_summary(
            get_theme("amber"),
            **{
                **_BASE,
                "profile": None,
                "emissions_g_co2": None,
                "predictions_path": None,
                "primary_metric_value": float("nan"),
            },
        )
        assert isinstance(panel, Panel)

    def test_print_run_summary_writes_to_stderr_console(self):
        console = Console(file=StringIO(), stderr=True, force_terminal=True, width=120)
        print_run_summary(console, get_theme("amber"), **_BASE)
        assert "Run summary" in console.file.getvalue()
