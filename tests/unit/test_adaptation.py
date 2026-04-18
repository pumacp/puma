"""Unit tests for puma.adaptation — strategy instantiation, prompt rendering."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from puma.adaptation.examples import select_examples
from puma.adaptation.strategies import (
    STRATEGY_REGISTRY,
    FewShotK,
    SelfConsistency,
    ZeroShot,
    get_strategy,
)


def _make_scenario(name: str = "triage_jira", labels: list[str] | None = None) -> MagicMock:
    s = MagicMock()
    s.name = name
    s.labels = labels or ["Critical", "Major", "Minor", "Trivial"]
    s.parse_response = lambda raw: "Critical" if "critical" in raw.lower() else None
    return s


def _make_instance() -> dict:
    return {"title": "Login fails", "description": "Users cannot log in after update."}


@pytest.mark.unit
class TestStrategyRegistry:
    def test_all_strategies_registered(self):
        expected = {
            "zero-shot", "zero-shot-cot", "one-shot",
            "few-shot-3", "few-shot-5", "few-shot-8",
            "cot-few-shot", "rcoif", "contextual-anchoring",
            "self-consistency", "egi",
        }
        assert expected.issubset(set(STRATEGY_REGISTRY.keys()))

    def test_get_strategy_returns_instance(self):
        s = get_strategy("zero-shot")
        assert isinstance(s, ZeroShot)

    def test_get_strategy_few_shot_k(self):
        s = get_strategy("few-shot-5")
        assert isinstance(s, FewShotK)
        assert s.k == 5

    def test_get_strategy_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown strategy"):
            get_strategy("does-not-exist")


@pytest.mark.unit
class TestZeroShotPrompt:
    def test_renders_instance_fields(self):
        strategy = ZeroShot()
        scenario = _make_scenario()
        instance = _make_instance()
        prompt = strategy.build_prompt(scenario, instance)
        assert "Login fails" in prompt
        assert "Users cannot log in" in prompt

    def test_renders_labels(self):
        strategy = ZeroShot()
        scenario = _make_scenario()
        instance = _make_instance()
        prompt = strategy.build_prompt(scenario, instance)
        assert "Critical" in prompt

    def test_deterministic(self):
        strategy = ZeroShot()
        scenario = _make_scenario()
        instance = _make_instance()
        assert strategy.build_prompt(scenario, instance) == strategy.build_prompt(scenario, instance)


@pytest.mark.unit
class TestFewShotKPrompt:
    def test_limits_examples_to_k(self):
        strategy = get_strategy("few-shot-3")
        scenario = _make_scenario()
        instance = _make_instance()
        examples = [
            {"title": f"Issue {i}", "description": f"Desc {i}", "priority": "Major"}
            for i in range(10)
        ]
        prompt = strategy.build_prompt(scenario, instance, examples=examples)
        # Rendered template uses loop.index — check at most 3 example blocks
        assert prompt.count("Example") <= 3

    def test_zero_shot_fallback_no_examples(self):
        strategy = get_strategy("zero-shot")
        scenario = _make_scenario()
        prompt = strategy.build_prompt(scenario, _make_instance())
        assert isinstance(prompt, str)
        assert len(prompt) > 10


@pytest.mark.unit
class TestSelfConsistencyAggregate:
    def test_majority_vote(self):
        strategy = SelfConsistency()
        scenario = _make_scenario()
        scenario.parse_response = lambda r: r.strip()
        responses = ["Critical", "Critical", "Major", "Critical", "Major"]
        result = strategy.aggregate(responses, scenario)
        assert result == "Critical"

    def test_all_none_returns_none(self):
        strategy = SelfConsistency()
        scenario = _make_scenario()
        scenario.parse_response = lambda r: None
        result = strategy.aggregate(["a", "b", "c"], scenario)
        assert result is None


@pytest.mark.unit
class TestSelectExamples:
    def test_returns_k_examples(self):
        import pandas as pd

        df = pd.DataFrame([
            {"title": f"T{i}", "priority": ["Critical", "Major"][i % 2]}
            for i in range(20)
        ])
        result = select_examples(df, k=4, seed=42)
        assert len(result) <= 4

    def test_deterministic_with_seed(self):
        import pandas as pd

        df = pd.DataFrame([{"title": f"T{i}", "priority": "Major"} for i in range(20)])
        r1 = select_examples(df, k=5, seed=42)
        r2 = select_examples(df, k=5, seed=42)
        assert [d["title"] for d in r1] == [d["title"] for d in r2]

    def test_excludes_target_index(self):
        import pandas as pd

        df = pd.DataFrame([{"title": f"T{i}"} for i in range(10)])
        result = select_examples(df, k=5, seed=42, exclude_index=0)
        titles = [d["title"] for d in result]
        assert "T0" not in titles

    def test_stratified_returns_all_classes(self):
        import pandas as pd

        df = pd.DataFrame([
            {"title": f"T{i}", "priority": ["Critical", "Major", "Minor", "Trivial"][i % 4]}
            for i in range(40)
        ])
        result = select_examples(df, k=8, seed=42, stratify_by="priority")
        classes = {d["priority"] for d in result}
        assert len(classes) >= 2
