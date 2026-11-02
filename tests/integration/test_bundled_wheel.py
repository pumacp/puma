"""A wheel built from this tree bundles the runtime data and works outside a clone (D42).

Builds the wheel in-process with ``setuptools.build_meta`` (no network), checks
that every file in ``puma.resources.BUNDLED_PATTERNS`` is inside it under
``puma/_bundled/`` byte-identical to the repository copy, then unpacks the wheel
into an empty directory placed first on ``PYTHONPATH`` and imports the package
from a working directory outside the repository, where only the bundled copies can be found.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from puma import resources

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BUNDLED_PREFIX = "puma/_bundled/"

pytestmark = [pytest.mark.integration, pytest.mark.slow]


def _setuptools_version() -> tuple[int, ...]:
    setuptools = pytest.importorskip("setuptools")
    return tuple(int(part) for part in setuptools.__version__.split(".")[:2])


@pytest.fixture(scope="module")
def wheel_path(tmp_path_factory) -> Path:
    if _setuptools_version() < (77,):
        pytest.skip("building this project needs setuptools >= 77")
    out_dir = tmp_path_factory.mktemp("wheel")
    # setuptools writes build/ and src/puma_cp.egg-info/ next to setup.py; remove
    # whatever this build created so the checkout is left as it was found.
    leftovers = [_REPO_ROOT / "build", _REPO_ROOT / "src" / "puma_cp.egg-info"]
    pre_existing = {p for p in leftovers if p.exists()}
    code = "import sys; from setuptools import build_meta; build_meta.build_wheel(sys.argv[1])"
    try:
        result = subprocess.run(
            [sys.executable, "-c", code, str(out_dir)],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        for p in leftovers:
            if p.exists() and p not in pre_existing:
                shutil.rmtree(p)
    assert result.returncode == 0, f"wheel build failed:\n{result.stdout}\n{result.stderr}"
    wheels = list(out_dir.glob("puma_cp-*.whl"))
    assert len(wheels) == 1, wheels
    return wheels[0]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_wheel_bundles_every_runtime_file_byte_identically(wheel_path):
    with zipfile.ZipFile(wheel_path) as zf:
        names = set(zf.namelist())
        for repo_file in resources.bundled_files(_REPO_ROOT):
            relative = repo_file.relative_to(_REPO_ROOT).as_posix()
            entry = _BUNDLED_PREFIX + relative
            assert entry in names, f"{entry} missing from the wheel"
            assert _sha256(zf.read(entry)) == _sha256(repo_file.read_bytes()), relative
        assert "puma/community/schema_data/submission.v1.json" in names
        bundled = sorted(n for n in names if n.startswith(_BUNDLED_PREFIX))
    expected = sorted(
        _BUNDLED_PREFIX + p.relative_to(_REPO_ROOT).as_posix()
        for p in resources.bundled_files(_REPO_ROOT)
    )
    assert bundled == expected, "the wheel bundles exactly the declared files"
    assert not any(n.startswith(_BUNDLED_PREFIX + "data/tawos") for n in bundled)


def test_source_tree_has_no_bundled_copies():
    assert not (_REPO_ROOT / "src" / "puma" / "_bundled").exists()


def test_installed_wheel_resolves_to_bundled_copies_outside_the_repo(wheel_path, tmp_path):
    """Unpack the wheel into an empty directory and import it from elsewhere.

    The directory is put first on ``PYTHONPATH`` (replacing any ``src`` entry),
    so ``puma`` is the wheel's copy while its dependencies come from the
    interpreter running the tests. The working directory is outside the
    repository, so only the bundled copies can satisfy the lookups.
    """
    site = tmp_path / "site"
    with zipfile.ZipFile(wheel_path) as zf:
        zf.extractall(site)
    workdir = tmp_path / "elsewhere"
    workdir.mkdir()
    env = dict(os.environ, PYTHONPATH=str(site))
    code = """
import json, puma.resources as r
from puma.community import schema
from puma.preflight import catalog, profile
from puma.adaptation import base
from puma.storage import db
db.init_db("bundled.db")
print(json.dumps({
    "module": r.__file__,
    "profiles": str(profile._PROFILES_PATH),
    "catalog": str(catalog._CATALOG_PATH),
    "prompts": str(base.PROMPTS_DIR),
    "alembic": str(r.resolve("alembic")),
    "profile_ids": sorted(schema._VALID_PROFILE_IDS),
    "n_catalog": len(catalog.load_catalog()),
}))
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=workdir,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "Profile catalog not found" not in result.stderr

    info = json.loads(result.stdout.strip().splitlines()[-1])
    bundled_root = site / "puma" / "_bundled"
    assert Path(info["module"]) == site / "puma" / "resources.py"
    assert Path(info["profiles"]) == bundled_root / "config" / "profiles.yaml"
    assert Path(info["catalog"]) == bundled_root / "config" / "models_catalog.yaml"
    assert Path(info["prompts"]) == bundled_root / "specs" / "prompts"
    assert Path(info["alembic"]) == bundled_root / "alembic"
    assert "gpu-entry" in info["profile_ids"]
    assert info["n_catalog"] > 0
    assert (workdir / "bundled.db").exists(), "init_db ran the bundled migrations"
