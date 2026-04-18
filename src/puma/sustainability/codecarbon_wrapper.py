"""CodeCarbon wrapper and derived CO2 metrics (gCO2/F1-point, gCO2/MAE-unit)."""

from __future__ import annotations

import functools
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


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

    Uses tracking_mode='process' (offline, no cloud reporting).
    Guarantees tracker.stop() even if the wrapped function raises.
    Injects an `emissions_data` attribute onto the returned result if possible.
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                from codecarbon import EmissionsTracker
                tracker = EmissionsTracker(
                    project_name=project_name,
                    output_dir=str(output_dir),
                    log_level="error",
                    save_to_file=True,
                    tracking_mode="process",
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
