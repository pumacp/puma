"""Assert the SECURITY.md + docs/security.md surface is well-formed (S12-N2).

S12-N2 introduces the security audit MVP: SECURITY.md at repo root is
the canonical disclosure-policy file GitHub surfaces, docs/security.md
is the comprehensive Pages reference for the threat model and security
posture. These tests pin the structural invariants of the pairing and
the new CI security workflows.

Brand tokens are assembled from fragments at runtime to keep this file
clean of the literal — the repo-wide brand-scanner
(test_agent_agnostic_remote.py::test_no_brand_references_in_tracked_tree)
would otherwise trip on this file.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DOCS = _REPO_ROOT / "docs"
_SECURITY_MD = _REPO_ROOT / "SECURITY.md"
_DOCS_SECURITY = _DOCS / "security.md"
_WORKFLOWS = _REPO_ROOT / ".github" / "workflows"

# Canonical disclosure email (also in SECURITY.md and docs/security.md).
_DISCLOSURE_EMAIL = "pumacapstoneproject@gmail.com"

# Tokens that must not appear in the security docs.
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

# Brand tokens assembled from fragments to keep this file free of the
# literal — mirrors the pattern in test_agent_agnostic_remote.py.
_BRAND = "cl" + "aude"
_BRAND_TOKENS = [
    _BRAND.capitalize(),
    f"{_BRAND.capitalize()} Code",
    f"{_BRAND}.ai",
    "Anthropic",
]

# Spanish function words — same list as test_pages_content_audit.py so
# behavior is consistent across docs.
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

# Workflows added or modified by S12-N2.
_S12_N2_WORKFLOWS = {
    "pip-audit.yml": "audit",
    "bandit.yml": "sast",
    "gitleaks.yml": "scan",
    "publish-docker.yml": "build-and-push",
}


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
class TestSecurityDocs:
    def test_security_md_exists_at_root(self):
        assert _SECURITY_MD.exists(), (
            "SECURITY.md must exist at the repository root — GitHub "
            "surfaces it in the Security tab and disclosure flows."
        )

    def test_docs_security_exists(self):
        assert _DOCS_SECURITY.exists(), (
            "docs/security.md must exist — it is the comprehensive "
            "Pages-side reference for the threat model and posture."
        )

    def test_security_md_documents_disclosure_email(self):
        text = _SECURITY_MD.read_text(encoding="utf-8")
        assert _DISCLOSURE_EMAIL in text, (
            f"SECURITY.md must contain the canonical disclosure email ({_DISCLOSURE_EMAIL!r})."
        )

    def test_docs_security_documents_disclosure_email_or_pointer(self):
        """docs/security.md need not repeat the email — a back-link to
        SECURITY.md is sufficient, since the canonical contact lives
        there."""
        text = _DOCS_SECURITY.read_text(encoding="utf-8")
        assert _DISCLOSURE_EMAIL in text or "SECURITY.md" in text, (
            "docs/security.md must either repeat the disclosure email "
            "or back-link to SECURITY.md as the canonical contact."
        )

    def test_docs_security_documents_determinism(self):
        text = _DOCS_SECURITY.read_text(encoding="utf-8")
        for marker in ("seed", "temperature", "0.0", "42"):
            assert marker in text, (
                "docs/security.md must document the determinism "
                f"guarantees — missing marker: {marker!r}"
            )

    def test_docs_security_documents_no_outbound_telemetry(self):
        text = _DOCS_SECURITY.read_text(encoding="utf-8").lower()
        assert "outbound" in text, (
            "docs/security.md must use the word 'outbound' when "
            "describing the no-telemetry default."
        )
        assert "telemetry" in text, "docs/security.md must use the word 'telemetry' explicitly."

    def test_docs_security_documents_submission_integrity(self):
        text = _DOCS_SECURITY.read_text(encoding="utf-8")
        # Accept either SHA-256 or sha-256 / sha256 spelling.
        assert (
            "SHA-256" in text or "SHA256" in text or "sha256" in text or "sha-256" in text.lower()
        ), "docs/security.md must mention SHA-256 as the integrity hash."
        for marker in ("submission", "predictions"):
            assert marker in text.lower(), (
                f"docs/security.md must document submission integrity — missing marker: {marker!r}"
            )

    def test_docs_security_documents_phase_z2_history_sanitization(self):
        text = _DOCS_SECURITY.read_text(encoding="utf-8")
        assert "Phase Z-2" in text or "Z-2" in text, (
            "docs/security.md must reference the Phase Z-2 git history sanitization milestone."
        )
        assert "filter-repo" in text, (
            "docs/security.md must name the git filter-repo tool used for the history rewrite."
        )
        assert "trailer" in text.lower(), (
            "docs/security.md must describe the trailer-stripping policy (current and future)."
        )

    def test_docs_security_documents_brand_scanner_pattern(self):
        text = _DOCS_SECURITY.read_text(encoding="utf-8")
        # The doc must reference the fragment-assembly idiom and the
        # scanner test that enforces it.
        assert "test_no_brand_references_in_tracked_tree" in text, (
            "docs/security.md must name the repo-wide brand-scanner "
            "test so contributors can find the enforcing code."
        )
        # The fragment-assembly idiom (some form of '+'-concatenation
        # split that avoids the literal) must appear as an example.
        assert re.search(r'"cl"\s*\+\s*"aude"', text), (
            "docs/security.md must show the fragment-assembly idiom "
            '(e.g. _BRAND = "cl" + "aude") as the worked example.'
        )

    def test_security_workflows_yaml_valid(self):
        """All four S12-N2 workflows parse as YAML and declare the
        expected job key + permissions."""
        for filename, expected_job in _S12_N2_WORKFLOWS.items():
            path = _WORKFLOWS / filename
            assert path.is_file(), f"missing workflow: {filename}"
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
            assert doc is not None, f"{filename}: empty document"
            # YAML 1.1 quirk: bare `on:` is parsed as True. Accept either.
            assert "on" in doc or True in doc, f"{filename}: missing on:"
            assert "jobs" in doc, f"{filename}: missing jobs:"
            assert expected_job in doc["jobs"], (
                f"{filename}: missing expected job key {expected_job!r}; "
                f"got {list(doc['jobs'].keys())}"
            )
            # Permissions may be top-level or per-job.
            top_perms = doc.get("permissions")
            job_perms = doc["jobs"][expected_job].get("permissions")
            assert top_perms is not None or job_perms is not None, (
                f"{filename}: neither top-level nor job-level permissions: block declared"
            )

    def test_docs_security_in_mkdocs_nav(self):
        nav_pages = set(_flatten_nav(_read_mkdocs_nav()))
        assert "security.md" in nav_pages, (
            f"security.md must be present in the mkdocs nav. Got: {sorted(nav_pages)}"
        )

    def test_no_forbidden_tokens_in_security_docs(self):
        """No academic-framing or unrelated-benchmark brand tokens
        appear in the security docs. Brand tokens (AI-assistant names)
        are checked separately."""
        for path in (_SECURITY_MD, _DOCS_SECURITY):
            text = path.read_text(encoding="utf-8")
            offenders = [tok for tok in _FORBIDDEN_TOKENS if tok in text]
            assert not offenders, f"{path.name} contains forbidden tokens: {offenders}"

    def test_no_brand_tokens_in_security_docs(self):
        """No AI-assistant brand names appear in the security docs.
        Tokens are assembled from fragments to keep this test file clean."""
        for path in (_SECURITY_MD, _DOCS_SECURITY):
            text = path.read_text(encoding="utf-8")
            offenders = [tok for tok in _BRAND_TOKENS if tok in text]
            assert not offenders, (
                f"{path.name} contains AI-assistant brand tokens "
                f"(the security docs must be tool-agnostic): {offenders}"
            )

    def test_security_docs_english_only(self):
        for path in (_SECURITY_MD, _DOCS_SECURITY):
            text = path.read_text(encoding="utf-8")
            offenders = [w for w in _SPANISH if re.search(rf"\b{re.escape(w)}\b", text)]
            assert not offenders, f"{path.name} trips the Spanish-detection heuristic: {offenders}"
