"""Unit tests for puma.preflight.provisioning."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from puma.preflight.detect import SystemCapabilities
from puma.preflight.profile import Profile
from puma.preflight.provisioning import (
    IssueSeverity,
    ProvisioningIssue,
    check_provisioning,
)


def _make_profile(name="cpu-standard", min_disk_gb=25.0, models=None, gpu_required=False):
    return Profile(
        name=name,
        description="test",
        models=models or ["qwen2.5:3b"],
        scenarios=["triage_jira"],
        min_ram_gb=16.0,
        gpu_required=gpu_required,
        min_vram_gb=0.0,
        min_disk_gb=min_disk_gb,
    )


def _make_caps(disk_free_gb=50.0, gpu_backend="none"):
    return SystemCapabilities(
        os_system="Linux", os_arch="x86_64", python_version="3.11",
        cpu_model="CPU", cpu_cores_physical=4, cpu_threads=8, cpu_freq_mhz=2400,
        ram_total_gb=16.0, ram_available_gb=8.0, disk_free_gb=disk_free_gb,
        gpu_name=None, gpu_vram_gb=None, gpu_backend=gpu_backend,
        ollama_version=None, ollama_reachable=False,
    )


@pytest.mark.unit
class TestCheckProvisioning:
    def test_no_issues_when_all_ok(self):
        caps = _make_caps(disk_free_gb=100.0)
        profile = _make_profile(min_disk_gb=25.0)

        with patch("shutil.which", return_value="/usr/bin/docker"):
            issues = check_provisioning(caps, profile, check_docker_gpu=False)

        errors = [i for i in issues if i.severity == IssueSeverity.ERROR]
        assert len(errors) == 0

    def test_disk_too_small_raises_error(self):
        caps = _make_caps(disk_free_gb=5.0)
        profile = _make_profile(min_disk_gb=25.0)

        with patch("shutil.which", return_value="/usr/bin/docker"):
            issues = check_provisioning(caps, profile, check_docker_gpu=False)

        errors = [i for i in issues if i.severity == IssueSeverity.ERROR]
        assert any("disk" in i.message.lower() or "space" in i.message.lower() for i in errors)

    def test_docker_missing_raises_error(self):
        caps = _make_caps(disk_free_gb=100.0)
        profile = _make_profile()

        with patch("shutil.which", return_value=None):
            issues = check_provisioning(caps, profile, check_docker_gpu=False)

        errors = [i for i in issues if i.severity == IssueSeverity.ERROR]
        assert any("docker" in i.message.lower() for i in errors)

    def test_returns_list_of_provisioning_issues(self):
        caps = _make_caps()
        profile = _make_profile()

        with patch("shutil.which", return_value="/usr/bin/docker"):
            issues = check_provisioning(caps, profile, check_docker_gpu=False)

        assert isinstance(issues, list)
        for issue in issues:
            assert isinstance(issue, ProvisioningIssue)
