"""CLI-level tests for the `puma models` discovery sub-group (US-12.14)."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from puma.cli import app
from puma.models.client import LocalModel, ModelNotFound, OllamaUnreachable

runner = CliRunner()

_WIDE = {"COLUMNS": "200"}


def _models() -> list[LocalModel]:
    return [
        LocalModel(
            name="qwen2.5:3b",
            size_bytes=1_900_000_000,
            digest="d1",
            modified_at="2026-05-20",
            parameter_size="3.1B",
            quantization="Q4_K_M",
            family="qwen2",
        ),
        LocalModel(
            name="mistral:7b",
            size_bytes=4_400_000_000,
            digest="d2",
            modified_at="2026-05-01",
            parameter_size="7B",
            quantization="Q4_0",
            family="llama",
        ),
    ]


@pytest.mark.unit
class TestModelsCli:
    def test_models_list_exit_0_with_table(self, monkeypatch):
        monkeypatch.setattr("puma.models.client.list_local_models", lambda **k: _models())
        result = runner.invoke(app, ["models", "list"], env=_WIDE)
        assert result.exit_code == 0
        assert "qwen2.5:3b" in result.stdout

    def test_models_list_exit_1_when_ollama_unreachable(self, monkeypatch):
        def boom(**k):
            raise OllamaUnreachable("down")

        monkeypatch.setattr("puma.models.client.list_local_models", boom)
        result = runner.invoke(app, ["models", "list"])
        assert result.exit_code == 1

    def test_models_show_exit_0_with_panel(self, monkeypatch):
        monkeypatch.setattr("puma.models.client.show_local_model", lambda **k: _models()[0])
        result = runner.invoke(app, ["models", "show", "qwen2.5:3b"], env=_WIDE)
        assert result.exit_code == 0
        assert "qwen2.5:3b" in result.stdout

    def test_models_show_exit_1_when_model_not_found(self, monkeypatch):
        def boom(**k):
            raise ModelNotFound("nope")

        monkeypatch.setattr("puma.models.client.show_local_model", boom)
        result = runner.invoke(app, ["models", "show", "ghost:1b"])
        assert result.exit_code == 1

    def test_models_recommended_exit_0_when_ollama_ok(self, monkeypatch):
        monkeypatch.setattr("puma.models.client.list_local_models", lambda **k: _models())
        result = runner.invoke(app, ["models", "recommended"], env=_WIDE)
        assert result.exit_code == 0
        assert "qwen2.5:3b" in result.stdout

    def test_models_recommended_exit_0_when_ollama_unreachable(self, monkeypatch):
        def boom(**k):
            raise OllamaUnreachable("down")

        monkeypatch.setattr("puma.models.client.list_local_models", boom)
        result = runner.invoke(app, ["models", "recommended"], env=_WIDE)
        # Graceful: the curated table still renders, with Local? all "—".
        assert result.exit_code == 0
        assert "qwen2.5:3b" in result.stdout

    def test_models_respects_theme(self, monkeypatch):
        seen: dict[str, str] = {}

        def cap(label):
            def _fake(theme, *a, **k):
                from rich.text import Text

                seen[label] = theme.name
                return Text("stub")

            return _fake

        monkeypatch.setattr("puma.ui.models_view.render_models_list_table", cap("list"))
        monkeypatch.setattr("puma.ui.models_view.render_model_show_panel", cap("show"))
        monkeypatch.setattr("puma.ui.models_view.render_recommended_table", cap("recommended"))
        monkeypatch.setattr("puma.models.client.list_local_models", lambda **k: _models())
        monkeypatch.setattr("puma.models.client.show_local_model", lambda **k: _models()[0])

        assert runner.invoke(app, ["--theme", "green", "models", "list"]).exit_code == 0
        assert (
            runner.invoke(app, ["--theme", "green", "models", "show", "qwen2.5:3b"]).exit_code == 0
        )
        assert runner.invoke(app, ["--theme", "green", "models", "recommended"]).exit_code == 0
        assert seen == {"list": "green", "show": "green", "recommended": "green"}
