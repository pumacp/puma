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
    "Strategy",
    "ZeroShot",
    "ZeroShotCoT",
    "OneShot",
    "FewShotK",
    "CoTFewShot",
    "RCOIF",
    "ContextualAnchoring",
    "SelfConsistency",
    "EGI",
    "STRATEGY_REGISTRY",
    "get_strategy",
    "select_examples",
]
