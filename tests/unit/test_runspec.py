"""Unit tests for puma.orchestrator.runspec — RunSpec validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from puma.orchestrator.runspec import AdaptationConfig, InferenceConfig, RunSpec


def _valid_spec(**overrides) -> dict:
    base = {
        "id": "test_run_v1",
        "description": "Unit test run",
        "scenario": "triage_jira",
        "sample_size": 10,
        "models": ["qwen2.5:3b"],
        "adaptation": {"strategy": ["zero-shot"]},
        "inference": {"temperature": 0.0, "seed": 42},
        "metrics": ["f1_macro"],
    }
    base.update(overrides)
    return base


@pytest.mark.unit
class TestRunSpecValidation:
    def test_valid_spec_parses(self):
        spec = RunSpec(**_valid_spec())
        assert spec.id == "test_run_v1"
        assert spec.scenario == "triage_jira"

    def test_invalid_scenario_raises(self):
        with pytest.raises(ValidationError):
            RunSpec(**_valid_spec(scenario="unknown_scenario"))

    def test_sample_size_must_be_positive(self):
        with pytest.raises(ValidationError):
            RunSpec(**_valid_spec(sample_size=0))

    def test_sample_size_max_10000(self):
        with pytest.raises(ValidationError):
            RunSpec(**_valid_spec(sample_size=99999))

    def test_models_must_not_be_empty(self):
        with pytest.raises(ValidationError):
            RunSpec(**_valid_spec(models=[]))

    def test_self_consistency_requires_temperature_nonzero(self):
        with pytest.raises(ValidationError, match="self-consistency"):
            RunSpec(**_valid_spec(
                adaptation={"strategy": ["self-consistency"]},
                inference={"temperature": 0.0, "seed": 42},
            ))

    def test_repeat_defaults_to_one(self):
        spec = RunSpec(**_valid_spec())
        assert spec.repeat == 1

    def test_spec_hash_stable(self):
        spec1 = RunSpec(**_valid_spec())
        spec2 = RunSpec(**_valid_spec())
        assert spec1.spec_hash() == spec2.spec_hash()

    def test_spec_hash_changes_with_content(self):
        spec1 = RunSpec(**_valid_spec(sample_size=10))
        spec2 = RunSpec(**_valid_spec(sample_size=20))
        assert spec1.spec_hash() != spec2.spec_hash()

    def test_perturbations_default_empty(self):
        spec = RunSpec(**_valid_spec())
        assert spec.perturbations == []

    def test_inference_config_defaults(self):
        spec = RunSpec(**_valid_spec())
        assert spec.inference.temperature == 0.0
        assert spec.inference.seed == 42
        assert spec.inference.logprobs is False


@pytest.mark.unit
class TestAdaptationConfig:
    def test_strategy_list_accepted(self):
        cfg = AdaptationConfig(strategy=["zero-shot", "few-shot-3"])
        assert "zero-shot" in cfg.strategy

    def test_cot_defaults_to_false_list(self):
        cfg = AdaptationConfig(strategy=["zero-shot"])
        assert cfg.cot == [False]


@pytest.mark.unit
class TestInferenceConfig:
    def test_temperature_range(self):
        with pytest.raises(ValidationError):
            InferenceConfig(temperature=-0.1, seed=42)

    def test_seed_required(self):
        cfg = InferenceConfig(temperature=0.0, seed=99)
        assert cfg.seed == 99
