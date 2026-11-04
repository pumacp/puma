"""Locate PUMA's runtime data files.

PUMA reads several non-Python files at run time: the hardware profiles and the
model catalog under ``config/``, the prompt templates and run-specs under
``specs/``, the Alembic migration environment, the dashboard logo and the
triage dataset. In a clone they live at the repository root, and nothing
about that changes. A wheel built with ``python -m build`` additionally
carries byte-identical copies of them under ``puma/_bundled/`` (see
``setup.py``), so a ``pip install puma-cp`` works without a clone.

Two kinds of lookup exist, matching how the paths were computed before the
data was bundled:

* :func:`resolve` for paths that were derived from the package location
  (``config/``, ``specs/prompts``, ``assets/``, the ``alembic/`` directory):
  the source tree ``<repository root>/<relative path>`` when it exists, then
  the bundled copy ``puma/_bundled/<relative path>``. When neither exists the
  source-tree path is returned unchanged, so callers keep their error messages.
* :func:`resolve_cwd` for paths that were relative to the working directory
  (datasets under ``data/``, run-specs under ``specs/runs``): the directory
  named by ``PUMA_DATA_DIR`` (for ``data/``) or ``PUMA_SPECS_DIR`` (for
  ``specs/``) when the variable is set and the file exists there, then the
  working-directory path exactly as before (returned as the same relative
  ``Path``), then the source tree, then the bundled copy. When none exists the
  relative path is returned unchanged, so callers keep their error messages.
"""

from __future__ import annotations

import os
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


#: Top-level directory of a working-directory-relative path -> environment
#: variable naming a replacement directory for that domain.
DOMAIN_ENV_VARS: dict[str, str] = {
    "data": "PUMA_DATA_DIR",
    "specs": "PUMA_SPECS_DIR",
}


def search_roots() -> tuple[Path, Path]:
    """Return the roots searched by :func:`resolve`: the source tree, then the bundle."""
    return (SOURCE_ROOT, BUNDLED_ROOT)


def domain_override(relative: str) -> Path | None:
    """Return ``<env dir>/<rest of path>`` for an overridable domain, else ``None``.

    ``relative`` is ``<domain>/<rest>``; the override applies only when the
    domain is in :data:`DOMAIN_ENV_VARS` and its variable is set and non-empty,
    so ``data/tawos_clean.csv`` becomes ``$PUMA_DATA_DIR/tawos_clean.csv`` and
    ``specs/runs/x.yaml`` becomes ``$PUMA_SPECS_DIR/runs/x.yaml``.
    """
    domain, _, rest = relative.partition("/")
    variable = DOMAIN_ENV_VARS.get(domain)
    value = os.environ.get(variable, "") if variable else ""
    if not value or not rest:
        return None
    return Path(value) / rest


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


def resolve_cwd(relative: str) -> Path:
    """Resolve a path that used to be relative to the working directory.

    Order: the :func:`domain_override` directory when set and the file exists
    there; the working-directory path ``Path(relative)`` when it exists (returned
    relative, as it was before); the source tree; the bundled copy. When none
    exists ``Path(relative)`` is returned, so callers keep their error messages.
    """
    override = domain_override(relative)
    if override is not None and override.exists():
        return override
    local = Path(relative)
    if local.exists():
        return local
    for root in search_roots():
        candidate = root / relative
        if candidate.exists():
            return candidate
    return local


def bundled_files(root: Path = SOURCE_ROOT) -> list[Path]:
    """Return the files under ``root`` matched by :data:`BUNDLED_PATTERNS`."""
    files: list[Path] = []
    for pattern in BUNDLED_PATTERNS:
        files.extend(sorted(p for p in root.glob(pattern) if p.is_file()))
    return files
