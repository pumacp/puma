"""Assert the public Pages docs expose no sensitive references (S12 Phase E).

Scope = the pages published by the mkdocs nav. Private endpoints, secret env-var
names, and maintainer-operational references must not appear on the public site.
The publication workflow must present Docker as the supported default runtime.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_DOCS = Path(__file__).resolve().parents[2] / "docs"

# Expanded in S12.17 from the v4.0.0 minimal 6-page surface to the full
# 24-page mkdocs nav (D30 resolution).
_PUBLIC_DOCS = [
    "index.md",
    "overview.md",
    "user_guide.md",
    "cli_reference.md",
    "troubleshooting.md",
    "architecture.md",
    "scenarios_reference.md",
    "metrics_reference.md",
    "sustainability.md",
    "adding_models.md",
    "adding_scenarios.md",
    "publication_workflow.md",
    "knowledge_graph.md",
    "TESTING.md",
    "baseline_inventory.md",
    "baseline_references.md",
    "CATALOG_HISTORY.md",
    "CROSS_ARCH_REPRODUCIBILITY.md",
    "HARDWARE.md",
    "MACOS_NOTES.md",
    "RELEASES/v3.1.0.md",
    "RELEASES/v3.0.0.md",
    "PROJECT_TECHNICAL_CLOSURE.md",
    "open_questions.md",
]

_SENSITIVE = [
    "private endpoint",
    "puma-verifier",
    "HF_TOKEN",
    "ZENODO_TOKEN",
    "KAGGLE_KEY",
    "DISCORD_WEBHOOK",
    "TELEGRAM_BOT_TOKEN",
]

_MAINTAINER_PHRASES = ["pumacp namespace", "namespace pumacp", "write scope", "token scope"]


@pytest.mark.integration
class TestPagesNoSensitiveContent:
    def test_no_private_endpoint_refs_in_public_docs(self):
        offenders: list[str] = []
        for name in _PUBLIC_DOCS:
            text = (_DOCS / name).read_text(encoding="utf-8")
            for token in _SENSITIVE:
                if token.lower() in text.lower():
                    offenders.append(f"{name}: '{token}'")
        assert not offenders, f"Sensitive references in public docs: {offenders}"

    def test_no_maintainer_namespace_refs_in_public_docs(self):
        offenders: list[str] = []
        for name in _PUBLIC_DOCS:
            text = (_DOCS / name).read_text(encoding="utf-8").lower()
            for phrase in _MAINTAINER_PHRASES:
                if phrase in text:
                    offenders.append(f"{name}: '{phrase}'")
        assert not offenders, f"Maintainer namespace/scope phrases in public docs: {offenders}"

    def test_publication_workflow_is_docker_aware(self):
        text = (_DOCS / "publication_workflow.md").read_text(encoding="utf-8")
        m = re.search(r"## Prerequisites\n(.*?)\n## ", text, re.S)
        assert m, "Prerequisites section not found in publication_workflow.md"
        assert "docker" in m.group(1).lower(), "Prerequisites section does not mention Docker"
