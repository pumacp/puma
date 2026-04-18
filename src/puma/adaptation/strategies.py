"""Nine prompting strategies for PUMA evaluation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from puma.adaptation.base import Strategy

if TYPE_CHECKING:
    from puma.scenarios.base import Scenario


class ZeroShot(Strategy):
    """Direct zero-shot prompting with no examples."""

    name = "zero-shot"

    def _template_name(self, scenario_name: str) -> str:
        return "zero_shot.jinja"


class ZeroShotCoT(Strategy):
    """Zero-shot chain-of-thought: appends 'think step by step' instruction."""

    name = "zero-shot-cot"

    def _template_name(self, scenario_name: str) -> str:
        return "zero_shot_cot.jinja"


class OneShot(Strategy):
    """One-shot prompting with a single example."""

    name = "one-shot"

    def _template_name(self, scenario_name: str) -> str:
        return "few_shot.jinja"

    def build_prompt(
        self,
        scenario: Scenario,
        instance: dict,
        examples: list[dict] | None = None,
    ) -> str:
        if examples and len(examples) > 1:
            examples = examples[:1]
        return super().build_prompt(scenario, instance, examples)


class FewShotK(Strategy):
    """Few-shot prompting with k examples (k ∈ {3, 5, 8})."""

    name = "few-shot-3"

    def __init__(self, k: int = 3) -> None:
        self.k = k
        self.name = f"few-shot-{k}"

    def _template_name(self, scenario_name: str) -> str:
        return "few_shot.jinja"

    def build_prompt(
        self,
        scenario: Scenario,
        instance: dict,
        examples: list[dict] | None = None,
    ) -> str:
        if examples and len(examples) > self.k:
            examples = examples[: self.k]
        return super().build_prompt(scenario, instance, examples)


class CoTFewShot(Strategy):
    """Few-shot with chain-of-thought reasoning in examples."""

    name = "cot-few-shot"

    def _template_name(self, scenario_name: str) -> str:
        return "cot_few_shot.jinja"


class RCOIF(Strategy):
    """Role-Context-Objective-Instructions-Format structured prompt."""

    name = "rcoif"

    def _template_name(self, scenario_name: str) -> str:
        return "rcoif.jinja"


class ContextualAnchoring(Strategy):
    """Fixed PM domain context block anchored at prompt start."""

    name = "contextual-anchoring"

    def _template_name(self, scenario_name: str) -> str:
        return "contextual_anchoring.jinja"


class SelfConsistency(Strategy):
    """Wraps ZeroShot; build_prompt returns zero-shot template; caller must run n=5 times."""

    name = "self-consistency"
    n_samples: int = 5

    def _template_name(self, scenario_name: str) -> str:
        return "zero_shot.jinja"

    def aggregate(self, responses: list[str], scenario: Scenario) -> str | float | None:
        """Majority-vote aggregation over n responses."""
        parsed = [scenario.parse_response(r) for r in responses]
        valid = [p for p in parsed if p is not None]
        if not valid:
            return None
        if isinstance(valid[0], float):
            return sum(valid) / len(valid)  # type: ignore[arg-type]
        return max(set(valid), key=valid.count)


class EGI(Strategy):
    """Exploratory Guided Interaction — multi-turn with clarifying question."""

    name = "egi"

    def _template_name(self, scenario_name: str) -> str:
        return "egi.jinja"

    def clarification_prompt(self, scenario: Scenario, instance: dict) -> str:
        """First-turn clarifying question template."""
        from puma.adaptation.base import _get_jinja_env

        env = _get_jinja_env(scenario.name)
        try:
            tmpl = env.get_template("egi_clarify.jinja")
            return tmpl.render(instance=instance, labels=scenario.labels, scenario=scenario)
        except Exception:
            return self.build_prompt(scenario, instance)


STRATEGY_REGISTRY: dict[str, type[Strategy]] = {
    "zero-shot": ZeroShot,
    "zero-shot-cot": ZeroShotCoT,
    "one-shot": OneShot,
    "few-shot-3": FewShotK,
    "few-shot-5": FewShotK,
    "few-shot-8": FewShotK,
    "cot-few-shot": CoTFewShot,
    "rcoif": RCOIF,
    "contextual-anchoring": ContextualAnchoring,
    "self-consistency": SelfConsistency,
    "egi": EGI,
}


def get_strategy(name: str) -> Strategy:
    """Instantiate a strategy by name."""
    if name not in STRATEGY_REGISTRY:
        raise ValueError(f"Unknown strategy '{name}'. Available: {sorted(STRATEGY_REGISTRY)}")
    cls = STRATEGY_REGISTRY[name]
    if name.startswith("few-shot-"):
        k = int(name.split("-")[-1])
        return cls(k=k)  # type: ignore[call-arg]
    return cls()
