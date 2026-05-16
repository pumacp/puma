"""Apple Silicon detection unit tests (Sprint 9 / v2.6.0).

All tests mock the platform/subprocess layer so the suite runs on
Linux CI without skipping anything (P9). Real-hardware integration
tests on Apple Silicon are deferred until Mac hardware joins the
validation set (see docs/CROSS_ARCH_REPRODUCIBILITY.md).
"""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from puma.preflight import apple_silicon as asi
from puma.preflight.apple_silicon import (
    CHIP_BRAND_TO_PROFILE,
    detect_apple_silicon_profile,
    get_apple_silicon_info,
    get_chip_brand,
    get_unified_memory_gb,
    is_apple_silicon,
)

# -- is_apple_silicon ------------------------------------------------------


@pytest.mark.unit
def test_is_apple_silicon_true_on_darwin_arm64() -> None:
    with (
        patch.object(asi.platform, "system", return_value="Darwin"),
        patch.object(asi.platform, "machine", return_value="arm64"),
    ):
        assert is_apple_silicon() is True


@pytest.mark.unit
def test_is_apple_silicon_false_on_intel_mac() -> None:
    with (
        patch.object(asi.platform, "system", return_value="Darwin"),
        patch.object(asi.platform, "machine", return_value="x86_64"),
    ):
        assert is_apple_silicon() is False


@pytest.mark.unit
def test_is_apple_silicon_false_on_linux() -> None:
    with (
        patch.object(asi.platform, "system", return_value="Linux"),
        patch.object(asi.platform, "machine", return_value="x86_64"),
    ):
        assert is_apple_silicon() is False


# -- get_chip_brand --------------------------------------------------------


@pytest.mark.unit
def test_get_chip_brand_returns_sysctl_output_on_apple_silicon() -> None:
    with (
        patch.object(asi, "is_apple_silicon", return_value=True),
        patch.object(asi.subprocess, "run") as run_mock,
    ):
        run_mock.return_value = MagicMock(stdout="Apple M4 Pro\n", returncode=0)
        assert get_chip_brand() == "Apple M4 Pro"


@pytest.mark.unit
def test_get_chip_brand_returns_none_off_apple_silicon() -> None:
    with patch.object(asi, "is_apple_silicon", return_value=False):
        assert get_chip_brand() is None


@pytest.mark.unit
def test_get_chip_brand_returns_none_when_sysctl_missing() -> None:
    with (
        patch.object(asi, "is_apple_silicon", return_value=True),
        patch.object(asi.subprocess, "run", side_effect=FileNotFoundError),
    ):
        assert get_chip_brand() is None


@pytest.mark.unit
def test_get_chip_brand_returns_none_on_timeout() -> None:
    with (
        patch.object(asi, "is_apple_silicon", return_value=True),
        patch.object(
            asi.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired(cmd="sysctl", timeout=5),
        ),
    ):
        assert get_chip_brand() is None


@pytest.mark.unit
def test_get_chip_brand_returns_none_on_called_process_error() -> None:
    with (
        patch.object(asi, "is_apple_silicon", return_value=True),
        patch.object(
            asi.subprocess,
            "run",
            side_effect=subprocess.CalledProcessError(returncode=1, cmd="sysctl"),
        ),
    ):
        assert get_chip_brand() is None


# -- get_unified_memory_gb -------------------------------------------------


@pytest.mark.unit
def test_get_unified_memory_gb_returns_int_gb() -> None:
    # 24 GiB in bytes
    twenty_four_gib = 24 * (1024**3)
    with (
        patch.object(asi, "is_apple_silicon", return_value=True),
        patch.object(asi.subprocess, "run") as run_mock,
    ):
        run_mock.return_value = MagicMock(stdout=f"{twenty_four_gib}\n", returncode=0)
        assert get_unified_memory_gb() == 24


@pytest.mark.unit
def test_get_unified_memory_gb_returns_none_off_apple_silicon() -> None:
    with patch.object(asi, "is_apple_silicon", return_value=False):
        assert get_unified_memory_gb() is None


@pytest.mark.unit
def test_get_unified_memory_gb_returns_none_on_garbage_output() -> None:
    with (
        patch.object(asi, "is_apple_silicon", return_value=True),
        patch.object(asi.subprocess, "run") as run_mock,
    ):
        run_mock.return_value = MagicMock(stdout="not a number\n", returncode=0)
        assert get_unified_memory_gb() is None


