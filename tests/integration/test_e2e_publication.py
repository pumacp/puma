"""End-to-end publication-pipeline regression test (US-12.5).

Exercises the full pipeline on a small *real* run:

    runner -> share-results (--dry-run) -> community CLI validate + verify-hash

This guards against recurrence of D24/D25/D26 — the integration gaps Sprint 11'
(S11'.10.a) surfaced, where component-level unit tests at 80-89% coverage on the
community CLI did not detect that canonical runner output could not feed
share-results. A single end-to-end test with real artifacts would have caught
all three immediately; this is that test.

Marked ``@pytest.mark.ollama`` + ``@pytest.mark.e2e`` so it is excluded from the
default ``-m "not ollama"`` suite and selectable via ``-m e2e``.

The predictions JSONL that ``verify-hash`` consumes is produced by
``share-results --dry-run`` itself (the D27 exporter, closed in S12.2), so this
test consumes the real artifacts end-to-end with no DB stand-in.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

# Repo root: tests/integration/test_e2e_publication.py -> parents[2].
_REPO_ROOT = Path(__file__).resolve().parents[2]

# 10-instance smoke spec (lives in tmp_path, never committed). Mirrors
# specs/runs/baseline_triage.yaml with sample_size=10 and codecarbon enabled
# (the D25 convention) so share-results has an emissions record to build from.
_SMOKE_SPEC = """\
id: e2e_publication_smoke_v1
description: "E2E publication-pipeline smoke (US-12.5): triage_jira x qwen2.5:3b x contextual-anchoring x 10 instances."
scenario: triage_jira
sample_size: 10
models:
  - qwen2.5:3b
adaptation:
  strategy: [contextual-anchoring]
  cot: [false]
inference:
  temperature: 0.0
  seed: 42
  max_tokens: 256
  logprobs: false
perturbations: []
metrics:
  - f1_macro
  - latency_p95
sustainability:
  codecarbon: true
repeat: 1
"""

_RUN_ID_RE = re.compile(r"run_id=(\S+)")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _run_cli(args: list[str], *, env: dict[str, str] | None = None, timeout: int = 240):
    """Run ``puma <args>`` from the repo root, capturing output."""
    return subprocess.run(
        ["puma", *args],
        cwd=str(_REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _assert_ok(proc: subprocess.CompletedProcess, label: str) -> None:
    assert proc.returncode == 0, (
        f"{label} exited {proc.returncode}\n"
        f"--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}"
    )


@pytest.mark.ollama
@pytest.mark.e2e
def test_e2e_publication_pipeline(tmp_path):
    """Full pipeline on a real 10-instance run; fails loudly on any step.

    Runs ~10 instances of baseline_triage to stay well under ~60s on gpu-entry
    while exercising every real component (no hand-crafted Run or
    ProfileSnapshot rows).
    """
    # 1. Compose the smoke spec.
    spec_path = tmp_path / "e2e_publication_smoke.yaml"
    spec_path.write_text(_SMOKE_SPEC, encoding="utf-8")

    # 2. Real run against Ollama (OLLAMA_HOST is provided by the environment).
    run_proc = _run_cli(["run", str(spec_path)], timeout=240)
    _assert_ok(run_proc, "puma run")
    combined = run_proc.stdout + run_proc.stderr
    run_ids = _RUN_ID_RE.findall(combined)
    assert run_ids, f"could not parse run_id from puma run output:\n{combined}"
    run_id = run_ids[-1]

    # 3. share-results --dry-run -> BOTH the submission JSON and the predictions
    #    JSONL (the D27 exporter) in an isolated temp dir.
    submissions_dir = tmp_path / "submissions"
    env = {
        **os.environ,
        "PUMA_DRY_RUN_DIR": str(submissions_dir),
        "PUMA_DRY_RUN_OVERWRITE": "1",
    }
    share_proc = _run_cli(
        ["share-results", "--dry-run", "--run-id", run_id, "-y"],
        env=env,
        timeout=120,
    )
    _assert_ok(share_proc, "puma share-results --dry-run")
    submissions = sorted(submissions_dir.glob("*.json"))
    assert len(submissions) == 1, (
        f"expected exactly one submission JSON, found {submissions}\n"
        f"--- stdout ---\n{share_proc.stdout}"
    )
    submission_path = submissions[0]

    # 4. The D27 exporter wrote the predictions JSONL next to the submission.
    preds_path = submission_path.parent / f"{submission_path.stem}.predictions.jsonl"
    assert preds_path.is_file(), (
        f"share-results did not emit {preds_path.name}\n--- stdout ---\n{share_proc.stdout}"
    )

    # 5. Schema validation (strict also checks filename + n_instances vs rows).
    validate_proc = _run_cli(
        ["community", "validate", str(submission_path), "--strict"],
        timeout=120,
    )
    _assert_ok(validate_proc, "puma community validate --strict")

    # 6. Integrity round trip: recompute the hash locally and compare.
    verify_proc = _run_cli(
        [
            "community",
            "verify-hash",
            str(submission_path),
            "--predictions",
            str(preds_path),
        ],
        timeout=120,
    )
    _assert_ok(verify_proc, "puma community verify-hash")

    # 7. Assert the previously-missing fields are present (D24/D25/D26).
    payload = json.loads(submission_path.read_text(encoding="utf-8"))
    hardware = payload["hardware_profile"]
    assert hardware["profile_id"], "D24: hardware_profile.profile_id must be non-null"
    assert int(hardware["cpu_cores"]) > 0, "D26: hardware_profile.cpu_cores must be > 0"
    declared_hash = str(payload["integrity"]["predictions_summary_hash"])
    assert _SHA256_RE.match(declared_hash), f"integrity hash is not sha256 hex: {declared_hash!r}"
    assert payload["sustainability"]["energy_kwh_total"] is not None, (
        "D25: sustainability emissions must be present"
    )
    assert payload["puma_version"] != "2.0.0-dev", "D26: puma_version must be dynamic"

    # The D27 exporter's JSONL row count matches the declared n_instances.
    n_jsonl = sum(1 for line in preds_path.read_text(encoding="utf-8").splitlines() if line.strip())
    assert n_jsonl == int(payload["run_metadata"]["n_instances"]), (
        f"predictions JSONL has {n_jsonl} rows but submission declares "
        f"n_instances={payload['run_metadata']['n_instances']}"
    )
