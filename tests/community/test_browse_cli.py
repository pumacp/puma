"""Tests for ``puma community browse`` (respx-mocked GitHub Contents API)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
from typer.testing import CliRunner

from puma.community import browse_cli  # noqa: F401 — registers the command
from puma.community._community_app import community_app

INDEX_URL = "https://api.github.com/repos/pumacp/puma-community/contents/submissions"
runner = CliRunner()


@pytest.fixture(autouse=True)
def _isolated_creds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # No credential file -> CredentialStore.get returns None -> no Bearer header.
    monkeypatch.setenv("PUMA_CONFIG_DIR", str(tmp_path / "cfg"))


def _entry(name: str, download_url: str) -> dict[str, Any]:
    return {"name": name, "type": "file", "download_url": download_url}


def _submission(
    *,
    sid: str,
    scenario: str = "triage_jira",
    model: str = "qwen2.5:3b",
    strategy: str = "zero_shot",
    submitted_at: str = "2026-05-20T10:00:00+00:00",
    alias: str = "alice",
    f1: float | None = 0.58,
    mae: float | None = None,
    co2: float = 1.0,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    if f1 is not None:
        metrics["f1_macro"] = f1
    if mae is not None:
        metrics["mae"] = mae
    return {
        "submission_id": sid,
        "submitted_at": submitted_at,
        "run_metadata": {"scenario": scenario, "model": model, "strategy": strategy},
        "metrics": metrics,
        "sustainability": {"co2_grams_total": co2},
        "submitter": {"name_or_alias": alias},
    }


def _mock_index(*submissions: dict[str, Any]) -> None:
    entries = []
    for sub in submissions:
        url = f"https://raw.example/{sub['submission_id']}.json"
        entries.append(_entry(f"{sub['submission_id']}.json", url))
        respx.get(url).mock(return_value=httpx.Response(200, json=sub))
    respx.get(INDEX_URL).mock(return_value=httpx.Response(200, json=entries))


@respx.mock
def test_empty_index_exits_zero_with_message() -> None:
    respx.get(INDEX_URL).mock(return_value=httpx.Response(200, json=[]))
    result = runner.invoke(community_app, ["browse"])
    assert result.exit_code == 0
    assert "No submissions match" in result.stdout


@respx.mock
def test_single_submission_renders_table() -> None:
    _mock_index(_submission(sid="sub-1", model="qwen2.5:3b"))
    result = runner.invoke(community_app, ["browse"])
    assert result.exit_code == 0
    # Rich truncates cells at the 80-col test width; assert the table title
    # and submission_id render (cell content is covered by the --json tests).
    assert "PUMA Community submissions" in result.stdout
    assert "sub-1" in result.stdout


@respx.mock
def test_last_n_keeps_most_recent() -> None:
    _mock_index(
        _submission(sid="old", submitted_at="2026-05-01T00:00:00+00:00"),
        _submission(sid="mid", submitted_at="2026-05-10T00:00:00+00:00"),
        _submission(sid="new", submitted_at="2026-05-20T00:00:00+00:00"),
    )
    result = runner.invoke(community_app, ["browse", "--last-n", "2", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    ids = [row["submission_id"] for row in payload]
    assert ids == ["new", "mid"]


@respx.mock
def test_scenario_filter() -> None:
    _mock_index(
        _submission(sid="triage", scenario="triage_jira"),
        _submission(sid="effort", scenario="effort_tawos", f1=None, mae=4.2),
    )
    result = runner.invoke(community_app, ["browse", "--scenario", "effort", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert [r["submission_id"] for r in payload] == ["effort"]


@respx.mock
def test_model_substring_filter() -> None:
    _mock_index(
        _submission(sid="a", model="qwen2.5:3b"),
        _submission(sid="b", model="mistral:7b"),
    )
    result = runner.invoke(community_app, ["browse", "--model", "mistral", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert [r["submission_id"] for r in payload] == ["b"]


@respx.mock
def test_json_output_is_valid_json() -> None:
    _mock_index(_submission(sid="sub-1"))
    result = runner.invoke(community_app, ["browse", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.stdout)
    assert parsed[0]["submission_id"] == "sub-1"


@respx.mock
def test_anonymous_sends_no_bearer_header() -> None:
    route = respx.get(INDEX_URL).mock(return_value=httpx.Response(200, json=[]))
    result = runner.invoke(community_app, ["browse", "--anonymous"])
    assert result.exit_code == 0
    request = route.calls.last.request
    assert "Authorization" not in request.headers


@respx.mock
def test_rate_limited_exits_two() -> None:
    respx.get(INDEX_URL).mock(
        return_value=httpx.Response(403, headers={"X-RateLimit-Remaining": "0"}, json={})
    )
    result = runner.invoke(community_app, ["browse"])
    assert result.exit_code == 2
    assert "rate limit" in result.stdout.lower()


@respx.mock
def test_api_unreachable_exits_one() -> None:
    respx.get(INDEX_URL).mock(side_effect=httpx.ConnectError("boom"))
    result = runner.invoke(community_app, ["browse"])
    assert result.exit_code == 1
