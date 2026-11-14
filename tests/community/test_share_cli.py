"""Tests for ``puma share-results``."""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from puma.community import share_cli
from puma.community.credentials import CredentialStore
from puma.community.share_cli import share_results_app

FAKE_GH_TOKEN = "ghp_" + "a" * 36


@pytest.fixture
def isolated_env(tmp_path: Path, monkeypatch):
    """Isolate config/cache/dry-run dirs and disable the cooldown for clean runs."""
    monkeypatch.setenv("PUMA_CONFIG_DIR", str(tmp_path / "puma-config"))
    monkeypatch.setenv("PUMA_CACHE_DIR", str(tmp_path / "puma-cache"))
    monkeypatch.setenv("PUMA_DRY_RUN_DIR", str(tmp_path / "puma-dry-run"))
    monkeypatch.setenv("PUMA_RATE_LIMIT_COOLDOWN_S", "0")
    return tmp_path


@pytest.fixture
def patched_session(populated_db, monkeypatch):
    """Route the share_cli's session_scope through the populated in-memory DB."""

    @contextmanager
    def fake_scope():
        session = populated_db()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    monkeypatch.setattr(share_cli, "session_scope", fake_scope)
    # The runs_query helpers also need the patched scope.
    from puma.community import runs_query

    monkeypatch.setattr(runs_query, "session_scope", fake_scope)
    return populated_db


@pytest.fixture
def cli(isolated_env, patched_session) -> CliRunner:
    return CliRunner()


def _store_github_token(isolated_env: Path) -> None:
    store = CredentialStore()
    store.set("github", FAKE_GH_TOKEN)


def test_empty_state_when_no_shareable_runs(isolated_env, monkeypatch) -> None:
    monkeypatch.setattr(share_cli, "list_shareable_runs", lambda **_: [])
    monkeypatch.setattr(share_cli, "get_run_summary", lambda _: None)
    runner = CliRunner()
    result = runner.invoke(share_results_app, ["--dry-run"])
    assert result.exit_code == 0
    assert "No shareable runs" in result.stdout


def test_dry_run_saves_payload_locally_and_exits_zero(cli: CliRunner, isolated_env) -> None:
    result = cli.invoke(
        share_results_app,
        [
            "--dry-run",
            "--yes",
            "--run-id",
            "run-A",
            "--submitter-alias",
            "alice_42",
        ],
    )
    assert result.exit_code == 0, result.stdout
    dry_dir = isolated_env / "puma-dry-run"
    saved = list(dry_dir.glob("*.json"))
    assert len(saved) == 1
    payload = json.loads(saved[0].read_text(encoding="utf-8"))
    assert payload["submitter"]["name_or_alias"] == "alice_42"
    assert payload["run_metadata"]["scenario"] == "effort_tawos"


def test_dry_run_does_not_call_github_client(cli: CliRunner, isolated_env) -> None:
    with patch("puma.community.share_cli.CommunityGitHubClient") as ghc:
        result = cli.invoke(
            share_results_app,
            [
                "--dry-run",
                "--yes",
                "--run-id",
                "run-A",
                "--submitter-alias",
                "alice_42",
            ],
        )
        assert result.exit_code == 0, result.stdout
        ghc.assert_not_called()


def test_publish_mode_opens_pull_request(cli: CliRunner, isolated_env) -> None:
    _store_github_token(isolated_env)
    fake_client = MagicMock()
    fake_client.authenticated_user_login.return_value = "alice"
    fake_client.ensure_fork.return_value = "alice"
    fake_client.create_submission_branch.return_value = "submission/x"

    from puma.community.github_client import SubmissionPRResult

    fake_client.open_pull_request.return_value = SubmissionPRResult(
        pr_url="https://github.com/pumacp/puma-community/pull/42",
        pr_number=42,
        fork_owner="alice",
        branch_name="submission/x",
    )
    with patch("puma.community.share_cli.CommunityGitHubClient", return_value=fake_client):
        result = cli.invoke(
            share_results_app,
            ["--yes", "--run-id", "run-A", "--submitter-alias", "alice_42"],
        )
    assert result.exit_code == 0, result.stdout
    assert "https://github.com/pumacp/puma-community/pull/42" in result.stdout
    fake_client.open_pull_request.assert_called_once()


