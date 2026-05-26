"""Unit tests for the curated-catalog adapter (US-12.14).

These tests exercise the YAML-driven loader (config/models_catalog.yaml is the
source of truth) rather than a hardcoded Python registry.
"""

from __future__ import annotations

import pytest

from puma.models.catalog import CuratedModel, load_curated, merge_with_local
from puma.models.client import LocalModel


@pytest.mark.unit
class TestLoadCurated:
    def test_load_curated_reads_yaml_returns_models(self):
        models = load_curated()
        assert isinstance(models, tuple)
        assert len(models) > 0
        names = {m.name for m in models}
        for expected in ("qwen2.5:3b", "mistral:7b", "llama3.1:8b", "gemma3:1b"):
            assert expected in names

    def test_load_curated_all_have_required_fields(self):
        for m in load_curated():
            assert isinstance(m, CuratedModel)
            assert m.name and m.family
            assert isinstance(m.parameter_size_b, float)
            assert isinstance(m.validated_for, frozenset)
            assert isinstance(m.status, str) and m.status
            assert isinstance(m.rationale, str)

    def test_load_curated_applies_field_gap_defaults(self):
        # config/models_catalog.yaml does not encode validated_for/status (D30);
        # every entry is presented with the conservative defaults.
        for m in load_curated():
            assert m.status == "experimental"
            assert m.validated_for == frozenset({"triage", "estimation"})

    def test_load_curated_derives_family_from_tag(self):
        by_name = {m.name: m for m in load_curated()}
        assert by_name["qwen2.5:3b"].family == "Qwen2.5"
        assert by_name["mistral:7b"].family == "Mistral"

    def test_load_curated_custom_path(self, tmp_path):
        yaml_text = (
            'catalog_version: "test"\n'
            "models:\n"
            '  - ollama_tag: "foo:1b"\n'
            "    params_b: 1.0\n"
            "    gguf_size_gb: 0.5\n"
            "    context_window: 2048\n"
            "    logprobs_supported: true\n"
            "    profiles_compatible: [cpu-lite]\n"
            "    timeout_s: 60\n"
            '    notes: "tiny test model"\n'
        )
        path = tmp_path / "catalog.yaml"
        path.write_text(yaml_text, encoding="utf-8")
        models = load_curated(path)
        assert len(models) == 1
        assert models[0].name == "foo:1b"
        assert models[0].rationale == "tiny test model"


@pytest.mark.unit
class TestMergeWithLocal:
    def test_merge_with_local_pairs_correctly(self):
        curated = load_curated()
        target = curated[0]
        local = [LocalModel(name=target.name, size_bytes=1, digest="d", modified_at="m")]
        pairs = merge_with_local(curated, local)
        matched = dict(pairs)
        assert matched[target] is not None
        assert matched[target].name == target.name

    def test_merge_with_local_returns_none_for_unpulled(self):
        curated = load_curated()
        pairs = merge_with_local(curated, [])  # nothing pulled locally
        assert len(pairs) == len(curated)
        assert all(local is None for _, local in pairs)
