"""Unit tests for the read-only Ollama discovery client (US-12.14)."""

from __future__ import annotations

import httpx
import pytest

from puma.models.client import (
    LocalModel,
    ModelNotFound,
    OllamaUnreachable,
    list_local_models,
    show_local_model,
)


class _FakeResp:
    def __init__(self, status_code: int = 200, payload: dict | None = None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPError(f"HTTP {self.status_code}")


@pytest.mark.unit
class TestListLocalModels:
    def test_list_local_models_parses_api_tags_response(self, monkeypatch):
        payload = {
            "models": [
                {
                    "name": "mistral:7b",
                    "size": 4_400_000_000,
                    "digest": "d2",
                    "modified_at": "2026-05-01",
                    "details": {
                        "parameter_size": "7B",
                        "quantization_level": "Q4_0",
                        "family": "llama",
                    },
                },
                {
                    "name": "gemma3:1b",
                    "size": 800_000_000,
                    "digest": "d1",
                    "modified_at": "2026-05-02",
                    "details": {
                        "parameter_size": "1B",
                        "quantization_level": "Q4_K_M",
                        "family": "gemma3",
                    },
                },
            ]
        }
        monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResp(200, payload))
        models = list_local_models("http://h:11434")
        assert [m.name for m in models] == ["gemma3:1b", "mistral:7b"]  # sorted by name
        assert models[0].family == "gemma3"
        assert models[1].size_bytes == 4_400_000_000
        assert models[1].quantization == "Q4_0"

    def test_list_local_models_raises_ollama_unreachable_on_timeout(self, monkeypatch):
        def boom(*a, **k):
            raise httpx.TimeoutException("timeout")

        monkeypatch.setattr(httpx, "get", boom)
        with pytest.raises(OllamaUnreachable):
            list_local_models("http://h:11434")

    def test_list_local_models_raises_ollama_unreachable_on_connection_error(self, monkeypatch):
        def boom(*a, **k):
            raise httpx.ConnectError("refused")

        monkeypatch.setattr(httpx, "get", boom)
        with pytest.raises(OllamaUnreachable):
            list_local_models("http://h:11434")


@pytest.mark.unit
class TestShowLocalModel:
    def test_show_local_model_returns_merged_metadata(self, monkeypatch):
        tags_payload = {
            "models": [
                {
                    "name": "qwen2.5:3b",
                    "size": 1_900_000_000,
                    "digest": "sha256:abc",
                    "modified_at": "2026-05-20",
                    "details": {
                        "parameter_size": "3.1B",
                        "quantization_level": "Q4_K_M",
                        "family": "qwen2",
                    },
                }
            ]
        }
        show_payload = {
            "details": {
                "parameter_size": "3.1B",
                "quantization_level": "Q4_K_M",
                "family": "qwen2",
            }
        }
        monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResp(200, tags_payload))
        monkeypatch.setattr(httpx, "post", lambda *a, **k: _FakeResp(200, show_payload))
        model = show_local_model("http://h:11434", "qwen2.5:3b")
        assert model.name == "qwen2.5:3b"
        assert model.parameter_size == "3.1B"  # from /api/show details
        assert model.quantization == "Q4_K_M"
        assert model.family == "qwen2"
        assert model.size_bytes == 1_900_000_000  # merged from /api/tags
        assert model.digest == "sha256:abc"

    def test_show_local_model_raises_model_not_found_on_404(self, monkeypatch):
        monkeypatch.setattr(httpx, "post", lambda *a, **k: _FakeResp(404))
        with pytest.raises(ModelNotFound):
            show_local_model("http://h:11434", "ghost:1b")

    def test_show_local_model_raises_ollama_unreachable_on_timeout(self, monkeypatch):
        def boom(*a, **k):
            raise httpx.TimeoutException("timeout")

        monkeypatch.setattr(httpx, "post", boom)
        with pytest.raises(OllamaUnreachable):
            show_local_model("http://h:11434", "qwen2.5:3b")


@pytest.mark.unit
def test_local_model_is_frozen():
    from dataclasses import FrozenInstanceError

    m = LocalModel(name="x", size_bytes=1, digest="d", modified_at="m")
    with pytest.raises(FrozenInstanceError):
        m.name = "y"  # type: ignore[misc]
