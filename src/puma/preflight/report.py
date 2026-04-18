"""Preflight diagnostic report — builds and writes runtime_profile.yaml."""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml

from puma.preflight.detect import SystemCapabilities
from puma.preflight.profile import Profile
from puma.preflight.provisioning import IssueSeverity, ProvisioningIssue

_RUNTIME_PROFILE = Path("config") / "runtime_profile.yaml"


def write_runtime_profile(caps: SystemCapabilities, profile: Profile) -> Path:
    """Persist detected hardware + selected profile to config/runtime_profile.yaml."""
    _RUNTIME_PROFILE.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "profile": profile.name,
        "detected_at": datetime.now(UTC).isoformat(),
        "hardware": {
            "os": caps.os_system,
            "arch": caps.os_arch,
            "cpu": caps.cpu_model,
            "cpu_cores": caps.cpu_cores_physical,
            "cpu_threads": caps.cpu_threads,
            "ram_gb": caps.ram_total_gb,
            "gpu": caps.gpu_name,
            "gpu_backend": caps.gpu_backend,
            "gpu_vram_gb": caps.gpu_vram_gb,
        },
        "ollama": {
            "version": caps.ollama_version,
            "reachable": caps.ollama_reachable,
        },
        "models": profile.models,
        "scenarios": profile.scenarios,
    }
    with open(_RUNTIME_PROFILE, "w", encoding="utf-8") as fh:
        yaml.dump(data, fh, default_flow_style=False, allow_unicode=True)
    return _RUNTIME_PROFILE


def print_report(
    caps: SystemCapabilities,
    profile: Profile,
    issues: list[ProvisioningIssue],
    *,
    file=None,
) -> None:
    """Print a human-readable preflight diagnostic to stdout (or file)."""
    if file is None:
        file = sys.stdout

    sep = "=" * 60
    print(sep, file=file)
    print("PUMA Preflight Diagnostic", file=file)
    print(sep, file=file)

    print(f"\n  OS          : {caps.os_system} {caps.os_arch}", file=file)
    print(f"  Python      : {caps.python_version}", file=file)
    print(f"  CPU         : {caps.cpu_model}", file=file)
    print(f"  Cores       : {caps.cpu_cores_physical}P / {caps.cpu_threads}T", file=file)
    print(f"  RAM total   : {caps.ram_total_gb:.1f} GB", file=file)
    print(f"  RAM free    : {caps.ram_available_gb:.1f} GB", file=file)
    print(f"  Disk free   : {caps.disk_free_gb:.1f} GB", file=file)

    if caps.gpu_name:
        vram = f"{caps.gpu_vram_gb:.1f} GB VRAM" if caps.gpu_vram_gb else "VRAM unknown"
        print(f"  GPU         : {caps.gpu_name} ({vram})", file=file)
        print(f"  GPU backend : {caps.gpu_backend}", file=file)
    else:
        print("  GPU         : none detected", file=file)

    ollama_status = caps.ollama_version if caps.ollama_version else "not installed"
    reachable = "reachable" if caps.ollama_reachable else "not reachable"
    print(f"  Ollama      : {ollama_status} / {reachable}", file=file)

    print(f"\n  Selected profile : {profile.name}", file=file)
    print(f"  Description      : {profile.description}", file=file)
    print(f"  Models enabled   : {', '.join(profile.models)}", file=file)
    print(f"  Scenarios        : {', '.join(profile.scenarios)}", file=file)

    if issues:
        print("\n  Provisioning issues:", file=file)
        for issue in issues:
            icon = "ERROR  " if issue.severity == IssueSeverity.ERROR else "WARNING"
            print(f"    [{icon}] {issue.message}", file=file)
    else:
        print("\n  Provisioning: all checks passed", file=file)

    print(sep, file=file)
