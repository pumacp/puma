"""``puma community pull`` — download PUMA Community submissions (Anexo F.16.6).

Downloads all submissions (or a filtered subset) from ``pumacp/puma-community``
to the local filesystem, optionally consolidating into ``jsonl``, ``parquet``,
or ``csv``; ``raw`` preserves one JSON file per submission. Reuses the Contents
API fetch helper from :mod:`puma.community.browse_cli`.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

import typer
from rich.console import Console

from puma.community._community_app import community_app
from puma.community.browse_cli import (
    BrowseError,
    SubmissionRecord,
    fetch_submission_records,
)

log = logging.getLogger("puma.community.pull_cli")
console = Console()

DEFAULT_OUTPUT = Path("data/community/cache")
SUPPORTED_FORMATS = ("jsonl", "parquet", "csv", "raw")

# Filter key -> dotted path inside the submission payload.
_FILTER_KEYS: dict[str, tuple[str, ...]] = {
    "scenario": ("run_metadata", "scenario"),
    "model": ("run_metadata", "model"),
    "model_tag": ("run_metadata", "model"),
    "strategy": ("run_metadata", "strategy"),
    "submission_id": ("submission_id",),
    "submitter": ("submitter", "name_or_alias"),
    "alias": ("submitter", "name_or_alias"),
}

# typer default as a module-level singleton (ruff B008 for the Path-typed param).
_OUTPUT_OPT = typer.Option(DEFAULT_OUTPUT, "--output", help="Output directory.")


class PullError(Exception):
    """Pull failure carrying a process exit code."""

    def __init__(self, message: str, *, exit_code: int) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def _dig(payload: dict[str, Any], path: tuple[str, ...]) -> Any:
    cur: Any = payload
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def parse_filter(expr: str) -> list[tuple[str, str]]:
    """Parse ``key=value AND key=value`` into validated (key, value) pairs.

    Raises :class:`PullError` (exit 3) on a malformed clause or unknown key.
    """
    clauses = re.split(r"\s+AND\s+", expr.strip(), flags=re.IGNORECASE)
    parsed: list[tuple[str, str]] = []
    for clause in clauses:
        if "=" not in clause:
            raise PullError(
                f"Malformed filter clause {clause!r} (expected key=value).", exit_code=3
            )
        key, _, value = clause.partition("=")
        key = key.strip()
        value = value.strip()
        if key not in _FILTER_KEYS:
            raise PullError(
                f"Unknown filter key {key!r}. Allowed: {sorted(_FILTER_KEYS)}.",
                exit_code=3,
            )
        parsed.append((key, value))
    return parsed


def _matches(payload: dict[str, Any], clauses: list[tuple[str, str]]) -> bool:
    for key, value in clauses:
        actual = _dig(payload, _FILTER_KEYS[key])
        if actual is None or str(actual).lower() != value.lower():
            return False
    return True


def _flatten(payload: dict[str, Any]) -> dict[str, Any]:
    """One-level flatten: nested dicts/lists are JSON-encoded into a string cell."""
    flat: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, (dict, list)):
            flat[key] = json.dumps(value, sort_keys=True, ensure_ascii=False)
        else:
            flat[key] = value
    return flat


def _write_jsonl(records: list[SubmissionRecord], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "all.jsonl"
    with target.open("w", encoding="utf-8") as fh:
        for _name, payload in records:
            fh.write(json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str) + "\n")
    return target


def _write_raw(records: list[SubmissionRecord], out_dir: Path) -> Path:
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in records:
        (raw_dir / name).write_text(
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
    return raw_dir


def _write_csv(records: list[SubmissionRecord], out_dir: Path) -> Path:
    import pandas as pd

    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "all.csv"
    frame = pd.DataFrame([_flatten(payload) for _name, payload in records])
    frame.to_csv(target, index=False)
    return target


def _write_parquet(records: list[SubmissionRecord], out_dir: Path) -> Path:
    try:
        import pandas as pd
    except ImportError as exc:  # pragma: no cover — pandas is a core dep
        raise PullError(f"pandas is required for parquet output: {exc}", exit_code=2) from exc
    try:
        import pyarrow  # noqa: F401
    except ImportError as exc:
        raise PullError(
            "parquet output requires pyarrow (`pip install pyarrow`).",
            exit_code=2,
        ) from exc
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "all.parquet"
    frame = pd.DataFrame([_flatten(payload) for _name, payload in records])
    frame.to_parquet(target, index=False)
    return target


@community_app.command(name="pull")
def pull(
    output: Path = _OUTPUT_OPT,
    fmt: str = typer.Option("jsonl", "--format", help="jsonl | parquet | csv | raw."),
    filter_expr: str | None = typer.Option(
        None, "--filter", help='e.g. "scenario=triage_jira AND model_tag=qwen2.5:3b".'
    ),
    limit: int | None = typer.Option(None, "--limit", help="Keep at most N after filtering."),
    anonymous: bool = typer.Option(False, "--anonymous", help="Skip the stored PAT (60 req/h)."),
) -> None:
    """Download submissions (optionally filtered) and consolidate to the chosen format."""
    if fmt not in SUPPORTED_FORMATS:
        console.print(
            f"[red]Unknown --format {fmt!r}. Choose from {list(SUPPORTED_FORMATS)}.[/red]"
        )
        raise typer.Exit(code=2)

    try:
        clauses = parse_filter(filter_expr) if filter_expr else []
    except PullError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=exc.exit_code) from exc

    try:
        records = fetch_submission_records(anonymous=anonymous)
    except BrowseError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=exc.exit_code) from exc

    if clauses:
        records = [rec for rec in records if _matches(rec[1], clauses)]
    if limit is not None and limit >= 0:
        records = records[:limit]

    if not records:
        console.print("No submissions match the filter; nothing downloaded.")
        raise typer.Exit(code=0)

    writers = {
        "jsonl": _write_jsonl,
        "csv": _write_csv,
        "parquet": _write_parquet,
        "raw": _write_raw,
    }
    try:
        with console.status(f"Writing {len(records)} submission(s) as {fmt}…"):
            target = writers[fmt](records, output)
    except PullError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=exc.exit_code) from exc
    except OSError as exc:
        console.print(f"[red]Write error: {exc}[/red]")
        raise typer.Exit(code=2) from exc

    console.print(f"[green]Pulled {len(records)} submission(s)[/green] → {target}")


__all__ = ["PullError", "parse_filter", "pull"]
