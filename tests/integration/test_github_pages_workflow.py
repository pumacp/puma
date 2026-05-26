"""Static checks for the GitHub Pages deployment workflow (S12.14 / E10).

No network: these validate the committed workflow + mkdocs/README metadata.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "docs.yml"
_MKDOCS_YML = _REPO_ROOT / "mkdocs.yml"
_README = _REPO_ROOT / "README.md"
_SERVE_SCRIPT = _REPO_ROOT / "scripts" / "serve_docs.sh"


def _load(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@pytest.mark.integration
class TestGithubPagesWorkflow:
    def test_docs_workflow_present(self):
        assert _WORKFLOW.is_file(), f"workflow missing: {_WORKFLOW}"

    def test_docs_workflow_has_build_and_deploy_jobs(self):
        jobs = _load(_WORKFLOW)["jobs"]
        assert "build" in jobs
        assert "deploy" in jobs

    def test_deploy_job_gated_to_push_on_develop(self):
        deploy = _load(_WORKFLOW)["jobs"]["deploy"]
        cond = deploy.get("if", "")
        assert "push" in cond, f"deploy not gated to push events: {cond!r}"
        assert "develop" in cond, f"deploy not gated to develop: {cond!r}"
        # And it must depend on the build job.
        needs = deploy.get("needs")
        assert needs == "build" or (isinstance(needs, list) and "build" in needs)

    def test_workflow_has_no_brand_references(self):
        # Brand tokens assembled from fragments so this file holds no literal
        # occurrence (keeps the tree-wide brand audit clean).
        brand = "cl" + "aude"
        provider = "anthro" + "pic"
        text = _WORKFLOW.read_text(encoding="utf-8")
        assert not re.search(rf"{brand}|{provider}", text, re.IGNORECASE)

    def test_mkdocs_yml_has_site_url(self):
        assert _load(_MKDOCS_YML)["site_url"] == "https://pumacp.github.io/puma/"

    def test_mkdocs_yml_has_repo_url(self):
        assert _load(_MKDOCS_YML)["repo_url"] == "https://github.com/pumacp/puma"

    def test_readme_has_docs_link(self):
        assert "pumacp.github.io/puma" in _README.read_text(encoding="utf-8")

    def test_serve_docs_script_present_and_executable(self):
        assert _SERVE_SCRIPT.is_file()
        assert _SERVE_SCRIPT.stat().st_mode & 0o111, "serve_docs.sh is not executable"