def test_publish_mode_blocked_by_rate_limiter(cli: CliRunner, isolated_env) -> None:
    _store_github_token(isolated_env)
    fake_client = MagicMock()
    fake_client.authenticated_user_login.return_value = "alice"
    fake_limiter = MagicMock()
    fake_limiter.can_submit.return_value = (False, "Cooldown active. Try again in 30 seconds.")

    with (
        patch("puma.community.share_cli.CommunityGitHubClient", return_value=fake_client),
        patch("puma.community.share_cli.LocalRateLimiter", return_value=fake_limiter),
    ):
        result = cli.invoke(
            share_results_app,
            ["--yes", "--run-id", "run-A", "--submitter-alias", "alice_42"],
        )
    assert result.exit_code == 1
    assert "Cooldown active" in result.stdout
    fake_client.open_pull_request.assert_not_called()


def test_publish_mode_blocked_by_missing_github_token(cli: CliRunner) -> None:
    # No credential store entry; CommunityGitHubClient() will raise AuthenticationError.
    result = cli.invoke(
        share_results_app,
        ["--yes", "--run-id", "run-A", "--submitter-alias", "alice_42"],
    )
    assert result.exit_code == 1
    assert "puma auth login github" in result.stdout


def test_validation_failure_aborts_before_publish(cli: CliRunner, isolated_env) -> None:
    _store_github_token(isolated_env)
    fake_client = MagicMock()
    fake_client.authenticated_user_login.return_value = "alice"
    with (
        patch("puma.community.share_cli.CommunityGitHubClient", return_value=fake_client),
        patch(
            "puma.community.share_cli.is_safe_to_publish",
            return_value=(False, ["Anomalous timestamps: started_at is too old"]),
        ),
    ):
        result = cli.invoke(
            share_results_app,
            ["--yes", "--run-id", "run-A", "--submitter-alias", "alice_42"],
        )
    assert result.exit_code == 1
    assert "safety checks" in result.stdout.lower()
    fake_client.open_pull_request.assert_not_called()


def test_consent_declined_exits_zero_without_side_effects(cli: CliRunner, isolated_env) -> None:
    _store_github_token(isolated_env)
    fake_client = MagicMock()
    fake_client.authenticated_user_login.return_value = "alice"
    fake_limiter = MagicMock()
    with (
        patch("puma.community.share_cli.CommunityGitHubClient", return_value=fake_client),
        patch("puma.community.share_cli.LocalRateLimiter", return_value=fake_limiter),
        patch("puma.community.share_cli.save_dry_run") as saver,
    ):
        result = cli.invoke(
            share_results_app,
            ["--run-id", "run-A", "--submitter-alias", "alice_42"],
            input="n\n",
        )
    assert result.exit_code == 0
    assert "Aborted" in result.stdout
    saver.assert_not_called()
    fake_limiter.can_submit.assert_not_called()
    fake_client.open_pull_request.assert_not_called()


def test_run_id_not_found_exits_one(cli: CliRunner) -> None:
    result = cli.invoke(
        share_results_app,
        ["--dry-run", "--yes", "--run-id", "does-not-exist"],
    )
    assert result.exit_code == 1
    assert "not found" in result.stdout.lower()


def _publishing_client() -> MagicMock:
    from puma.community.github_client import SubmissionPRResult

    fake_client = MagicMock()
    fake_client.authenticated_user_login.return_value = "pumacp"
    fake_client.ensure_fork.return_value = "pumacp"
    fake_client.create_submission_branch.side_effect = lambda *, fork_owner, submission_id: (
        f"submission/{submission_id}"
    )
    fake_client.open_pull_request.side_effect = lambda **kw: SubmissionPRResult(
        pr_url="https://github.com/pumacp/puma-community/pull/9",
        pr_number=9,
        fork_owner=kw["fork_owner"],
        branch_name=kw["branch"],
    )
    return fake_client


