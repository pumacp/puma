"""Dashboard view modules, one per top-level view."""

from puma.dashboard.views import (
    fairness,
    instance_drilldown,
    model_comparison,
    overview,
    reliability,
    robustness,
    sustainability,
)

__all__ = [
    "fairness",
    "instance_drilldown",
    "model_comparison",
    "overview",
    "reliability",
    "robustness",
    "sustainability",
]
