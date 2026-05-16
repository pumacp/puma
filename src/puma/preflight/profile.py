"""Profile selection from detected hardware capabilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from puma.preflight.detect import SystemCapabilities

_PROFILES_PATH = Path(__file__).parent.parent.parent.parent / "config" / "profiles.yaml"


class InsufficientHardwareError(RuntimeError):
    """Raised when the host does not meet minimum requirements."""


@dataclass(frozen=True)
class Profile:
    """Hardware-resource thresholds and enabled scenarios for a profile.

    The list of compatible models is derived dynamically from the catalog
    via ``puma.preflight.catalog.models_for_profile(profile.name)`` since
    B.1.3, replacing the previous ``models: list[str]`` field.

    v2.6.0 added the optional ``apple_silicon_required`` /
    ``chip_brand_match`` / ``min_unified_memory_gb`` fields to support
    the apple-silicon-* profile family. Existing NVIDIA/CPU profiles
    leave them at their defaults and are unaffected.
    """

    name: str
    description: str
    scenarios: list[str]
    min_ram_gb: float
    gpu_required: bool
    min_vram_gb: float
    min_disk_gb: float
    # Apple Silicon fields (v2.6.0). Defaults preserve the v2.5.0
    # behaviour for the existing 5 profiles.
    apple_silicon_required: bool = False
    chip_brand_match: str | None = None
    min_unified_memory_gb: float = 0.0


def _load_profiles(path: Path = _PROFILES_PATH) -> dict[str, Profile]:
    with open(path, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    profiles: dict[str, Profile] = {}
    for name, data in raw["profiles"].items():
        req = data["requirements"]
        profiles[name] = Profile(
            name=name,
            description=data.get("description", ""),
            scenarios=data.get("scenarios", []),
            min_ram_gb=float(req.get("min_ram_gb", 0)),
            gpu_required=bool(req.get("gpu_required", False)),
            min_vram_gb=float(req.get("min_vram_gb", 0)),
            min_disk_gb=float(req.get("min_disk_gb", 0)),
            apple_silicon_required=bool(req.get("apple_silicon_required", False)),
            chip_brand_match=req.get("chip_brand_match"),
            min_unified_memory_gb=float(req.get("min_unified_memory_gb", 0)),
        )
    return profiles


def _match_apple_silicon_profile(
    caps: SystemCapabilities, profiles: dict[str, Profile]
) -> Profile | None:
    """Return the apple-silicon-* profile whose chip_brand_match matches caps.

    Returns None when caps does not advertise an Apple chip brand, or when
    the brand is recognised by ``sysctl`` but not yet mapped to a profile
    (forward-compat for future M-series variants). In both cases the
    caller falls through to the existing CPU/GPU dispatch.
    """
    if not caps.chip_brand or not caps.chip_brand.startswith("Apple M"):
        return None
    for profile in profiles.values():
        if profile.apple_silicon_required and profile.chip_brand_match == caps.chip_brand:
            return profile
    return None


def select_profile(
    caps: SystemCapabilities,
    override: str | None = None,
    profiles_path: Path = _PROFILES_PATH,
) -> Profile:
    """Return the best-fit Profile for the detected hardware.

    Raises InsufficientHardwareError if RAM < 8 GB.
    Raises ValueError if override names an unknown profile.
    """
    profiles = _load_profiles(profiles_path)

    if override and override != "auto":
        if override not in profiles:
            raise ValueError(f"Unknown profile: {override!r}. Valid: {list(profiles)}")
        return profiles[override]

    if caps.ram_total_gb < 8.0:
        raise InsufficientHardwareError(
            f"Insufficient RAM: {caps.ram_total_gb:.1f} GB detected, minimum 8 GB required. "
            "PUMA cannot run on this machine."
        )

    # Apple Silicon dispatch (v2.6.0). Runs BEFORE the existing GPU/CPU
    # dispatch — on macOS arm64 with a recognised chip brand, returns
    # the matching apple-silicon-* profile. Falls through to the
    # existing logic when the chip is unknown or unified memory is
    # insufficient for the matched profile (caller degrades to cpu-*).
    asi_profile = _match_apple_silicon_profile(caps, profiles)
    if asi_profile is not None:
        unified_gb = caps.unified_memory_gb or 0
        if unified_gb >= asi_profile.min_unified_memory_gb:
            return asi_profile
        # Chip recognised but the host has less unified memory than the
        # variant's typical floor — fall through; cpu-standard / cpu-lite
        # will be selected by the RAM check below.

    has_gpu = caps.gpu_backend != "none" and caps.gpu_vram_gb is not None
    vram = caps.gpu_vram_gb or 0.0

    if has_gpu and vram >= 24.0:
        return profiles["gpu-high"]
    if has_gpu and vram >= 12.0:
        return profiles["gpu-mid"]
    if has_gpu and vram >= 6.0:
        return profiles["gpu-entry"]
    if caps.ram_total_gb >= 16.0:
        return profiles["cpu-standard"]
    return profiles["cpu-lite"]
