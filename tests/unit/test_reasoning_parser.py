"""TDD-first tests for the <think>-block reasoning stripper (debt D17).

Reasoning models such as deepseek-r1 emit ``<think>...</think>`` blocks
containing internal deliberation that often shadows the final answer with
incidental matches against PUMA's regex extractors (e.g. the literal word
"critical" appearing inside reasoning). This module strips those blocks
*before* the per-scenario parser runs, restoring the same parse path used
for plain instruction-tuned models.

Tests fail until ``puma.scenarios._reasoning.strip_reasoning`` lands and the
three scenario parsers (``parse_prediction``, ``parse_story_points``,
prioritization's ``parse_response``) call it on entry.
"""

from __future__ import annotations

import pytest

from puma.scenarios._reasoning import strip_reasoning
from puma.scenarios.estimation_tawos import parse_story_points
from puma.scenarios.prioritization_jira import PrioritizationJiraScenario
from puma.scenarios.triage_jira import parse_prediction


@pytest.mark.unit
def test_strip_reasoning_removes_closed_block() -> None:
    raw = "<think>The bug is critical.</think>\nMajor"
    assert strip_reasoning(raw).strip() == "Major"


@pytest.mark.unit
def test_strip_reasoning_passthrough_simple_output() -> None:
    raw = "Major"
    assert strip_reasoning(raw) == "Major"


@pytest.mark.unit
def test_strip_reasoning_handles_inline_block() -> None:
    raw = "Hmm: <think>let me think</think> Critical"
    cleaned = strip_reasoning(raw)
    assert "<think>" not in cleaned and "</think>" not in cleaned
    assert "Critical" in cleaned


@pytest.mark.unit
def test_strip_reasoning_drops_unclosed_block_to_end() -> None:
    """Unclosed <think> (model truncated) — answer must appear before the
    block; everything from the lone <think> onwards is discarded."""
    raw = "Major\n<think>more reasoning..."
    assert strip_reasoning(raw).strip() == "Major"


@pytest.mark.unit
def test_strip_reasoning_strips_stray_close_tag() -> None:
    raw = "Major</think>"
    assert strip_reasoning(raw).strip() == "Major"


@pytest.mark.unit
def test_parse_prediction_with_reasoning_avoids_false_positive() -> None:
    """The reasoning mentions 'critical' incidentally; final answer is Major."""
    raw = "<think>Initially I thought this might be critical, but actually...</think>\nMajor"
    assert parse_prediction(raw) == "Major"


@pytest.mark.unit
def test_parse_story_points_with_reasoning_avoids_false_number() -> None:
    """The reasoning mentions '5' incidentally; final answer is 8."""
    raw = "<think>Maybe 5 points? No, this is larger and riskier.</think>\n8"
    assert parse_story_points(raw) == 8.0


@pytest.mark.unit
def test_prioritization_parse_with_reasoning() -> None:
    """Reasoning mentions both A and B; final answer is B."""
    scen = PrioritizationJiraScenario()
    raw = "<think>Could be A but actually B is higher priority because...</think>\nB"
    assert scen.parse_response(raw) == "B"
