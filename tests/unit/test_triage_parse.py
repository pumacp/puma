"""Unit tests for triage response parsing."""

import pytest

from puma.scenarios.triage_jira import (
    DETERMINISTIC_OPTIONS,
    SYSTEM_PROMPT,
    VALID_PRIORITIES,
    parse_prediction,
)


@pytest.mark.unit
class TestParsePredict:
    def test_exact_match(self):
        assert parse_prediction("Critical") == "Critical"
        assert parse_prediction("Major") == "Major"
        assert parse_prediction("Minor") == "Minor"
        assert parse_prediction("Trivial") == "Trivial"

    def test_case_insensitive(self):
        assert parse_prediction("critical") == "Critical"
        assert parse_prediction("MAJOR") == "Major"
        assert parse_prediction("minor") == "Minor"

    def test_embedded_in_text(self):
        assert parse_prediction("The issue is Critical") == "Critical"
        assert parse_prediction("Priority: Major") == "Major"

    def test_whitespace_stripped(self):
        assert parse_prediction("  Critical  ") == "Critical"

    def test_invalid_returns_none(self):
        assert parse_prediction("High") is None
        assert parse_prediction("Low") is None
        assert parse_prediction("unknown") is None
        assert parse_prediction("") is None
        assert parse_prediction("BLOCKER") is None

    def test_valid_priorities_constant(self):
        assert VALID_PRIORITIES == ["Critical", "Major", "Minor", "Trivial"]

    def test_deterministic_options(self):
        assert DETERMINISTIC_OPTIONS["temperature"] == 0.0
        assert DETERMINISTIC_OPTIONS["seed"] == 42

    def test_system_prompt_contains_labels(self):
        for label in VALID_PRIORITIES:
            assert label in SYSTEM_PROMPT
