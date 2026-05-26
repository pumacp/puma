"""Themed error rendering for the PUMA CLI.

Presentation only: builds themed error panels and Rich tracebacks from a
:class:`Theme`. This module never changes exit codes, never alters which
exceptions are raised, and never touches any computation — it only controls
how an error is shown on the terminal.
"""

from __future__ import annotations

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.traceback import Traceback

from puma.ui.themes import Theme

# Exception classes treated as "expected" (operational / user-facing): they get
# a terse themed panel and a traceback only when --verbose is set. Everything
# else is "unexpected".
_EXPECTED_TYPES: tuple[type[BaseException], ...] = (
    FileNotFoundError,
    PermissionError,
    IsADirectoryError,
    ValueError,
    yaml.YAMLError,
    KeyError,
)


def _is_expected(exc: BaseException) -> bool:
    """Return True for operational errors that warrant a terse panel."""
    return isinstance(exc, _EXPECTED_TYPES)


def format_error_panel(
    theme: Theme,
    title: str,
    message: str,
    *,
    hint: str | None = None,
) -> Panel:
    """Build a themed error :class:`rich.panel.Panel`.

    The border and title use ``theme.error``; an optional ``hint`` renders on a
    new line in ``theme.muted``.
    """
    body = Text()
    body.append(message)
    if hint is not None:
        body.append("\n")
        body.append(hint, style=theme.muted)
    return Panel(
        body,
        title=f"[{theme.error}]{title}[/]",
        border_style=theme.error,
        padding=(1, 2),
    )


def install_themed_traceback(theme: Theme, *, show_locals: bool = False) -> None:
    """Install a Rich traceback handler whose colors track ``theme``.

    Idempotent: re-calling replaces the previous installation (Rich's
    ``install`` swaps ``sys.excepthook`` rather than chaining). ``show_locals``
    defaults to False to avoid leaking local variables into CI logs.
    """
    from rich.theme import Theme as RichTheme
    from rich.traceback import install

    overlay = RichTheme(
        {
            "traceback.border": theme.error,
            "traceback.border.syntax_error": theme.error,
            "traceback.title": theme.error,
            "traceback.exc_type": theme.error,
        },
        inherit=True,
    )
    install(console=Console(stderr=True, theme=overlay), show_locals=show_locals)


def print_error(
    console: Console,
    theme: Theme,
    exc: BaseException,
    *,
    show_traceback: bool = False,
) -> None:
    """Print a themed error panel for ``exc`` to ``console`` (typically stderr).

    When ``show_traceback`` is True, the Rich traceback for ``exc`` is printed
    below the panel. Never raises; never alters control flow.
    """
    message = str(exc) or type(exc).__name__
    console.print(format_error_panel(theme, type(exc).__name__, message))
    if show_traceback:
        console.print(Traceback.from_exception(type(exc), exc, exc.__traceback__))