# -- detect_apple_silicon_profile -----------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    ("brand", "expected"),
    [
        ("Apple M3", "apple-silicon-m3"),
        ("Apple M3 Pro", "apple-silicon-m3-pro"),
        ("Apple M3 Max", "apple-silicon-m3-max"),
        ("Apple M4", "apple-silicon-m4"),
        ("Apple M4 Pro", "apple-silicon-m4-pro"),
        ("Apple M4 Max", "apple-silicon-m4-max"),
        ("Apple M5", "apple-silicon-m5"),
        ("Apple M5 Pro", "apple-silicon-m5-pro"),
        ("Apple M5 Max", "apple-silicon-m5-max"),
        ("Apple M5 Ultra", "apple-silicon-m5-ultra"),
    ],
)
def test_detect_apple_silicon_profile_maps_known_brands(brand: str, expected: str) -> None:
    with patch.object(asi, "get_chip_brand", return_value=brand):
        assert detect_apple_silicon_profile() == expected


@pytest.mark.unit
def test_detect_apple_silicon_profile_returns_none_for_future_chip() -> None:
    """Unknown but real-looking brand (e.g. a future M6) returns None so
    select_profile falls through to existing dispatch."""
    with patch.object(asi, "get_chip_brand", return_value="Apple M6 Hyperdrive"):
        assert detect_apple_silicon_profile() is None


@pytest.mark.unit
def test_detect_apple_silicon_profile_returns_none_when_brand_unavailable() -> None:
    with patch.object(asi, "get_chip_brand", return_value=None):
        assert detect_apple_silicon_profile() is None


# -- get_apple_silicon_info -----------------------------------------------


@pytest.mark.unit
def test_get_apple_silicon_info_returns_none_off_apple_silicon() -> None:
    with patch.object(asi, "is_apple_silicon", return_value=False):
        assert get_apple_silicon_info() is None


@pytest.mark.unit
def test_get_apple_silicon_info_returns_full_dict_on_apple_silicon() -> None:
    with (
        patch.object(asi, "is_apple_silicon", return_value=True),
        patch.object(asi, "get_chip_brand", return_value="Apple M4"),
        patch.object(asi, "get_unified_memory_gb", return_value=16),
    ):
        info = get_apple_silicon_info()
    assert info is not None
    assert info["chip_brand"] == "Apple M4"
    assert info["profile"] == "apple-silicon-m4"
    assert info["unified_memory_gb"] == 16
    assert "platform" in info


@pytest.mark.unit
def test_get_apple_silicon_info_handles_unmapped_chip_gracefully() -> None:
    """If sysctl reports a chip we have not yet catalogued, ``profile``
    is None but the rest of the diagnostic info is still returned."""
    with (
        patch.object(asi, "is_apple_silicon", return_value=True),
        patch.object(asi, "get_chip_brand", return_value="Apple M6 Hyperdrive"),
        patch.object(asi, "get_unified_memory_gb", return_value=48),
    ):
        info = get_apple_silicon_info()
    assert info is not None
    assert info["chip_brand"] == "Apple M6 Hyperdrive"
    assert info["profile"] is None  # unmapped chip → fall-through
    assert info["unified_memory_gb"] == 48


# -- CHIP_BRAND_TO_PROFILE consistency ------------------------------------


@pytest.mark.unit
def test_chip_brand_to_profile_covers_9_variants() -> None:
    """The v2.6.0 catalogue has 10 chip variants (M3 base/Pro/Max, M4
    base/Pro/Max, M5 base/Pro/Max, M5 Ultra). Update this assertion if a
    new chip variant is added."""
    assert len(CHIP_BRAND_TO_PROFILE) == 10
    assert all(b.startswith("Apple M") for b in CHIP_BRAND_TO_PROFILE)
    assert all(p.startswith("apple-silicon-") for p in CHIP_BRAND_TO_PROFILE.values())


@pytest.mark.unit
def test_chip_brand_to_profile_values_are_unique() -> None:
    """No two chip brands map to the same profile identifier."""
    values = list(CHIP_BRAND_TO_PROFILE.values())
    assert len(values) == len(set(values))
