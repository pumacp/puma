"""Retro mainframe 80s banner for the PUMA CLI.

The banner consumes a :class:`puma.ui.themes.Theme` for all styling; when no
theme is passed it resolves the default via ``get_theme(None)`` (which honors
the ``PUMA_THEME`` env var, defaulting to amber). With no env var set the
output is identical to the S12.6 amber render.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

import pyfiglet
from rich.console import Console, RenderableType
from rich.panel import Panel
from rich.text import Text

from puma.ui.themes import Theme, get_theme

_BANNER_TEXT = "PUMA"
_BANNER_FONT = "block"
_TAGLINE = "Local LLM benchmarks for project management"


def _resolve_puma_version() -> str:
    """Return the installed PUMA distribution version or a fallback."""
    try:
        return version("puma")
    except PackageNotFoundError:
        return "0.0.0-unknown"


def render_banner(theme: Theme | None = None, version: str | None = None) -> RenderableType:
    """Build the retro mainframe banner as a Rich renderable (a Panel).

    Args:
        theme: color theme to use; resolved via ``get_theme(None)`` when None.
        version: version string to display; resolved from the installed
            distribution when None.

    Caller is responsible for printing with a Rich Console.
    """
    resolved_theme = theme if theme is not None else get_theme(None)
    resolved_version = version if version is not None else _resolve_puma_version()

    figlet = pyfiglet.Figlet(font=_BANNER_FONT)
    ascii_art = figlet.renderText(_BANNER_TEXT).rstrip("\n")

    body = Text()
    body.append(ascii_art, style=resolved_theme.title)
    body.append("\n")
    body.append(
        f"  {_TAGLINE}\n",
        style=f"{resolved_theme.title} italic",
    )
    body.append(
        f"  v{resolved_version}",
        style="dim",
    )

    return Panel(
        body,
        border_style=resolved_theme.border,
        padding=(1, 2),
    )


def print_banner(console: Console, theme: Theme | None = None) -> None:
    """Render the banner to the given Console using ``theme`` (or the default)."""
    console.print(render_banner(theme=theme))
