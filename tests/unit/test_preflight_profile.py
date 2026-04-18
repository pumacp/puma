"""Unit tests for puma.preflight.profile — profile selection logic."""

from __future__ import annotations

import pytest

from puma.preflight.detect import SystemCapabilities
from puma.preflight.profile import InsufficientHardwareError, select_profile


def _make_caps(ram_gb: float = 16.0, gpu_vram_gb: float | None = None, gpu_backend: str = "none"):
    return SystemCapabilities(
        os_system="Linux",
        os_arch="x86_64",
        python_version="3.11.0",
        cpu_model="Test CPU",
        cpu_cores_physical=4,
        cpu_threads=8,
        cpu_freq_mhz=2400.0,
        ram_total_gb=ram_gb,
        ram_available_gb=ram_gb * 0.5,
        disk_free_gb=100.0,
        gpu_name="Test GPU" if gpu_vram_gb else None,
        gpu_vram_gb=gpu_vram_gb,
        gpu_backend=gpu_backend,
        ollama_version=None,
        ollama_reachable=False,
    )


@pytest.mark.unit
class TestSelectProfile:
    def test_cpu_standard_16gb_no_gpu(self):
        caps = _make_caps(ram_gb=16.0)
        profile = select_profile(caps)
        assert profile.name == "cpu-standard"

    def test_cpu_lite_8gb_no_gpu(self):
        caps = _make_caps(ram_gb=8.0)
        profile = select_profile(caps)
        assert profile.name == "cpu-lite"

    def test_cpu_lite_10gb_no_gpu(self):
        caps = _make_caps(ram_gb=10.0)
        profile = select_profile(caps)
        assert profile.name == "cpu-lite"

    def test_insufficient_hardware_error(self):
        caps = _make_caps(ram_gb=6.0)
        with pytest.raises(InsufficientHardwareError):
            select_profile(caps)

    def test_gpu_entry_6gb_vram(self):
        caps = _make_caps(ram_gb=16.0, gpu_vram_gb=6.0, gpu_backend="nvidia")
        profile = select_profile(caps)
        assert profile.name == "gpu-entry"

    def test_gpu_entry_8gb_vram(self):
        caps = _make_caps(ram_gb=16.0, gpu_vram_gb=8.0, gpu_backend="nvidia")
        profile = select_profile(caps)
        assert profile.name == "gpu-entry"

    def test_gpu_mid_12gb_vram(self):
        caps = _make_caps(ram_gb=16.0, gpu_vram_gb=12.0, gpu_backend="nvidia")
        profile = select_profile(caps)
        assert profile.name == "gpu-mid"

    def test_gpu_high_24gb_vram(self):
        caps = _make_caps(ram_gb=32.0, gpu_vram_gb=24.0, gpu_backend="nvidia")
        profile = select_profile(caps)
        assert profile.name == "gpu-high"

    def test_profile_has_models(self):
        caps = _make_caps(ram_gb=16.0)
        profile = select_profile(caps)
        assert len(profile.models) > 0

    def test_profile_has_scenarios(self):
        caps = _make_caps(ram_gb=16.0)
        profile = select_profile(caps)
        assert len(profile.scenarios) > 0

    def test_manual_override_valid(self):
        caps = _make_caps(ram_gb=16.0)
        profile = select_profile(caps, override="cpu-lite")
        assert profile.name == "cpu-lite"

    def test_manual_override_invalid_raises(self):
        caps = _make_caps(ram_gb=16.0)
        with pytest.raises(ValueError, match="Unknown profile"):
            select_profile(caps, override="super-gpu-9000")
