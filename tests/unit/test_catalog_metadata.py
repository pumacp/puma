"""Catalog metadata sanity tests.

After B.1.3 the catalog (``config/models_catalog.yaml``) is the single
source of truth for model dispatch — ``profiles.yaml`` no longer carries a
``models[]`` list per profile, so the bidirectional consistency tests
(formerly Tests 2 and 3) are now trivially true by construction and have
been removed. The remaining checks verify only that the catalog itself is
internally well-formed.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from puma.preflight.catalog import load_catalog

VALID_PROFILES = {"cpu-lite", "cpu-standard", "gpu-entry", "gpu-mid", "gpu-high"}

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PROFILES_PATH = _REPO_ROOT / "config" / "profiles.yaml"

# Ollama tag format: <name>:<tag>. Name allows lowercase letters, digits, dots,
# dashes, slashes; tag allows the same plus letters/digits/hyphens.
_TAG_RE = re.compile(r"^[a-z0-9][a-z0-9._/\-]*:[a-zA-Z0-9._\-]+$")


@pytest.fixture(scope="module")
def profiles() -> dict:
    with open(_PROFILES_PATH, encoding="utf-8") as fh:
        return yaml.safe_load(fh)["profiles"]


@pytest.mark.unit
def test_catalog_has_at_least_one_entry() -> None:
    """A catalog with zero entries would silently disable every profile."""
    assert len(load_catalog()) > 0


@pytest.mark.unit
def test_model_metadata_is_internally_consistent() -> None:
    """Each catalog entry must have positive numeric metadata, a parseable
    ollama_tag, and a profiles_compatible[] that is a subset of VALID_PROFILES."""
    errors: list[str] = []
    for entry in load_catalog():
        tag = entry.ollama_tag

        if not isinstance(entry.gguf_size_gb, int | float) or entry.gguf_size_gb <= 0:
            errors.append(f"{tag}: gguf_size_gb must be > 0 (got {entry.gguf_size_gb!r})")
        if not isinstance(entry.params_b, int | float) or entry.params_b <= 0:
            errors.append(f"{tag}: params_b must be > 0 (got {entry.params_b!r})")
        if not isinstance(entry.context_window, int) or entry.context_window <= 0:
            errors.append(f"{tag}: context_window must be > 0 int (got {entry.context_window!r})")
        if not isinstance(tag, str) or not _TAG_RE.match(tag):
            errors.append(f"{tag!r}: ollama_tag does not match name:tag format")

        unknown = set(entry.profiles_compatible) - VALID_PROFILES
        if unknown:
            errors.append(f"{tag}: unknown profiles in compatible list: {sorted(unknown)}")

    assert not errors, "Catalog metadata violations:\n  " + "\n  ".join(errors)


@pytest.mark.unit
def test_profile_has_at_least_one_compatible_model(profiles: dict) -> None:
    """Every defined profile must have at least one catalog entry that
    declares it in ``profiles_compatible``. Otherwise the profile would
    select hardware but dispatch zero models — equivalent to the old
    'profile.models is empty' failure mode."""
    catalog = load_catalog()
    empty: list[str] = []
    for profile_name in profiles:
        compatible = [m for m in catalog if profile_name in m.profiles_compatible]
        if not compatible:
            empty.append(profile_name)
    assert not empty, f"Profiles with zero catalog-compatible models: {empty}"


@pytest.mark.unit
def test_catalog_has_version_field() -> None:
    """v2.5.0 introduced a ``catalog_version`` root field and a pointer to
    docs/CATALOG_HISTORY.md. Both fields are read by docs tooling and by
    the user-facing version string; they must remain present and match
    the expected values for the current release."""
    catalog_path = _REPO_ROOT / "config" / "models_catalog.yaml"
    with open(catalog_path, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    assert raw.get("catalog_version") == "2.5.0", (
        f"catalog_version must be '2.5.0' for this release; got {raw.get('catalog_version')!r}"
    )
    assert raw.get("catalog_changelog_path") == "docs/CATALOG_HISTORY.md", (
        f"catalog_changelog_path must point to docs/CATALOG_HISTORY.md; "
        f"got {raw.get('catalog_changelog_path')!r}"
    )


@pytest.mark.unit
def test_gemma4_family_excluded_from_gpu_entry() -> None:
    """D18 resolution: gemma4 family is empirically incompatible with the
    gpu-entry profile (6 GB VRAM forces CPU offload, which breaks Ollama's
    detokenizer for MoE outputs on structured prompts; B.3 sweep recorded
    parse_failure_rate 0.98-1.00 and S2.2 inspection confirmed
    raw_response='' despite non-zero eval_count). The catalog must therefore
    not advertise gpu-entry compatibility for any gemma4 tag."""
    catalog = {entry.ollama_tag: entry for entry in load_catalog()}
    for tag in ("gemma4:e2b", "gemma4:e4b", "gemma4:26b-a4b"):
        entry = catalog.get(tag)
        if entry is None:
            # Catalog may evolve; skip if tag has been removed entirely.
            continue
        assert "gpu-entry" not in entry.profiles_compatible, (
            f"{tag} must not advertise gpu-entry compatibility (D18): "
            f"got {entry.profiles_compatible}"
        )
