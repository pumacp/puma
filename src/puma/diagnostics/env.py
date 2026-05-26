"""Resolved-environment introspection for ``puma env`` (read-only)."""

from __future__ import annotations

import platform
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from puma.ui.themes import Theme


@dataclass(frozen=True)
class EnvironmentInfo:
    puma_version: str
    python_version: str
    platform: str
    theme: str
    profile: str
    ollama_endpoint: str
    db_path: str
    cache_dirs: list[str]


def _resolve_puma_version() -> str:
    try:
        return version("puma")
    except PackageNotFoundError:
        return "0.0.0-unknown"


def _detect_profile() -> str:
    """Best-effort profile name via the existing detector; never raises."""
    try:
        from puma.preflight.detect import detect_capabilities
        from puma.preflight.profile import select_profile

        return select_profile(detect_capabilities()).name
    except Exception:
        return "—"


def collect_environment(theme: Theme, ollama_endpoint: str, db_path: Path) -> EnvironmentInfo:
    """Gather the resolved environment for display. Read-only; never raises."""
    return EnvironmentInfo(
        puma_version=_resolve_puma_version(),
        python_version=platform.python_version(),
        platform=platform.platform(),
        theme=theme.name,
        profile=_detect_profile(),
        ollama_endpoint=ollama_endpoint,
        db_path=str(db_path),
        cache_dirs=["data/cache"],
    )
