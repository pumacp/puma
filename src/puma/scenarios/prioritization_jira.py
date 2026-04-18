"""Prioritization scenario: pairwise priority ranking on Jira issues."""

from __future__ import annotations

import re

import pandas as pd

from puma.scenarios.base import Scenario

PRIORITY_ORDER = {"Blocker": 5, "Critical": 4, "Major": 3, "Minor": 2, "Trivial": 1}
_ANSWER_RE = re.compile(r"\b([AB])\b", re.IGNORECASE)


def _priority_rank(priority: str) -> int:
    return PRIORITY_ORDER.get(priority.capitalize(), 0)


class PrioritizationJiraScenario(Scenario):
    """Pairwise priority ranking on Jira Social Repository issues."""

    name = "prioritization_jira"
    dataset = "jira_sr"
    task_type = "ranking"
    labels = ["A", "B"]

    def sample(self, n: int, seed: int = 42) -> pd.DataFrame:
        from puma.datasets.jira_sr import load, sample

        base = sample(load(), n * 2, seed=seed)
        rows = base.to_dict("records")
        pairs = []
        for i in range(0, len(rows) - 1, 2):
            a, b = rows[i], rows[i + 1]
            rank_a = _priority_rank(str(a.get("priority", "")))
            rank_b = _priority_rank(str(b.get("priority", "")))
            gold = "A" if rank_a >= rank_b else "B"
            pairs.append({
                "issue_key_a": a.get("issue_key", f"A_{i}"),
                "issue_key_b": b.get("issue_key", f"B_{i}"),
                "title_a": a.get("title", ""),
                "description_a": a.get("description", ""),
                "priority_a": a.get("priority", ""),
                "title_b": b.get("title", ""),
                "description_b": b.get("description", ""),
                "priority_b": b.get("priority", ""),
                "higher_priority": gold,
            })
        return pd.DataFrame(pairs[:n])

    def parse_response(self, raw: str) -> str | None:
        m = _ANSWER_RE.search(raw)
        return m.group(0).upper() if m else None

    def gold_label(self, instance: dict) -> str:
        return str(instance.get("higher_priority", "A"))
