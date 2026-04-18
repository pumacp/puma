"""Integration tests — TAWOS SQL parse and Jira CSV load."""

from __future__ import annotations

import pytest

from puma.datasets.jira_sr import load as load_jira
from puma.datasets.tawos import load as load_tawos
from puma.datasets.verify import verify_jira, verify_tawos


@pytest.mark.integration
class TestTawosLoad:
    def test_load_returns_dataframe(self):
        df = load_tawos()
        assert len(df) > 0

    def test_required_columns_present(self):
        df = load_tawos()
        for col in ("story_id", "project_key", "title", "description", "story_points"):
            assert col in df.columns, f"Missing column: {col}"

    def test_story_points_positive(self):
        df = load_tawos()
        assert (df["story_points"] > 0).all()

    def test_mesos_project_present(self):
        df = load_tawos()
        assert "MESOS" in df["project_key"].values

    def test_multiple_projects(self):
        df = load_tawos()
        assert df["project_key"].nunique() >= 2


@pytest.mark.integration
class TestJiraLoad:
    def test_load_returns_dataframe(self):
        df = load_jira()
        assert len(df) > 0

    def test_required_columns(self):
        df = load_jira()
        for col in ("issue_key", "title", "description", "priority"):
            assert col in df.columns

    def test_priorities_capitalised(self):
        df = load_jira()
        valid = {"Blocker", "Critical", "Major", "Minor", "Trivial"}
        assert set(df["priority"].unique()).issubset(valid)


@pytest.mark.integration
class TestVerifyDatasets:
    def test_verify_jira_passes(self):
        report = verify_jira()
        assert report.present
        assert report.rows > 0

    def test_verify_tawos_passes(self):
        report = verify_tawos()
        assert report.present
        assert report.rows > 0
