"""Tests for ``puma community verify-hash`` (local + D23-aware --remote)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from puma.community import verify_cli
from puma.community._community_app import community_app
from puma.community.verify_cli import hash_predictions_jsonl

runner = CliRunner()

_PRED_ROWS = [
    {"instance_id": "i1", "predicted_label": "L0", "predicted_value": 0.5, "prompt_hash": "ph0"},
    {"instance_id": "i2", "predicted_label": "L1", "predicted_value": 0.7, "prompt_hash": "ph1"},
    {"instance_id": "i3", "predicted_label": "L2", "predicted_value": 0.9, "prompt_hash": "ph2"},
]


def _write_predictions(path: Path) -> str:
    path.write_text(
        "\n".join(json.dumps(r) for r in _PRED_ROWS) + "\n",
        encoding="utf-8",
    )
    return hash_predictions_jsonl(path)


def _write_submission(sub_path: Path, *, declared: str, raw_url: str | None = None) -> None:
    payload: dict[str, Any] = {"integrity": {"predictions_summary_hash": declared}}
    if raw_url is not None:
        payload["raw_predictions_url"] = raw_url
    sub_path.write_text(json.dumps(payload), encoding="utf-8")


def _setup(tmp_path: Path, *, tamper: bool = False, raw_url: str | None = None) -> Path:
    preds = tmp_path / "sub.predictions.jsonl"
    digest = _write_predictions(preds)
    declared = ("b" * 64) if tamper else digest
    sub = tmp_path / "sub.json"
    _write_submission(sub, declared=declared, raw_url=raw_url)
    return sub


# ── local-only ────────────────────────────────────────────────────────────


def test_local_match_verified(tmp_path: Path) -> None:
    sub = _setup(tmp_path)
    result = runner.invoke(community_app, ["verify-hash", str(sub)])
    assert result.exit_code == 0, result.output
    assert "verified" in result.output


def test_local_mismatch_exits_one(tmp_path: Path) -> None:
    sub = _setup(tmp_path, tamper=True)
    result = runner.invoke(community_app, ["verify-hash", str(sub)])
    assert result.exit_code == 1
    assert "mismatch" in result.output


def test_predictions_missing_exits_two(tmp_path: Path) -> None:
    sub = tmp_path / "sub.json"
    _write_submission(sub, declared="a" * 64)
    result = runner.invoke(community_app, ["verify-hash", str(sub)])
    assert result.exit_code == 2


# ── --remote (D23-aware) ────────────────────────────────────────────────────


def test_remote_no_url_local_verified_exits_zero_with_d23_note(tmp_path: Path) -> None:
    sub = _setup(tmp_path)  # no raw_predictions_url
    result = runner.invoke(community_app, ["verify-hash", str(sub), "--remote"])
    assert result.exit_code == 0, result.output
    assert "D23" in result.stderr
    assert "schema v1.0.0" in result.stderr


def test_remote_no_url_local_mismatch_exits_one(tmp_path: Path) -> None:
    sub = _setup(tmp_path, tamper=True)
    result = runner.invoke(community_app, ["verify-hash", str(sub), "--remote"])
    assert result.exit_code == 1


def test_remote_missing_hf_token_exits_three(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("HF_TOKEN", raising=False)
    sub = _setup(tmp_path, raw_url="https://example/preds.jsonl")
    result = runner.invoke(community_app, ["verify-hash", str(sub), "--remote"])
    assert result.exit_code == 3
    assert "HF_TOKEN" in result.stderr


def test_remote_verified_and_local_verified_exits_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HF_TOKEN", "hf_" + "x" * 36)
    sub = _setup(tmp_path, raw_url="https://example/preds.jsonl")
    with patch.object(verify_cli, "_call_verifier", return_value={"status": "verified"}):
        result = runner.invoke(community_app, ["verify-hash", str(sub), "--remote"])
    assert result.exit_code == 0, result.output
    assert "verified" in result.output


def test_remote_mismatch_but_local_verified_is_d23_warned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HF_TOKEN", "hf_" + "x" * 36)
    sub = _setup(tmp_path, raw_url="https://example/preds.jsonl")
    with patch.object(verify_cli, "_call_verifier", return_value={"status": "mismatch"}):
        result = runner.invoke(community_app, ["verify-hash", str(sub), "--remote"])
    assert result.exit_code == 0, result.output
    assert "verified-local-only (D23 warned)" in result.output
    assert "D23" in result.stderr


def test_remote_exception_falls_back_to_local(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HF_TOKEN", "hf_" + "x" * 36)
    sub = _setup(tmp_path, raw_url="https://example/preds.jsonl")
    with patch.object(verify_cli, "_call_verifier", side_effect=RuntimeError("space down")):
        result = runner.invoke(community_app, ["verify-hash", str(sub), "--remote"])
    assert result.exit_code == 0  # local verified
    assert "Falling back" in result.stderr
