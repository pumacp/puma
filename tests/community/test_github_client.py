"""Tests for the PyGithub wrapper. All network access is mocked."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from puma.community.credentials import CredentialStore
from puma.community.github_client import (
    AuthenticationError,
    CommunityGitHubClient,
    ConflictError,
    GitHubError,
)

# Mirrors the regex in credentials.py for "github" so tests don't break on
# format validation. These are clearly synthetic placeholders.
FAKE_TOKEN = "ghp_" + "a" * 36


@pytest.fixture
def configured_store(tmp_path: Path, monkeypatch) -> CredentialStore:
    monkeypatch.setenv("PUMA_CONFIG_DIR", str(tmp_path / "puma-config"))
    store = CredentialStore()
    store.set("github", FAKE_TOKEN)
    return store


@pytest.fixture
def empty_store(tmp_path: Path, monkeypatch) -> CredentialStore:
    monkeypatch.setenv("PUMA_CONFIG_DIR", str(tmp_path / "puma-config-empty"))
    return CredentialStore()


def _make_github_exception(status: int):
    """Build a ``GithubException`` instance the way PyGithub expects."""
    from github.GithubException import GithubException

    return GithubException(status=status, data={}, headers={})


def test_raises_authentication_error_when_no_token(empty_store: CredentialStore) -> None:
    with pytest.raises(AuthenticationError):
        CommunityGitHubClient(store=empty_store)


def test_pat_never_appears_in_repr(configured_store: CredentialStore) -> None:
    with patch("puma.community.github_client.Github") as gh_class:
        gh_class.return_value = MagicMock()
        client = CommunityGitHubClient(store=configured_store)
        text = repr(client)
        assert FAKE_TOKEN not in text
        assert "ghp_" + "a" * 4 not in text


def test_ensure_fork_returns_existing_fork_owner_without_creating(
    configured_store: CredentialStore,
) -> None:
    with patch("puma.community.github_client.Github") as gh_class:
        instance = MagicMock()
        user = MagicMock()
        existing_fork = MagicMock(fork=True)
        existing_fork.owner.login = "alice"
        user.get_repo.return_value = existing_fork
        instance.get_user.return_value = user
        gh_class.return_value = instance

        client = CommunityGitHubClient(store=configured_store)
        result = client.ensure_fork()
        assert result == "alice"
        user.create_fork.assert_not_called()


def test_ensure_fork_creates_when_missing(configured_store: CredentialStore) -> None:
    with patch("puma.community.github_client.Github") as gh_class:
        instance = MagicMock()
        user = MagicMock()
        # First call: 404; subsequent calls: success
        new_fork = MagicMock(fork=True)
        new_fork.owner.login = "alice"
        user.get_repo.side_effect = [
            _make_github_exception(404),
            new_fork,
        ]
        instance.get_user.return_value = user
        instance.get_repo.return_value = MagicMock()
        gh_class.return_value = instance

        client = CommunityGitHubClient(store=configured_store)
        result = client.ensure_fork()
        assert result == "alice"
        user.create_fork.assert_called_once()


def test_create_submission_branch_raises_conflict_if_branch_exists(
    configured_store: CredentialStore,
) -> None:
    with patch("puma.community.github_client.Github") as gh_class:
        instance = MagicMock()
        upstream = MagicMock()
        upstream.get_branch.return_value.commit.sha = "deadbeef"
        fork = MagicMock()
        fork.get_branch.return_value = MagicMock()  # branch already exists
        instance.get_repo.side_effect = lambda full_name: (
            upstream if full_name.startswith("pumacp/") else fork
        )
        gh_class.return_value = instance

        client = CommunityGitHubClient(store=configured_store)
        with pytest.raises(ConflictError):
            client.create_submission_branch(fork_owner="alice", submission_id="abc-123")


def test_create_submission_branch_succeeds_when_branch_missing(
    configured_store: CredentialStore,
) -> None:
    with patch("puma.community.github_client.Github") as gh_class:
        instance = MagicMock()
        upstream = MagicMock()
        upstream.get_branch.return_value.commit.sha = "deadbeef"
        fork = MagicMock()
        fork.get_branch.side_effect = _make_github_exception(404)
        instance.get_repo.side_effect = lambda full_name: (
            upstream if full_name.startswith("pumacp/") else fork
        )
        gh_class.return_value = instance

        client = CommunityGitHubClient(store=configured_store)
        branch = client.create_submission_branch(fork_owner="alice", submission_id="abc-123")
        assert branch == "submission/abc-123"
        fork.create_git_ref.assert_called_once()


def test_open_pull_request_returns_url_and_number(
    configured_store: CredentialStore,
) -> None:
    with patch("puma.community.github_client.Github") as gh_class:
        instance = MagicMock()
        pr = MagicMock(html_url="https://github.com/pumacp/puma-community/pull/7", number=7)
        upstream = MagicMock()
        upstream.create_pull.return_value = pr
        instance.get_repo.return_value = upstream
        gh_class.return_value = instance

        client = CommunityGitHubClient(store=configured_store)
        result = client.open_pull_request(
            fork_owner="alice",
            branch="submission/abc-123",
            submission_id="abc-123",
            title="Submission abc-123",
            body="body",
        )
        assert result.pr_url == "https://github.com/pumacp/puma-community/pull/7"
        assert result.pr_number == 7
        assert result.fork_owner == "alice"
        assert result.branch_name == "submission/abc-123"


def test_open_pull_request_conflict_maps_to_conflict_error(
    configured_store: CredentialStore,
) -> None:
    with patch("puma.community.github_client.Github") as gh_class:
        instance = MagicMock()
        upstream = MagicMock()
        upstream.create_pull.side_effect = _make_github_exception(422)
        instance.get_repo.return_value = upstream
        gh_class.return_value = instance

        client = CommunityGitHubClient(store=configured_store)
        with pytest.raises(ConflictError):
            client.open_pull_request(
                fork_owner="alice",
                branch="submission/abc-123",
                submission_id="abc-123",
                title="t",
                body="b",
            )


def test_token_never_in_exception_messages(
    configured_store: CredentialStore,
) -> None:
    with patch("puma.community.github_client.Github") as gh_class:
        instance = MagicMock()
        instance.get_user.side_effect = _make_github_exception(401)
        gh_class.return_value = instance

        client = CommunityGitHubClient(store=configured_store)
        with pytest.raises((AuthenticationError, GitHubError)) as captured:
            client.authenticated_user_login()
        assert FAKE_TOKEN not in str(captured.value)
