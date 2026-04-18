"""RunSpec: declarative YAML run specification with Pydantic validation."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, Field, model_validator

VALID_SCENARIOS = Literal["triage_jira", "estimation_tawos", "prioritization_jira"]


class InferenceConfig(BaseModel):
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    seed: int = 42
    max_tokens: int = Field(default=256, gt=0)
    logprobs: bool = False
    top_logprobs: int = Field(default=0, ge=0, le=20)
    format: dict | str | None = None


class AdaptationConfig(BaseModel):
    strategy: list[str] = Field(default_factory=lambda: ["zero-shot"])
    cot: list[bool] = Field(default_factory=lambda: [False])


class SustainabilityConfig(BaseModel):
    codecarbon: bool = False
    country_iso: str = "ESP"


class RunSpec(BaseModel):
    id: str
    description: str = ""
    scenario: VALID_SCENARIOS
    sample_size: int = Field(default=100, gt=0, le=10000)
    models: list[str] = Field(min_length=1)
    adaptation: AdaptationConfig = Field(default_factory=AdaptationConfig)
    inference: InferenceConfig = Field(default_factory=InferenceConfig)
    perturbations: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=lambda: ["f1_macro"])
    sustainability: SustainabilityConfig = Field(default_factory=SustainabilityConfig)
    repeat: int = Field(default=1, ge=1, le=100)
    profile_required: str | None = None

    @model_validator(mode="after")
    def _validate_self_consistency_temperature(self) -> RunSpec:
        strategies = self.adaptation.strategy
        if "self-consistency" in strategies and self.inference.temperature == 0.0:
            raise ValueError(
                "self-consistency strategy requires temperature > 0 "
                "(use temperature=0.7 for meaningful majority voting)"
            )
        return self

    def spec_hash(self) -> str:
        """Stable SHA-256 of the spec content (excluding description)."""
        payload = self.model_dump(exclude={"description"})
        canonical = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]

    @classmethod
    def from_yaml(cls, path: str) -> RunSpec:
        """Load and validate a RunSpec from a YAML file."""

        import yaml

        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        return cls(**data)
