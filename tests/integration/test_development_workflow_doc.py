"""Assert the CONTRIBUTING.md + docs/development-workflow.md surface is
well-formed and stays coherent (S12-N4).

S12-N4 introduces docs/development-workflow.md as the canonical
procedural reference for the manual IDE-based contribution workflow,
and updates the root CONTRIBUTING.md to point at it. These tests
guard the structural invariants that make the pairing useful:

  - both files exist on disk;
  - CONTRIBUTING.md links to the development-workflow page;
  - the page is wired into the mkdocs nav;
  - the page contains zero forbidden tokens (Spanish, Anexo, TFG,
    memoria, brand markers, AI-tool names);
  - the page references the canonical CLI surface (puma models list /
    show / recommended, puma run, ...) — guards against silent drift
    if the CLI is renamed;
  - the page lists the locked paths;
  - the page documents the conventional-commits format.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DOCS = _REPO_ROOT / "docs"
_CONTRIBUTING = _REPO_ROOT / "CONTRIBUTING.md"
_DEV_WORKFLOW = _DOCS / "development-workflow.md"

# Tokens that must not appear in the workflow doc. Two classes:
# (a) academic-framing tokens the project has moved away from, and
# (b) unrelated benchmark / methodology brands PUMA does not claim a
# relationship with. AI-tool references are checked separately below.
_FORBIDDEN_TOKENS = [
    "Anexo",
    "memoria",
    "TFG",
    "Federación",
    "federation hub",
    "HELM",
    "Stanford",
    "AgentPM",
    "MIT Student Method",
]

# AI-tool brand names that must not appear in the workflow doc — the
# guidance is intentionally tool-agnostic. The hook strips these from
# commit trailers; the docs page must not introduce them either.
#
# The brand token is assembled from fragments at runtime so this file
# itself contains no literal occurrence — mirroring the pattern used
# by tests/integration/test_agent_agnostic_remote.py, which scans the
# entire tracked tree for the same brand.
_BRAND = "cl" + "aude"
_AI_TOOL_TOKENS = [
    _BRAND.capitalize(),
    f"{_BRAND.capitalize()} Code",
    f"{_BRAND}.ai",
    "Anthropic",
]

# Spanish function words for the heuristic. Mirrors the list used by
# test_pages_content_audit.py so behavior is consistent across docs.
_SPANISH = [
    "el",
    "la",
    "los",
    "las",
    "para",
    "este",
    "esta",
    "una",
    "del",
    "qué",
    "cómo",
    "cuál",
    "función",
    "propósito",
    "salida",
    "comando",
    "sintaxis",
]

# Canonical CLI surface the workflow doc is expected to reference at
# least once — guards against silent drift if any of these commands is
# renamed or removed. Sourced from docs/cli_reference.md (v4.0.0).
_CANONICAL_CLI_COMMANDS = [
    "puma models list",
    "puma models show",
    "puma models recommended",
    "puma run",
    "puma share-results",
    "puma auth",
    "puma doctor",
]

# Paths the workflow doc must document as locked. Subset of the locked
# set tracked in docs/known_debt.md + the operational constraints.
_LOCKED_PATHS = [
    "schema/",
    "specs/runs/",
    "config/profiles.yaml",
    "config/models_catalog.yaml",
    "src/puma/community/integrity.py",
    "src/puma/orchestrator/runner.py",
    "src/puma/runtime/retry.py",
    "src/puma/models/",
    "src/puma/preflight/",
    "docs/sprints/",
    "docs/known_debt.md",
]


def _read_mkdocs_nav() -> list:
    raw = (_REPO_ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    return yaml.safe_load(raw)["nav"]


def _flatten_nav(nav: list) -> list[str]:
    out: list[str] = []
    for entry in nav:
        if isinstance(entry, str):
            out.append(entry)
        elif isinstance(entry, dict):
            for value in entry.values():
                if isinstance(value, str):
                    out.append(value)
                elif isinstance(value, list):
                    out.extend(_flatten_nav(value))
    return out


@pytest.mark.integration
class TestDevelopmentWorkflowDoc:
    def test_contributing_md_exists_at_root(self):
        assert _CONTRIBUTING.exists(), (
            "CONTRIBUTING.md must exist at the repository root — it is "
            "the canonical entry point GitHub surfaces in PR creation."
        )

    def test_development_workflow_doc_exists(self):
        assert _DEV_WORKFLOW.exists(), (
            "docs/development-workflow.md must exist — it is the "
            "canonical procedural reference linked from CONTRIBUTING.md."
        )

    def test_contributing_links_to_development_workflow(self):
        text = _CONTRIBUTING.read_text(encoding="utf-8")
        # Accept either the relative docs path or the published Pages URL.
        link_patterns = [
            "docs/development-workflow.md",
            "pumacp.github.io/puma/development-workflow",
        ]
        assert any(p in text for p in link_patterns), (
            "CONTRIBUTING.md must contain a link to "
            "docs/development-workflow.md (or its rendered Pages URL)."
        )

    def test_development_workflow_in_mkdocs_nav(self):
        nav_pages = set(_flatten_nav(_read_mkdocs_nav()))
        assert "development-workflow.md" in nav_pages, (
            f"development-workflow.md must be present in the mkdocs nav. Got: {sorted(nav_pages)}"
        )

    def test_development_workflow_no_forbidden_tokens(self):
        """The page must not introduce forbidden tokens — except inside
        §13 'What NOT to do', which legitimately lists them as the very
        thing future contributors must avoid. We strip that section
        before scanning."""
        text = _DEV_WORKFLOW.read_text(encoding="utf-8")
        # Drop everything from the §13 heading up to (but not including)
        # the §14 heading; the prohibited-tokens list necessarily appears
        # inside §13.
        scrubbed = re.sub(
            r"^## 13\. What NOT to do.*?(?=^## 14\.)",
            "",
            text,
            flags=re.MULTILINE | re.DOTALL,
        )
        offenders = [tok for tok in _FORBIDDEN_TOKENS if tok in scrubbed]
        assert not offenders, (
            "development-workflow.md contains forbidden tokens outside "
            f"the §13 'What NOT to do' section: {offenders}"
        )

    def test_development_workflow_no_ai_tool_references(self):
        text = _DEV_WORKFLOW.read_text(encoding="utf-8")
        # The page is intentionally tool-agnostic. The .githooks/commit-msg
        # hook is mentioned generically; specific assistant names must not
        # appear anywhere.
        offenders = [tok for tok in _AI_TOOL_TOKENS if tok in text]
        assert not offenders, (
            f"development-workflow.md references AI tools by name "
            f"(the page must stay tool-agnostic): {offenders}"
        )

    def test_development_workflow_in_english_only(self):
        text = _DEV_WORKFLOW.read_text(encoding="utf-8")
        offenders = [w for w in _SPANISH if re.search(rf"\b{re.escape(w)}\b", text)]
        assert not offenders, (
            f"development-workflow.md trips the Spanish-detection heuristic: {offenders}"
        )

    def test_development_workflow_references_canonical_cli(self):
        text = _DEV_WORKFLOW.read_text(encoding="utf-8")
        missing = [cmd for cmd in _CANONICAL_CLI_COMMANDS if cmd not in text]
        assert not missing, (
            "development-workflow.md does not mention every canonical CLI "
            f"command in _CANONICAL_CLI_COMMANDS — missing: {missing}"
        )

    def test_development_workflow_documents_locked_paths(self):
        text = _DEV_WORKFLOW.read_text(encoding="utf-8")
        missing = [p for p in _LOCKED_PATHS if p not in text]
        assert not missing, (
            "development-workflow.md does not mention every locked path "
            f"in _LOCKED_PATHS — missing: {missing}"
        )

    def test_development_workflow_documents_conventional_commits(self):
        text = _DEV_WORKFLOW.read_text(encoding="utf-8")
        # Conventional-commits surface: the format string + every type
        # currently in use in the project.
        assert "Conventional Commits" in text, (
            "development-workflow.md must mention 'Conventional Commits' by name."
        )
        for typ in ("feat", "fix", "docs", "test", "chore", "refactor", "ci", "build"):
            assert re.search(rf"`{typ}`", text), (
                f"development-workflow.md does not document the `{typ}` commit type in backticks."
            )

    def test_development_workflow_documents_ai_trailer_policy(self):
        """The .githooks/commit-msg hook policy is part of the workflow.
        The page must describe it without naming any specific assistant."""
        text = _DEV_WORKFLOW.read_text(encoding="utf-8")
        for marker in (
            ".githooks/commit-msg",
            "Co-authored-by:",
            "Generated-by:",
            "core.hooksPath",
        ):
            assert marker in text, (
                f"development-workflow.md must document the commit-msg "
                f"hook policy — missing marker: {marker!r}"
            )

    def test_development_workflow_documents_acrostic_relaxation(self):
        """PR #47 relaxed the acrostic immutability assertions. The
        workflow doc must warn future contributors NOT to re-introduce
        byte-identical assertions or rewrite the acrostic prose
        gratuitously."""
        text = _DEV_WORKFLOW.read_text(encoding="utf-8")
        assert "acrostic" in text.lower(), (
            "development-workflow.md must mention the acrostic-block "
            "relaxation so future contributors do not re-introduce the "
            "immutability assertions."
        )
        # The page should reference the three skipped tests by name (or
        # at minimum the test files), so the relaxation is auditable.
        assert "pytest.mark.skip" in text, (
            "development-workflow.md must reference @pytest.mark.skip in "
            "the context of the acrostic relaxation."
        )

    def test_development_workflow_has_worked_example(self):
        """The worked-example appendix (PR #47) is a concrete reference
        for first-time contributors. Removing it would degrade the
        page's usefulness."""
        text = _DEV_WORKFLOW.read_text(encoding="utf-8")
        assert "PR #47" in text, (
            "development-workflow.md must reference PR #47 as a worked example (Appendix section)."
        )
        # The worked example walks through gh pr create + gh pr merge —
        # both must appear as concrete command examples somewhere.
        assert "gh pr create" in text
        assert "gh pr merge" in text
