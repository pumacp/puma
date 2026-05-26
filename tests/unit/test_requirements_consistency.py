"""Guard against pyproject/requirements drift (S12 CI-fix meta-test).

The CI workflows install via ``requirements.txt`` + ``requirements-dev.txt``,
while ``pyproject.toml`` is the canonical dependency spec. This test asserts that
every runtime dependency and every ``dev`` extra declared in pyproject is also
present (by normalized package name) in the requirements files — so a dependency
added to pyproject (as ``pyfiglet`` was in S12.6) cannot silently break CI again.

Version specifiers are intentionally ignored: this checks *presence*, not pins.
The ``docs`` extra is excluded — it is installed via ``pip install -e ".[docs]"``
in the Docs workflow, not from the requirements files.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PYPROJECT = _REPO_ROOT / "pyproject.toml"
_REQ = _REPO_ROOT / "requirements.txt"
_REQ_DEV = _REPO_ROOT / "requirements-dev.txt"


def _norm(spec: str) -> str:
    """Normalized PEP 503 package name from a requirement string."""
    base = re.split(r"[><=!~;\[ ]", spec.strip(), maxsplit=1)[0]
    return base.lower().replace("_", "-").replace(".", "-")


def _req_names(path: Path) -> set[str]:
    names: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "-")):
            continue
        names.add(_norm(line))
    return names


@pytest.mark.unit
def test_pyproject_deps_present_in_requirements_files():
    pp = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
    declared = {_norm(d) for d in pp["project"]["dependencies"]}
    declared |= {_norm(d) for d in pp["project"]["optional-dependencies"]["dev"]}

    available = _req_names(_REQ) | _req_names(_REQ_DEV)

    missing = sorted(declared - available)
    assert not missing, (
        f"pyproject deps missing from requirements files (add them to keep CI green): {missing}"
    )
