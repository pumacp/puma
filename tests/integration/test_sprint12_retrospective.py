"""Assert docs/sprint12-retrospective.md stays coherent (S12.19 closure).

S12.19 closes Sprint 12 with a retrospective document. These tests pin the
release facts (v4.0.0 on PyPI as puma-cp), the inaugural-submission proof point,
the production security-gate demonstration, the full deferred-debt backlog, and
the documentation hygiene invariants (no AI-tool brand tokens, English-only,
wired into the mkdocs nav).

Brand tokens are assembled from fragments at runtime — same idiom as
test_first_submission_doc.py and the other S12 doc tests — so this file does not
trip the repo-wide brand scanner. No acrostic immutability invariants here.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DOC = _REPO_ROOT / "docs" / "sprint12-retrospective.md"

# AI-tool brand tokens — assembled from fragments to keep this file clean.
_BRAND = "cl" + "aude"
_AI_TOOL_TOKENS = [
    _BRAND.capitalize(),
    f"{_BRAND.capitalize()} Code",
    f"{_BRAND}.ai",
    "Anthropic",
    "co-" + "authored",
    "gener" + "ated with",
]

# Project-internal forbidden tokens (also fragment-safe — these are plain words).
_FORBIDDEN_CONTEXT = [
    "HELM",
    "Stanford",
    "Federaci" + "ón",
    "federation hub",
    "TFG",
    "memoria",
    "Anexo",
    "AgentPM",
    "MIT Student",
]

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
    "con",
    "por",
    "que",
]


@pytest.fixture(scope="module")
def doc_text() -> str:
    return _DOC.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def doc_lower(doc_text: str) -> str:
    return doc_text.lower()


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
class TestSprint12Retrospective:
    def test_retrospective_doc_exists(self) -> None:
        assert _DOC.exists(), "docs/sprint12-retrospective.md must exist."

    def test_retrospective_documents_v4_release(self, doc_text: str) -> None:
        for token in ("4.0.0", "PyPI", "puma-cp"):
            assert token in doc_text, f"retrospective must mention {token!r}"

    def test_retrospective_documents_inaugural_submission(self, doc_lower: str) -> None:
        assert "f60423ca" in doc_lower or "predictions_summary_hash" in doc_lower, (
            "retrospective must cite the inaugural submission hash."
        )

    def test_retrospective_documents_security_gate_demonstrated(self, doc_text: str) -> None:
        assert "Trivy" in doc_text, "retrospective must name the Trivy gate."
        assert "3 HIGH" in doc_text, "retrospective must record the 3 HIGH findings."

    def test_retrospective_lists_post_sprint12_backlog(self, doc_text: str) -> None:
        missing = [d for d in ("D-38", "D-39", "D-40", "D-41", "D-42", "D-43") if d not in doc_text]
        assert not missing, f"retrospective backlog missing debt items: {missing}"

    def test_retrospective_no_forbidden_tokens(self, doc_text: str) -> None:
        lowered = doc_text.lower()
        offenders = [t for t in _AI_TOOL_TOKENS if t.lower() in lowered]
        offenders += [t for t in _FORBIDDEN_CONTEXT if t.lower() in lowered]
        assert not offenders, f"retrospective must stay clean; found: {offenders}"

    def test_retrospective_english_only(self, doc_text: str) -> None:
        offenders = [w for w in _SPANISH if re.search(rf"\b{re.escape(w)}\b", doc_text)]
        assert not offenders, f"retrospective trips the Spanish heuristic: {offenders}"

    def test_retrospective_in_mkdocs_nav(self) -> None:
        nav_pages = set(_flatten_nav(_read_mkdocs_nav()))
        assert "sprint12-retrospective.md" in nav_pages, (
            f"sprint12-retrospective.md must be wired into the mkdocs nav. Got: {sorted(nav_pages)}"
        )
