"""Prompting strategies: zero-shot, few-shot, CoT, RCOIF, self-consistency."""

from puma.adaptation.base import Strategy
from puma.adaptation.examples import select_examples
from puma.adaptation.strategies import (
    EGI,
    RCOIF,
    STRATEGY_REGISTRY,
    ContextualAnchoring,
    CoTFewShot,
    FewShotK,
    OneShot,
    SelfConsistency,
    ZeroShot,
    ZeroShotCoT,
    get_strategy,
)

__all__ = [
    "EGI",
    "RCOIF",
    "STRATEGY_REGISTRY",
    "CoTFewShot",
    "ContextualAnchoring",
    "FewShotK",
    "OneShot",
    "SelfConsistency",
    "Strategy",
    "ZeroShot",
    "ZeroShotCoT",
    "get_strategy",
    "select_examples",
]
