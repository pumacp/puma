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
    name: str
    description: str
    models: list[str]
    scenarios: list[str]
    min_ram_gb: float
    gpu_required: bool
    min_vram_gb: float
    min_disk_gb: float


def _load_profiles(path: Path = _PROFILES_PATH) -> dict[str, Profile]:
    with open(path, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    profiles: dict[str, Profile] = {}
    for name, data in raw["profiles"].items():
        req = data["requirements"]
        profiles[name] = Profile(
            name=name,
            description=data.get("description", ""),
            models=data.get("models", []),
            scenarios=data.get("scenarios", []),
            min_ram_gb=float(req.get("min_ram_gb", 0)),
            gpu_required=bool(req.get("gpu_required", False)),
            min_vram_gb=float(req.get("min_vram_gb", 0)),
            min_disk_gb=float(req.get("min_disk_gb", 0)),
        )
    return profiles


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
