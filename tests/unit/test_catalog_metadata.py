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
