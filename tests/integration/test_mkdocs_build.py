"""Integration tests for the mkdocs scaffolding (US-12.16).

These verify the site is configured and buildable, not its content. The strict
build is the buildability oracle: it fails on broken links, orphan pages, or any
warning.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MKDOCS_YML = _REPO_ROOT / "mkdocs.yml"
_DOCS_DIR = _REPO_ROOT / "docs"


def _load_config() -> dict:
    with open(_MKDOCS_YML, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _nav_md_files(nav: list) -> list[str]:
    """Flatten an mkdocs nav (lists of {title: page | sublist}) to page paths."""
    pages: list[str] = []
    for entry in nav:
        if isinstance(entry, str):
            pages.append(entry)
        elif isinstance(entry, dict):
            for value in entry.values():
                if isinstance(value, str):
                    pages.append(value)
                elif isinstance(value, list):
                    pages.extend(_nav_md_files(value))
    return pages


@pytest.mark.integration
class TestMkdocsBuild:
    def test_mkdocs_yaml_parses(self):
        config = _load_config()
        for key in ("site_name", "theme", "nav", "markdown_extensions"):
            assert key in config, f"missing top-level key: {key}"
        assert config["site_name"] == "PUMA"
        assert config["theme"]["name"] == "material"

    def test_mkdocs_strict_build_succeeds(self, tmp_path):
        pytest.importorskip("mkdocs")
        site = tmp_path / "site"
        result = subprocess.run(
            ["mkdocs", "build", "--strict", "--quiet", "--site-dir", str(site)],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"strict build failed:\n{result.stderr}"
        assert (site / "index.html").is_file()

    def test_nav_pages_exist(self):
        config = _load_config()
        pages = _nav_md_files(config["nav"])
        assert pages, "nav has no pages"
        for rel in pages:
            assert (_DOCS_DIR / rel).is_file(), f"nav page not found on disk: {rel}"

    def test_excluded_docs_remain_present_in_docs_dir(self):
        # Excluded from the build (D30), but kept on disk for the S12.17 sync.
        for name in ("user_guide.md", "troubleshooting.md", "adding_models.md"):
            assert (_DOCS_DIR / name).is_file(), f"excluded doc unexpectedly removed: {name}"
