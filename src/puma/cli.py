"""PUMA unified CLI entrypoint."""

from __future__ import annotations

import typer

app = typer.Typer(
    name="puma",
    help="PUMA — Local LLM benchmarking for project management tasks.",
    no_args_is_help=True,
)


@app.command()
def preflight(
    profile: str | None = typer.Option(
        None,
        "--profile",
        help="Override auto-detected profile (cpu-lite|cpu-standard|gpu-entry|gpu-mid|gpu-high|auto)",
    ),
    write_config: bool = typer.Option(
        True,
        "--write-config/--no-write-config",
        help="Write config/runtime_profile.yaml",
    ),
) -> None:
    """Detect hardware, select execution profile, and report readiness."""
    from puma.preflight.detect import detect_capabilities
    from puma.preflight.profile import InsufficientHardwareError, select_profile
    from puma.preflight.provisioning import IssueSeverity, check_provisioning
    from puma.preflight.report import print_report, write_runtime_profile

    override = None if (profile is None or profile == "auto") else profile

    caps = detect_capabilities()

    try:
        selected = select_profile(caps, override=override)
    except InsufficientHardwareError as exc:
        typer.secho(f"[ERROR] {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    except ValueError as exc:
        typer.secho(f"[ERROR] {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    issues = check_provisioning(caps, selected)
    print_report(caps, selected, issues)

    if write_config:
        path = write_runtime_profile(caps, selected)
        typer.echo(f"\nProfile written to {path}")

    has_errors = any(i.severity == IssueSeverity.ERROR for i in issues)
    if has_errors:
        raise typer.Exit(code=1)


@app.command(name="models")
def models_cmd(
    action: str = typer.Argument("list", help="Action: list | pull"),
    model: str | None = typer.Argument(None, help="Model tag (for pull)"),
) -> None:
    """List available models for the current profile, or pull a specific model."""
    if action == "list":
        from pathlib import Path

        import yaml

        catalog_path = Path("config/models_catalog.yaml")
        if not catalog_path.exists():
            typer.echo("models_catalog.yaml not found in config/")
            raise typer.Exit(1)
        with open(catalog_path) as fh:
            data = yaml.safe_load(fh)
        typer.echo(f"{'Model':<30} {'Params':>8}  {'Size':>8}  {'Profiles'}")
        typer.echo("-" * 75)
        for m in data["models"]:
            profiles = ", ".join(m.get("profiles_compatible", []))
            typer.echo(
                f"{m['ollama_tag']:<30} {m['params_b']:>6}B  "
                f"{m['gguf_size_gb']:>5.1f} GB  {profiles}"
            )
    elif action == "pull":
        if not model:
            typer.echo("Specify a model tag to pull, e.g.: puma models pull qwen2.5:3b")
            raise typer.Exit(1)
        import subprocess

        typer.echo(f"Pulling {model}...")
        result = subprocess.run(["ollama", "pull", model])
        raise typer.Exit(result.returncode)
    else:
        typer.echo(f"Unknown action: {action!r}. Use 'list' or 'pull'.")
        raise typer.Exit(1)


@app.command()
def datasets(
    action: str = typer.Argument("verify", help="Action: verify"),
) -> None:
    """Verify dataset integrity and show statistics."""
    if action == "verify":
        from puma.datasets.verify import print_verify_report, verify_jira, verify_tawos

        typer.echo("=" * 60)
        typer.echo("PUMA Dataset Verification")
        typer.echo("=" * 60)
        reports = [verify_jira(), verify_tawos()]
        all_ok = print_verify_report(reports)
        typer.echo("=" * 60)
        if not all_ok:
            raise typer.Exit(code=1)
    else:
        typer.echo(f"Unknown action: {action!r}. Use 'verify'.")
        raise typer.Exit(1)


@app.command()
def cache(
    action: str = typer.Argument("stats", help="Action: stats | clear"),
) -> None:
    """Manage the inference cache."""
    from puma.runtime.cache import InferenceCache

    c = InferenceCache()
    if action == "stats":
        stats = c.stats()
        typer.echo(
            f"Inference cache: {stats['total_entries']} entries, "
            f"{stats['db_size_bytes'] / 1024:.1f} KB"
        )
    elif action == "clear":
        c.clear()
        typer.echo("Inference cache cleared")
    else:
        typer.echo(f"Unknown action: {action!r}")
        raise typer.Exit(1)


@app.command()
def run(
    spec: str = typer.Argument(..., help="Path to run-spec YAML"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Build prompts without calling Ollama"),
    ollama_host: str = typer.Option(
        "http://localhost:11434", "--ollama-host", envvar="OLLAMA_HOST"
    ),
    db_path: str = typer.Option("data/puma.db", "--db"),
) -> None:
    """Execute a benchmark run-spec."""
    from puma.orchestrator.runner import Runner
    from puma.orchestrator.runspec import RunSpec

    try:
        run_spec = RunSpec.from_yaml(spec)
    except Exception as exc:
        typer.secho(f"[ERROR] Invalid run-spec: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc

    runner = Runner(run_spec, db_path=db_path, ollama_host=ollama_host, dry_run=dry_run)
    try:
        summary = runner.run()
        typer.echo(f"\nRun complete: {summary['run_id']}")
        typer.echo(f"Predictions: {summary['n_predictions']}")
        for k, v in summary.get("metrics", {}).items():
            if isinstance(v, int | float):
                typer.echo(f"  {k}: {v:.4f}")
    except Exception as exc:
        typer.secho(f"[ERROR] Run failed: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc


def _run_baseline_for_validation(spec: str, db_path: str, ollama_host: str) -> dict[str, float]:
    """Execute a baseline spec and return its scalar metrics.

    Extracted as a module-level helper so unit tests can monkeypatch it
    without spinning up Ollama or the dataset pipeline.
    """
    from puma.orchestrator.runner import Runner
    from puma.orchestrator.runspec import RunSpec

    run_spec = RunSpec.from_yaml(spec)
    summary = Runner(run_spec, db_path=db_path, ollama_host=ollama_host, dry_run=False).run()
    return {k: v for k, v in summary.get("metrics", {}).items() if isinstance(v, int | float)}


@app.command(name="validate-baseline")
def validate_baseline(
    spec: str = typer.Option(
        "specs/runs/baseline_triage.yaml",
        "--spec",
        help="Path to the canonical baseline run-spec",
    ),
    expected_f1: float = typer.Option(0.5867, "--expected-f1", help="Expected F1-macro value"),
    tolerance: float = typer.Option(
        0.01, "--tolerance", help="Absolute tolerance window around expected_f1"
    ),
    db_path: str = typer.Option("data/puma.db", "--db"),
    ollama_host: str = typer.Option(
        "http://localhost:11434", "--ollama-host", envvar="OLLAMA_HOST"
    ),
) -> None:
    """Validate the canonical baseline F1-macro against its reference value.

    Runs the spec, reads ``f1_macro`` from the resulting metrics and exits 0
    if ``|f1 - expected_f1| <= tolerance``, non-zero otherwise. Use as a CI
    reproducibility check or before tagging a release.
    """
    metrics = _run_baseline_for_validation(spec, db_path, ollama_host)
    f1 = metrics.get("f1_macro")
    if f1 is None:
        typer.secho(
            "[ERROR] Baseline run produced no f1_macro metric.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(2)

    delta = f1 - expected_f1
    if abs(delta) <= tolerance:
        typer.echo(f"PASS: f1_macro={f1:.4f} (delta={delta:+.4f}, tolerance=+/-{tolerance})")
        raise typer.Exit(0)
    typer.echo(f"FAIL: f1_macro={f1:.4f} (delta={delta:+.4f}, outside +/-{tolerance})")
    raise typer.Exit(1)


@app.command()
def compare(
    run_ids: list[str] = typer.Argument(..., help="Two or more run IDs to compare"),  # noqa: B008
    db_path: str = typer.Option("data/puma.db", "--db"),
    output: str | None = typer.Option(None, "--output", help="Save comparison JSON to file"),
) -> None:
    """Compare metrics across two or more runs."""
    from puma.orchestrator.compare import compare_runs

    if len(run_ids) < 2:
        typer.secho("[ERROR] Provide at least two run IDs.", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    result = compare_runs(run_ids, db_path=db_path)
    typer.echo(result["markdown_table"])
    if result.get("diffs"):
        typer.echo("\nDifferences (run2 - run1):")
        for k, v in result["diffs"].items():
            sign = "+" if v >= 0 else ""
            typer.echo(f"  {k}: {sign}{v:.4f}")
    if output:
        import json
        from pathlib import Path

        Path(output).write_text(json.dumps(result, indent=2, default=str))
        typer.echo(f"\nSaved to {output}")


db_app = typer.Typer(
    name="db",
    help="Manage the PUMA database schema (Alembic-driven).",
    no_args_is_help=True,
)
app.add_typer(db_app, name="db")


@db_app.command("migrate")
def db_migrate(
    revision: str = typer.Argument("head", help="Target revision (default: head)"),
    db_path: str = typer.Option("data/puma.db", "--db"),
) -> None:
    """Apply Alembic migrations up to the target revision."""
    from alembic import command

    from puma.storage.db import _alembic_config_for

    cfg = _alembic_config_for(f"sqlite:///{db_path}")
    command.upgrade(cfg, revision)
    typer.echo(f"Database migrated to revision: {revision}")


@db_app.command("downgrade")
def db_downgrade(
    revision: str = typer.Argument("-1", help="Target revision (default: -1)"),
    db_path: str = typer.Option("data/puma.db", "--db"),
) -> None:
    """Reverse Alembic migrations down to the target revision."""
    from alembic import command

    from puma.storage.db import _alembic_config_for

    cfg = _alembic_config_for(f"sqlite:///{db_path}")
    command.downgrade(cfg, revision)
    typer.echo(f"Database downgraded to revision: {revision}")


@db_app.command("history")
def db_history(
    db_path: str = typer.Option("data/puma.db", "--db"),
) -> None:
    """Show the Alembic revision chain for the database."""
    from alembic import command

    from puma.storage.db import _alembic_config_for

    cfg = _alembic_config_for(f"sqlite:///{db_path}")
    command.history(cfg)


@db_app.command("status")
def db_status(
    db_path: str = typer.Option("data/puma.db", "--db"),
) -> None:
    """Show the database file status: path and size, or not-found guidance."""
    from pathlib import Path

    p = Path(db_path)
    if p.exists():
        typer.echo(f"{db_path}: {p.stat().st_size / 1024:.1f} KB")
    else:
        typer.echo(f"{db_path}: not found (run 'puma db migrate' to create)")


@app.command()
def dashboard(
    port: int = typer.Option(8501, "--port", help="Port to listen on"),
    host: str = typer.Option("0.0.0.0", "--host", help="Host address"),
) -> None:
    """Launch the Streamlit dashboard."""
    import subprocess
    from pathlib import Path

    app_path = Path(__file__).parent / "dashboard" / "app.py"
    result = subprocess.run(
        [
            "streamlit",
            "run",
            str(app_path),
            "--server.port",
            str(port),
            "--server.address",
            host,
            "--server.headless",
            "true",
        ]
    )
    raise typer.Exit(result.returncode)


@app.command()
def report(
    run_id: str = typer.Argument(..., help="Run ID to generate report for"),
    fmt: str = typer.Option("md", "--format", help="Output format: md|pdf"),
    db_path: str = typer.Option("data/puma.db", "--db"),
) -> None:
    """Generate a Markdown (or PDF) run report."""
    from puma.reporting.report import generate_report

    try:
        path = generate_report(run_id, db_path=db_path, to_pdf=(fmt == "pdf"))
        typer.echo(f"Report written to {path}")
    except ValueError as exc:
        typer.secho(f"[ERROR] {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc


# ── Sprint 7 — CLI completeness (Anexo F § A.2) ───────────────────────────────


@app.command(name="list-runs")
def list_runs(
    db_path: str = typer.Option("data/puma.db", "--db", help="Path to puma.db"),
    scenario: str | None = typer.Option(None, "--scenario", help="Filter by scenario"),
    model: str | None = typer.Option(None, "--model", help="Filter by model tag"),
    last_n: int | None = typer.Option(None, "--last-n", help="Show only the last N runs"),
    since: str | None = typer.Option(
        None,
        "--since",
        help="ISO date or relative offset (e.g. '24h', '7d')",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON instead of a table"),
) -> None:
    """List runs registered in the database with their headline metrics (Anexo F § A.2.5)."""
    import json as _json
    import re
    import sqlite3
    from datetime import datetime, timedelta
    from pathlib import Path as _Path

    from rich.console import Console
    from rich.table import Table

    db = _Path(db_path)
    if not db.exists():
        typer.secho(f"[ERROR] DB not found: {db}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    since_iso: str | None = None
    if since:
        m = re.fullmatch(r"(\d+)([hd])", since.strip())
        if m:
            n, unit = int(m.group(1)), m.group(2)
            delta = timedelta(hours=n) if unit == "h" else timedelta(days=n)
            since_iso = (datetime.utcnow() - delta).isoformat()
        else:
            since_iso = since  # assume ISO

    sql = (
        "SELECT r.run_id, r.profile, r.started_at, r.finished_at, r.status, "
        "MAX(CASE WHEN m.metric_name='f1_macro' THEN m.value END) AS f1_macro, "
        "MAX(CASE WHEN m.metric_name='mae_sp' THEN m.value END) AS mae_sp, "
        "MAX(CASE WHEN m.metric_name='parse_failure_rate' THEN m.value END) AS pfr "
        "FROM runs r LEFT JOIN metrics m ON r.run_id = m.run_id WHERE 1=1"
    )
    params: list = []
    if scenario:
        sql += " AND r.run_id LIKE ?"
        params.append(f"%{scenario}%")
    if since_iso:
        sql += " AND r.started_at >= ?"
        params.append(since_iso)
    sql += " GROUP BY r.run_id ORDER BY r.started_at DESC"
    if last_n is not None:
        sql += " LIMIT ?"
        params.append(last_n)

    con = sqlite3.connect(str(db))
    try:
        rows = con.execute(sql, params).fetchall()
    finally:
        con.close()

    if model:
        # Filter by model after the fact via predictions table
        con = sqlite3.connect(str(db))
        try:
            models_by_run = dict(
                con.execute(
                    "SELECT run_id, MIN(model) FROM predictions GROUP BY run_id"
                ).fetchall()
            )
        finally:
            con.close()
        rows = [r for r in rows if models_by_run.get(r[0]) == model]

    if not rows:
        typer.secho("No runs match the current filters.", fg=typer.colors.YELLOW)
        raise typer.Exit(2)

    records = [
        {
            "run_id": r[0],
            "profile": r[1],
            "started_at": r[2],
            "finished_at": r[3],
            "status": r[4],
            "f1_macro": r[5],
            "mae_sp": r[6],
            "parse_failure_rate": r[7],
        }
        for r in rows
    ]

    if json_output:
        typer.echo(_json.dumps(records, indent=2, default=str))
        return

    table = Table(title=f"PUMA runs ({len(records)})")
    table.add_column("run_id", overflow="fold")
    table.add_column("profile")
    table.add_column("status")
    table.add_column("F1 macro", justify="right")
    table.add_column("MAE SP", justify="right")
    table.add_column("Parse fail", justify="right")
    table.add_column("started_at")
    for rec in records:
        def _fmt(v: object) -> str:
            return f"{v:.4f}" if isinstance(v, float) else ("—" if v is None else str(v))

        table.add_row(
            rec["run_id"],
            rec["profile"] or "—",
            rec["status"] or "—",
            _fmt(rec["f1_macro"]),
            _fmt(rec["mae_sp"]),
            _fmt(rec["parse_failure_rate"]),
            str(rec["started_at"])[:19] if rec["started_at"] else "—",
        )
    Console().print(table)


@app.command(name="list-ollama-models")
def list_ollama_models(
    json_output: bool = typer.Option(False, "--json", help="Emit JSON instead of a table"),
) -> None:
    """List models effectively present in the Ollama volume (Anexo F § A.2.6)."""
    import json as _json
    import re
    import subprocess

    from rich.console import Console
    from rich.table import Table

    result = subprocess.run(
        ["docker", "exec", "puma_ollama", "ollama", "list"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        typer.secho(
            f"[ERROR] Ollama did not respond (exit {result.returncode}): "
            f"{result.stderr.strip() or 'no stderr'}",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1)

    lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
    if not lines or not lines[0].lower().startswith("name"):
        typer.secho(
            "[ERROR] Unexpected `ollama list` output (no header found)",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1)

    records: list[dict] = []
    for ln in lines[1:]:
        # Ollama list uses variable whitespace; collapse to single splits
        parts = re.split(r"\s{2,}", ln.strip())
        if len(parts) < 4:
            continue
        records.append(
            {
                "model_tag": parts[0],
                "id": parts[1],
                "size": parts[2],
                "modified": parts[3],
            }
        )

    if json_output:
        typer.echo(_json.dumps(records, indent=2))
        return

    table = Table(title=f"Ollama models present in volume ({len(records)})")
    table.add_column("model_tag")
    table.add_column("ID")
    table.add_column("size", justify="right")
    table.add_column("modified")
    for r in records:
        table.add_row(r["model_tag"], r["id"], r["size"], r["modified"])
    Console().print(table)


if __name__ == "__main__":
    app()
