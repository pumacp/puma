"""TAWOS dataset loader.

Primary source: data/tawos_clean.csv (pre-processed from TAWOS.sql).
The raw db/TAWOS.sql from https://github.com/SOLAR-group/TAWOS is 4+ GB and
is not parsed at runtime — the clean CSV is the canonical runtime artifact.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

_CSV_PATH = Path("data") / "tawos_clean.csv"
_DB_CSV = Path("db") / "tawos.csv"
_SQL_PATH = Path("db") / "TAWOS.sql"

_REQUIRED_COLS = {"story_id", "project_key", "title", "description", "story_points"}


def _normalise(df: pd.DataFrame) -> pd.DataFrame:
    col_lower = {c.lower(): c for c in df.columns}
    rename = {}
    for canon, aliases in {
        "project_key": ["project"],
        "story_id": ["id", "issue_id"],
        "title": ["summary"],
    }.items():
        if canon not in col_lower:
            for alias in aliases:
                if alias in col_lower:
                    rename[col_lower[alias]] = canon
                    break
    if rename:
        df = df.rename(columns=rename)
    if "story_id" not in df.columns:
        df["story_id"] = df.index.astype(str)
    if "description" not in df.columns:
        df["description"] = ""
    return df


def load(csv_path: Path = _CSV_PATH, db_path: Path = _DB_CSV) -> pd.DataFrame:
    """Load TAWOS dataset from CSV.

    Checks db/tawos.csv first (full dataset), then data/tawos_clean.csv
    (pre-processed balanced subset).
    """
    target = db_path if db_path.exists() else csv_path
    if not target.exists():
        raise FileNotFoundError(
            f"TAWOS data not found. Expected {db_path} or {csv_path}.\n"
            "Run `python scripts/download_datasets.py` or place tawos_clean.csv in data/."
        )
    df = _normalise(pd.read_csv(target))
    if "story_points" in df.columns:
        df = df[df["story_points"].notna() & (df["story_points"] > 0)]
    logger.info("Loaded %d TAWOS issues from %s", len(df), target)
    return df.reset_index(drop=True)


def sample(df: pd.DataFrame, n: int, seed: int = 42) -> pd.DataFrame:
    """Return a reproducible random sample of n rows."""
    if n >= len(df):
        return df.copy()
    return df.sample(n=n, random_state=seed).reset_index(drop=True)
