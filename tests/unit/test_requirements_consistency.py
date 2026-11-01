"""Guard against pyproject/requirements drift (S12 CI-fix meta-test).

The CI workflows install via ``requirements.txt`` + ``requirements-dev.txt``,
while ``pyproject.toml`` is the canonical dependency spec. This test asserts that
every runtime dependency and every ``dev`` extra declared in pyproject is also
present (by normalized package name) in the requirements files — so a dependency
added to pyproject (as ``pyfiglet`` was in S12.6) cannot silently break CI again.

Version specifiers are intentionally ignored: this checks *presence*, not pins.
The ``docs`` extra is excluded — it is installed via ``pip install -e ".[docs]"``
in the Docs workflow, not from the requirements files.

The reverse direction is guarded too (D48): every third-party package that
``src/puma`` imports at module level must be declared in pyproject (dependencies
or an extra), otherwise ``pip install puma-cp`` ships a package that cannot be
imported — ``matplotlib`` was missing and ``puma dashboard`` failed on a wheel.
Only module-level imports are checked. Imports inside functions are out of
scope: they are lazy, so a wheel without those packages still imports. Today
these are ``pyarrow`` (community/pull_cli.py, behind an explicit ImportError
message), ``torch`` (orchestrator/runner.py, inside a try block), ``ollama``
(scenarios/triage_jira.py and estimation_tawos.py, a bare import inside the
live evaluators) and ``click`` (cli.py, a bare import inside ``main()``, provided
transitively by typer).
"""

from __future__ import annotations

import ast
import re
import sys
import tomllib
from importlib.metadata import packages_distributions
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PYPROJECT = _REPO_ROOT / "pyproject.toml"
_REQ = _REPO_ROOT / "requirements.txt"
_REQ_DEV = _REPO_ROOT / "requirements-dev.txt"
_SRC = _REPO_ROOT / "src" / "puma"


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


def _module_level_third_party_imports() -> dict[str, str]:
    """Map each third-party top-level module imported at module level to one file:line."""
    stdlib = set(sys.stdlib_module_names)
    found: dict[str, str] = {}
    for path in sorted(_SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:  # module level only: nested imports are lazy by design
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            else:
                continue
            for name in names:
                top = name.split(".")[0]
                if top in stdlib or top == "puma":
                    continue
                found.setdefault(top, f"{path.relative_to(_REPO_ROOT)}:{node.lineno}")
    return found


def _distributions_for(module: str) -> set[str]:
    """Normalized distribution names providing ``module`` (falls back to the module name)."""
    dists = packages_distributions().get(module) or [module]
    return {_norm(d) for d in dists}


@pytest.mark.unit
def test_module_level_imports_are_declared_in_pyproject():
    pp = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
    declared = {_norm(d) for d in pp["project"]["dependencies"]}
    for extra in pp["project"]["optional-dependencies"].values():
        declared |= {_norm(d) for d in extra}

    undeclared = {
        module: where
        for module, where in _module_level_third_party_imports().items()
        if not (_distributions_for(module) & declared)
    }
    assert not undeclared, (
        "modules imported at module level in src/puma but not declared in pyproject "
        f"(a wheel built from pyproject would not install them): {undeclared}"
    )
