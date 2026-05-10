"""Tests for the model-catalog reader (puma.preflight.catalog).

The catalog (`config/models_catalog.yaml`) is the single source of truth
for model metadata after B.1.3. ``models_for_profile`` derives the per-profile
dispatch list dynamically from the catalog, replacing the manual
``profile.models[]`` list that previously lived in ``config/profiles.yaml``.

Authored under TDD per rule §0.6: every test fails until B.1.3.b lands the
implementation.
"""

from __future__ import annotations

import pytest

# Module under test — does not exist before B.1.3.b
from puma.preflight.catalog import ModelEntry, get_model_by_tag, load_catalog, models_for_profile


@pytest.mark.unit
def test_load_catalog_returns_all_entries() -> None:
    """Catalog file currently lists 15 models; load_catalog must return all of them."""
    catalog = load_catalog()
    assert len(catalog) == 15
    assert all(isinstance(m, ModelEntry) for m in catalog)
    assert all(m.ollama_tag for m in catalog)


@pytest.mark.unit
def test_model_entry_has_required_fields() -> None:
    """Each ModelEntry must populate the metadata fields with sensible types."""
    catalog = load_catalog()
    for m in catalog:
        assert m.ollama_tag and ":" in m.ollama_tag, f"bad tag: {m.ollama_tag!r}"
        assert m.params_b > 0, f"{m.ollama_tag}: params_b must be > 0"
        assert m.gguf_size_gb > 0, f"{m.ollama_tag}: gguf_size_gb must be > 0"
        assert m.context_window > 0, f"{m.ollama_tag}: context_window must be > 0"
        assert isinstance(m.profiles_compatible, list)
        assert isinstance(m.logprobs_supported, bool)


@pytest.mark.unit
def test_models_for_profile_returns_compatible_subset() -> None:
    """models_for_profile filters the catalog by profiles_compatible[]."""
    cpu_lite_models = models_for_profile("cpu-lite")
    assert len(cpu_lite_models) >= 1
    assert all("cpu-lite" in m.profiles_compatible for m in cpu_lite_models)


@pytest.mark.unit
def test_models_for_profile_unknown_returns_empty() -> None:
    """Unknown profile name yields an empty list (does not raise)."""
    assert models_for_profile("nonexistent-profile") == []


@pytest.mark.unit
def test_models_for_profile_gpu_entry_includes_previously_missing_models() -> None:
    """Specific to the gap detected in B.1.1 Test 2: the catalog declares
    qwen2.5:1.5b and qwen2.5:7b compatible with gpu-entry but the old
    profiles.yaml.gpu-entry.models[] did not list them. Dynamic dispatch
    must surface them."""
    gpu_entry_models = models_for_profile("gpu-entry")
    tags = [m.ollama_tag for m in gpu_entry_models]
    assert "qwen2.5:1.5b" in tags, "1.5b is catalog-compat with gpu-entry"
    assert "qwen2.5:7b" in tags, "7b is catalog-compat with gpu-entry"


@pytest.mark.unit
def test_get_model_by_tag_returns_correct_entry() -> None:
    """get_model_by_tag returns the matching ModelEntry."""
    m = get_model_by_tag("qwen2.5:3b")
    assert m is not None
    assert m.ollama_tag == "qwen2.5:3b"
    assert m.params_b == 3.0
    assert m.gguf_size_gb == 1.9


@pytest.mark.unit
def test_get_model_by_tag_unknown_returns_none() -> None:
    """get_model_by_tag returns None for unknown tags (dict.get-like API)."""
    assert get_model_by_tag("nonexistent:99b") is None
