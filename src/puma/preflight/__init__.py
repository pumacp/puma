"""Hardware detection, profile selection, and provisioning verification."""

from puma.preflight.detect import SystemCapabilities, detect_capabilities
from puma.preflight.profile import InsufficientHardwareError, Profile, select_profile
from puma.preflight.provisioning import ProvisioningIssue, check_provisioning
from puma.preflight.report import print_report, write_runtime_profile

__all__ = [
    "SystemCapabilities",
    "detect_capabilities",
    "InsufficientHardwareError",
    "Profile",
    "select_profile",
    "ProvisioningIssue",
    "check_provisioning",
    "print_report",
    "write_runtime_profile",
]


def run_preflight(profile_override: str | None = None) -> tuple[SystemCapabilities, Profile, list[ProvisioningIssue]]:
    """Run full preflight sequence and return (caps, profile, issues)."""
    caps = detect_capabilities()
    profile = select_profile(caps, override=profile_override)
    issues = check_provisioning(caps, profile)
    return caps, profile, issues
