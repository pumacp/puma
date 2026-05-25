"""``puma community browse`` — list PUMA Community submissions (Anexo F.16.5).

Reads the public ``submissions/`` index of ``pumacp/puma-community`` through the
GitHub Contents API and renders a filtered Rich table (or JSON). Authentication
is optional: a stored GitHub PAT raises the rate limit from 60 to 5000 req/h,
but ``--anonymous`` (or simply having no token) still works for public reads.

This module owns the shared submission-fetch helper (:func:`fetch_submission_records`)
reused by :mod:`puma.community.pull_cli`; both speak to the Contents API over
``httpx`` (not PyGithub) so the HTTP surface is mockable with ``respx`` in tests.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

import httpx
import typer
from rich.console import Console
from rich.table import Table

from puma.community._community_app import community_app
from puma.community.credentials import CredentialStore

log = logging.getLogger("puma.community.browse_cli")
console = Console()

GITHUB_API = "https://api.github.com"
UPSTREAM_OWNER = "pumacp"
UPSTREAM_REPO = "puma-community"
SUBMISSIONS_DIR = "submissions"
HTTP_TIMEOUT_S = 30.0

# (filename, parsed submission payload)
SubmissionRecord = tuple[str, dict[str, Any]]


class BrowseError(Exception):
    """Base class for browse/pull fetch failures, carrying a process exit code."""

    def __init__(self, message: str, *, exit_code: int) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def _auth_headers(*, anonymous: bool) -> dict[str, str]:
    """Return Contents-API headers, adding a Bearer PAT unless ``anonymous``."""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if anonymous:
        return headers
    token = CredentialStore().get("github")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _raise_for_listing(resp: httpx.Response) -> None:
    """Map a non-200 Contents-API listing response to a :class:`BrowseError`."""
    if resp.status_code == 200:
        return
    if resp.status_code == 403 and resp.headers.get("X-RateLimit-Remaining") == "0":
        raise BrowseError(
            "GitHub API rate limit exhausted. Authenticate to raise it: `puma auth login github`.",
            exit_code=2,
        )
    raise BrowseError(
        f"GitHub Contents API returned HTTP {resp.status_code} for the submissions index.",
        exit_code=1,
    )


def fetch_submission_records(
    *,
    anonymous: bool = False,
    client: httpx.Client | None = None,
) -> list[SubmissionRecord]:
    """Return ``(filename, payload)`` for every ``*.json`` under ``submissions/``.

    Raises :class:`BrowseError` (carrying an ``exit_code``) on a non-reachable
    or rate-limited API. The caller owns translating that into ``typer.Exit``.
    """
    owns_client = client is None
    http = client if client is not None else httpx.Client(timeout=HTTP_TIMEOUT_S)
    headers = _auth_headers(anonymous=anonymous)
    index_url = f"{GITHUB_API}/repos/{UPSTREAM_OWNER}/{UPSTREAM_REPO}/contents/{SUBMISSIONS_DIR}"
    try:
        try:
            resp = http.get(index_url, headers=headers)
        except httpx.HTTPError as exc:
            raise BrowseError(f"GitHub API not reachable: {exc}", exit_code=1) from exc
        _raise_for_listing(resp)

        records: list[SubmissionRecord] = []
        for entry in resp.json():
            if entry.get("type") != "file":
                continue
            name = str(entry.get("name", ""))
            if not name.endswith(".json"):
                continue
            download_url = entry.get("download_url")
            if not download_url:
                continue
            try:
                file_resp = http.get(download_url, headers=headers)
            except httpx.HTTPError as exc:
                raise BrowseError(f"GitHub API not reachable: {exc}", exit_code=1) from exc
            if file_resp.status_code != 200:
                log.warning("skipping %s: HTTP %d", name, file_resp.status_code)
                continue
            try:
                payload = file_resp.json()
            except json.JSONDecodeError:
                log.warning("skipping %s: invalid JSON", name)
                continue
            records.append((name, payload))
        return records
    finally:
        if owns_client:
            http.close()


def _primary_metric(payload: dict[str, Any]) -> str:
    """Return the headline metric (f1_macro for triage, mae for estimation)."""
    metrics = payload.get("metrics", {}) or {}
    if metrics.get("f1_macro") is not None:
        return f"f1={float(metrics['f1_macro']):.4f}"
    if metrics.get("mae") is not None:
        return f"mae={float(metrics['mae']):.4f}"
    if metrics.get("accuracy") is not None:
        return f"acc={float(metrics['accuracy']):.4f}"
    return "—"


def _row_for(payload: dict[str, Any]) -> dict[str, Any]:
    """Flatten a submission payload into the display columns."""
    run_md = payload.get("run_metadata", {}) or {}
    submitter = payload.get("submitter", {}) or {}
    sustainability = payload.get("sustainability", {}) or {}
    return {
        "submission_id": str(payload.get("submission_id", "—")),
        "scenario": str(run_md.get("scenario", "—")),
        "model": str(run_md.get("model", "—")),
        "strategy": str(run_md.get("strategy", "—")),
        "metric": _primary_metric(payload),
        "co2_grams_total": sustainability.get("co2_grams_total"),
        "submitted_at": str(payload.get("submitted_at", "—")),
        "submitter_alias": str(submitter.get("name_or_alias", "—")),
    }


def _parse_since(since: str) -> datetime:
    """Parse an ISO 8601 date/datetime; raise BrowseError(exit 1) on bad input."""
    try:
        parsed = datetime.fromisoformat(since)
    except ValueError as exc:
        raise BrowseError(
            f"--since value {since!r} is not an ISO 8601 date (e.g. 2026-05-01).",
            exit_code=1,
        ) from exc
    return parsed


def _submitted_at(payload: dict[str, Any]) -> datetime | None:
    raw = payload.get("submitted_at")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw))
    except ValueError:
        return None


def _apply_filters(
    records: list[SubmissionRecord],
    *,
    scenario: str | None,
    model: str | None,
    since: str | None,
    last_n: int | None,
) -> list[dict[str, Any]]:
    """Apply client-side filters and return the display rows."""
    rows: list[tuple[datetime | None, dict[str, Any]]] = []
    since_dt = _parse_since(since) if since else None
    for _name, payload in records:
        run_md = payload.get("run_metadata", {}) or {}
        if scenario and scenario.lower() not in str(run_md.get("scenario", "")).lower():
            continue
        if model and model.lower() not in str(run_md.get("model", "")).lower():
            continue
        sub_dt = _submitted_at(payload)
        if since_dt is not None and (sub_dt is None or sub_dt < _ensure_aware(since_dt, sub_dt)):
            continue
        rows.append((sub_dt, _row_for(payload)))

    # Sort newest-first; None timestamps sort last.
    rows.sort(key=lambda pair: (pair[0] is not None, pair[0] or datetime.min), reverse=True)
    ordered = [row for _dt, row in rows]
    if last_n is not None and last_n >= 0:
        ordered = ordered[:last_n]
    return ordered


def _ensure_aware(reference: datetime, sample: datetime | None) -> datetime:
    """Align ``reference`` tz-awareness to ``sample`` to allow a safe comparison."""
    if sample is None:
        return reference
    if sample.tzinfo is not None and reference.tzinfo is None:
        return reference.replace(tzinfo=sample.tzinfo)
    if sample.tzinfo is None and reference.tzinfo is not None:
        return reference.replace(tzinfo=None)
    return reference


def _render_table(rows: list[dict[str, Any]]) -> None:
    table = Table(title="PUMA Community submissions", show_lines=False)
    for col in (
        "submission_id",
        "scenario",
        "model",
        "strategy",
        "metric",
        "co2_g",
        "submitted_at",
        "submitter",
    ):
        table.add_column(col, overflow="fold")
    for row in rows:
        co2 = row["co2_grams_total"]
        table.add_row(
            row["submission_id"],
            row["scenario"],
            row["model"],
            row["strategy"],
            row["metric"],
            f"{float(co2):.2f}" if co2 is not None else "—",
            row["submitted_at"],
            row["submitter_alias"],
        )
    console.print(table)


@community_app.command(name="browse")
def browse(
    scenario: str | None = typer.Option(None, "--scenario", help="Filter by scenario substring."),
    model: str | None = typer.Option(None, "--model", help="Filter by model substring."),
    last_n: int | None = typer.Option(None, "--last-n", help="Keep the N most recent."),
    since: str | None = typer.Option(None, "--since", help="ISO 8601 date, e.g. 2026-05-01."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON instead of a table."),
    anonymous: bool = typer.Option(False, "--anonymous", help="Skip the stored PAT (60 req/h)."),
) -> None:
    """List submissions in pumacp/puma-community, filtered and sorted newest-first."""
    try:
        records = fetch_submission_records(anonymous=anonymous)
        rows = _apply_filters(records, scenario=scenario, model=model, since=since, last_n=last_n)
    except BrowseError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=exc.exit_code) from exc

    if not rows:
        console.print("No submissions match the filter.")
        raise typer.Exit(code=0)

    if json_output:
        typer.echo(json.dumps(rows, indent=2, sort_keys=True, default=str))
        return
    _render_table(rows)


__all__ = [
    "BrowseError",
    "SubmissionRecord",
    "browse",
    "fetch_submission_records",
]
