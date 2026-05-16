"""CodeCarbon wrapper and derived CO2 metrics (gCO2/F1-point, gCO2/MAE-unit)."""

from __future__ import annotations

import functools
import logging
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from puma.preflight.apple_silicon import is_apple_silicon

logger = logging.getLogger(__name__)


def _powermetrics_available_without_sudo() -> bool:
    """Probe whether ``powermetrics`` can run without ``sudo``.

    On stock macOS the answer is always False — Apple ships powermetrics
    with sudo-only execution. Returns True only when an administrator has
    configured a sudoers entry granting passwordless powermetrics access
    (see docs/MACOS_NOTES.md). Off macOS this always returns False
    without invoking subprocess.
    """
    if not is_apple_silicon():
        return False
    try:
        result = subprocess.run(
            ["powermetrics", "-n", "1", "-i", "1"],
            capture_output=True,
            timeout=3,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, PermissionError, OSError):
        return False


def get_tracking_mode_and_warnings() -> tuple[str, list[str]]:
    """Return the appropriate CodeCarbon ``tracking_mode`` and any warnings.

    Linux + NVIDIA: returns ``("machine", [])`` — identical to the v2.5.0
    default and the behaviour relied upon by PUMA's split-container
    architecture (the GPU work happens in ``puma_ollama`` and only
    ``tracking_mode='machine'`` captures it).

    macOS (Apple Silicon, Mode B):
    - With passwordless powermetrics: returns ``("machine", [])``.
    - Without passwordless powermetrics: returns
      ``("process", [<single-warning>])`` and the caller is expected to
      log the warning. Energy figures will be less accurate.

    The warning text points at docs/MACOS_NOTES.md so users can opt in
    to passwordless powermetrics via sudoers.
    """
    warnings: list[str] = []
    if is_apple_silicon():
        if _powermetrics_available_without_sudo():
            return "machine", warnings
        warnings.append(
            "macOS Mode B: powermetrics requires sudo for accurate energy "
            "tracking. Falling back to tracking_mode='process' — figures "
            "are less precise than machine-mode on Linux+NVIDIA. To enable "
            "the machine path, configure passwordless sudo for "
            "powermetrics (see docs/MACOS_NOTES.md) or run "
            "`puma run --no-emissions` to disable tracking entirely."
        )
        return "process", warnings
    return "machine", warnings


def gco2_per_f1_point(emissions_g: float, f1: float) -> float | None:
    """Grams of CO2 per F1-macro point. Returns None if f1 == 0."""
    if f1 == 0.0:
        return None
    return emissions_g / f1


def gco2_per_mae_unit(emissions_g: float, mae: float) -> float | None:
    """Grams of CO2 per MAE unit. Returns None if mae == 0."""
    if mae == 0.0:
        return None
    return emissions_g / mae


def track_emissions(
    project_name: str,
    output_dir: str | Path = "results/",
) -> Callable:
    """Decorator: wraps a function with CodeCarbon EmissionsTracker.

    Uses tracking_mode='machine' so GPU work performed by other processes
    on the same host (notably the puma_ollama container under PUMA's
    split-container architecture) is captured. Offline, no cloud reporting.
    Guarantees tracker.stop() even if the wrapped function raises.
    Injects an `emissions_data` attribute onto the returned result if possible.
    """

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                from codecarbon import EmissionsTracker

                tracking_mode, warnings = get_tracking_mode_and_warnings()
                for w in warnings:
                    logger.warning(w)
                tracker = EmissionsTracker(
                    project_name=project_name,
                    output_dir=str(output_dir),
                    log_level="error",
                    save_to_file=True,
                    tracking_mode=tracking_mode,
                )
                tracker.start()
            except Exception as exc:
                logger.warning("CodeCarbon unavailable, running without tracking: %s", exc)
                return fn(*args, **kwargs)

            try:
                result = fn(*args, **kwargs)
            finally:
                try:
                    emissions = tracker.stop()
                    logger.debug("emissions_kg=%.6f", emissions or 0.0)
                except Exception as exc:
                    logger.warning("CodeCarbon stop() failed: %s", exc)

            return result

        return wrapper

    return decorator


def emissions_summary(emissions_csv_path: Path) -> dict:
    """Parse a CodeCarbon emissions.csv and return a summary dict."""
    import pandas as pd

    if not emissions_csv_path.exists():
        return {}
    try:
        df = pd.read_csv(emissions_csv_path)
        if df.empty:
            return {}
        last = df.iloc[-1]
        return {
            "kwh": float(last.get("energy_consumed", 0)),
            "co2_kg": float(last.get("emissions", 0)),
            "co2_g": float(last.get("emissions", 0)) * 1000,
            "duration_s": float(last.get("duration", 0)),
            "cpu_energy_kwh": float(last.get("cpu_energy", 0)),
            "gpu_energy_kwh": float(last.get("gpu_energy", 0)),
            "ram_energy_kwh": float(last.get("ram_energy", 0)),
        }
    except Exception as exc:
        logger.warning("Could not parse emissions CSV %s: %s", emissions_csv_path, exc)
        return {}
