"""Abstract base class for PUMA evaluation scenarios."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Literal

import pandas as pd


class Scenario(ABC):
    """Base class for all evaluation scenarios."""

    name: ClassVar[str]
    dataset: ClassVar[str]
    task_type: ClassVar[Literal["classification", "regression", "ranking"]]
    labels: ClassVar[list[str]]

    @abstractmethod
    def sample(self, n: int, seed: int = 42) -> pd.DataFrame:
        """Return a reproducible random subset of n instances."""

    @abstractmethod
    def parse_response(self, raw: str) -> str | float | None:
        """Extract structured prediction from raw LLM text. Returns None if unparseable."""

    @abstractmethod
    def gold_label(self, instance: dict[str, Any]) -> str | float:
        """Return the ground-truth label for an instance dict (row from DataFrame)."""
