"""End-to-end publication-demo test (S12.12 / E5).

Runs scripts/publication_demo.sh against real Ollama on the small demo spec and
checks the produced package. Marked ``ollama`` (needs a live model).
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEMO_SCRIPT = _REPO_ROOT / "scripts" / "publication_demo.sh"
_REQUIRED_KEYS = (
    "submitter",
    "puma_version",
    "run_metadata",
    "hardware_profile",
    "metrics",
    "sustainability",
    "integrity",
)


@pytest.fixture(scope="module")
def demo_package(tmp_path_factory):
    out = tmp_path_factory.mktemp("pub_demo")
    env = {
        **os.environ,
        "PUMA_DEMO_OUT": str(out),
        "PUMA_DEMO_SPEC": "specs/runs/demo_publication.yaml",
    }
    result = subprocess.run(
        ["bash", str(_DEMO_SCRIPT)],
        cwd=_REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    return out, result


@pytest.mark.ollama
class TestPublicationDemo:
    def test_publication_demo_produces_package(self, demo_package):
        out, result = demo_package
        assert result.returncode == 0, (
            f"demo failed (exit {result.returncode}):\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
        assert "✓ Demo complete." in result.stdout

        submission = out / "submission.json"
        predictions = out / "predictions.jsonl"
        assert submission.is_file(), "submission.json not produced"
        assert predictions.is_file(), "predictions.jsonl not produced"

        payload = json.loads(submission.read_text(encoding="utf-8"))
        for key in _REQUIRED_KEYS:
            assert key in payload, f"submission.json missing top-level key: {key}"
        assert payload["integrity"].get("predictions_summary_hash"), "no declared hash"

        lines = [ln for ln in predictions.read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert len(lines) >= 1, "predictions.jsonl is empty"
        for line in lines:
            json.loads(line)  # every line must be valid JSON

    def test_publication_demo_verifies_clean(self, demo_package):
        out, result = demo_package
        assert result.returncode == 0
        verify = subprocess.run(
            [
                "puma",
                "community",
                "verify-hash",
                str(out / "submission.json"),
                "--predictions",
                str(out / "predictions.jsonl"),
            ],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert verify.returncode == 0, (
            f"verify-hash failed (exit {verify.returncode}):\n{verify.stdout}\n{verify.stderr}"
        )
