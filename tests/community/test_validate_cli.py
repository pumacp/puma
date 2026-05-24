"""Tests for ``puma community validate`` (Pydantic + jsonschema + --strict + drift)."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import httpx
import respx
from typer.testing import CliRunner

from puma.community._community_app import community_app
from puma.community.validate_cli import BUNDLED_SCHEMA
from tests.community.conftest import SAMPLE_VALID_PAYLOAD

runner = CliRunner()
_DRIFT_META_URL = (
    "https://api.github.com/repos/pumacp/puma-community/contents/schema/submission.v1.json"
)


def _write(path: Path, payload: dict[str, Any]) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_valid_submission_with_explicit_schema_exits_zero(tmp_path: Path) -> None:
    sub = _write(tmp_path / "sub.json", SAMPLE_VALID_PAYLOAD)
    result = runner.invoke(community_app, ["validate", str(sub), "--schema", str(BUNDLED_SCHEMA)])
    assert result.exit_code == 0, result.output
    assert "valid" in result.output


def test_missing_required_field_exits_one(tmp_path: Path) -> None:
    bad = copy.deepcopy(SAMPLE_VALID_PAYLOAD)
    del bad["submitter"]
    sub = _write(tmp_path / "sub.json", bad)
    result = runner.invoke(community_app, ["validate", str(sub), "--schema", str(BUNDLED_SCHEMA)])
    assert result.exit_code == 1
    assert "submitter" in result.output.lower()


def test_strict_filename_mismatch_exits_one(tmp_path: Path) -> None:
    payload = copy.deepcopy(SAMPLE_VALID_PAYLOAD)
    payload["submission_id"] = "11111111-1111-1111-1111-111111111111"
    sub = _write(tmp_path / "different.json", payload)
    result = runner.invoke(
        community_app, ["validate", str(sub), "--schema", str(BUNDLED_SCHEMA), "--strict"]
    )
    assert result.exit_code == 1
    assert "filename" in result.output.lower()


def test_strict_n_instances_mismatch_exits_one(tmp_path: Path) -> None:
    sub = _write(tmp_path / "x.json", SAMPLE_VALID_PAYLOAD)  # n_instances=200
    (tmp_path / "x.predictions.jsonl").write_text(
        '{"instance_id":"a"}\n{"instance_id":"b"}\n', encoding="utf-8"
    )
    result = runner.invoke(
        community_app, ["validate", str(sub), "--schema", str(BUNDLED_SCHEMA), "--strict"]
    )
    assert result.exit_code == 1
    assert "n_instances" in result.output


def test_json_output_parseable(tmp_path: Path) -> None:
    sub = _write(tmp_path / "sub.json", SAMPLE_VALID_PAYLOAD)
    result = runner.invoke(
        community_app, ["validate", str(sub), "--schema", str(BUNDLED_SCHEMA), "--json"]
    )
    assert result.exit_code == 0, result.output
    parsed = json.loads(result.output)
    assert parsed[0]["valid"] is True


def test_schema_not_found_exits_two(tmp_path: Path) -> None:
    sub = _write(tmp_path / "sub.json", SAMPLE_VALID_PAYLOAD)
    result = runner.invoke(
        community_app, ["validate", str(sub), "--schema", str(tmp_path / "nope.json")]
    )
    assert result.exit_code == 2


@respx.mock
def test_schema_drift_warns(tmp_path: Path) -> None:
    # Default (no --schema) path triggers the online drift check.
    respx.get(_DRIFT_META_URL).mock(
        return_value=httpx.Response(200, json={"download_url": "https://raw.example/schema.json"})
    )
    respx.get("https://raw.example/schema.json").mock(
        return_value=httpx.Response(200, content=b"{}")  # differs from bundled -> drift
    )
    sub = _write(tmp_path / "sub.json", SAMPLE_VALID_PAYLOAD)
    result = runner.invoke(community_app, ["validate", str(sub)])
    assert result.exit_code == 0, result.output
    assert "drift" in result.stderr.lower()


@respx.mock
def test_schema_drift_network_failure_is_silent(tmp_path: Path) -> None:
    respx.get(_DRIFT_META_URL).mock(side_effect=httpx.ConnectError("offline"))
    sub = _write(tmp_path / "sub.json", SAMPLE_VALID_PAYLOAD)
    result = runner.invoke(community_app, ["validate", str(sub)])
    assert result.exit_code == 0, result.output
    assert "drift" not in result.stderr.lower()
