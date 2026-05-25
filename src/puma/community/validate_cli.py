"""``puma community validate`` — validate submission JSON files (Anexo F.16.7).

By default each file is validated with the canonical Pydantic validator
(:func:`puma.community.validator.validate_submission_dict`). ``--schema PATH``
switches to JSON-Schema validation against an explicit schema file. ``--strict``
adds filename↔submission_id and n_instances↔predictions-count cross-checks.

When no ``--schema`` is given, the command also performs a best-effort online
drift check: it compares the SHA-256 of the bundled schema against the copy in
``pumacp/puma-community``; a mismatch prints a non-fatal warning, and any
network failure is silent.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

import httpx
import typer
from pydantic import ValidationError
from rich.console import Console

from puma.community._community_app import community_app
from puma.community.validator import validate_submission_dict

log = logging.getLogger("puma.community.validate_cli")
console = Console()
err_console = Console(stderr=True)

BUNDLED_SCHEMA = Path(__file__).parent / "schema_data" / "submission.v1.json"
_REMOTE_SCHEMA_URL = (
    "https://api.github.com/repos/pumacp/puma-community/contents/schema/submission.v1.json"
)
_HTTP_TIMEOUT_S = 15.0

# typer defaults as module-level singletons (ruff B008 for Path-typed params).
_PATHS_ARG = typer.Argument(..., exists=True, help="Submission JSON file(s).")
_SCHEMA_OPT = typer.Option(None, "--schema", help="Explicit JSON Schema file.")


def _pydantic_violations(payload: dict[str, Any]) -> list[str]:
    try:
        validate_submission_dict(payload)
    except ValidationError as exc:
        out: list[str] = []
        for err in exc.errors():
            loc = ".".join(str(p) for p in err.get("loc", ()))
            out.append(f"{loc or '<root>'}: {err.get('msg', 'invalid')}")
        return out
    return []


def _jsonschema_violations(payload: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    import jsonschema

    validator = jsonschema.Draft202012Validator(schema)
    out: list[str] = []
    for err in sorted(validator.iter_errors(payload), key=lambda e: list(e.absolute_path)):
        path = ".".join(str(p) for p in err.absolute_path)
        out.append(f"{path or '<root>'}: {err.message}")
    return out


def _strict_violations(path: Path, payload: dict[str, Any]) -> list[str]:
    out: list[str] = []
    submission_id = str(payload.get("submission_id", ""))
    if submission_id:
        expected = f"{submission_id}.json"
        if path.name.lower() != expected.lower():
            out.append(
                f"filename {path.name!r} does not match submission_id (expected {expected!r})"
            )
    preds = path.parent / f"{path.stem}.predictions.jsonl"
    if preds.is_file():
        declared_n = (payload.get("run_metadata", {}) or {}).get("n_instances")
        if declared_n is not None:
            actual_n = sum(
                1 for line in preds.read_text(encoding="utf-8").splitlines() if line.strip()
            )
            if int(declared_n) != actual_n:
                out.append(
                    f"run_metadata.n_instances={declared_n} but predictions file has {actual_n} rows"
                )
    return out


def _check_schema_drift() -> None:
    """Best-effort: warn if the bundled schema differs from the community copy."""
    try:
        local_sha = hashlib.sha256(BUNDLED_SCHEMA.read_bytes()).hexdigest()
        with httpx.Client(timeout=_HTTP_TIMEOUT_S) as http:
            meta = http.get(
                _REMOTE_SCHEMA_URL,
                headers={"Accept": "application/vnd.github+json"},
            )
            if meta.status_code != 200:
                return
            download_url = meta.json().get("download_url")
            if not download_url:
                return
            remote = http.get(download_url)
            if remote.status_code != 200:
                return
            remote_sha = hashlib.sha256(remote.content).hexdigest()
    except (httpx.HTTPError, OSError, json.JSONDecodeError):
        return  # network/IO failures are silent per spec
    if local_sha != remote_sha:
        err_console.print(
            "WARNING: schema drift — bundled submission.v1.json "
            f"(sha256 {local_sha[:12]}…) differs from the pumacp/puma-community copy "
            f"(sha256 {remote_sha[:12]}…)."
        )


@community_app.command(name="validate")
def validate(
    paths: list[Path] = _PATHS_ARG,
    schema_path: Path | None = _SCHEMA_OPT,
    strict: bool = typer.Option(False, "--strict", help="Also check filename/n_instances."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON results."),
) -> None:
    """Validate one or more submission JSON files against the schema."""
    schema: dict[str, Any] | None = None
    if schema_path is not None:
        if not schema_path.is_file():
            console.print(f"[red]Schema not found: {schema_path}[/red]")
            raise typer.Exit(code=2)
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    else:
        _check_schema_drift()

    results: list[dict[str, Any]] = []
    for path in paths:
        violations: list[str] = []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            results.append(
                {"file": str(path), "valid": False, "violations": [f"unreadable: {exc}"]}
            )
            continue
        if schema is not None:
            violations.extend(_jsonschema_violations(payload, schema))
        else:
            violations.extend(_pydantic_violations(payload))
        if strict:
            violations.extend(_strict_violations(path, payload))
        results.append({"file": str(path), "valid": not violations, "violations": violations})

    valid_count = sum(1 for r in results if r["valid"])
    invalid_count = len(results) - valid_count

    if json_output:
        typer.echo(json.dumps(results, indent=2, sort_keys=True))
    else:
        for r in results:
            if r["valid"]:
                console.print(f"[green]OK[/green]    {r['file']}")
            else:
                console.print(f"[red]INVALID[/red] {r['file']}")
                for v in r["violations"]:
                    console.print(f"    • {v}")
        console.print(f"\n{len(results)} validated, {valid_count} valid, {invalid_count} invalid")

    raise typer.Exit(code=0 if invalid_count == 0 else 1)


__all__ = ["BUNDLED_SCHEMA", "validate"]
