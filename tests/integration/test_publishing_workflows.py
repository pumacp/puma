"""Assert the PyPI + GHCR publishing workflows and PyPI metadata are well-formed.

PyYAML maps a bare ``on:`` key to the boolean ``True`` (YAML 1.1), so the helper
normalizes it back to ``"on"`` before assertions. GitHub Actions parses ``on:``
correctly regardless.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
import yaml

_ROOT = Path(__file__).resolve().parents[2]
_PYPI_WF = _ROOT / ".github" / "workflows" / "publish-pypi.yml"
_DOCKER_WF = _ROOT / ".github" / "workflows" / "publish-docker.yml"
_PYPROJECT = _ROOT / "pyproject.toml"


def _load_workflow(path: Path) -> dict:
    wf = yaml.safe_load(path.read_text(encoding="utf-8"))
    wf["on"] = wf.get("on", wf.get(True))  # normalize the YAML on/True quirk
    return wf


@pytest.mark.integration
class TestPublishingWorkflows:
    def test_pypi_workflow_yaml_valid(self):
        wf = _load_workflow(_PYPI_WF)
        assert "build" in wf["jobs"]
        assert "publish-pypi" in wf["jobs"]
        assert wf["on"]["push"]["tags"] == ["v*"]
        assert "workflow_dispatch" in wf["on"]

    def test_docker_workflow_yaml_valid(self):
        wf = _load_workflow(_DOCKER_WF)
        assert "build-and-push" in wf["jobs"]
        assert wf["on"]["push"]["tags"] == ["v*"]
        perms = wf["jobs"]["build-and-push"]["permissions"]
        assert perms.get("packages") == "write"

    def test_pyproject_has_pypi_metadata(self):
        cfg = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
        project = cfg["project"]
        assert project["name"]
        assert project["description"]
        assert project["license"]
        assert project["readme"] == "README.md"
        assert "classifiers" in project
        assert len(project["classifiers"]) >= 5