def test_publish_mode_transport_failure_exits_one_with_github_error(
    cli: CliRunner, isolated_env
) -> None:
    """D40: a RetryError inside the client is mapped to GitHubError and rendered."""
    from puma.community.github_client import GitHubError

    _store_github_token(isolated_env)
    fake_client = _publishing_client()
    fake_client.ensure_fork.side_effect = GitHubError(
        "GitHub request failed (RetryError). Check connectivity and the API rate limit, then retry."
    )
    with patch("puma.community.share_cli.CommunityGitHubClient", return_value=fake_client):
        result = cli.invoke(
            share_results_app,
            ["--yes", "--run-id", "run-A", "--submitter-alias", "alice_42"],
        )
    assert result.exit_code == 1
    assert "GitHub error" in result.stdout
    assert "RetryError" in result.stdout
    fake_client.open_pull_request.assert_not_called()


def test_publish_mode_prints_progress_line_between_panel_and_pr(
    cli: CliRunner, isolated_env
) -> None:
    _store_github_token(isolated_env)
    fake_client = _publishing_client()
    with patch("puma.community.share_cli.CommunityGitHubClient", return_value=fake_client):
        result = cli.invoke(
            share_results_app,
            ["--yes", "--run-id", "run-A", "--submitter-alias", "alice_42"],
        )
    assert result.exit_code == 0, result.stdout
    out = result.stdout
    panel = out.index("Review submission")
    progress = out.index("Contacting GitHub")
    opened = out.index("Pull request opened")
    assert panel < progress < opened


def test_publish_mode_upstream_owner_pr_head_matches_inaugural_shape(
    cli: CliRunner, isolated_env
) -> None:
    """Owner path: branch and file go to the upstream; PR head is owner:submission/<id>."""
    _store_github_token(isolated_env)
    fake_client = _publishing_client()
    with patch("puma.community.share_cli.CommunityGitHubClient", return_value=fake_client):
        result = cli.invoke(
            share_results_app,
            ["--yes", "--run-id", "run-A", "--submitter-alias", "alice_42"],
        )
    assert result.exit_code == 0, result.stdout
    sid = fake_client.create_submission_branch.call_args.kwargs["submission_id"]
    assert fake_client.create_submission_branch.call_args.kwargs["fork_owner"] == "pumacp"
    write_kwargs = fake_client.write_submission_file.call_args.kwargs
    assert write_kwargs["fork_owner"] == "pumacp"
    assert write_kwargs["branch"] == f"submission/{sid}"
    pr_kwargs = fake_client.open_pull_request.call_args.kwargs
    assert pr_kwargs["fork_owner"] == "pumacp"
    assert pr_kwargs["branch"] == f"submission/{sid}"
    assert f"PR #9 from pumacp:submission/{sid}" in result.stdout


def test_publish_mode_artifacts_consumed_by_puma_community_are_unchanged(
    cli: CliRunner, isolated_env
) -> None:
    """Invariants for pumacp/puma-community: schema v1.0.0 payload, file path,
    branch name, commit message, PR title and body shape."""
    from puma.community.validator import validate_submission_dict

    _store_github_token(isolated_env)
    fake_client = _publishing_client()
    with patch("puma.community.share_cli.CommunityGitHubClient", return_value=fake_client):
        result = cli.invoke(
            share_results_app,
            ["--yes", "--run-id", "run-A", "--submitter-alias", "alice_42"],
        )
    assert result.exit_code == 0, result.stdout

    write_kwargs = fake_client.write_submission_file.call_args.kwargs
    payload = json.loads(write_kwargs["payload_json"])
    sid = payload["submission_id"]
    # Payload: schema-valid, canonical serialisation, same id everywhere.
    validate_submission_dict(payload)
    assert payload["schema_version"] == "1.0.0"
    assert write_kwargs["payload_json"] == json.dumps(payload, indent=2, sort_keys=True)
    assert write_kwargs["submission_id"] == sid
    assert write_kwargs["commit_message"] == f"data(community): add submission {sid}"
    assert write_kwargs["branch"] == f"submission/{sid}"
    # PR title/body: produced by the unchanged helpers.
    pr_kwargs = fake_client.open_pull_request.call_args.kwargs
    assert (
        pr_kwargs["title"] == f"Submission {sid[:12]}: estimation_tawos / qwen2.5:3b / few-shot-3"
    )
    body = pr_kwargs["body"]
    assert body.startswith(f"# PUMA Community submission `{sid}`")
    assert "This submission was generated by `puma share-results`." in body
    assert (
        f"- predictions_summary_hash: `{payload['integrity']['predictions_summary_hash']}`" in body
    )
    assert "https://pumacp.github.io/puma-community/schema/submission.v1.json" in body
