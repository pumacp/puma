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
        typer.echo(f"Inference cache: {stats['total_entries']} entries, "
                   f"{stats['db_size_bytes'] / 1024:.1f} KB")
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
    ollama_host: str = typer.Option("http://localhost:11434", "--ollama-host", envvar="OLLAMA_HOST"),
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
            if isinstance(v, (int, float)):
                typer.echo(f"  {k}: {v:.4f}")
    except Exception as exc:
        typer.secho(f"[ERROR] Run failed: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc


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


@app.command()
def db(
    action: str = typer.Argument("migrate", help="Action: migrate | status"),
    db_path: str = typer.Option("data/puma.db", "--db"),
) -> None:
    """Manage the PUMA database schema."""
    from puma.storage.db import init_db
    from puma.storage.models import Base

    if action == "migrate":
        init_db(db_path)
        typer.echo(f"Schema applied to {db_path}")
        tables = Base.metadata.tables.keys()
        for t in sorted(tables):
            typer.echo(f"  table: {t}")
    elif action == "status":
        from pathlib import Path
        p = Path(db_path)
        if p.exists():
            typer.echo(f"{db_path}: {p.stat().st_size / 1024:.1f} KB")
        else:
            typer.echo(f"{db_path}: not found (run 'puma db migrate' to create)")
    else:
        typer.echo(f"Unknown action: {action!r}")
        raise typer.Exit(1)


@app.command()
def dashboard(
    port: int = typer.Option(8501, "--port", help="Port to listen on"),
    host: str = typer.Option("0.0.0.0", "--host", help="Host address"),
) -> None:
    """Launch the Streamlit dashboard."""
    import subprocess
    from pathlib import Path

    app_path = Path(__file__).parent / "dashboard" / "app.py"
    result = subprocess.run([
        "streamlit", "run", str(app_path),
        "--server.port", str(port),
        "--server.address", host,
        "--server.headless", "true",
    ])
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


if __name__ == "__main__":
    app()
