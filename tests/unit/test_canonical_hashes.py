"""Canonical spec and prompt hashes must not move (D42 prototype guard).

The values below were computed on ``develop`` at 378b34d. ``spec_hash`` is
``RunSpec.spec_hash()`` for every canonical run-spec; the prompt hash mirrors
``runner.py`` (``sha256(prompt)[:16]``) over each template rendered with a
fixed synthetic instance. If the templates or specs were moved, re-encoded or
read from a different copy, these values would change.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape

from puma.adaptation.base import PROMPTS_DIR
from puma.orchestrator.runspec import RunSpec
from puma.resources import resolve

_EXPECTED_SPEC_HASH = {
    "baseline_estimation_canonical.yaml": "4d4e4d2cbd53ba91",
    "baseline_triage.yaml": "5cdcac316d06f2ca",
    "baseline_triage_with_logprobs.yaml": "1dd3fca2f401d128",
    "demo_publication.yaml": "92999ed37774b14d",
    "gate_f7_smoke.yaml": "f85b64bd49708883",
    "live_smoke_estimation.yaml": "7467e1ac795fe418",
    "live_smoke_triage.yaml": "e2f6342c4e792132",
    "smoke_estimation.yaml": "6126bae829c10b18",
    "smoke_triage.yaml": "1c18239e4deed5f7",
    "smoke_triage_zeroshot.yaml": "9c4e10726e62d7f9",
    "smoke_triage_zeroshot_cot.yaml": "97b3c261896e6879",
    "sweep_bias_perturbations.yaml": "64d5d90adfbffbdc",
}

_EXPECTED_PROMPT_HASH = {
    "estimation_tawos/contextual_anchoring.jinja": "69b9e9858be8aa49",
    "estimation_tawos/cot_few_shot.jinja": "b80b7e330a4d3195",
    "estimation_tawos/egi.jinja": "c37873cd3b25f70e",
    "estimation_tawos/few_shot.jinja": "0b25a764f0723596",
    "estimation_tawos/rcoif.jinja": "28429d9701c13edd",
    "estimation_tawos/zero_shot.jinja": "00e98d2eca98ddfc",
    "estimation_tawos/zero_shot_cot.jinja": "dc313a02348a8e10",
    "prioritization_jira/contextual_anchoring.jinja": "50479572943692fa",
    "prioritization_jira/cot_few_shot.jinja": "37dd0004747ae629",
    "prioritization_jira/egi.jinja": "d267427658d7fc4b",
    "prioritization_jira/few_shot.jinja": "9387e16e175d48c0",
    "prioritization_jira/rcoif.jinja": "121cace5f2f23a26",
    "prioritization_jira/zero_shot.jinja": "ebe718d18d69b260",
    "prioritization_jira/zero_shot_cot.jinja": "515b617cb182c117",
    "triage_jira/contextual_anchoring.jinja": "3271cfadb7b2f564",
    "triage_jira/cot_few_shot.jinja": "0fc53377da475308",
    "triage_jira/egi.jinja": "cdd8c1c1a512938c",
    "triage_jira/few_shot.jinja": "45593d10b3f0bccf",
    "triage_jira/rcoif.jinja": "e2367d4fb08d1e08",
    "triage_jira/zero_shot.jinja": "e91d184832b6222d",
    "triage_jira/zero_shot_cot.jinja": "0fc49b81635f7f73",
}


class _Lenient(dict):
    def __missing__(self, key):  # every template field renders as "x"
        return "x"


class _Scenario:
    def __init__(self, name: str) -> None:
        self.name = name
        self.labels = ["Critical", "Major", "Minor", "Trivial"]


_INSTANCE = _Lenient(
    issue_key="PUMA-1",
    title="Login fails after upgrade",
    description="Users cannot log in since 2.0.",
    priority="Major",
    story_points=3,
    summary="Login fails after upgrade",
)
_EXAMPLES = [
    _Lenient(
        title="Crash on start",
        description="App crashes",
        priority="Critical",
        story_points=5,
        label="Critical",
        summary="Crash on start",
    )
]


@pytest.mark.unit
def test_spec_hashes_match_develop():
    runs_dir = resolve("specs/runs")
    actual = {
        p.name: RunSpec.from_yaml(str(p)).spec_hash() for p in sorted(runs_dir.glob("*.yaml"))
    }
    assert actual == _EXPECTED_SPEC_HASH


@pytest.mark.unit
def test_prompt_hashes_match_develop():
    actual: dict[str, str] = {}
    for scenario_dir in sorted(d for d in Path(PROMPTS_DIR).iterdir() if d.is_dir()):
        env = Environment(
            loader=FileSystemLoader(str(scenario_dir)),
            autoescape=select_autoescape([]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        scenario = _Scenario(scenario_dir.name)
        for template in sorted(scenario_dir.glob("*.jinja")):
            text = env.get_template(template.name).render(
                instance=_INSTANCE, examples=_EXAMPLES, labels=scenario.labels, scenario=scenario
            )
            key = f"{scenario_dir.name}/{template.name}"
            actual[key] = hashlib.sha256(text.encode()).hexdigest()[:16]
    assert actual == _EXPECTED_PROMPT_HASH
