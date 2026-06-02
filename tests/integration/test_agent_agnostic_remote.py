"""Assert the public remote is free of the AI-assistant brand and that the
GitNexus tooling surface is present and tool-neutral.

The forbidden brand token is assembled from fragments at runtime so this file
itself contains no literal occurrence of it — keeping the entire tracked tree
free of the token (which ``test_no_brand_references_in_tracked_tree`` enforces).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BRAND = "cl" + "aude"  # assembled to avoid a literal occurrence in this file
_BRAND_DIR = f".{_BRAND}/"  # ".<brand>/"
_BRAND_MD = f"{_BRAND.upper()}.md"  # "<BRAND>.md"


def _git(args: list[str]) -> subprocess.CompletedProcess[str]:
    # safe.directory=* so git works even when the repo is bind-mounted under a
    # different owner (e.g. inside the runner container).
    return subprocess.run(
        ["git", "-c", "safe.directory=*", *args],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )


def _active_lines(path: Path) -> list[str]:
    lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines()]
    return [ln for ln in lines if ln and not ln.startswith("#")]


@pytest.mark.integration
class TestAgentAgnosticRemote:
    def test_no_brand_skill_tracked(self):
        assert _git(["ls-files", _BRAND_DIR]).stdout.strip() == ""

    def test_no_brand_md_tracked(self):
        assert _git(["ls-files", _BRAND_MD]).stdout.strip() == ""

    def test_agents_md_not_tracked(self):
        # AGENTS.md is auto-regenerated locally by GitNexus and intentionally not
        # tracked (friction-driven untrack).
        assert _git(["ls-files", "AGENTS.md"]).stdout.strip() == ""

    def test_gitignore_excludes_brand_tooling(self):
        active = _active_lines(_REPO_ROOT / ".gitignore")
        assert _BRAND_DIR in active
        assert _BRAND_MD in active
        # AGENTS.md is now an active ignore rule (untracked; regenerated locally).
        assert "AGENTS.md" in active

    def test_gitnexusignore_present_and_excludes_brand_tooling(self):
        gni = _REPO_ROOT / ".gitnexusignore"
        assert gni.is_file()
        assert _BRAND_DIR in _active_lines(gni)

    def test_gitnexusignore_excludes_agents_md(self):
        assert "AGENTS.md" in _active_lines(_REPO_ROOT / ".gitnexusignore")

    def test_knowledge_graph_doc_present_and_brand_free(self):
        doc = _REPO_ROOT / "docs" / "knowledge_graph.md"
        assert doc.is_file()
        text = doc.read_text(encoding="utf-8")
        assert "GitNexus" in text
        assert "gitnexus.vercel.app" in text
        assert _BRAND not in text.lower()

    def test_no_brand_references_in_tracked_tree(self):
        pattern = f"{_BRAND}|{_BRAND} code|{_BRAND}\\.ai"
        result = _git(["grep", "-in", "-E", pattern, "--", ":!.gitignore", ":!.gitnexusignore"])
        assert result.stdout.strip() == "", f"brand references found:\n{result.stdout}"

    def test_sync_wiki_script_present_and_executable(self):
        script = _REPO_ROOT / "scripts" / "sync_gitnexus_wiki.sh"
        assert script.is_file()
        assert script.stat().st_mode & 0o111, "sync script is not executable"
