"""Unit tests for puma.datasets — loaders and verify."""

from __future__ import annotations

import pandas as pd
import pytest

from puma.datasets.jira_sr import _normalise
from puma.datasets.jira_sr import sample as jira_sample
from puma.datasets.tawos import sample as tawos_sample
from puma.datasets.verify import DatasetReport, print_verify_report


@pytest.mark.unit
class TestJiraNormalise:
    def test_normalises_summary_to_title(self):
        df = pd.DataFrame({"Summary": ["Issue 1"], "Priority": ["major"], "Description": ["d"]})
        out = _normalise(df)
        assert "title" in out.columns
        assert out["title"].iloc[0] == "Issue 1"

    def test_capitalises_priority(self):
        df = pd.DataFrame({"issue_key": ["K-1"], "title": ["T"], "description": ["D"], "priority": ["major"]})
        out = _normalise(df)
        assert out["priority"].iloc[0] == "Major"

    def test_adds_issue_key_if_missing(self):
        df = pd.DataFrame({"title": ["T"], "description": ["D"], "priority": ["Major"]})
        out = _normalise(df)
        assert "issue_key" in out.columns


@pytest.mark.unit
class TestJiraSample:
    def _make_df(self):
        return pd.DataFrame({
            "issue_key": [f"K-{i}" for i in range(20)],
            "priority": ["Critical"] * 5 + ["Major"] * 5 + ["Minor"] * 5 + ["Trivial"] * 5,
            "title": ["t"] * 20,
            "description": ["d"] * 20,
        })

    def test_sample_size(self):
        df = self._make_df()
        s = jira_sample(df, n=8, seed=42)
        assert len(s) == 8

    def test_sample_deterministic(self):
        df = self._make_df()
        s1 = jira_sample(df, n=8, seed=42)
        s2 = jira_sample(df, n=8, seed=42)
        assert list(s1["issue_key"]) == list(s2["issue_key"])

    def test_sample_larger_than_df_returns_all(self):
        df = self._make_df()
        s = jira_sample(df, n=100, seed=42)
        assert len(s) == len(df)


@pytest.mark.unit
class TestTawosSample:
    def _make_df(self):
        return pd.DataFrame({
            "story_id": [str(i) for i in range(30)],
            "project_key": ["MESOS"] * 30,
            "title": ["t"] * 30,
            "description": ["d"] * 30,
            "story_points": [1, 2, 3, 5, 8, 13] * 5,
        })

    def test_sample_size(self):
        df = self._make_df()
        s = tawos_sample(df, n=10, seed=0)
        assert len(s) == 10

    def test_sample_deterministic(self):
        df = self._make_df()
        s1 = tawos_sample(df, n=10, seed=7)
        s2 = tawos_sample(df, n=10, seed=7)
        assert list(s1["story_id"]) == list(s2["story_id"])


@pytest.mark.unit
class TestVerifyReport:
    def test_all_ok_returns_true(self, capsys):
        reports = [
            DatasetReport("jira_sr", True, 200, ["issue_key", "priority"], []),
            DatasetReport("tawos", True, 1000, ["story_id", "story_points"], []),
        ]
        result = print_verify_report(reports)
        assert result is True

    def test_missing_returns_false(self, capsys):
        reports = [
            DatasetReport("jira_sr", False, 0, [], ["File not found"]),
        ]
        result = print_verify_report(reports)
        assert result is False
