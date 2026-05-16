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

VALID_PROFILES = {
    "cpu-lite",
    "cpu-standard",
    "gpu-entry",
    "gpu-mid",
    "gpu-high",
    # Apple Silicon profiles introduced in v2.6.0 (catalog_version 2.6.0).
    # Empirical validation pending — see config/profiles.yaml and
    # docs/CROSS_ARCH_REPRODUCIBILITY.md.
    "apple-silicon-m3",
    "apple-silicon-m3-pro",
    "apple-silicon-m3-max",
    "apple-silicon-m4",
    "apple-silicon-m4-pro",
    "apple-silicon-m4-max",
    "apple-silicon-m5",
    "apple-silicon-m5-pro",
    "apple-silicon-m5-max",
    "apple-silicon-m5-ultra",
}

APPLE_SILICON_PROFILES = {p for p in VALID_PROFILES if p.startswith("apple-silicon-")}

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
    assert raw.get("catalog_version") == "2.7.0", (
        f"catalog_version must be '2.7.0' for this release; got {raw.get('catalog_version')!r}"
    )
    assert raw.get("catalog_changelog_path") == "docs/CATALOG_HISTORY.md", (
        f"catalog_changelog_path must point to docs/CATALOG_HISTORY.md; "
        f"got {raw.get('catalog_changelog_path')!r}"
    )


@pytest.mark.unit
def test_valid_profiles_includes_all_apple_silicon_identifiers() -> None:
    """v2.6.0 introduces 9 Apple Silicon profile identifiers (M3/M4/M5
    base, Pro, Max + M5 Ultra). They must all be in VALID_PROFILES so the
    internal-consistency check accepts model entries that include them."""
    expected = {
        "apple-silicon-m3",
        "apple-silicon-m3-pro",
        "apple-silicon-m3-max",
        "apple-silicon-m4",
        "apple-silicon-m4-pro",
        "apple-silicon-m4-max",
        "apple-silicon-m5",
        "apple-silicon-m5-pro",
        "apple-silicon-m5-max",
        "apple-silicon-m5-ultra",
    }
    assert expected.issubset(VALID_PROFILES), f"missing: {expected - VALID_PROFILES}"


@pytest.mark.unit
def test_apple_silicon_profiles_defined_in_profiles_yaml(profiles: dict) -> None:
    """All 9 apple-silicon-* identifiers must be defined as profiles in
    config/profiles.yaml with the v2.6.0 schema extension (apple_silicon_required
    + chip_brand_match + min_unified_memory_gb)."""
    for name in APPLE_SILICON_PROFILES:
        assert name in profiles, f"{name} missing from profiles.yaml"
        req = profiles[name]["requirements"]
        assert req.get("apple_silicon_required") is True, (
            f"{name} must declare apple_silicon_required: true"
        )
        assert isinstance(req.get("chip_brand_match"), str), (
            f"{name} must declare a chip_brand_match string"
        )
        assert req["chip_brand_match"].startswith("Apple M"), (
            f"{name} chip_brand_match must start with 'Apple M'"
        )
        assert isinstance(req.get("min_unified_memory_gb"), int), (
            f"{name} must declare an integer min_unified_memory_gb"
        )
        assert profiles[name].get("empirical_validation") == "pending", (
            f"{name} must declare empirical_validation: pending until Mac hardware "
            f"validation is performed"
        )


@pytest.mark.unit
def test_apple_silicon_chip_brand_match_is_unique(profiles: dict) -> None:
    """Each apple-silicon-* profile must map to a distinct chip brand —
    select_profile() relies on the chip_brand_match being unique to dispatch."""
    brands = [profiles[name]["requirements"]["chip_brand_match"] for name in APPLE_SILICON_PROFILES]
    assert len(brands) == len(set(brands)), f"duplicate chip_brand_match entries: {brands}"


@pytest.mark.unit
def test_gemma4_family_not_compatible_with_any_apple_silicon() -> None:
    """P2/P6 reinforcement: the gemma4 family is excluded from every
    apple-silicon-* profile. Same VRAM-pressure failure mode as on
    gpu-entry (RTX 2060 6 GB) applies to small unified-memory variants;
    re-enabling requires new empirical evidence on Mac hardware. Also
    guards against accidental copy-paste of profile lists during future
    catalog edits."""
    catalog = {entry.ollama_tag: entry for entry in load_catalog()}
    for tag in ("gemma4:e2b", "gemma4:e4b", "gemma4:26b-a4b"):
        entry = catalog.get(tag)
        if entry is None:
            continue
        for profile in entry.profiles_compatible:
            assert not profile.startswith("apple-silicon-"), (
                f"{tag} must not advertise any apple-silicon-* profile (P6, D18 by "
                f"analogy on unified memory pressure); got {entry.profiles_compatible}"
            )


@pytest.mark.unit
def test_qwen25_3b_compatible_with_apple_silicon_m4_pro() -> None:
    """Anchor test: the canonical model used by puma validate-baseline
    must be advertised on at least one Apple Silicon Pro variant so a
    Mac user can run the canonical baseline natively when the time
    comes for validation."""
    catalog = {entry.ollama_tag: entry for entry in load_catalog()}
    entry = catalog["qwen2.5:3b"]
    assert "apple-silicon-m4-pro" in entry.profiles_compatible


