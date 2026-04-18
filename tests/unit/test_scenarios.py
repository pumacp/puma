"""Unit tests for scenario classes — parse_response, gold_label, structure."""

from __future__ import annotations

import pytest

from puma.scenarios.base import Scenario
from puma.scenarios.estimation_tawos import parse_story_points
from puma.scenarios.prioritization_jira import PrioritizationJiraScenario
from puma.scenarios.triage_jira import TriageJiraScenario, parse_prediction


@pytest.mark.unit
class TestTriageJiraScenario:
    def test_is_scenario_subclass(self):
        assert issubclass(TriageJiraScenario, Scenario)

    def test_task_type(self):
        s = TriageJiraScenario()
        assert s.task_type == "classification"

    def test_labels(self):
        s = TriageJiraScenario()
        assert "Critical" in s.labels
        assert "Major" in s.labels

    def test_parse_response_exact(self):
        s = TriageJiraScenario()
        assert s.parse_response("Critical") == "Critical"

    def test_parse_response_case_insensitive(self):
        s = TriageJiraScenario()
        assert s.parse_response("MAJOR issue here") == "Major"

    def test_parse_response_none_on_unknown(self):
        s = TriageJiraScenario()
        assert s.parse_response("I don't know") is None

    def test_gold_label(self):
        s = TriageJiraScenario()
        assert s.gold_label({"priority": "Minor"}) == "Minor"


@pytest.mark.unit
class TestParsePrediction:
    def test_exact_match(self):
        assert parse_prediction("Critical") == "Critical"

    def test_embedded(self):
        assert parse_prediction("This is a major issue") == "Major"

    def test_none_on_no_match(self):
        assert parse_prediction("unknown label") is None


@pytest.mark.unit
class TestParseStoryPoints:
    def test_exact_fibonacci(self):
        assert parse_story_points("5") == 5.0

    def test_snap_to_fibonacci(self):
        assert parse_story_points("4") in [3.0, 5.0]

    def test_none_on_empty(self):
        assert parse_story_points("no number") is None

    def test_integer_in_text(self):
        result = parse_story_points("The answer is 8 story points")
        assert result == 8.0


@pytest.mark.unit
class TestPrioritizationJiraScenario:
    def test_task_type(self):
        s = PrioritizationJiraScenario()
        assert s.task_type == "ranking"

    def test_labels(self):
        s = PrioritizationJiraScenario()
        assert set(s.labels) == {"A", "B"}

    def test_parse_response_a(self):
        s = PrioritizationJiraScenario()
        assert s.parse_response("The answer is A") == "A"

    def test_parse_response_b(self):
        s = PrioritizationJiraScenario()
        assert s.parse_response("B") == "B"

    def test_parse_response_none_on_unknown(self):
        s = PrioritizationJiraScenario()
        assert s.parse_response("neither") is None

    def test_gold_label(self):
        s = PrioritizationJiraScenario()
        assert s.gold_label({"higher_priority": "B"}) == "B"
