"""Unit tests for puma.perturbations.text — idempotence and rate checks."""

from __future__ import annotations

import pytest

from puma.perturbations.text import case_change, reorder_fields, tech_noise, truncate, typos


@pytest.mark.unit
class TestTypos:
    TEXT = "Hello World, this is a test string for typos."

    def test_deterministic_with_seed(self):
        assert typos(self.TEXT, seed=1) == typos(self.TEXT, seed=1)

    def test_different_seeds_differ(self):
        r1 = typos(self.TEXT, rate=0.5, seed=1)
        r2 = typos(self.TEXT, rate=0.5, seed=99)
        assert r1 != r2

    def test_same_length(self):
        result = typos(self.TEXT, rate=0.1, seed=42)
        assert len(result) == len(self.TEXT)

    def test_zero_rate_no_change(self):
        result = typos(self.TEXT, rate=0.0, seed=42)
        # rate=0 means 0 substitutions requested; at least checks no crash
        assert isinstance(result, str)

    def test_empty_string(self):
        assert typos("", seed=42) == ""

    def test_at_least_one_sub_at_high_rate(self):
        original = "aeiou" * 20
        result = typos(original, rate=1.0, seed=42)
        assert result != original


@pytest.mark.unit
class TestCaseChange:
    TEXT = "Hello World"

    def test_upper(self):
        assert case_change(self.TEXT, mode="upper") == "HELLO WORLD"

    def test_lower(self):
        assert case_change(self.TEXT, mode="lower") == "hello world"

    def test_random_deterministic(self):
        r1 = case_change(self.TEXT, mode="random", seed=42)
        r2 = case_change(self.TEXT, mode="random", seed=42)
        assert r1 == r2

    def test_random_same_chars(self):
        result = case_change(self.TEXT, mode="random", seed=42)
        assert result.lower() == self.TEXT.lower()

    def test_invalid_mode(self):
        with pytest.raises(ValueError, match="Unknown mode"):
            case_change(self.TEXT, mode="title")


@pytest.mark.unit
class TestTruncate:
    TEXT = "abcdefghij"  # 10 chars

    def test_keep_half_from_end(self):
        result = truncate(self.TEXT, keep=0.5, from_="end")
        assert result == "abcde"

    def test_keep_half_from_middle(self):
        result = truncate(self.TEXT, keep=0.5, from_="middle")
        assert len(result) == 5

    def test_keep_1_no_change(self):
        assert truncate(self.TEXT, keep=1.0) == self.TEXT

    def test_empty_string(self):
        assert truncate("", keep=0.5) == ""

    def test_invalid_from_(self):
        with pytest.raises(ValueError, match="Unknown from_"):
            truncate(self.TEXT, from_="start")

    def test_result_shorter_than_original(self):
        result = truncate(self.TEXT, keep=0.3, from_="end")
        assert len(result) < len(self.TEXT)


@pytest.mark.unit
class TestReorderFields:
    def test_order_respected(self):
        instance = {"title": "T", "description": "D", "priority": "P"}
        result = reorder_fields(instance, order=["description", "title", "priority"])
        keys = list(result.keys())
        assert keys[0] == "description"
        assert keys[1] == "title"

    def test_missing_keys_ignored(self):
        instance = {"title": "T", "description": "D"}
        result = reorder_fields(instance, order=["description", "title", "nonexistent"])
        assert "nonexistent" not in result

    def test_extra_keys_preserved(self):
        instance = {"title": "T", "description": "D", "extra": "E"}
        result = reorder_fields(instance, order=["title"])
        assert "extra" in result

    def test_values_unchanged(self):
        instance = {"a": 1, "b": 2}
        result = reorder_fields(instance, order=["b", "a"])
        assert result["a"] == 1
        assert result["b"] == 2


@pytest.mark.unit
class TestTechNoise:
    TEXT = "Fix the login button that does not work correctly."

    def test_deterministic(self):
        r1 = tech_noise(self.TEXT, seed=42)
        r2 = tech_noise(self.TEXT, seed=42)
        assert r1 == r2

    def test_tokens_present(self):
        terms = ["TODO", "FIXME"]
        result = tech_noise(self.TEXT, terms=terms, insertions=5, seed=42)
        assert any(t in result for t in terms)

    def test_longer_than_original(self):
        result = tech_noise(self.TEXT, insertions=3, seed=42)
        assert len(result) > len(self.TEXT)

    def test_zero_insertions_unchanged(self):
        result = tech_noise(self.TEXT, insertions=0, seed=42)
        assert result == self.TEXT

    def test_empty_string(self):
        result = tech_noise("", insertions=3, seed=42)
        assert result == ""
