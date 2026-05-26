"""PUMA unified CLI entrypoint."""

from __future__ import annotations

from typing import Any

import typer

from puma.community._community_app import community_app
from puma.community.auth_cli import auth_app
from puma.community.share_cli import share_results_app

app = typer.Typer(
    name="puma",
    help="PUMA — Local LLM benchmarking for project management tasks.",
)

# Resolved CLI state (theme + verbose) recorded by the root callback so the
# top-level main() wrapper can render errors with the same theme/verbosity.
_CLI_STATE: dict[str, Any] = {}


@app.callback(invoke_without_command=True)
def _main(
    ctx: typer.Context,
    no_banner: bool = typer.Option(False, "--no-banner", "-B", help="Suppress the startup banner."),
    theme: str | None = typer.Option(
        None,
        "--theme",
        help="Color theme: amber (default) or green. Overrides PUMA_THEME env var.",
    ),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress progress display."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show full traceback on errors."),
    no_summary: bool = typer.Option(
        False, "--no-summary", help="Suppress the post-run summary table."
    ),
) -> None:
    """PUMA — Local LLM benchmarking for project management tasks."""
    from rich.console import Console

    from puma.ui.banner import print_banner
    from puma.ui.errors import format_error_panel, install_themed_traceback
    from puma.ui.themes import THEMES, get_theme

    # Resolve the theme for every invocation (precedence: --theme > PUMA_THEME
    # > amber). On an unknown theme there is no valid theme to style with, so
    # the panel uses the default theme; exit 2 is unchanged.
    try:
        resolved_theme = get_theme(theme)
    except ValueError as exc:
        Console(stderr=True).print(format_error_panel(THEMES["amber"], "Unknown theme", str(exc)))
        raise typer.Exit(code=2) from exc

    # Install the themed Rich traceback handler for any uncaught path, and
    # record state for the top-level main() wrapper.
    install_themed_traceback(resolved_theme, show_locals=False)
    _CLI_STATE["theme"] = resolved_theme
    _CLI_STATE["verbose"] = verbose

    # Make the resolved theme + flags available to downstream subcommands.
    ctx.ensure_object(dict)
    ctx.obj["theme"] = resolved_theme
    ctx.obj["quiet"] = quiet
    ctx.obj["verbose"] = verbose
    ctx.obj["no_summary"] = no_summary

    # When invoked with no subcommand, show the help (with the banner above it
    # unless suppressed). Subcommands return from here and run as before.
    if ctx.invoked_subcommand is None:
        if not no_banner:
            print_banner(Console(), resolved_theme)
        typer.echo(ctx.get_help())
        raise typer.Exit()


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
    ctx: typer.Context,
    spec: str = typer.Argument(..., help="Path to run-spec YAML"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Build prompts without calling Ollama"),
    ollama_host: str = typer.Option(
        "http://localhost:11434", "--ollama-host", envvar="OLLAMA_HOST"
    ),
    db_path: str = typer.Option("data/puma.db", "--db"),
) -> None:
    """Execute a benchmark run-spec."""
    from rich.console import Console

    from puma.orchestrator.runner import Runner
    from puma.orchestrator.runspec import RunSpec
    from puma.ui.errors import print_error
    from puma.ui.themes import get_theme

    obj = ctx.obj or {}
    theme = obj.get("theme") or get_theme(None)
    verbose = bool(obj.get("verbose", False))
    err_console = Console(stderr=True)

    try:
        run_spec = RunSpec.from_yaml(spec)
    except Exception as exc:
        print_error(err_console, theme, exc, show_traceback=verbose)
        raise typer.Exit(1) from exc

    runner = Runner(
        run_spec,
        db_path=db_path,
        ollama_host=ollama_host,
        dry_run=dry_run,
        theme=obj.get("theme"),
        quiet=bool(obj.get("quiet", False)),
        summary=not bool(obj.get("no_summary", False)),
    )
    try:
        summary = runner.run()
        typer.echo(f"\nRun complete: {summary['run_id']}")
        typer.echo(f"Predictions: {summary['n_predictions']}")
        for k, v in summary.get("metrics", {}).items():
            if isinstance(v, int | float):
                typer.echo(f"  {k}: {v:.4f}")
    except Exception as exc:
        print_error(err_console, theme, exc, show_traceback=verbose)
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
    spec: str | None = typer.Option(
        None,
        "--spec",
        help=(
            "Path to the canonical baseline run-spec. Defaults to "
            "specs/runs/baseline_triage.yaml for the F1 path and "
            "specs/runs/baseline_estimation_canonical.yaml for the MAE path."
        ),
    ),
    expected_f1: float | None = typer.Option(
        None,
        "--expected-f1",
        help="Expected F1-macro value (mutually exclusive with --expected-mae)",
    ),
    expected_mae: float | None = typer.Option(
        None,
        "--expected-mae",
        help="Expected MAE in story points (mutually exclusive with --expected-f1)",
    ),
    tolerance: float = typer.Option(
        0.01, "--tolerance", help="Absolute tolerance window around the expected value"
    ),
    db_path: str = typer.Option("data/puma.db", "--db"),
    ollama_host: str = typer.Option(
        "http://localhost:11434", "--ollama-host", envvar="OLLAMA_HOST"
    ),
) -> None:
    """Validate a canonical baseline metric against its reference value.

    Runs the spec, reads the relevant metric from the resulting summary and
    exits 0 if ``|actual - expected| <= tolerance``, non-zero otherwise. Use
    as a CI reproducibility check or before tagging a release.

    Two scenarios are supported:

    * ``--expected-f1`` validates ``f1_macro`` from a ``triage_jira`` spec
      (default reference: ``0.5867`` on ``baseline_triage.yaml``, established
      in v2.0.0).
    * ``--expected-mae`` validates ``mae`` from an ``estimation_tawos`` spec
      (reference established in v2.5.0 on
      ``specs/runs/baseline_estimation_canonical.yaml``; see
      ``docs/baseline_references.md``).

    Calling with neither flag preserves the historical default (F1 against
    0.5867 on the triage baseline), so existing CI commands continue to
    work unchanged.
    """
    if expected_f1 is not None and expected_mae is not None:
        typer.secho(
            "[ERROR] --expected-f1 and --expected-mae are mutually exclusive.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(2)

    if expected_f1 is None and expected_mae is None:
        # Backward-compatible default: triage F1 against v2.0.0 reference.
        expected_f1 = 0.5867

    if expected_mae is not None:
        resolved_spec = spec or "specs/runs/baseline_estimation_canonical.yaml"
        metric_key = "mae"
        expected_value = expected_mae
    else:
        resolved_spec = spec or "specs/runs/baseline_triage.yaml"
        metric_key = "f1_macro"
        expected_value = expected_f1  # type: ignore[assignment]

    metrics = _run_baseline_for_validation(resolved_spec, db_path, ollama_host)
    actual = metrics.get(metric_key)
    if actual is None:
        typer.secho(
            f"[ERROR] Baseline run produced no {metric_key} metric.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(2)

    delta = actual - expected_value
    if abs(delta) <= tolerance:
        typer.echo(
            f"PASS: {metric_key}={actual:.4f} (delta={delta:+.4f}, tolerance=+/-{tolerance})"
        )
        raise typer.Exit(0)
    typer.echo(f"FAIL: {metric_key}={actual:.4f} (delta={delta:+.4f}, outside +/-{tolerance})")
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


# ── Sprint 7 — CLI completeness ───────────────────────────────


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
    """List runs registered in the database with their headline metrics."""
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
    params: list[Any] = []
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
                con.execute("SELECT run_id, MIN(model) FROM predictions GROUP BY run_id").fetchall()
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
    """List models effectively present in the Ollama volume."""
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

    records: list[dict[str, Any]] = []
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


@app.command(name="prepare-datasets")
def prepare_datasets(
    dataset: str | None = typer.Option(
        None, "--dataset", help="Prepare a single dataset by ID (default: all)"
    ),
    force_redownload: bool = typer.Option(
        False,
        "--force-redownload",
        help="Delete existing CSVs before invoking the prepare script so it re-generates",
    ),
    verify: bool = typer.Option(
        False, "--verify", help="Print SHA-256 of resulting CSVs for manual verification"
    ),
) -> None:
    """Prepare canonical datasets (jira_balanced_200, tawos, prioritization).

    Thin wrapper over ``scripts/prepare_datasets.py``. ``--force-redownload``
    removes the existing CSVs first so the script regenerates them.
    ``--verify`` emits SHA-256 hashes (full manifest comparison is documented
    but not implemented in v2.4.0).
    """
    import hashlib
    import subprocess
    import sys
    from pathlib import Path as _Path

    repo_root = _Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "prepare_datasets.py"
    data_dir = repo_root / "data"

    targets = {
        "jira_balanced_200": data_dir / "jira_balanced_200.csv",
        "tawos_estimation": data_dir / "tawos_clean.csv",
    }

    if force_redownload:
        for name, p in targets.items():
            if dataset and name != dataset:
                continue
            if p.exists():
                typer.echo(f"  removing {p.relative_to(repo_root)} (--force-redownload)")
                p.unlink()

    result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
    typer.echo(result.stdout)
    if result.returncode != 0:
        typer.secho(
            f"[ERROR] prepare_datasets.py exited {result.returncode}:\n{result.stderr}",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1)

    if verify:
        typer.echo("\nSHA-256 of generated CSVs:")
        any_mismatch = False
        for name, p in sorted(targets.items()):
            if dataset and name != dataset:
                continue
            if not p.exists():
                typer.secho(f"  {name}: MISSING ({p})", fg=typer.colors.YELLOW)
                any_mismatch = True
                continue
            h = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
            typer.echo(f"  {name}: {h}…  ({p.stat().st_size:,} bytes)")
        if any_mismatch:
            raise typer.Exit(2)


@app.command(name="wilcoxon")
def wilcoxon_cmd(
    run_id_a: str = typer.Argument(..., help="First run_id"),
    run_id_b: str = typer.Argument(..., help="Second run_id"),
    metric: str = typer.Option(
        "f1_macro", "--metric", help="Metric for headline accuracy: f1_macro|accuracy|ece"
    ),
    alpha: float = typer.Option(0.05, "--alpha", help="Significance threshold"),
    db_path: str = typer.Option("data/puma.db", "--db"),
    output: str | None = typer.Option(
        None, "--output", help="Write Markdown report to this path (default: stdout only)"
    ),
) -> None:
    """Wilcoxon signed-rank pairwise comparison of two runs."""
    import math
    import sqlite3
    from pathlib import Path as _Path

    import numpy as np

    db = _Path(db_path)
    if not db.exists():
        typer.secho(f"[ERROR] DB not found: {db}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    sql = """
        SELECT p.run_id, p.instance_id, p.parsed_label, i.gold_label
        FROM predictions p
        LEFT JOIN instances i ON p.instance_id = i.instance_id
        WHERE p.run_id IN (?, ?)
    """
    con = sqlite3.connect(str(db))
    try:
        rows = con.execute(sql, (run_id_a, run_id_b)).fetchall()
    finally:
        con.close()

    if not rows:
        typer.secho(
            f"[ERROR] No predictions found for runs {run_id_a!r}, {run_id_b!r}",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1)

    by_run: dict[str, dict[str, tuple[str, str]]] = {run_id_a: {}, run_id_b: {}}
    for run_id, inst, parsed, gold in rows:
        if run_id in by_run:
            by_run[run_id][inst] = (parsed, gold)

    if not by_run[run_id_a] or not by_run[run_id_b]:
        missing = [r for r in (run_id_a, run_id_b) if not by_run[r]]
        typer.secho(
            f"[ERROR] No predictions for run(s): {', '.join(missing)}",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1)

    shared = sorted(set(by_run[run_id_a]) & set(by_run[run_id_b]))
    if len(shared) < 10:
        typer.secho(
            f"[ERROR] Only {len(shared)} paired instances; need ≥ 10 for the test.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(2)

    preds_a = np.array([by_run[run_id_a][i][0] for i in shared])
    preds_b = np.array([by_run[run_id_b][i][0] for i in shared])
    gold = np.array([by_run[run_id_a][i][1] for i in shared])

    from puma.metrics.statistical_tests import wilcoxon_signed_rank_models

    result = wilcoxon_signed_rank_models(preds_a, preds_b, gold)
    p_value = float(result["p_value"])
    n_pairs = int(result["n_pairs"])
    mean_diff = float(result["mean_diff"])
    statistic = float(result["statistic"])

    if p_value < 0.001:
        marker = "***"
    elif p_value < 0.01:
        marker = "**"
    elif p_value < alpha:
        marker = "*"
    else:
        marker = "n.s."

    # Effect size r = |Z| / sqrt(N). Approximate Z from p_value (two-sided).
    try:
        from scipy.stats import norm

        z_abs = abs(norm.isf(p_value / 2)) if p_value > 0 else float("inf")
        r_effect = z_abs / math.sqrt(n_pairs) if n_pairs > 0 else float("nan")
    except ImportError:
        r_effect = float("nan")

    acc_a = float((preds_a == gold).mean())
    acc_b = float((preds_b == gold).mean())

    report = (
        f"# Wilcoxon signed-rank — {run_id_a} vs {run_id_b}\n\n"
        f"- Metric (headline): {metric}\n"
        f"- α: {alpha}\n"  # noqa: RUF001 -- intentional Greek alpha for statistical notation
        f"- Paired instances (non-tied): {n_pairs} / {len(shared)} total\n\n"
        "| Run | Accuracy |\n"
        "|---|---:|\n"
        f"| `{run_id_a}` | {acc_a:.4f} |\n"
        f"| `{run_id_b}` | {acc_b:.4f} |\n\n"
        "| Statistic | Value |\n"
        "|---|---:|\n"
        f"| W | {statistic:.4f} |\n"
        f"| p-value (two-sided) | {p_value:.4f} {marker} |\n"
        f"| mean Δ (a − b) | {mean_diff:+.4f} |\n"  # noqa: RUF001 -- intentional Unicode minus for math notation
        f"| effect size r | {r_effect:.4f} |\n\n"
        f"Significance: **{marker}** (α = {alpha}).\n"  # noqa: RUF001 -- intentional Greek alpha for statistical notation
    )
    typer.echo(report)
    if output:
        from pathlib import Path as _P

        _P(output).write_text(report, encoding="utf-8")
        typer.echo(f"\nReport written to {output}")


@app.command(name="bias-analysis")
def bias_analysis_cmd(
    db_path: str = typer.Option("data/puma.db", "--db"),
    models: str | None = typer.Option(
        None, "--models", help="Comma-separated subset of model tags to include"
    ),
    perturbations: str | None = typer.Option(
        None,
        "--perturbations",
        help="Comma-separated subset of perturbation names to analyse",
    ),
    output: str = typer.Option(
        "docs/results/bias_evaluation.md", "--output", help="Output Markdown path"
    ),
) -> None:
    """Bias analysis from perturbed runs already in DB."""
    from pathlib import Path as _Path

    from puma.dashboard.data import load_predictions_with_gold
    from puma.metrics.fairness import perturbation_disparity

    db = _Path(db_path)
    if not db.exists():
        typer.secho(f"[ERROR] DB not found: {db}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    preds = load_predictions_with_gold(db_path=db)
    pert_rows = preds[preds["perturbation"].notna()] if not preds.empty else preds
    if preds.empty or pert_rows.empty:
        typer.secho(
            "[ERROR] No perturbed predictions found in the database.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1)

    model_filter = {m.strip() for m in models.split(",")} if models else None
    pert_filter = {p.strip() for p in perturbations.split(",")} if perturbations else None

    if model_filter:
        preds = preds[preds["model"].isin(model_filter) | preds["model"].isna()]
        pert_rows = pert_rows[pert_rows["model"].isin(model_filter)]
    if pert_filter:
        kept = preds["perturbation"].isin(pert_filter) | preds["perturbation"].isna()
        preds = preds[kept]
        pert_rows = pert_rows[pert_rows["perturbation"].isin(pert_filter)]
        if pert_rows.empty:
            typer.secho(
                f"[ERROR] No predictions match the requested perturbations: {pert_filter}",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(2)

    disparity_rows: list[dict[str, Any]] = []
    directional_rows: list[dict[str, Any]] = []
    for model in sorted(preds["model"].dropna().unique()):
        base = preds[(preds["model"] == model) & preds["perturbation"].isna()]
        base_lookup = dict(zip(base["instance_id"], base["parsed_label"], strict=False))
        gold_lookup = dict(zip(base["instance_id"], base["gold_label"], strict=False))

        sub_by_pert: dict[str, dict[str, str]] = {}
        model_perts = sorted(pert_rows[pert_rows["model"] == model]["perturbation"].unique())
        for pert in model_perts:
            sub = pert_rows[(pert_rows["model"] == model) & (pert_rows["perturbation"] == pert)]
            sub_lookup = dict(zip(sub["instance_id"], sub["parsed_label"], strict=False))
            sub_by_pert[pert] = sub_lookup
            shared = sorted(set(sub_lookup) & set(base_lookup))
            if not shared:
                continue
            metrics = perturbation_disparity(
                [base_lookup[i] for i in shared],
                [sub_lookup[i] for i in shared],
                [gold_lookup[i] for i in shared],
            )
            disparity_rows.append(
                {"model": model, "perturbation": pert, "n": len(shared), **metrics}
            )

        male_lookup = sub_by_pert.get("gender_swap_prefix_male")
        female_lookup = sub_by_pert.get("gender_swap_prefix_female")
        if male_lookup and female_lookup:
            shared = sorted(set(male_lookup) & set(female_lookup) & set(gold_lookup))
            if shared:
                metrics = perturbation_disparity(
                    [male_lookup[i] for i in shared],
                    [female_lookup[i] for i in shared],
                    [gold_lookup[i] for i in shared],
                )
                directional_rows.append(
                    {
                        "model": model,
                        "comparison": "male vs female",
                        "n": len(shared),
                        **metrics,
                    }
                )

    if not disparity_rows:
        typer.secho(
            "[ERROR] No baseline/perturbation pairs to compare after filters.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1)

    def _fmt_table(rows: list[dict[str, Any]], headers: list[str]) -> str:
        out = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
        for r in rows:
            cells = [
                f"{r[h]:.4f}" if isinstance(r.get(h), float) else str(r.get(h, "")) for h in headers
            ]
            out.append("| " + " | ".join(cells) + " |")
        return "\n".join(out)

    parts = [
        "# Bias evaluation (CLI)",
        "",
        "## Disparity vs un-perturbed baseline",
        "",
        _fmt_table(
            disparity_rows,
            [
                "model",
                "perturbation",
                "n",
                "acc_baseline",
                "acc_perturbed",
                "disparity",
                "flip_rate",
                "flip_to_correct",
                "flip_to_incorrect",
            ],
        ),
        "",
    ]
    if directional_rows:
        parts += [
            "## Directional (male vs female)",
            "",
            _fmt_table(
                directional_rows,
                [
                    "model",
                    "comparison",
                    "n",
                    "acc_baseline",
                    "acc_perturbed",
                    "disparity",
                    "flip_rate",
                    "flip_to_correct",
                    "flip_to_incorrect",
                ],
            ),
            "",
        ]

    out_path = _Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(parts), encoding="utf-8")
    typer.echo(f"Wrote {out_path}")


@app.command(name="generate-plots")
def generate_plots_cmd(
    source: str = typer.Option(
        "phase_b",
        "--source",
        help="Data source: phase_b | bias_eval | multi_seed",
    ),
    output_dir: str = typer.Option(
        "docs/results/figures/", "--output", help="Output directory for figures"
    ),
    fmt: str = typer.Option("png", "--format", help="Output format: png | pdf | svg | all"),
) -> None:
    """Generate consolidated plots from runs in the DB."""
    import subprocess
    import sys
    from pathlib import Path as _Path

    if source not in {"phase_b", "bias_eval", "multi_seed"}:
        typer.secho(
            f"[ERROR] Unknown source {source!r}. Valid: phase_b, bias_eval, multi_seed",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(2)

    if source != "phase_b":
        typer.secho(
            f"Source {source!r} is documented but not yet implemented in v2.4.0. "
            "Only phase_b plotting is available.",
            fg=typer.colors.YELLOW,
        )
        raise typer.Exit(2)

    repo_root = _Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "generate_phase_b_plots.py"

    typer.echo(
        f"Generating phase_b plots into {output_dir} (format={fmt}, "
        "additional formats may require post-processing)…"
    )
    result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
    typer.echo(result.stdout)
    if result.returncode != 0:
        typer.secho(
            f"[ERROR] generate_phase_b_plots.py exited {result.returncode}:\n{result.stderr}",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1)


@app.command("doctor")
def doctor(ctx: typer.Context) -> None:
    """Run read-only environment health checks (OK/WARN/FAIL); exit 1 on any failure."""
    import os
    from pathlib import Path

    from rich.console import Console

    from puma.diagnostics.checks import run_all_checks
    from puma.ui.diagnostics_view import render_doctor_table
    from puma.ui.themes import get_theme

    obj = ctx.obj or {}
    theme = obj.get("theme") or get_theme(None)
    endpoint = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    results = run_all_checks(ollama_endpoint=endpoint, db_path=Path("data/puma.db"))
    Console().print(render_doctor_table(theme, results))
    if any(r.status == "fail" for r in results):
        raise typer.Exit(code=1)


@app.command("env")
def env_command(ctx: typer.Context) -> None:
    """Print the resolved PUMA environment (version, platform, theme, profile, paths)."""
    import os
    from pathlib import Path

    from rich.console import Console

    from puma.diagnostics.env import collect_environment
    from puma.ui.diagnostics_view import render_env_table
    from puma.ui.themes import get_theme

    obj = ctx.obj or {}
    theme = obj.get("theme") or get_theme(None)
    endpoint = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    env_info = collect_environment(theme, endpoint, Path("data/puma.db"))
    Console().print(render_env_table(theme, env_info))


app.add_typer(auth_app, name="auth")
app.add_typer(share_results_app, name="share-results")
# The four community verbs self-register on community_app via decorators when
# their modules are imported (puma.community.__init__ imports all four).
app.add_typer(community_app, name="community")


def main() -> None:
    """Console-script entry point with themed, exit-code-preserving errors.

    Runs the Typer app with Click's ``standalone_mode=False`` so this wrapper
    controls rendering and exit codes (all preserved from prior behavior):
      - ``typer.Exit(code)`` / ``--help`` -> app returns the code; we exit it.
      - usage errors (``ClickException``) -> Click's own message, exit 2.
      - ``KeyboardInterrupt`` (Click delivers it as ``Abort``) -> themed
        "Interrupted." panel, exit 130.
      - expected / unexpected errors -> themed panel (+ traceback if --verbose),
        exit 1.
    Theme/verbosity come from the state the root callback recorded.
    """
    import click
    from rich.console import Console

    from puma.ui.errors import format_error_panel, print_error
    from puma.ui.themes import get_theme

    console = Console(stderr=True)
    try:
        exit_code = app(standalone_mode=False)
    except click.exceptions.Exit as exc:  # defensive; Click usually returns the code
        raise SystemExit(exc.exit_code) from None
    except (click.exceptions.Abort, KeyboardInterrupt):
        theme = _CLI_STATE.get("theme") or get_theme(None)
        console.print(format_error_panel(theme, "Interrupted.", "Operation cancelled by user."))
        raise SystemExit(130) from None
    except click.ClickException as exc:  # usage errors, bad parameters, etc.
        exc.show()
        raise SystemExit(exc.exit_code) from None
    except SystemExit:
        raise
    except BaseException as exc:
        theme = _CLI_STATE.get("theme") or get_theme(None)
        verbose = bool(_CLI_STATE.get("verbose", False))
        print_error(console, theme, exc, show_traceback=verbose)
        raise SystemExit(1) from None
    if exit_code:
        raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
