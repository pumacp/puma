"""``puma community verify-hash`` — integrity check for a submission (Anexo F.16.8).

Recomputes ``predictions_summary_hash`` from a predictions JSONL and compares it
to the value declared in the submission JSON. The local recomputation is
**byte-identical** to the canonical algorithm in
:mod:`puma.community.integrity`: it reuses that module's column order and
per-cell serializer so a file-based check agrees bit-for-bit with the
database-based hash produced at submission time.

Predictions JSONL contract — one JSON object per line, carrying the canonical
columns: ``instance_id``, ``predicted_label``, ``predicted_value``,
``prompt_hash``. Rows are ordered by ``instance_id`` ascending before hashing.

``--remote`` (deuda técnica D23): the Verifier Space
``pumaproject/puma-verifier`` hashes a *different* input shape (a 2-field
``instance_id``/``prediction`` JSONL fetched from ``raw_predictions_url``) and
prefixes ``sha256:``. It therefore returns a systematic ``mismatch`` for genuine
submissions even though the local hash matches. ``raw_predictions_url`` IS an
optional field in schema v1.0.0, so ``--remote`` is reachable when that field is
present; it is simply uninformative until D23 is resolved (see
``docs/known_debt.md``). Local verification is canonical.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import os
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from puma.community._community_app import community_app
from puma.community.integrity import _COLUMNS, _serialize_value
from puma.ui.themes import Theme, get_theme

log = logging.getLogger("puma.community.verify_cli")
console = Console()
err_console = Console(stderr=True)

VERIFIER_SPACE = "pumaproject/puma-verifier"

# typer defaults held as module-level singletons (ruff B008: avoid calls in
# argument defaults for Path-typed parameters).
_SUBMISSION_ARG = typer.Argument(..., exists=True, help="Submission JSON.")
_PREDICTIONS_OPT = typer.Option(
    None, "--predictions", help="Predictions JSONL (defaults to <id>.predictions.jsonl)."
)


def hash_predictions_jsonl(path: Path) -> str:
    """Return the canonical SHA-256 over a predictions JSONL.

    Byte-identical to :func:`puma.community.integrity.compute_predictions_hash`:
    same column order (``_COLUMNS``), same per-cell serializer
    (``_serialize_value``), CSV with LF line terminator and ``QUOTE_MINIMAL``,
    trailing newline stripped, UTF-8 encoded.
    """
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if not stripped:
                continue
            rows.append(json.loads(stripped))
    rows.sort(key=lambda r: str(r.get("instance_id", "")))

    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
    for row in rows:
        writer.writerow([_serialize_value(row.get(col)) for col in _COLUMNS])
    csv_text = buf.getvalue().rstrip("\n")
    return hashlib.sha256(csv_text.encode("utf-8")).hexdigest()


def _resolve_predictions_path(submission_path: Path, predictions_path: Path | None) -> Path | None:
    """Return the predictions JSONL path, or None if it cannot be located."""
    if predictions_path is not None:
        return predictions_path if predictions_path.is_file() else None
    conventional = submission_path.parent / f"{submission_path.stem}.predictions.jsonl"
    return conventional if conventional.is_file() else None


def _call_verifier(*, url: str, declared_hash: str, token: str) -> dict[str, Any]:
    """Invoke the Verifier Space via gradio_client. Patched in tests."""
    from gradio_client import Client

    client = Client(VERIFIER_SPACE, hf_token=token)
    result = client.predict(url, declared_hash, api_name="/verify")
    if isinstance(result, str):
        parsed: Any = json.loads(result)
        return dict(parsed)
    return dict(result)


def _render_local(declared: str, computed: str, verdict: str, theme: Theme | None = None) -> None:
    t = theme or get_theme(None)
    table = Table(title="verify-hash (local)", show_lines=False)
    table.add_column("field", style=t.accent)
    table.add_column("value", overflow="fold")
    table.add_row("declared_hash", declared)
    table.add_row("computed_hash", computed)
    style = t.success if verdict.startswith("verified") else t.error
    table.add_row("verdict", f"[{style}]{verdict}[/{style}]")
    console.print(table)


@community_app.command(name="verify-hash")
def verify_hash(
    ctx: typer.Context,
    submission_path: Path = _SUBMISSION_ARG,
    predictions_path: Path | None = _PREDICTIONS_OPT,
    remote: bool = typer.Option(False, "--remote", help="Also query the Verifier Space (D23)."),
) -> None:
    """Recompute the predictions hash locally and compare to the declared value."""
    theme = (ctx.obj or {}).get("theme") or get_theme(None)
    try:
        payload: dict[str, Any] = json.loads(submission_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        console.print(f"[{theme.error}]Cannot read submission JSON: {exc}[/{theme.error}]")
        raise typer.Exit(code=2) from exc

    integrity = payload.get("integrity", {}) or {}
    declared = str(integrity.get("predictions_summary_hash", ""))
    if not declared:
        console.print(
            f"[{theme.error}]Submission has no integrity.predictions_summary_hash.[/{theme.error}]"
        )
        raise typer.Exit(code=2)

    preds = _resolve_predictions_path(submission_path, predictions_path)
    if preds is None:
        console.print(
            f"[{theme.error}]Predictions JSONL not found.[/{theme.error}] Pass --predictions PATH "
            f"or place {submission_path.stem}.predictions.jsonl next to the submission."
        )
        raise typer.Exit(code=2)

    computed = hash_predictions_jsonl(preds)
    local_ok = computed == declared.lower()
    local_verdict = "verified" if local_ok else "mismatch"
    _render_local(declared, computed, local_verdict, theme)
    local_exit = 0 if local_ok else 1

    if not remote:
        raise typer.Exit(code=local_exit)

    # ── --remote (D23-aware) ──────────────────────────────────────────────
    raw_url = payload.get("raw_predictions_url")
    if not raw_url:
        err_console.print(
            "INFO: --remote needs the optional 'raw_predictions_url' field, which this "
            "submission does not set. raw_predictions_url IS part of schema v1.0.0 but is "
            "optional; without it there is no URL for the Verifier to fetch. This is tied to "
            "deuda técnica D23 (see docs/known_debt.md). Local verification is canonical."
        )
        raise typer.Exit(code=local_exit)

    token = os.environ.get("HF_TOKEN")
    if not token:
        err_console.print("ERROR: --remote requires the HF_TOKEN environment variable.")
        raise typer.Exit(code=3)

    try:
        remote_result = _call_verifier(url=str(raw_url), declared_hash=declared, token=token)
    except Exception as exc:
        err_console.print(
            f"WARNING: Verifier Space call failed ({type(exc).__name__}: {exc}). "
            "Falling back to the canonical local result."
        )
        raise typer.Exit(code=local_exit) from exc

    remote_status = str(remote_result.get("status", "error"))
    if not local_ok:
        console.print(
            f"[{theme.error}]verdict: mismatch (local hash does not match)[/{theme.error}]"
        )
        raise typer.Exit(code=1)

    if remote_status == "verified":
        console.print(
            f"[{theme.success}]verdict: verified (local + remote agree)[/{theme.success}]"
        )
        raise typer.Exit(code=0)

    # local verified but remote disagrees -> the expected D23 outcome.
    err_console.print(
        "WARNING: --remote returned "
        f"'{remote_status}' but the local hash matches. This is expected under deuda "
        "técnica D23 (the Verifier hashes a different input shape and prefixes 'sha256:'); "
        "see docs/known_debt.md. Local verification is canonical. Treating as VERIFIED."
    )
    console.print(f"[{theme.success}]verdict: verified-local-only (D23 warned)[/{theme.success}]")
    raise typer.Exit(code=0)


__all__ = ["hash_predictions_jsonl", "verify_hash"]
