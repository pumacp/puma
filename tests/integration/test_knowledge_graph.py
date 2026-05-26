"""Presence checks for the GitNexus knowledge-graph tooling (Sprint 12 side-task).

Verifies the project-scoped GitNexus skill is committed, that the knowledge-graph
doc exists and carries the regeneration command, and — when the CLI happens to be
on PATH — that it reports a version. The CLI test skips gracefully in
environments without GitNexus installed (e.g. the Python runner container).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SKILL_MD = _REPO_ROOT / ".claude" / "skills" / "gitnexus" / "gitnexus-guide" / "SKILL.md"
_DOC = _REPO_ROOT / "docs" / "knowledge_graph.md"


@pytest.mark.integration
class TestKnowledgeGraphSetup:
    def test_gitnexus_skill_present(self):
        assert _SKILL_MD.is_file(), f"GitNexus project skill missing: {_SKILL_MD}"

    def test_gitnexus_cli_available(self):
        if shutil.which("gitnexus") is None:
            pytest.skip("gitnexus CLI not on PATH in this environment")
        result = subprocess.run(
            ["gitnexus", "--version"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"gitnexus --version failed: {result.stderr}"
        assert result.stdout.strip(), "gitnexus --version produced no output"

    def test_knowledge_graph_doc_present(self):
        assert _DOC.is_file(), f"knowledge-graph doc missing: {_DOC}"
        text = _DOC.read_text(encoding="utf-8")
        assert "npx gitnexus analyze" in text, "doc must document the regeneration command"
