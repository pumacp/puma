"""Integration tests — verify data files exist and have correct structure."""

from pathlib import Path

import pandas as pd
import pytest


@pytest.mark.integration
class TestDataFiles:
    def test_jira_csv_exists(self):
        assert Path("data/jira_balanced_200.csv").exists()

    def test_tawos_csv_exists(self):
        assert Path("data/tawos_clean.csv").exists()

    def test_jira_csv_structure(self):
        df = pd.read_csv("data/jira_balanced_200.csv")
        for col in ("issue_key", "title", "description", "priority"):
            assert col in df.columns

    def test_jira_class_balance(self):
        df = pd.read_csv("data/jira_balanced_200.csv")
        counts = df["priority"].value_counts()
        assert len(counts) <= 4
        for prio in ("Critical", "Major", "Minor", "Trivial"):
            if prio in counts.index:
                assert 40 <= counts[prio] <= 60

    def test_tawos_csv_structure(self):
        df = pd.read_csv("data/tawos_clean.csv")
        for col in ("project", "title", "description", "story_points"):
            assert col in df.columns

    def test_tawos_mesos_project(self):
        df = pd.read_csv("data/tawos_clean.csv")
        assert "MESOS" in df["project"].values
        assert len(df[df["project"] == "MESOS"]) >= 100
