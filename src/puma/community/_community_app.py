"""Shared Typer group for the ``puma community`` subcommands.

Defined in its own leaf module (no imports of the command modules) so each
command module can decorate its function with ``@community_app.command(...)``
without creating an import cycle through :mod:`puma.community` or
:mod:`puma.cli`.
"""

from __future__ import annotations

import typer

community_app = typer.Typer(
    name="community",
    help="Browse, pull, verify, and validate PUMA Community submissions.",
    no_args_is_help=True,
)

__all__ = ["community_app"]
