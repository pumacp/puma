"""Hardware detection, profile selection, and provisioning verification."""

from puma.preflight.catalog import ModelEntry, get_model_by_tag, load_catalog, models_for_profile
from puma.preflight.detect import SystemCapabilities, detect_capabilities
from puma.preflight.profile import InsufficientHardwareError, Profile, select_profile
from puma.preflight.provisioning import ProvisioningIssue, check_provisioning
from puma.preflight.report import print_report, write_runtime_profile

__all__ = [
    "InsufficientHardwareError",
    "ModelEntry",
    "Profile",
    "ProvisioningIssue",
    "SystemCapabilities",
    "check_provisioning",
    "detect_capabilities",
    "get_model_by_tag",
    "load_catalog",
    "models_for_profile",
    "print_report",
    "select_profile",
    "write_runtime_profile",
]


def run_preflight(
    profile_override: str | None = None,
) -> tuple[SystemCapabilities, Profile, list[ProvisioningIssue]]:
    """Run full preflight sequence and return (caps, profile, issues)."""
    caps = detect_capabilities()
    profile = select_profile(caps, override=profile_override)
    issues = check_provisioning(caps, profile)
    return caps, profile, issues
