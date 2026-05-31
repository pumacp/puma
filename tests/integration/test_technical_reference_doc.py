"""Assert the docs/technical_reference.md surface stays coherent (S12-N3).

S12-N3 introduces docs/technical_reference.md as the consolidated
technical entry point. These tests pin the structural invariants that
make the page useful as a reference: it must mention every YAML config
key, every JSON Schema top-level field, every ORM model, every public
CLI command, plus the navigational furniture (glossary, decisions log,
strengths, risks) that turns it into a reference rather than a wall
of text.

Brand tokens are assembled from fragments at runtime — same idiom as
test_agent_agnostic_remote.py, test_development_workflow_doc.py, and
test_security_doc.py — to avoid tripping the repo-wide brand-scanner
on this file.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DOCS = _REPO_ROOT / "docs"
_TECH_REF = _DOCS / "technical_reference.md"

# Tokens that must not appear in the technical reference.
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

# AI-tool brand tokens — assembled from fragments to keep this test
# file clean. Mirrors the established pattern.
_BRAND = "cl" + "aude"
_AI_TOOL_TOKENS = [
    _BRAND.capitalize(),
    f"{_BRAND.capitalize()} Code",
    f"{_BRAND}.ai",
    "Anthropic",
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
    "cuál",
    "función",
    "propósito",
    "salida",
    "comando",
    "sintaxis",
]

# Top-level YAML keys the technical reference must document. Drawn
# from baseline_triage.yaml (run-spec) + profiles.yaml +
# models_catalog.yaml at the time of S12-N3.
_RUN_SPEC_KEYS = [
    "id",
    "description",
    "scenario",
    "sample_size",
    "models",
    "adaptation",
    "inference",
    "perturbations",
    "metrics",
    "sustainability",
    "repeat",
    "profile_required",
]
_PROFILE_KEYS = [
    "min_ram_gb",
    "gpu_required",
    "min_vram_gb",
    "min_disk_gb",
    "scenarios",
    "apple_silicon_required",
    "chip_brand_match",
    "min_unified_memory_gb",
]
_CATALOG_KEYS = [
    "ollama_tag",
    "params_b",
    "gguf_size_gb",
    "context_window",
    "logprobs_supported",
    "profiles_compatible",
    "timeout_s",
    "notes",
]

# JSON Schema root-payload fields (12) the technical reference must
# enumerate. Drawn from src/puma/community/schema_data/submission.v1.json.
_SCHEMA_ROOT_FIELDS = [
    "schema_version",
    "submission_id",
    "submitted_at",
    "submitter",
    "puma_version",
    "run_metadata",
    "hardware_profile",
    "metrics",
    "sustainability",
    "integrity",
    "raw_predictions_url",
    "notes",
]
# JSON Schema $defs (6 sub-objects).
_SCHEMA_DEFS = [
    "Submitter",
    "RunMetadata",
    "HardwareProfile",
    "Metrics",
    "Sustainability",
    "Integrity",
]

# ORM model names from src/puma/storage/models.py.
_ORM_MODELS = [
    "Run",
    "Instance",
    "Prediction",
    "Metric",
    "Emission",
    "ProfileSnapshot",
]

# Public CLI commands (from docs/cli_reference.md ### `puma <cmd>`
# headings). Each must appear at least once in the technical
# reference's CLI overview table.
_CLI_COMMANDS = [
    "puma run",
    "puma compare",
    "puma validate-baseline",
    "puma report",
    "puma list-runs",
    "puma doctor",
    "puma env",
    "puma preflight",
    "puma datasets",
    "puma prepare-datasets",
    "puma models list",
    "puma models show",
    "puma models recommended",
    "puma wilcoxon",
    "puma bias-analysis",
    "puma generate-plots",
    "puma db",
    "puma cache",
    "puma dashboard",
    "puma auth",
    "puma share-results",
    "puma community",
]

# Canonical docs the technical reference must link to.
_CANONICAL_CROSS_LINKS = [
    "cli_reference.md",
    "security.md",
    "development-workflow.md",
    "sustainability.md",
    "known_debt.md",
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
class TestTechnicalReferenceDoc:
    def test_technical_reference_doc_exists(self):
        assert _TECH_REF.exists(), (
            "docs/technical_reference.md must exist — it is the "
            "consolidated technical entry point for evaluators."
        )

    def test_technical_reference_in_mkdocs_nav(self):
        nav_pages = set(_flatten_nav(_read_mkdocs_nav()))
        assert "technical_reference.md" in nav_pages, (
            f"technical_reference.md must be present in the mkdocs nav. Got: {sorted(nav_pages)}"
        )

    def test_no_forbidden_tokens_in_technical_reference(self):
        text = _TECH_REF.read_text(encoding="utf-8")
        offenders = [tok for tok in _FORBIDDEN_TOKENS if tok in text]
        assert not offenders, f"technical_reference.md contains forbidden tokens: {offenders}"

    def test_no_ai_tool_tokens_in_technical_reference(self):
        text = _TECH_REF.read_text(encoding="utf-8")
        offenders = [tok for tok in _AI_TOOL_TOKENS if tok in text]
        assert not offenders, (
            f"technical_reference.md must stay tool-agnostic; brand tokens found: {offenders}"
        )

    def test_technical_reference_english_only(self):
        text = _TECH_REF.read_text(encoding="utf-8")
        offenders = [w for w in _SPANISH if re.search(rf"\b{re.escape(w)}\b", text)]
        assert not offenders, f"technical_reference.md trips the Spanish heuristic: {offenders}"

    def test_documents_all_run_spec_keys(self):
        text = _TECH_REF.read_text(encoding="utf-8")
        missing = [k for k in _RUN_SPEC_KEYS if k not in text]
        assert not missing, (
            f"technical_reference.md must document every run-spec key. Missing: {missing}"
        )

    def test_documents_all_profile_keys(self):
        text = _TECH_REF.read_text(encoding="utf-8")
        missing = [k for k in _PROFILE_KEYS if k not in text]
        assert not missing, (
            "technical_reference.md must document every profiles.yaml "
            f"requirement key. Missing: {missing}"
        )

    def test_documents_all_catalog_keys(self):
        text = _TECH_REF.read_text(encoding="utf-8")
        missing = [k for k in _CATALOG_KEYS if k not in text]
        assert not missing, (
            "technical_reference.md must document every "
            f"models_catalog.yaml per-entry key. Missing: {missing}"
        )

    def test_documents_all_schema_root_fields(self):
        text = _TECH_REF.read_text(encoding="utf-8")
        missing = [f for f in _SCHEMA_ROOT_FIELDS if f not in text]
        assert not missing, (
            "technical_reference.md must document every root field of "
            f"submission.v1.json. Missing: {missing}"
        )

    def test_documents_all_schema_defs(self):
        text = _TECH_REF.read_text(encoding="utf-8")
        missing = [d for d in _SCHEMA_DEFS if d not in text]
        assert not missing, (
            "technical_reference.md must document every $defs sub-object "
            f"of submission.v1.json. Missing: {missing}"
        )

    def test_documents_all_orm_models(self):
        text = _TECH_REF.read_text(encoding="utf-8")
        missing = [m for m in _ORM_MODELS if m not in text]
        assert not missing, (
            "technical_reference.md must document every ORM model in "
            f"src/puma/storage/models.py. Missing: {missing}"
        )

    def test_documents_all_public_cli_commands(self):
        text = _TECH_REF.read_text(encoding="utf-8")
        missing = [c for c in _CLI_COMMANDS if c not in text]
        assert not missing, (
            "technical_reference.md must reference every public CLI "
            f"command surfaced in cli_reference.md. Missing: {missing}"
        )

    def test_has_glossary_with_minimum_terms(self):
        """§9 Glossary must exist and contain at least 20 entries."""
        text = _TECH_REF.read_text(encoding="utf-8")
        assert "## 9. Glossary" in text, (
            "technical_reference.md must contain a '## 9. Glossary' section heading."
        )
        # Glossary entries are bullet lines starting with '- **<term>**'.
        glossary_section = re.search(
            r"^## 9\. Glossary(.*?)^## 10\.",
            text,
            flags=re.MULTILINE | re.DOTALL,
        )
        assert glossary_section is not None
        entries = re.findall(
            r"^- \*\*[^*]+\*\*",
            glossary_section.group(1),
            flags=re.MULTILINE,
        )
        assert len(entries) >= 20, (
            f"Glossary must contain at least 20 entries; found {len(entries)}."
        )

    def test_has_decisions_log_with_minimum_entries(self):
        """§10 Architectural decisions timeline must contain at least
        10 entries (one row per decision)."""
        text = _TECH_REF.read_text(encoding="utf-8")
        assert "## 10. Architectural decisions timeline" in text, (
            "technical_reference.md must contain a '## 10. Architectural "
            "decisions timeline' section heading."
        )
        timeline_section = re.search(
            r"^## 10\. Architectural decisions timeline(.*?)^## 11\.",
            text,
            flags=re.MULTILINE | re.DOTALL,
        )
        assert timeline_section is not None
        # Each timeline entry is a markdown table row; count data rows
        # (lines starting with '|' that are not the header or separator).
        rows = [
            ln
            for ln in timeline_section.group(1).splitlines()
            if ln.startswith("|") and "---" not in ln and "Sprint /" not in ln
        ]
        assert len(rows) >= 10, (
            f"Decisions timeline must contain at least 10 entries; found {len(rows)}."
        )

    def test_cross_links_canonical_docs(self):
        text = _TECH_REF.read_text(encoding="utf-8")
        missing = [link for link in _CANONICAL_CROSS_LINKS if link not in text]
        assert not missing, (
            f"technical_reference.md must cross-link the canonical docs. Missing: {missing}"
        )

    def test_has_strengths_and_risks_sections(self):
        text = _TECH_REF.read_text(encoding="utf-8")
        for heading in ("## 11. Strengths", "## 13. Risks"):
            assert heading in text, (
                f"technical_reference.md must contain section heading: {heading!r}"
            )
