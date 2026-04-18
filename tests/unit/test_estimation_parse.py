"""Unit tests for estimation response parsing."""

import pytest

from puma.scenarios.estimation_tawos import (
    DETERMINISTIC_OPTIONS,
    FEW_SHOT_EXAMPLES,
    FIBONACCI_SERIES,
    parse_story_points,
)


@pytest.mark.unit
class TestParseStoryPoints:
    def test_exact_fibonacci(self):
        for sp in FIBONACCI_SERIES:
            assert parse_story_points(str(sp)) == float(sp)

    def test_whitespace(self):
        assert parse_story_points("  5  ") == 5.0

    def test_float_input(self):
        assert parse_story_points("3.0") == 3.0

    def test_rounding_to_fibonacci(self):
        assert parse_story_points("4") == 3  # closest to 3 or 5; 4 is equidistant — min picks 3

    def test_invalid_returns_none(self):
        assert parse_story_points("not a number") is None
        assert parse_story_points("abc") is None
        assert parse_story_points("") is None

    def test_fibonacci_series_constant(self):
        assert FIBONACCI_SERIES == [1, 2, 3, 5, 8, 13, 21]

    def test_few_shot_count(self):
        assert len(FEW_SHOT_EXAMPLES) == 3

    def test_few_shot_structure(self):
        for ex in FEW_SHOT_EXAMPLES:
            assert "title" in ex
            assert "description" in ex
            assert "story_points" in ex

    def test_deterministic_options(self):
        assert DETERMINISTIC_OPTIONS["temperature"] == 0.0
        assert DETERMINISTIC_OPTIONS["seed"] == 42
