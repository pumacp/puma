"""TDD-first tests for D21: per-model timeout propagation through the runtime.

The catalog (`config/models_catalog.yaml`) declares a per-model
``timeout_s`` value, surfaced as ``ModelEntry.timeout_s`` in
:mod:`puma.preflight.catalog`. Until S1.5.bis lands, that value is not
consumed by the orchestrator: ``Runner.run`` constructs ``OllamaClient``
with a hard-coded ``timeout_s=120.0``, so reasoning models like
``deepseek-r1:7b`` (catalog timeout 300 s) hit the client cap on every
inference and return empty responses to the parser.

The fix introduces ``client_for_model`` in :mod:`puma.runtime.client` and
threads the catalog timeout through it.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from puma.runtime.client import OllamaClient


@pytest.mark.unit
def test_ollama_client_default_timeout_is_120s() -> None:
    """Backwards-compat: when no timeout is given, default to 120 s."""
    client = OllamaClient(base_url="http://localhost:11434")
    assert client.timeout_s == 120.0


@pytest.mark.unit
def test_ollama_client_accepts_explicit_timeout() -> None:
    """Constructor honors an explicit ``timeout_s`` argument."""
    client = OllamaClient(base_url="http://localhost:11434", timeout_s=600.0)
    assert client.timeout_s == 600.0


@pytest.mark.unit
def test_client_for_model_uses_catalog_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """The factory looks the model up in the catalog and propagates timeout_s."""
    from puma.runtime import client as client_module

    @dataclass(frozen=True)
    class _StubEntry:
        ollama_tag: str
        timeout_s: int

    monkeypatch.setattr(
        client_module,
        "get_model_by_tag",
        lambda tag: _StubEntry(ollama_tag=tag, timeout_s=600),
    )
    built = client_module.client_for_model("deepseek-r1:7b", base_url="http://localhost:11434")
    assert isinstance(built, OllamaClient)
    assert built.timeout_s == 600.0


@pytest.mark.unit
def test_client_for_model_falls_back_when_unknown_tag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the catalog has no entry for the tag, the factory uses the default."""
    from puma.runtime import client as client_module

    monkeypatch.setattr(client_module, "get_model_by_tag", lambda tag: None)
    built = client_module.client_for_model("unknown:99b", base_url="http://localhost:11434")
    assert built.timeout_s == 120.0


@pytest.mark.unit
def test_client_for_model_real_catalog_returns_300_for_deepseek(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End-to-end with the real catalog: deepseek-r1:7b → 300 s."""
    from puma.runtime import client as client_module

    built = client_module.client_for_model("deepseek-r1:7b", base_url="http://localhost:11434")
    assert built.timeout_s == 300.0
