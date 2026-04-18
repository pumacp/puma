"""Dataset integrity verification."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class DatasetReport:
    name: str
    present: bool
    rows: int
    columns: list[str]
    notes: list[str]


def verify_jira(csv_path: Path | None = None) -> DatasetReport:
    from puma.datasets.jira_sr import _CSV_PATH, _DB_CSV, load

    path = csv_path or (_DB_CSV if _DB_CSV.exists() else _CSV_PATH)
    notes: list[str] = []
    if not path.exists():
        return DatasetReport("jira_sr", False, 0, [], [f"File not found: {path}"])
    try:
        df = load()
        if "priority" in df.columns:
            dist = df["priority"].value_counts().to_dict()
            notes.append(f"Priority distribution: {dist}")
        return DatasetReport("jira_sr", True, len(df), list(df.columns), notes)
    except Exception as exc:
        return DatasetReport("jira_sr", False, 0, [], [str(exc)])


def verify_tawos(sql_path: Path | None = None) -> DatasetReport:
    from puma.datasets.tawos import load

    notes: list[str] = []
    try:
        df = load()
        if "project_key" in df.columns:
            projs = df["project_key"].value_counts().head(5).to_dict()
            notes.append(f"Top projects: {projs}")
        if "story_points" in df.columns:
            notes.append(f"SP range: {df['story_points'].min():.0f}–{df['story_points'].max():.0f}")
        return DatasetReport("tawos", True, len(df), list(df.columns), notes)
    except FileNotFoundError as exc:
        return DatasetReport("tawos", False, 0, [], [str(exc)])
    except Exception as exc:
        return DatasetReport("tawos", False, 0, [], [str(exc)])


def print_verify_report(reports: list[DatasetReport]) -> bool:
    """Print report to stdout. Returns True if all datasets present."""
    all_ok = True
    for r in reports:
        status = "OK" if r.present else "MISSING"
        print(f"  [{status}] {r.name}")
        if r.present:
            print(f"         rows={r.rows}, cols={len(r.columns)}")
        for note in r.notes:
            print(f"         {note}")
        if not r.present:
            all_ok = False
    return all_ok
