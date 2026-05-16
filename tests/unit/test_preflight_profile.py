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
        from puma.preflight.catalog import models_for_profile

        caps = _make_caps(ram_gb=16.0)
        profile = select_profile(caps)
        assert len(models_for_profile(profile.name)) > 0

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

    def test_manual_override_to_apple_silicon_profile(self):
        """v2.6.0: explicit override to an apple-silicon-* profile works
        on any host (Linux included), since override bypasses
        auto-detection. Useful for cross-arch reproducibility
        experiments that pin the profile name explicitly."""
        caps = _make_caps(ram_gb=16.0)
        profile = select_profile(caps, override="apple-silicon-m4")
        assert profile.name == "apple-silicon-m4"
        assert profile.apple_silicon_required is True
        assert profile.chip_brand_match == "Apple M4"


@pytest.mark.unit
class TestSelectProfileAppleSilicon:
    """v2.6.0 auto-dispatch tests: caps reports chip_brand → returns
    matching apple-silicon-* profile (without override)."""

    def _make_apple_caps(
        self,
        chip_brand: str,
        unified_memory_gb: int,
        ram_gb: float | None = None,
    ) -> SystemCapabilities:
        # On real Apple Silicon, ram_total_gb == unified_memory_gb.
        ram = ram_gb if ram_gb is not None else float(unified_memory_gb)
        return SystemCapabilities(
            os_system="Darwin",
            os_arch="arm64",
            python_version="3.11.0",
            cpu_model="Apple Silicon",
            cpu_cores_physical=8,
            cpu_threads=8,
            cpu_freq_mhz=0.0,
            ram_total_gb=ram,
            ram_available_gb=ram * 0.5,
            disk_free_gb=300.0,
            gpu_name="Apple Metal GPU",
            gpu_vram_gb=None,  # Apple Silicon has no discrete VRAM
            gpu_backend="metal",
            ollama_version=None,
            ollama_reachable=False,
            chip_brand=chip_brand,
            unified_memory_gb=unified_memory_gb,
        )

    def test_m4_base_dispatches_to_apple_silicon_m4(self):
        caps = self._make_apple_caps("Apple M4", 24)
        profile = select_profile(caps)
        assert profile.name == "apple-silicon-m4"

    def test_m4_pro_dispatches_to_apple_silicon_m4_pro(self):
        caps = self._make_apple_caps("Apple M4 Pro", 36)
        profile = select_profile(caps)
        assert profile.name == "apple-silicon-m4-pro"

    def test_m5_max_dispatches_to_apple_silicon_m5_max(self):
        caps = self._make_apple_caps("Apple M5 Max", 64)
        profile = select_profile(caps)
        assert profile.name == "apple-silicon-m5-max"

    def test_m3_with_insufficient_unified_memory_falls_through(self):
        """An M3 with only 4 GB unified memory (theoretical edge case)
        does not meet the m3 profile's min_unified_memory_gb=8, so the
        dispatch falls through to the CPU/GPU branch. With ram_gb=4
        this also triggers InsufficientHardwareError below 8 GB —
        verifying the fall-through is wired correctly."""
        caps = self._make_apple_caps("Apple M3", unified_memory_gb=4, ram_gb=4.0)
        with pytest.raises(InsufficientHardwareError):
            select_profile(caps)

    def test_m3_with_8gb_dispatches_to_apple_silicon_m3(self):
        """8 GB hits exactly the min_unified_memory_gb floor for the
        m3 base profile (boundary case)."""
        caps = self._make_apple_caps("Apple M3", unified_memory_gb=8, ram_gb=8.0)
        profile = select_profile(caps)
        assert profile.name == "apple-silicon-m3"

    def test_unknown_apple_chip_falls_through_to_cpu_dispatch(self):
        """Forward-compat: an Apple chip we have not catalogued yet
        (e.g. M6) returns None from _match_apple_silicon_profile and
        falls through to existing CPU/GPU dispatch. With 32 GB RAM and
        no discrete GPU, that yields cpu-standard."""
        caps = self._make_apple_caps("Apple M6 Hyperdrive", unified_memory_gb=32, ram_gb=32.0)
        profile = select_profile(caps)
        assert profile.name == "cpu-standard"

    def test_non_apple_chip_brand_does_not_match_apple_profile(self):
        """A caps with chip_brand set to something not starting with
        'Apple M' must not match any apple-silicon-* profile."""
        caps = self._make_apple_caps(
            "Qualcomm Snapdragon X Elite", unified_memory_gb=32, ram_gb=32.0
        )
        # Override fallback so chip_brand bypasses the 'Apple M' prefix check
        caps = SystemCapabilities(**{**caps.__dict__, "chip_brand": "Qualcomm Snapdragon X Elite"})
        profile = select_profile(caps)
        assert profile.name == "cpu-standard"
