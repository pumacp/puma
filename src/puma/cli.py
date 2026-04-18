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
def run(
    spec: str = typer.Argument(..., help="Path to run-spec YAML"),
) -> None:
    """Execute a benchmark run-spec. (Phase 5)"""
    typer.echo(f"[stub] puma run {spec} — not yet implemented (Phase 5)")


@app.command()
def dashboard() -> None:
    """Launch the Streamlit dashboard. (Phase 6)"""
    typer.echo("[stub] puma dashboard — not yet implemented (Phase 6)")


@app.command()
def report(
    run_id: str = typer.Argument(..., help="Run ID to generate report for"),
    fmt: str = typer.Option("md", "--format", help="Output format: md|pdf"),
) -> None:
    """Generate a run report. (Phase 7)"""
    typer.echo(f"[stub] puma report {run_id} --format {fmt} — not yet implemented (Phase 7)")


if __name__ == "__main__":
    app()
