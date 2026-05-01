"""Jira Social Repository dataset loader."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

_CSV_PATH = Path("data") / "jira_balanced_200.csv"
_DB_CSV = Path("db") / "jira_sr.csv"

_REQUIRED_COLS = {"issue_key", "title", "description", "priority"}
_PRIORITY_MAP = {
    "blocker": "Blocker", "critical": "Critical",
    "major": "Major", "minor": "Minor", "trivial": "Trivial",
}


def _normalise(df: pd.DataFrame) -> pd.DataFrame:
    rename = {}
    col_lower = {c.lower(): c for c in df.columns}
    for canon in ("issue_key", "title", "summary", "description", "priority",
                  "project_key", "issue_type", "created", "resolved"):
        if canon in col_lower and col_lower[canon] != canon:
            rename[col_lower[canon]] = canon
    if rename:
        df = df.rename(columns=rename)
    if "issue_key" not in df.columns:
        df["issue_key"] = df.index.astype(str)
    if "title" not in df.columns and "summary" in df.columns:
        df["title"] = df["summary"]
    if "description" not in df.columns:
        df["description"] = ""
    if "priority" in df.columns:
        df["priority"] = df["priority"].str.capitalize()
    return df


def load(csv_path: Path = _CSV_PATH, db_path: Path = _DB_CSV) -> pd.DataFrame:
    """Load Jira SR dataset from CSV."""
    target = db_path if db_path.exists() else csv_path
    if not target.exists():
        raise FileNotFoundError(
            f"Jira SR data not found. Expected {db_path} or {csv_path}."
        )
    df = _normalise(pd.read_csv(target))
    logger.info("Loaded %d Jira issues from %s", len(df), target)
    return df


def sample(
    df: pd.DataFrame,
    n: int,
    seed: int = 42,
    stratify_by: str = "priority",
) -> pd.DataFrame:
    """Return a reproducible stratified sample of n rows."""
    if n >= len(df):
        return df.copy()
    if stratify_by in df.columns:
        groups = df.groupby(stratify_by, group_keys=False)
        per_class = max(1, n // df[stratify_by].nunique())
        sampled = pd.concat([
            g.sample(min(per_class, len(g)), random_state=seed)
            for _, g in groups
        ])
        if len(sampled) < n:
            remaining = df.drop(sampled.index)
            extra = remaining.sample(min(n - len(sampled), len(remaining)), random_state=seed)
            sampled = pd.concat([sampled, extra])
        return sampled.head(n).reset_index(drop=True)
    return df.sample(n=n, random_state=seed).reset_index(drop=True)
