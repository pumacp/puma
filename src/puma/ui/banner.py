"""Retro mainframe 80s banner for the PUMA CLI.

Sprint 12 E4 first render — minimal implementation for visual approval at
PAUSE 2. Themes, env-var configurability, and the --no-banner flag are
introduced in Sprint 12 S12.7 (US-12.12).
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

import pyfiglet
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

_BANNER_TEXT = "PUMA"
_BANNER_FONT = "block"
_TAGLINE = "Local LLM benchmarks for project management"
_DEFAULT_THEME_COLOR = "orange3"  # amber-mainframe; S12.7 makes this
# configurable per theme.


def _resolve_puma_version() -> str:
    """Return the installed PUMA distribution version or a fallback."""
    try:
        return version("puma")
    except PackageNotFoundError:
        return "0.0.0-unknown"


def render_banner() -> Panel:
    """Build the retro mainframe banner as a Rich Panel.

    Caller is responsible for printing with a Rich Console.
    """
    figlet = pyfiglet.Figlet(font=_BANNER_FONT)
    ascii_art = figlet.renderText(_BANNER_TEXT).rstrip("\n")

    body = Text()
    body.append(ascii_art, style=_DEFAULT_THEME_COLOR)
    body.append("\n")
    body.append(
        f"  {_TAGLINE}\n",
        style=f"{_DEFAULT_THEME_COLOR} italic",
    )
    body.append(
        f"  v{_resolve_puma_version()}",
        style="dim",
    )

    return Panel(
        body,
        border_style=_DEFAULT_THEME_COLOR,
        padding=(1, 2),
    )


def print_banner(console: Console | None = None) -> None:
    """Render the banner to the given Console (or a fresh one)."""
    (console or Console()).print(render_banner())