@pytest.mark.unit
def test_qwen3_30b_catalogued_correctly() -> None:
    """v2.7.0 introduces ``qwen3:30b`` (dense). The entry must use the real
    Ollama tag (verified via registry probe; ``qwen3:27b`` returns 404 so
    the originally-planned 'Qwen3.6 27B Dense' is mapped to qwen3:30b),
    declare gpu-high only, advertise the verified GGUF size, and conserve
    logprobs_supported=False pending empirical verification."""
    catalog = {entry.ollama_tag: entry for entry in load_catalog()}
    entry = catalog.get("qwen3:30b")
    assert entry is not None, "qwen3:30b must be in the v2.7.0 catalog"
    assert entry.params_b == 30.0
    assert entry.gguf_size_gb == 17.3  # verified via Ollama registry manifest
    assert entry.context_window == 262144
    assert entry.logprobs_supported is False, (
        "logprobs_supported conservatively false until empirical verification"
    )
    assert entry.profiles_compatible == ["gpu-high"], (
        f"qwen3:30b must target gpu-high only (P10/P11); got {entry.profiles_compatible}"
    )


@pytest.mark.unit
def test_qwen3_30b_a3b_catalogued_correctly() -> None:
    """v2.7.0 introduces ``qwen3:30b-a3b`` (MoE: 30B total, ~3B active).
    Real Ollama tag (verified); planned 'Qwen3.6 35B-A3B' was 404 so we
    map to the 30B-A3B variant. params_b follows the gemma4:26b-a4b
    precedent (TOTAL when the tag encodes both); the notes field carries
    the F8/D18 caveat for MoE GGUF sizing."""
    catalog = {entry.ollama_tag: entry for entry in load_catalog()}
    entry = catalog.get("qwen3:30b-a3b")
    assert entry is not None, "qwen3:30b-a3b must be in the v2.7.0 catalog"
    assert entry.params_b == 30.0, "MoE convention (gemma4:26b-a4b precedent): params_b is TOTAL"
    assert entry.gguf_size_gb == 17.3
    assert entry.context_window == 262144
    assert entry.logprobs_supported is False
    assert entry.profiles_compatible == ["gpu-high"]
    # The F8 caveat must appear in notes (regression guard against future
    # edits stripping the MoE-sizing context from the docstring).
    assert entry.notes is not None
    assert "F8" in entry.notes or "MoE" in entry.notes, (
        "qwen3:30b-a3b notes must reference the MoE/F8 caveat"
    )


@pytest.mark.unit
def test_qwen3_entries_excluded_from_gpu_entry() -> None:
    """P10/P11: new entries added in v2.7.0 must NOT appear in gpu-entry
    until empirical validation occurs. PUMA's validation hardware (RTX
    2060 Mobile 6 GB) cannot run a 17.3 GB GGUF; advertising gpu-entry
    compatibility without evidence would repeat the gemma4 D18 failure
    mode on a new model family."""
    catalog = {entry.ollama_tag: entry for entry in load_catalog()}
    for tag in ("qwen3:30b", "qwen3:30b-a3b"):
        entry = catalog.get(tag)
        assert entry is not None
        assert "gpu-entry" not in entry.profiles_compatible, (
            f"{tag} must not advertise gpu-entry until empirical validation "
            f"on appropriate hardware (P10/P11)"
        )


@pytest.mark.unit
def test_qwen3_entries_excluded_from_all_apple_silicon() -> None:
    """P11 generalisation: pending-validation entries also exclude every
    apple-silicon-* profile. Unified-memory pressure on smaller M-series
    variants is the same VRAM-pressure failure mode that motivated the
    gpu-entry exclusion for gemma4 (D18/F8). Re-enabling requires new
    empirical evidence and an explicit debt entry."""
    catalog = {entry.ollama_tag: entry for entry in load_catalog()}
    for tag in ("qwen3:30b", "qwen3:30b-a3b"):
        entry = catalog.get(tag)
        assert entry is not None
        for profile in entry.profiles_compatible:
            assert not profile.startswith("apple-silicon-"), (
                f"{tag} must not advertise any apple-silicon-* profile "
                f"(P11 pending-validation invariant); "
                f"got {entry.profiles_compatible}"
            )


@pytest.mark.unit
def test_qwen3_entries_target_gpu_high_only() -> None:
    """Anchor: v2.7.0 ships qwen3:* with profiles_compatible == ['gpu-high'].
    This is the empirically-safe target given 17.3 GB GGUF: gpu-mid (12-24 GB
    VRAM) is borderline once the operating system and context are accounted
    for; gpu-high (24+ GB) is the only safe default. The test pins the
    decision so that loosening it requires deliberate intent."""
    catalog = {entry.ollama_tag: entry for entry in load_catalog()}
    for tag in ("qwen3:30b", "qwen3:30b-a3b"):
        entry = catalog.get(tag)
        assert entry is not None
        assert entry.profiles_compatible == ["gpu-high"], (
            f"{tag}.profiles_compatible must equal ['gpu-high'] in v2.7.0; "
            f"got {entry.profiles_compatible}"
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
