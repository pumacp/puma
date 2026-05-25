"""Structural verification of codecarbon config across baseline profiles (US-12.6).

The five canonical (non-Apple-Silicon) baseline profiles are verified to:
  * load through the profile loader and round-trip their ``profile_id``;
  * declare **no** per-profile codecarbon settings — codecarbon is configured
    globally in the runner, not in ``config/profiles.yaml``, so cross-profile
    emissions are measured identically (the uniformity that makes a
    cross-profile comparison meaningful);
  * be selectable via ``spec.profile_required`` without crashing runner
    construction;
  * be rejected (no silent fallback) when an unknown id reaches the selector.

This is the structural half of E2. Empirical emissions verification is inherent
to the host's auto-detected profile (gpu-entry) and is exercised by the
canonical baselines after D25 enabled codecarbon; live measurement on other
hardware is out of scope for a single-host Sprint.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
import yaml

from puma.orchestrator.runner import Runner, _resolve_run_profile
from puma.orchestrator.runspec import RunSpec
from puma.preflight.profile import _PROFILES_PATH, _load_profiles, select_profile

# The five canonical, non-Apple-Silicon baseline profiles (config/profiles.yaml).
_BASELINE_PROFILES = ("cpu-lite", "cpu-standard", "gpu-entry", "gpu-mid", "gpu-high")

# Keys that, if present on any profile, would make codecarbon config
# per-profile (i.e. non-uniform). codecarbon settings must NOT appear here.
_CODECARBON_KEYS = {
    "codecarbon",
    "tracking_mode",
    "measure_power_secs",
    "country_iso",
    "country_code",
    "output_dir",
    "save_to_file",
}


def _raw_profiles() -> dict:
    with open(_PROFILES_PATH, encoding="utf-8") as fh:
        return yaml.safe_load(fh)["profiles"]


def _spec(profile_required: str | None) -> RunSpec:
    return RunSpec(
        id="profile_cc_test_v1",
        scenario="triage_jira",
        models=["qwen2.5:3b"],
        profile_required=profile_required,
    )


@pytest.mark.unit
class TestProfileCodecarbonConfig:
    def test_all_baseline_profiles_loadable(self):
        profiles = _load_profiles()
        for pid in _BASELINE_PROFILES:
            assert pid in profiles, f"{pid} missing from config/profiles.yaml"
            assert profiles[pid].name == pid

    def test_codecarbon_settings_uniform_across_profiles(self):
        # Uniformity by absence: codecarbon lives globally in the runner, never
        # per-profile, so no baseline profile may declare a codecarbon override.
        raw = _raw_profiles()
        for pid in _BASELINE_PROFILES:
            entry = raw[pid]
            keys = set(entry) | set(entry.get("requirements", {}))
            leaked = keys & _CODECARBON_KEYS
            assert not leaked, f"{pid} declares per-profile codecarbon keys: {leaked}"

    @pytest.mark.parametrize("pid", _BASELINE_PROFILES)
    def test_runner_accepts_each_profile_via_spec_override(self, pid, tmp_path):
        spec = _spec(pid)
        # Construction must not raise: __init__ touches neither DB nor Ollama.
        runner = Runner(spec, db_path=tmp_path / "t.db", dry_run=True)
        assert runner.run_id.startswith("profile_cc_test_v1__")
        # The value persisted to Run.profile is spec.profile_required verbatim.
        assert _resolve_run_profile(spec) == pid

    def test_unknown_profile_id_rejected(self):
        # The selector validates against the catalog and rejects unknown ids
        # with a clear ValueError — no silent fallback to a default profile.
        caps = SimpleNamespace(ram_total_gb=64.0)
        with pytest.raises(ValueError, match="Unknown profile"):
            select_profile(caps, override="not-a-real-profile")
