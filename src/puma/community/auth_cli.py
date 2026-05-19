"""``puma auth`` subcommand — manage PUMA Community credentials.

Three operations: ``login``, ``status``, ``logout``. Tokens flow through this
module via :class:`puma.community.credentials.CredentialStore`; raw token values
are never echoed back to the terminal — only the masked form is surfaced.
"""

from __future__ import annotations

import logging

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from puma.community.credentials import (
    SUPPORTED_SERVICES,
    CredentialError,
    CredentialStore,
    InvalidTokenFormatError,
    mask_token,
)

log = logging.getLogger("puma.community.auth_cli")

console = Console()

auth_app = typer.Typer(
    name="auth",
    help="Manage PUMA Community credentials (GitHub, Hugging Face, Zenodo, etc.).",
    no_args_is_help=True,
)


def _store() -> CredentialStore:
    """Return a fresh CredentialStore each call so test env overrides apply."""
    return CredentialStore()


@auth_app.command("login")
def auth_login(
    service: str = typer.Argument(..., help=f"One of: {', '.join(SUPPORTED_SERVICES)}"),
) -> None:
    """Prompt for a token and store it (mode 0600 on POSIX)."""
    if service not in SUPPORTED_SERVICES:
        console.print(
            f"[red]Unknown service[/red] {service!r}. "
            f"Known services: {', '.join(SUPPORTED_SERVICES)}"
        )
        raise typer.Exit(code=2)

    token = typer.prompt(f"Paste your {service} token", hide_input=True)
    try:
        _store().set(service, token)
    except InvalidTokenFormatError as exc:
        console.print(f"[red]Invalid format:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    except CredentialError as exc:
        console.print(f"[red]Credential error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(
        Panel.fit(
            f"Saved {service} token: [bold]{mask_token(token)}[/bold]",
            title="[green]auth login[/green]",
            border_style="green",
        )
    )


@auth_app.command("status")
def auth_status() -> None:
    """Show which services have a credential configured (values are masked)."""
    store = _store()
    table = Table(title="PUMA Community credentials", show_lines=False)
    table.add_column("Service", style="cyan", no_wrap=True)
    table.add_column("Configured", justify="center")
    table.add_column("Token preview (masked)", style="dim")

    try:
        existing_services = set(store.list_services())
    except CredentialError as exc:
        console.print(f"[red]Cannot read credential store:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    for service in SUPPORTED_SERVICES:
        if service in existing_services:
            try:
                value = store.get(service)
            except CredentialError as exc:
                console.print(f"[red]Cannot read credential store:[/red] {exc}")
                raise typer.Exit(code=1) from exc
            preview = mask_token(value) if value else ""
            table.add_row(service, "[green]✓ configured[/green]", preview)
        else:
            table.add_row(service, "[red]✗ not configured[/red]", "")

    console.print(table)

    ok = store.verify_permissions()
    icon = "[green]✓[/green]" if ok else "[red]✗[/red]"
    console.print(f"\n{icon} Credentials file: {store.path}")
    if not ok:
        console.print(f"[yellow]File mode is not 0600. Run: chmod 600 {store.path}[/yellow]")


@auth_app.command("logout")
def auth_logout(
    service: str = typer.Argument(..., help=f"One of: {', '.join(SUPPORTED_SERVICES)}"),
) -> None:
    """Remove the stored token for ``service`` (with confirmation)."""
    if service not in SUPPORTED_SERVICES:
        console.print(
            f"[red]Unknown service[/red] {service!r}. "
            f"Known services: {', '.join(SUPPORTED_SERVICES)}"
        )
        raise typer.Exit(code=2)

    confirmed = typer.confirm(
        f"Are you sure you want to remove the {service} token?", default=False
    )
    if not confirmed:
        console.print("Aborted, no change made.")
        return

    try:
        removed = _store().delete(service)
    except CredentialError as exc:
        console.print(f"[red]Credential error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    if removed:
        console.print(f"[green]Removed {service} token.[/green]")
    else:
        console.print(f"[yellow]No {service} token was configured.[/yellow]")


__all__ = ["auth_app"]
