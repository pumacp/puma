"""Abstract base class for prompting strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader, select_autoescape

if TYPE_CHECKING:

    from puma.scenarios.base import Scenario

PROMPTS_DIR = Path(__file__).parent.parent.parent.parent / "specs" / "prompts"


def _get_jinja_env(scenario_name: str) -> Environment:
    template_dir = PROMPTS_DIR / scenario_name
    if not template_dir.exists():
        template_dir = PROMPTS_DIR
    return Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape([]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


class Strategy(ABC):
    """Base class for all prompting adaptation strategies."""

    name: str

    def build_prompt(
        self,
        scenario: Scenario,
        instance: dict,
        examples: list[dict] | None = None,
    ) -> str:
        """Render the Jinja template for this strategy and scenario."""
        env = _get_jinja_env(scenario.name)
        template = env.get_template(self._template_name(scenario.name))
        return template.render(
            instance=instance,
            examples=examples or [],
            labels=scenario.labels,
            scenario=scenario,
        )

    def parse(self, raw_response: str, scenario: Scenario) -> str | float | None:
        """Delegate response parsing to the scenario."""
        return scenario.parse_response(raw_response)

    @abstractmethod
    def _template_name(self, scenario_name: str) -> str:
        """Return the Jinja template filename for this strategy."""
