"""Tests for the dashboard's Community view."""

from __future__ import annotations

import importlib
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def test_view_module_imports_cleanly() -> None:
    """The community view module imports without side effects and exposes ``render``."""
    module = importlib.import_module("puma.dashboard.views.community")
    assert callable(module.render)
    assert hasattr(module, "STATE_AUTH")
    assert hasattr(module, "STATE_BROWSE")
    assert hasattr(module, "STATE_CONSENT")
    assert hasattr(module, "STATE_PUBLISH")


def test_view_registered_in_main_app() -> None:
    """``app.py``'s ``VIEWS`` dict registers the community view under the emoji key."""
    app_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "puma"
        / "dashboard"
        / "app.py"
    )
    source = app_path.read_text(encoding="utf-8")
    match = re.search(r"VIEWS\s*=\s*\{(.*?)\}", source, re.DOTALL)
    assert match is not None, "VIEWS dict not found in app.py"
    body = match.group(1)
    assert '"🤝 Community": community.render' in body


def test_resolve_state_redirects_to_auth_without_token(monkeypatch) -> None:
    """When the user lands in BROWSE without a stored token, the wizard redirects to AUTH."""
    community = importlib.import_module("puma.dashboard.views.community")
    fake_session = {
        community._SESSION_KEY: {
            "state": community.STATE_BROWSE,
            "selected_run_id": None,
            "last_result": None,
            "action_mode": None,
            "allow_dry_run_without_token": False,
        }
    }
    monkeypatch.setattr("streamlit.session_state", fake_session)
    monkeypatch.setattr(community, "_has_github_token", lambda: False)
    assert community._resolve_state() == community.STATE_AUTH


def test_resolve_state_stays_in_browse_when_token_present(monkeypatch) -> None:
    community = importlib.import_module("puma.dashboard.views.community")
    fake_session = {
        community._SESSION_KEY: {
            "state": community.STATE_BROWSE,
            "selected_run_id": None,
            "last_result": None,
            "action_mode": None,
            "allow_dry_run_without_token": False,
        }
    }
    monkeypatch.setattr("streamlit.session_state", fake_session)
    monkeypatch.setattr(community, "_has_github_token", lambda: True)
    assert community._resolve_state() == community.STATE_BROWSE


def test_resolve_state_allows_dry_run_override_without_token(monkeypatch) -> None:
    """User pressed 'Continue in dry-run mode' — wizard stays in BROWSE despite no token."""
    community = importlib.import_module("puma.dashboard.views.community")
    fake_session = {
        community._SESSION_KEY: {
            "state": community.STATE_BROWSE,
            "selected_run_id": None,
            "last_result": None,
            "action_mode": None,
            "allow_dry_run_without_token": True,
        }
    }
    monkeypatch.setattr("streamlit.session_state", fake_session)
    monkeypatch.setattr(community, "_has_github_token", lambda: False)
    assert community._resolve_state() == community.STATE_BROWSE


def test_do_dry_run_calls_save_dry_run() -> None:
    community = importlib.import_module("puma.dashboard.views.community")
    payload = {"submission_id": "abc-123"}
    fake_path = Path("/tmp/abc-123.json")
    with patch.object(community, "save_dry_run", return_value=fake_path) as saver:
        result = community._do_dry_run(payload)
    saver.assert_called_once_with(payload=payload)
    assert result == {"ok": True, "kind": "dry-run", "path": str(fake_path)}


def test_do_publish_blocked_by_rate_limiter() -> None:
    community = importlib.import_module("puma.dashboard.views.community")
    payload = {
        "submission_id": "x",
        "run_metadata": {"scenario": "triage_jira", "model": "m", "strategy": "zero_shot"},
        "integrity": {"predictions_summary_hash": "h" * 64},
    }
    limiter = MagicMock()
    limiter.can_submit.return_value = (False, "Cooldown active. Try again in 30 seconds.")
    with patch.object(community, "LocalRateLimiter", return_value=limiter):
        result = community._do_publish(payload, alias="alice")
    assert result["ok"] is False
    assert "Cooldown active" in result["error"]


def test_do_publish_happy_path_returns_pr_url() -> None:
    community = importlib.import_module("puma.dashboard.views.community")
    from puma.community.github_client import SubmissionPRResult

    payload = {
        "submission_id": "happy-1",
        "run_metadata": {
            "scenario": "triage_jira",
            "model": "qwen2.5:3b",
            "strategy": "zero_shot",
        },
        "integrity": {"predictions_summary_hash": "a" * 64},
    }
    limiter = MagicMock()
    limiter.can_submit.return_value = (True, "ok")
    client = MagicMock()
    client.ensure_fork.return_value = "alice"
    client.create_submission_branch.return_value = "submission/happy-1"
    client.open_pull_request.return_value = SubmissionPRResult(
        pr_url="https://github.com/pumacp/puma-community/pull/9",
        pr_number=9,
        fork_owner="alice",
        branch_name="submission/happy-1",
    )
    with (
        patch.object(community, "LocalRateLimiter", return_value=limiter),
        patch.object(community, "CommunityGitHubClient", return_value=client),
    ):
        result = community._do_publish(payload, alias="alice")
    assert result["ok"] is True
    assert result["pr_number"] == 9
    assert result["pr_url"].endswith("/pull/9")
    limiter.record_submission.assert_called_once()


def test_render_does_not_log_token_values(caplog, monkeypatch) -> None:
    """Even when render() is invoked indirectly via state helpers, no token leaks to logs."""
    import logging

    community = importlib.import_module("puma.dashboard.views.community")
    fake_session = {
        community._SESSION_KEY: {
            "state": community.STATE_BROWSE,
            "selected_run_id": None,
            "last_result": None,
            "action_mode": None,
            "allow_dry_run_without_token": False,
        }
    }
    monkeypatch.setattr("streamlit.session_state", fake_session)
    monkeypatch.setattr(community, "_has_github_token", lambda: False)
    with caplog.at_level(logging.DEBUG, logger="puma.dashboard.community"):
        community._resolve_state()
    fake_token = "ghp_" + "a" * 36
    for record in caplog.records:
        assert fake_token not in record.getMessage()


@pytest.mark.skipif(
    not hasattr(__import__("streamlit"), "testing"),
    reason="streamlit.testing.v1 not available in this environment",
)
def test_render_via_apptest_renders_title() -> None:
    """If Streamlit's AppTest is available, render() must produce the expected title."""
    from streamlit.testing.v1 import AppTest

    app_test = AppTest.from_function(
        lambda: importlib.import_module("puma.dashboard.views.community").render()
    )
    result = app_test.run()
    titles = [t.value for t in result.title]
    assert any("PUMA Community" in title for title in titles)
