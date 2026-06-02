"""Assert the docs/first-submission.md write-up stays coherent (S12-N1).

S12-N1 introduces docs/first-submission.md documenting the inaugural PUMA
Community submission. These tests pin the identifiers, the propagation chain,
the reproducibility parameters, the F1 floor-anchor rationale, the
maintainer-driven path, and the deferred workflow gaps that the page must carry.

Brand tokens are assembled from fragments at runtime — same idiom as
test_technical_reference_doc.py, test_development_workflow_doc.py, and
test_security_doc.py — to avoid tripping the repo-wide brand scanner on this
file. This file intentionally asserts NO acrostic immutability invariants.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DOC = _REPO_ROOT / "docs" / "first-submission.md"

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
class TestFirstSubmissionDoc:
    def test_doc_exists(self) -> None:
        assert _DOC.exists(), "docs/first-submission.md must exist."

    def test_no_forbidden_tokens(self, doc_text: str) -> None:
        offenders = [tok for tok in _AI_TOOL_TOKENS if tok.lower() in doc_text.lower()]
        assert not offenders, f"first-submission.md must stay tool-agnostic; found: {offenders}"

    def test_english_only(self, doc_text: str) -> None:
        offenders = [w for w in _SPANISH if re.search(rf"\b{re.escape(w)}\b", doc_text)]
        assert not offenders, f"first-submission.md trips the Spanish heuristic: {offenders}"

    def test_in_mkdocs_nav(self) -> None:
        nav_pages = set(_flatten_nav(_read_mkdocs_nav()))
        assert "first-submission.md" in nav_pages, (
            f"first-submission.md must be wired into the mkdocs nav. Got: {sorted(nav_pages)}"
        )

    def test_documents_pr_url(self, doc_text: str) -> None:
        assert "https://github.com/pumacp/puma-community/pull/8" in doc_text

    def test_documents_predictions_hash(self, doc_text: str) -> None:
        expected = "f60423ca6a6e9b033f0f89ac5a5a127d889a6e2627fc07c480c44bfdf53857ec"
        assert expected in doc_text
        assert re.search(r"\b[0-9a-f]{64}\b", doc_text), "no 64-hex digest found"

    def test_documents_run_id(self, doc_text: str) -> None:
        expected = "baseline_triage_zero_shot_s12_n1__83ec5feaa8df4844__20260531T091417"
        assert expected in doc_text

    def test_documents_merge_sha(self, doc_text: str) -> None:
        assert "111cee36" in doc_text

    def test_documents_submission_id(self, doc_text: str) -> None:
        assert "1d88e49b-5b49-46b9-a8a6-df7bdd5bf80b" in doc_text

    def test_documents_propagation_chain(self, doc_lower: str) -> None:
        for term in ("dataset", "update-badges", "leaderboard"):
            assert term in doc_lower, f"propagation step missing: {term!r}"
        assert "merge" in doc_lower

    def test_documents_reproducibility(self, doc_lower: str) -> None:
        assert "seed" in doc_lower
        assert "42" in doc_lower
        assert "temperature" in doc_lower
        assert "0.0" in doc_lower

    def test_documents_f1_floor_anchor_rationale(self, doc_lower: str) -> None:
        assert "floor anchor" in doc_lower
        assert "0.3898" in doc_lower
        assert "zero_shot" in doc_lower
        # Framed as a floor, not a regression vs. contextual anchoring.
        assert "regression" in doc_lower
        assert "contextual" in doc_lower

    def test_documents_maintainer_driven_path(self, doc_lower: str) -> None:
        assert "maintainer-driven" in doc_lower
        assert "share-results" in doc_lower
        assert "hang" in doc_lower

    def test_documents_known_workflow_gaps(self, doc_lower: str) -> None:
        assert "validate-submission" in doc_lower
        assert "verify submission integrity" in doc_lower
        assert "s12.19" in doc_lower
