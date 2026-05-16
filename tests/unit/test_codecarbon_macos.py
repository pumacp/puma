"""CodeCarbon macOS-aware tracking_mode tests (Sprint 9 / v2.6.0).

Verifies the platform-aware ``get_tracking_mode_and_warnings`` helper.
All tests mock the Apple Silicon gate and the powermetrics probe so
the suite runs on Linux CI (P9). Linux behaviour must remain identical
to v2.5.0 (machine mode, no warnings).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from puma.sustainability import codecarbon_wrapper as cw
from puma.sustainability.codecarbon_wrapper import (
    _powermetrics_available_without_sudo,
    get_tracking_mode_and_warnings,
)

# -- get_tracking_mode_and_warnings ---------------------------------------


@pytest.mark.unit
def test_linux_returns_machine_mode_no_warnings() -> None:
    """On Linux, the function returns ('machine', []) — byte-identical
    to the v2.5.0 behaviour relied upon by PUMA's split-container
    architecture (GPU work in puma_ollama only shows under 'machine')."""
    with patch.object(cw, "is_apple_silicon", return_value=False):
        mode, warnings = get_tracking_mode_and_warnings()
    assert mode == "machine"
    assert warnings == []


@pytest.mark.unit
def test_macos_without_passwordless_sudo_falls_back_to_process() -> None:
    """On macOS Mode B without passwordless powermetrics, the function
    returns 'process' and emits exactly one warning pointing at
    docs/MACOS_NOTES.md."""
    with (
        patch.object(cw, "is_apple_silicon", return_value=True),
        patch.object(cw, "_powermetrics_available_without_sudo", return_value=False),
    ):
        mode, warnings = get_tracking_mode_and_warnings()
    assert mode == "process"
    assert len(warnings) == 1
    assert "powermetrics" in warnings[0]
    assert "MACOS_NOTES.md" in warnings[0]


@pytest.mark.unit
def test_macos_with_passwordless_sudo_returns_machine_no_warnings() -> None:
    """If the admin has granted passwordless powermetrics access, the
    machine path is selected and no warning is emitted."""
    with (
        patch.object(cw, "is_apple_silicon", return_value=True),
        patch.object(cw, "_powermetrics_available_without_sudo", return_value=True),
    ):
        mode, warnings = get_tracking_mode_and_warnings()
    assert mode == "machine"
    assert warnings == []


# -- _powermetrics_available_without_sudo --------------------------------


@pytest.mark.unit
def test_powermetrics_probe_returns_false_on_linux() -> None:
    """The probe must short-circuit on non-Apple-Silicon hosts and
    NEVER invoke subprocess — otherwise CI on Linux would attempt to
    run a macOS-only utility."""
    with (
        patch.object(cw, "is_apple_silicon", return_value=False),
        patch.object(cw.subprocess, "run") as run_mock,
    ):
        assert _powermetrics_available_without_sudo() is False
    run_mock.assert_not_called()


@pytest.mark.unit
def test_powermetrics_probe_returns_false_when_command_missing() -> None:
    """Apple Silicon host but powermetrics absent (theoretical edge —
    powermetrics ships with macOS): probe returns False, no exception
    propagates."""
    with (
        patch.object(cw, "is_apple_silicon", return_value=True),
        patch.object(cw.subprocess, "run", side_effect=FileNotFoundError),
    ):
        assert _powermetrics_available_without_sudo() is False


@pytest.mark.unit
def test_powermetrics_probe_returns_false_on_non_zero_exit() -> None:
    """When sudoers requires password (default), powermetrics exits
    non-zero — the probe returns False without raising."""
    from unittest.mock import MagicMock

    with (
        patch.object(cw, "is_apple_silicon", return_value=True),
        patch.object(cw.subprocess, "run", return_value=MagicMock(returncode=1)),
    ):
        assert _powermetrics_available_without_sudo() is False


@pytest.mark.unit
def test_powermetrics_probe_returns_true_on_zero_exit() -> None:
    """The only path that returns True: Apple Silicon + powermetrics
    exits with code 0 inside the timeout. Indicates passwordless sudo."""
    from unittest.mock import MagicMock

    with (
        patch.object(cw, "is_apple_silicon", return_value=True),
        patch.object(cw.subprocess, "run", return_value=MagicMock(returncode=0)),
    ):
        assert _powermetrics_available_without_sudo() is True
