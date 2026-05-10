"""Provisioning verification — disk space, Docker, GPU-in-Docker."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from puma.preflight.catalog import _CATALOG_PATH, load_catalog
from puma.preflight.detect import SystemCapabilities
from puma.preflight.profile import Profile


class IssueSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class ProvisioningIssue:
    severity: IssueSeverity
    message: str


def _check_disk(
    caps: SystemCapabilities, profile: Profile, catalog_path: Path
) -> list[ProvisioningIssue]:
    catalog = load_catalog(catalog_path)
    profile_models = [m for m in catalog if profile.name in m.profiles_compatible]
    required = sum(m.gguf_size_gb for m in profile_models) + 5.0
    if caps.disk_free_gb < required:
        return [
            ProvisioningIssue(
                severity=IssueSeverity.ERROR,
                message=(
                    f"Insufficient disk space: {caps.disk_free_gb:.1f} GB free, "
                    f"{required:.1f} GB required for profile '{profile.name}'. "
                    "Free up space or use a smaller profile."
                ),
            )
        ]
    return []


def _check_docker() -> list[ProvisioningIssue]:
    issues = []
    if not shutil.which("docker"):
        issues.append(
            ProvisioningIssue(
                severity=IssueSeverity.ERROR,
                message="Docker not found. Install Docker: https://docs.docker.com/engine/install/",
            )
        )
        return issues
    compose_found = shutil.which("docker-compose") or _docker_compose_plugin()
    if not compose_found:
        issues.append(
            ProvisioningIssue(
                severity=IssueSeverity.WARNING,
                message="docker-compose not found. Install the Docker Compose plugin.",
            )
        )
    return issues


def _docker_compose_plugin() -> bool:
    try:
        result = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _check_docker_gpu() -> list[ProvisioningIssue]:
    try:
        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "--gpus",
                "all",
                "nvidia/cuda:12.2.0-base-ubuntu22.04",
                "nvidia-smi",
            ],
            capture_output=True,
            timeout=60,
        )
        if result.returncode != 0:
            return [
                ProvisioningIssue(
                    severity=IssueSeverity.WARNING,
                    message=(
                        "GPU not accessible from Docker. Install nvidia-container-toolkit: "
                        "https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
                    ),
                )
            ]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return [
            ProvisioningIssue(
                severity=IssueSeverity.WARNING,
                message="Could not verify GPU access from Docker (timeout or docker not found).",
            )
        ]
    return []


def check_provisioning(
    caps: SystemCapabilities,
    profile: Profile,
    check_docker_gpu: bool = True,
    catalog_path: Path = _CATALOG_PATH,
) -> list[ProvisioningIssue]:
    """Verify provisioning requirements and return a list of issues."""
    issues: list[ProvisioningIssue] = []
    issues.extend(_check_disk(caps, profile, catalog_path))
    issues.extend(_check_docker())
    if check_docker_gpu and profile.gpu_required:
        issues.extend(_check_docker_gpu())
    return issues
