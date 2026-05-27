"""Audit the public Pages content + corporate palette compliance (S12 Phase D-1).

Scope = the pages actually published by the mkdocs nav (the "public" surface).
Excluded docs (sprints/, known_debt.md, community/, RELEASES/, …) are NOT scanned:
they stay on disk for internal use and never reach the live site.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DOCS = _REPO_ROOT / "docs"

# The published nav set (see mkdocs.yml). These are the only "public" pages.
_PUBLIC_DOCS = [
    "index.md",
    "cli_reference.md",
    "publication_workflow.md",
    "knowledge_graph.md",
    "sustainability.md",
    "PROJECT_TECHNICAL_CLOSURE.md",
]

# Lowercase Spanish function words, matched as whole words, case-sensitively —
# so method acronyms like "PARA" (uppercase) do not false-trigger.
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

_ACROSTIC = (
    "<!-- PUMA-ACROSTIC-BLOCK START — DO NOT MODIFY — IMMUTABLE -->\n"
    "---\n"
    "**F**ollowing empirical evidence, ICT project management faces triage, estimation, and learning inefficiencies.<br>\n"
    "**O**bserved widely, these persist despite abundant historical data.<br>\n"
    "**L**aying a rigorous foundation requires reproducible benchmarking.<br>\n"
    "**L**everaging labeled datasets enables systematic evaluation of LLM performance.<br>\n"
    "**O**utcomes are compared using quantitative metrics and statistical analysis.<br>\n"
    "**W**ith an incremental design, a minimal viable benchmark is defined.<br>\n"
    "**T**hrough open-source release, results become reproducible and verifiable.<br>\n"
    "**H**ence, the framework supports extensibility across models and tasks.<br>\n"
    "**E**ventually, it enables integration into real organizational settings.<br>\n"
    "**W**ithin ICT environments, recurring inefficiencies hinder effective decision-making.<br>\n"
    "**H**eterogeneous data sources complicate prioritization and estimation processes.<br>\n"
    "**I**n response, this work builds a reproducible LLM-based benchmark.<br>\n"
    "**T**he focus is on issue triage and story-point estimation tasks.<br>\n"
    "**E**valuation follows controlled experiments with statistical validation.<br>\n"
    "**P**rotocols ensure reproducibility through fixed parameters and configurations.<br>\n"
    "**U**sing carbon tracking, the framework measures energy impact.<br>\n"
    "**M**oreover, the MVP delivers a valid and original contribution.<br>\n"
    "**A**ll artefacts are released as open source for replication and extension.<br>\n"
    "---\n"
    "<!-- PUMA-ACROSTIC-BLOCK END -->"
)


@pytest.mark.integration
class TestPagesContentAudit:
    def test_no_spanish_in_public_docs(self):
        offenders: list[str] = []
        for name in _PUBLIC_DOCS:
            text = (_DOCS / name).read_text(encoding="utf-8")
            for word in _SPANISH:
                if re.search(rf"\b{re.escape(word)}\b", text):
                    offenders.append(f"{name}: '{word}'")
        assert not offenders, f"Spanish detected in public docs: {offenders}"

    def test_no_anexo_references_in_public_docs(self):
        offenders = [
            name
            for name in _PUBLIC_DOCS
            if "anexo" in (_DOCS / name).read_text(encoding="utf-8").lower()
        ]
        assert not offenders, f"Anexo references in public docs: {offenders}"

    def test_landing_page_has_acrostic_block(self):
        text = (_DOCS / "index.md").read_text(encoding="utf-8")
        assert _ACROSTIC in text, "Immutable acrostic block missing or modified on the landing page"

    def test_landing_page_sections_present(self):
        text = (_DOCS / "index.md").read_text(encoding="utf-8")
        for heading in (
            "Quick start",
            "Practical tutorials",
            "PUMA Community",
            "Resources",
            "Citation",
        ):
            assert f"## {heading}" in text, f"Missing landing-page section: {heading}"

    def test_corporate_palette_in_extra_css(self):
        css = (_DOCS / "stylesheets" / "extra.css").read_text(encoding="utf-8").upper()
        for hex_value in ("#000000", "#FFFFFF", "#FAFAFA", "#F5F5F5", "#0D0D0D"):
            assert hex_value in css, f"Corporate palette missing hex {hex_value}"

    def test_no_orange_or_red_palette_in_mkdocs_yml(self):
        raw = (_REPO_ROOT / "mkdocs.yml").read_text(encoding="utf-8").lower()
        # Drop comment lines so words like "gitignored" don't false-match "red".
        body = "\n".join(ln for ln in raw.splitlines() if not ln.lstrip().startswith("#"))
        for token in ("deep orange", "deep-orange", "amber", "orange"):
            assert token not in body, f"mkdocs.yml palette contains '{token}'"
        assert not re.search(r"\bred\b", body), "mkdocs.yml palette contains 'red'"
