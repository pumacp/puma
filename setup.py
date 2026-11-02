"""Build-time bundling of PUMA's runtime data (D42 prototype).

All project metadata lives in ``pyproject.toml``; this file only extends the
standard setuptools ``build_py`` step so that wheels carry byte-identical
copies of the data files the package reads at run time (the patterns are
``puma.resources.BUNDLED_PATTERNS``) under ``puma/_bundled/``. The copies are
made in the build directory only: nothing is written to the source tree, and
editable installs skip the step because they use the source tree directly.
``MANIFEST.in`` adds the same files to the sdist, so a wheel built from the
sdist (the default ``python -m build`` path) bundles them as well.
"""

from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py

ROOT = Path(__file__).resolve().parent


def _load_resources_module():  # type: ignore[no-untyped-def]
    """Import ``src/puma/resources.py`` by path, without importing ``puma``."""
    spec = importlib.util.spec_from_file_location(
        "_puma_resources", ROOT / "src" / "puma" / "resources.py"
    )
    if spec is None or spec.loader is None:  # pragma: no cover - the file ships with the project
        raise RuntimeError("src/puma/resources.py is missing")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class build_py(_build_py):
    """``build_py`` that also copies the runtime data into ``puma/_bundled/``."""

    def run(self) -> None:
        super().run()
        if getattr(self, "editable_mode", False):
            return
        resources = _load_resources_module()
        target = Path(self.build_lib) / "puma" / "_bundled"
        for src in resources.bundled_files(ROOT):
            dst = target / src.relative_to(ROOT)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)


setup(cmdclass={"build_py": build_py})
