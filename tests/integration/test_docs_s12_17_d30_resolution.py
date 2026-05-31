"""Assert the S12.17 mkdocs content sync that resolved D30 stays resolved.

D30 (docs/known_debt.md §D30) was the docs-sync debt for the v4.0.0 read-only
``puma models`` sub-group plus the held-out pages that needed link repair to
re-enter the mkdocs nav. S12.17 (2026-05-31) landed those fixes; these tests
prevent the resolution from silently regressing.

Scope = active user-facing documentation. Historical artefacts that
legitimately mention the removed command forms (``docs/known_debt.md``
itself, ``docs/CATALOG_HISTORY.md``, ``docs/RELEASES/v2.*.md``) are
explicitly excluded.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DOCS = _REPO_ROOT / "docs"

# Files where stale CLI references would indicate the D30 fix has regressed.
_ACTIVE_USER_DOCS = [
    _REPO_ROOT / "README.md",
    _DOCS / "user_guide.md",
    _DOCS / "troubleshooting.md",
    _DOCS / "adding_models.md",
    _DOCS / "cli_reference.md",
    _DOCS / "index.md",
    _DOCS / "overview.md",
]

# Files that legitimately mention the legacy commands as historical context.
# Listed here so the audit grep does not have to skip them by directory rule.
_HISTORICAL_DOCS = {
    _DOCS / "known_debt.md",
    _DOCS / "CATALOG_HISTORY.md",
}

# Pages newly entered into the mkdocs nav by S12.17 (D30 resolution). These
# must be present on disk and listed in the build's nav.
_S12_17_NAV_ADDITIONS = [
    "overview.md",
    "user_guide.md",
    "troubleshooting.md",
    "architecture.md",
    "scenarios_reference.md",
    "metrics_reference.md",
    "adding_models.md",
    "adding_scenarios.md",
    "TESTING.md",
    "baseline_inventory.md",
    "baseline_references.md",
    "CATALOG_HISTORY.md",
    "CROSS_ARCH_REPRODUCIBILITY.md",
    "HARDWARE.md",
    "MACOS_NOTES.md",
    "RELEASES/v3.0.0.md",
    "open_questions.md",
]

# Cross-repo broken-link patterns that previously kept overview.md and
# RELEASES/v3.0.0.md out of the nav (mkdocs --strict rejects ../ paths
# that escape docs/).
_BROKEN_CROSS_REPO_LINK = re.compile(
    r"\]\((\.\./){1,2}(CONTRIBUTING|CHANGELOG|README)\.md\)"
)


def _read_known_debt() -> str:
    return (_DOCS / "known_debt.md").read_text(encoding="utf-8")


def _read_mkdocs_nav() -> list:
    raw = (_REPO_ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    # PyYAML cannot parse the `!!python/name:` Material constructors etc.
    # mkdocs.yml here uses none of those, but to be safe we strip the
    # `extra_css:` list resolution and just load.
    return yaml.safe_load(raw)["nav"]


def _flatten_nav(nav: list) -> list[str]:
    """Yield every page-path string in a (possibly nested) mkdocs nav."""
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
class TestD30Resolution:
    def test_no_stale_puma_models_pull_in_active_docs(self):
        """``puma models pull`` was removed in v4.0.0 (S12.9). It must not
        appear in any user-facing doc."""
        offenders: list[str] = []
        for path in _ACTIVE_USER_DOCS:
            text = path.read_text(encoding="utf-8")
            for line_no, line in enumerate(text.splitlines(), start=1):
                if "puma models pull" in line:
                    offenders.append(f"{path.relative_to(_REPO_ROOT)}:{line_no}")
        assert not offenders, (
            f"Stale `puma models pull` references resurfaced in active docs "
            f"(D30 regression): {offenders}"
        )

    def test_no_stale_list_ollama_models_in_active_docs(self):
        """``puma list-ollama-models`` was folded into ``puma models list``
        in v4.0.0 (S12.9). It must not appear in any user-facing doc."""
        offenders: list[str] = []
        for path in _ACTIVE_USER_DOCS:
            text = path.read_text(encoding="utf-8")
            for line_no, line in enumerate(text.splitlines(), start=1):
                if "puma list-ollama-models" in line:
                    offenders.append(f"{path.relative_to(_REPO_ROOT)}:{line_no}")
        assert not offenders, (
            f"Stale `puma list-ollama-models` references resurfaced in "
            f"active docs (D30 regression): {offenders}"
        )

    def test_d30_marked_resolved_with_date(self):
        """The D30 entry in docs/known_debt.md carries the RESOLVED marker
        with an ISO date (the audit signature for the resolution)."""
        text = _read_known_debt()
        section = re.search(
            r"^### D30 — .*?(?=^### D31|^### P1 |^## )",
            text,
            flags=re.MULTILINE | re.DOTALL,
        )
        assert section is not None, "D30 section not found in known_debt.md"
        body = section.group(0)
        assert re.search(
            r"\*\*Status:\*\*\s*RESOLVED\s*\(\d{4}-\d{2}-\d{2},\s*S12\.17\)",
            body,
        ), (
            "D30 Status line is not 'RESOLVED (YYYY-MM-DD, S12.17)'. "
            f"Found:\n{body[:200]}"
        )

    def test_mkdocs_nav_contains_s12_17_additions(self):
        """Every page S12.17 surfaced into the nav must actually be wired in."""
        nav_pages = set(_flatten_nav(_read_mkdocs_nav()))
        missing = [p for p in _S12_17_NAV_ADDITIONS if p not in nav_pages]
        assert not missing, (
            f"Pages re-entered into nav by S12.17 (D30) are no longer "
            f"in mkdocs.yml nav: {missing}"
        )

    def test_overview_and_v3_release_have_no_cross_repo_broken_links(self):
        """overview.md and RELEASES/v3.0.0.md previously linked to
        ../CONTRIBUTING.md / ../../CHANGELOG.md — paths that escape docs/
        and abort mkdocs --strict. S12.17 rewrote them to absolute GitHub
        URLs. Make sure those broken-link patterns do not creep back."""
        offenders: list[str] = []
        for rel in ("overview.md", "RELEASES/v3.0.0.md"):
            text = (_DOCS / rel).read_text(encoding="utf-8")
            for match in _BROKEN_CROSS_REPO_LINK.finditer(text):
                offenders.append(f"{rel}: {match.group(0)}")
        assert not offenders, (
            f"Cross-repo broken links resurfaced (would re-break mkdocs "
            f"--strict): {offenders}"
        )

    def test_active_user_docs_exist(self):
        """All paths referenced as 'active user docs' actually exist —
        guards against a refactor that silently moves a page out of the
        D30 audit set."""
        missing = [
            str(p.relative_to(_REPO_ROOT))
            for p in _ACTIVE_USER_DOCS
            if not p.exists()
        ]
        assert not missing, f"D30 audit set references missing files: {missing}"
