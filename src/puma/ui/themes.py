"""Color themes for the PUMA retro CLI.

A small, self-contained registry of Rich color themes. This module is a leaf
dependency: it imports nothing from the rest of PUMA and exposes only the
``Theme`` dataclass, the ``THEMES`` registry, and ``get_theme``. The banner,
and (in later phases) progress / error / summary rendering, consume a resolved
``Theme`` rather than hard-coding colors.

Theme resolution precedence (see ``get_theme``):
    explicit name argument  >  PUMA_THEME env var  >  "amber" (default)
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    """A set of Rich color strings for one CLI color scheme."""

    name: str
    accent: str
    title: str
    border: str
    success: str
    warning: str
    error: str
    muted: str


THEMES: dict[str, Theme] = {
    "amber": Theme(
        name="amber",
        accent="orange3",
        title="orange3",
        border="orange3",
        success="green3",
        warning="yellow3",
        error="red3",
        muted="grey50",
    ),
    "green": Theme(
        name="green",
        accent="green3",
        title="green3",
        border="green3",
        success="bright_green",
        warning="yellow3",
        error="red3",
        muted="grey50",
    ),
}

_DEFAULT_THEME = "amber"


def _unknown_theme_msg(name: str) -> str:
    available = ", ".join(sorted(THEMES))
    return f"Unknown theme '{name}'. Available: {available}"


def get_theme(name: str | None = None) -> Theme:
    """Resolve a :class:`Theme`.

    Precedence: explicit ``name`` > ``PUMA_THEME`` env var > ``"amber"``.

    Raises:
        ValueError: if ``name`` is given but unknown, or if ``PUMA_THEME`` is
            set to an unknown value.
    """
    if name is not None:
        try:
            return THEMES[name]
        except KeyError:
            raise ValueError(_unknown_theme_msg(name)) from None

    env_name = os.environ.get("PUMA_THEME")
    if env_name:
        try:
            return THEMES[env_name]
        except KeyError:
            raise ValueError(_unknown_theme_msg(env_name)) from None

    return THEMES[_DEFAULT_THEME]
