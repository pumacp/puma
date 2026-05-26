"""Unit tests for the models table/panel renderers (US-12.14)."""

from __future__ import annotations

from io import StringIO

import pytest
from rich.console import Console
from rich.panel import Panel

from puma.models.catalog import CuratedModel
from puma.models.client import LocalModel
from puma.ui.models_view import (
    _status_text,
    render_model_show_panel,
    render_models_list_table,
    render_recommended_table,
)
from puma.ui.themes import get_theme


def _local(name: str = "qwen2.5:3b") -> LocalModel:
    return LocalModel(
        name=name,
        size_bytes=1_900_000_000,
        digest="sha256:deadbeef",
        modified_at="2026-05-20T10:00:00Z",
        parameter_size="3.1B",
        quantization="Q4_K_M",
        family="qwen2",
    )


def _curated(name: str, status: str) -> CuratedModel:
    return CuratedModel(
        name=name,
        family=name.split(":")[0].capitalize(),
        parameter_size_b=3.0,
        gguf_size_gb=1.9,
        context_window=32768,
        validated_for=frozenset({"triage", "estimation"}),
        status=status,
        rationale="comparison baseline",
    )


@pytest.mark.unit
class TestModelsView:
    def test_render_models_list_table_amber_uses_orange3(self):
        panel = render_models_list_table(get_theme("amber"), [_local()])
        assert isinstance(panel, Panel)
        assert panel.renderable.columns[0].style == "orange3"

    def test_render_models_list_table_empty_shows_help_message(self):
        panel = render_models_list_table(get_theme("amber"), [])
        console = Console(file=StringIO(), force_terminal=False, width=100)
        console.print(panel)
        out = console.file.getvalue()
        assert "No models pulled locally" in out
        assert "ollama pull" in out

    def test_render_model_show_panel_includes_all_fields(self):
        console = Console(file=StringIO(), force_terminal=False, width=140)
        console.print(render_model_show_panel(get_theme("amber"), _local()))
        out = console.file.getvalue()
        for label in ("Name", "Family", "Parameters", "Quantization", "Size", "Digest", "Modified"):
            assert label in out
        assert "qwen2.5:3b" in out

    def test_render_recommended_table_local_column_marks_pulled(self):
        pairs = [
            (_curated("qwen2.5:3b", "validated"), _local("qwen2.5:3b")),
            (_curated("mistral:7b", "experimental"), None),
        ]
        console = Console(file=StringIO(), force_terminal=False, width=200)
        console.print(render_recommended_table(get_theme("amber"), pairs))
        out = console.file.getvalue()
        assert "✓" in out  # pulled model marked present
        assert "—" in out  # unpulled model marked absent

    def test_render_recommended_table_status_color_validated_vs_experimental(self):
        theme = get_theme("amber")
        assert _status_text(theme, "validated").style == theme.success
        assert _status_text(theme, "experimental").style == theme.warning
