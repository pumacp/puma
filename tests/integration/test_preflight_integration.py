"""Integration tests for preflight — runs against actual hardware."""

from __future__ import annotations

import pytest
import yaml

from puma.preflight import detect_capabilities, select_profile, write_runtime_profile


@pytest.mark.integration
class TestPreflightIntegration:
    def test_detect_runs_without_error(self):
        caps = detect_capabilities()
        assert caps.ram_total_gb > 0
        assert caps.os_system != ""

    def test_select_profile_for_this_machine(self):
        caps = detect_capabilities()
        profile = select_profile(caps)
        valid_profiles = {"cpu-lite", "cpu-standard", "gpu-entry", "gpu-mid", "gpu-high"}
        assert profile.name in valid_profiles

    def test_write_runtime_profile_creates_file(self, tmp_path, monkeypatch):
        from puma.preflight import report as report_mod

        monkeypatch.setattr(
            report_mod, "_RUNTIME_PROFILE", tmp_path / "runtime_profile.yaml"
        )
        caps = detect_capabilities()
        profile = select_profile(caps)
        path = write_runtime_profile(caps, profile)

        assert path.exists()
        data = yaml.safe_load(path.read_text())
        assert "profile" in data
        assert "hardware" in data
        assert data["profile"] == profile.name
        assert data["hardware"]["ram_gb"] > 0

    def test_runtime_profile_has_models(self, tmp_path, monkeypatch):
        from puma.preflight import report as report_mod

        monkeypatch.setattr(
            report_mod, "_RUNTIME_PROFILE", tmp_path / "runtime_profile.yaml"
        )
        caps = detect_capabilities()
        profile = select_profile(caps)
        path = write_runtime_profile(caps, profile)

        data = yaml.safe_load(path.read_text())
        assert len(data.get("models", [])) > 0
