"""Tests for ``puma community pull`` (respx-mocked index + filesystem output)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
from typer.testing import CliRunner

from puma.community import pull_cli  # noqa: F401 — registers the command
from puma.community._community_app import community_app

INDEX_URL = "https://api.github.com/repos/pumacp/puma-community/contents/submissions"
runner = CliRunner()


@pytest.fixture(autouse=True)
def _isolated_creds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PUMA_CONFIG_DIR", str(tmp_path / "cfg"))


def _submission(
    sid: str, scenario: str = "triage_jira", model: str = "qwen2.5:3b"
) -> dict[str, Any]:
    return {
        "submission_id": sid,
        "run_metadata": {"scenario": scenario, "model": model, "strategy": "zero_shot"},
        "metrics": {"f1_macro": 0.58},
        "sustainability": {"co2_grams_total": 1.0},
        "submitter": {"name_or_alias": "alice"},
    }


def _mock_index(*subs: dict[str, Any]) -> None:
    entries = []
    for sub in subs:
        url = f"https://raw.example/{sub['submission_id']}.json"
        entries.append(
            {"name": f"{sub['submission_id']}.json", "type": "file", "download_url": url}
        )
        respx.get(url).mock(return_value=httpx.Response(200, json=sub))
    respx.get(INDEX_URL).mock(return_value=httpx.Response(200, json=entries))


@respx.mock
def test_jsonl_output_writes_one_line_per_submission(tmp_path: Path) -> None:
    _mock_index(_submission("a"), _submission("b"), _submission("c"))
    out = tmp_path / "cache"
    result = runner.invoke(community_app, ["pull", "--output", str(out), "--format", "jsonl"])
    assert result.exit_code == 0, result.stdout
    lines = (out / "all.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3
    assert all(json.loads(line)["submission_id"] for line in lines)


@respx.mock
def test_csv_output_flattens_nested_dicts(tmp_path: Path) -> None:
    _mock_index(_submission("a"))
    out = tmp_path / "cache"
    result = runner.invoke(community_app, ["pull", "--output", str(out), "--format", "csv"])
    assert result.exit_code == 0, result.stdout
    text = (out / "all.csv").read_text(encoding="utf-8")
    assert "submission_id" in text
    # nested run_metadata is JSON-encoded into a single cell
    assert "triage_jira" in text


@respx.mock
def test_raw_output_writes_separate_files(tmp_path: Path) -> None:
    _mock_index(_submission("a"), _submission("b"), _submission("c"))
    out = tmp_path / "cache"
    result = runner.invoke(community_app, ["pull", "--output", str(out), "--format", "raw"])
    assert result.exit_code == 0, result.stdout
    files = sorted(p.name for p in (out / "raw").glob("*.json"))
    assert files == ["a.json", "b.json", "c.json"]


@respx.mock
def test_parquet_output(tmp_path: Path) -> None:
    pytest.importorskip("pyarrow")
    _mock_index(_submission("a"), _submission("b"))
    out = tmp_path / "cache"
    result = runner.invoke(community_app, ["pull", "--output", str(out), "--format", "parquet"])
    assert result.exit_code == 0, result.stdout
    assert (out / "all.parquet").is_file()


@respx.mock
def test_filter_and_expression(tmp_path: Path) -> None:
    _mock_index(
        _submission("keep", scenario="triage_jira", model="qwen2.5:3b"),
        _submission("drop1", scenario="effort_tawos", model="qwen2.5:3b"),
        _submission("drop2", scenario="triage_jira", model="mistral:7b"),
    )
    out = tmp_path / "cache"
    result = runner.invoke(
        community_app,
        [
            "pull",
            "--output",
            str(out),
            "--format",
            "raw",
            "--filter",
            "scenario=triage_jira AND model_tag=qwen2.5:3b",
        ],
    )
    assert result.exit_code == 0, result.stdout
    files = [p.name for p in (out / "raw").glob("*.json")]
    assert files == ["keep.json"]


@respx.mock
def test_unknown_filter_key_exits_three(tmp_path: Path) -> None:
    _mock_index(_submission("a"))
    result = runner.invoke(
        community_app,
        ["pull", "--output", str(tmp_path / "c"), "--filter", "bogus=value"],
    )
    assert result.exit_code == 3
    assert "Unknown filter key" in result.stdout


@respx.mock
def test_limit_applies_after_filter(tmp_path: Path) -> None:
    _mock_index(_submission("a"), _submission("b"), _submission("c"))
    out = tmp_path / "cache"
    result = runner.invoke(
        community_app, ["pull", "--output", str(out), "--format", "raw", "--limit", "2"]
    )
    assert result.exit_code == 0, result.stdout
    assert len(list((out / "raw").glob("*.json"))) == 2


def test_unknown_format_exits_two(tmp_path: Path) -> None:
    result = runner.invoke(
        community_app, ["pull", "--output", str(tmp_path / "c"), "--format", "xml"]
    )
    assert result.exit_code == 2
