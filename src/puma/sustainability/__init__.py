"""CodeCarbon wrapper and derived CO2 metrics (gCO2/F1-point, gCO2/MAE-unit)."""

from puma.sustainability.codecarbon_wrapper import (
    emissions_summary,
    gco2_per_f1_point,
    gco2_per_mae_unit,
    track_emissions,
)

__all__ = [
    "track_emissions",
    "gco2_per_f1_point",
    "gco2_per_mae_unit",
    "emissions_summary",
]
