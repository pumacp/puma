"""Locate PUMA's runtime data files (D42 prototype).

PUMA reads several non-Python files at run time: the hardware profiles and the
model catalog under ``config/``, the prompt templates and run-specs under
``specs/``, the Alembic migration environment, the dashboard logo and the
triage dataset. In a clone they live at the repository root, and nothing
about that changes. A wheel built with ``python -m build`` additionally
carries byte-identical copies of them under ``puma/_bundled/`` (see
``setup.py``), so a ``pip install puma-cp`` works without a clone.

This module is the single place that decides which copy a lookup uses:

1. the source tree, ``<repository root>/<relative path>``, whenever it exists,
   so an editable install or ``PYTHONPATH=src`` behaves exactly as before;
2. the bundled copy, ``puma/_bundled/<relative path>``.

When neither exists the source-tree path is returned unchanged, so the callers
keep today's error messages and ``exists()`` checks.
"""

from __future__ import annotations

from pathlib import Path

_PACKAGE_DIR = Path(__file__).resolve().parent
#: ``<repository root>`` for ``src/puma/resources.py``; for an installed wheel it is
#: ``<site-packages>/..``, where none of the data files exist.
SOURCE_ROOT: Path = _PACKAGE_DIR.parents[1]
#: Where ``setup.py`` places the copies inside a built wheel.
BUNDLED_ROOT: Path = _PACKAGE_DIR / "_bundled"

#: Repository-relative glob patterns of the files that wheels bundle. ``setup.py``
#: reads this tuple; the tests check that every pattern matches and that nothing
#: else (notably ``data/tawos_clean.csv``) is included.
BUNDLED_PATTERNS: tuple[str, ...] = (
    "config/profiles.yaml",
    "config/models_catalog.yaml",
    "specs/prompts/*/*.jinja",
    "specs/runs/*.yaml",
    "alembic.ini",
    "alembic/env.py",
    "alembic/script.py.mako",
    "alembic/versions/*.py",
    "assets/img/PUMA.png",
    "data/jira_balanced_200.csv",
)


def search_roots() -> tuple[Path, Path]:
    """Return the roots searched by :func:`resolve`: the source tree, then the bundle."""
    return (SOURCE_ROOT, BUNDLED_ROOT)


def in_source_tree(relative: str) -> bool:
    """True when ``<repository root>/relative`` exists, i.e. the package runs from a clone."""
    return (SOURCE_ROOT / relative).exists()


def resolve(relative: str) -> Path:
    """Return the first existing ``<root>/relative`` in precedence order.

    Falls back to the source-tree path when the file exists in neither place, so
    callers see the same path (and the same error) a clone without the file gives.
    """
    for root in search_roots():
        candidate = root / relative
        if candidate.exists():
            return candidate
    return SOURCE_ROOT / relative


def bundled_files(root: Path = SOURCE_ROOT) -> list[Path]:
    """Return the files under ``root`` matched by :data:`BUNDLED_PATTERNS`."""
    files: list[Path] = []
    for pattern in BUNDLED_PATTERNS:
        files.extend(sorted(p for p in root.glob(pattern) if p.is_file()))
    return files
