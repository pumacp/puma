"""Tests for the PyGithub wrapper. All network access is mocked."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from puma.community.credentials import CredentialStore
from puma.community.github_client import (
    APIRateLimitError,
    AuthenticationError,
    CommunityGitHubClient,
    ConflictError,
    GitHubError,
)

UPSTREAM = "pumacp/puma-community"

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


def _github_instance(login: str = "alice", remaining: int = 4000) -> tuple[MagicMock, MagicMock]:
    """A fake ``Github`` instance with an authenticated user and a healthy rate limit."""
    instance = MagicMock()
    user = MagicMock()
    user.login = login
    instance.get_user.return_value = user
    instance.get_rate_limit.return_value.core.remaining = remaining
    return instance, user


def _fork_of(parent_full_name: str, owner: str = "alice") -> MagicMock:
    repo = MagicMock(fork=True)
    repo.owner.login = owner
    repo.parent.full_name = parent_full_name
    return repo


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
        instance, user = _github_instance()
        user.get_repo.return_value = _fork_of(UPSTREAM)
        gh_class.return_value = instance

        client = CommunityGitHubClient(store=configured_store)
        result = client.ensure_fork()
        assert result == "alice"
        user.create_fork.assert_not_called()


def test_ensure_fork_creates_when_missing(configured_store: CredentialStore) -> None:
    with patch("puma.community.github_client.Github") as gh_class:
        instance, user = _github_instance()
        # First call: 404; subsequent calls: success
        user.get_repo.side_effect = [
            _make_github_exception(404),
            _fork_of(UPSTREAM),
        ]
        instance.get_repo.return_value = MagicMock()
        gh_class.return_value = instance

        client = CommunityGitHubClient(store=configured_store)
        result = client.ensure_fork()
        assert result == "alice"
        user.create_fork.assert_called_once()


def test_ensure_fork_upstream_owner_publishes_without_forking(
    configured_store: CredentialStore,
) -> None:
    """D40: the owner of pumacp/puma-community cannot fork it into the same account."""
    with patch("puma.community.github_client.Github") as gh_class:
        instance, user = _github_instance(login="pumacp")
        gh_class.return_value = instance

        client = CommunityGitHubClient(store=configured_store)
        assert client.ensure_fork() == "pumacp"
        user.create_fork.assert_not_called()
        user.get_repo.assert_not_called()


def test_ensure_fork_ignores_same_named_repo_that_is_not_a_fork(
    configured_store: CredentialStore,
) -> None:
    with patch("puma.community.github_client.Github") as gh_class:
        instance, user = _github_instance()
        unrelated = MagicMock(fork=False)
        unrelated.owner.login = "alice"
        user.get_repo.side_effect = [unrelated, _fork_of(UPSTREAM)]
        instance.get_repo.return_value = MagicMock()
        gh_class.return_value = instance

        client = CommunityGitHubClient(store=configured_store)
        assert client.ensure_fork() == "alice"
        user.create_fork.assert_called_once()


def test_ensure_fork_ignores_fork_of_another_repository(
    configured_store: CredentialStore,
) -> None:
    with patch("puma.community.github_client.Github") as gh_class:
        instance, user = _github_instance()
        user.get_repo.side_effect = [_fork_of("someone-else/puma-community"), _fork_of(UPSTREAM)]
        instance.get_repo.return_value = MagicMock()
        gh_class.return_value = instance

        client = CommunityGitHubClient(store=configured_store)
        assert client.ensure_fork() == "alice"
        user.create_fork.assert_called_once()


def test_ensure_fork_checks_rate_limit_before_any_write(
    configured_store: CredentialStore,
) -> None:
    with patch("puma.community.github_client.Github") as gh_class:
        instance, user = _github_instance(remaining=0)
        gh_class.return_value = instance

        client = CommunityGitHubClient(store=configured_store)
        with pytest.raises(APIRateLimitError, match="rate limit exhausted"):
            client.ensure_fork()
        user.create_fork.assert_not_called()
        user.get_repo.assert_not_called()


def _rate_limit_legacy(remaining: int) -> SimpleNamespace:
    """``RateLimit`` as returned by PyGithub < 2.7: buckets are attributes."""
    core = SimpleNamespace(remaining=remaining, reset=datetime(2026, 1, 1, tzinfo=UTC))
    return SimpleNamespace(core=core, search=core, graphql=core)


def _rate_limit_overview(remaining: int) -> SimpleNamespace:
    """``RateLimitOverview`` as returned by PyGithub >= 2.7: no ``.core``,
    buckets nested under ``.resources`` plus the legacy ``.rate`` mirror."""
    core = SimpleNamespace(remaining=remaining, reset=datetime(2026, 1, 1, tzinfo=UTC))
    return SimpleNamespace(
        resources=SimpleNamespace(core=core, search=core, graphql=core), rate=core
    )


@pytest.mark.parametrize("shape", [_rate_limit_legacy, _rate_limit_overview])
def test_check_rate_limit_accepts_both_pygithub_shapes_with_quota(
    configured_store: CredentialStore, shape
) -> None:
    with patch("puma.community.github_client.Github") as gh_class:
        instance, _ = _github_instance()
        instance.get_rate_limit.return_value = shape(4000)
        gh_class.return_value = instance

        client = CommunityGitHubClient(store=configured_store)
        client.check_rate_limit()  # must not raise


@pytest.mark.parametrize("shape", [_rate_limit_legacy, _rate_limit_overview])
def test_check_rate_limit_accepts_both_pygithub_shapes_when_exhausted(
    configured_store: CredentialStore, shape
) -> None:
    with patch("puma.community.github_client.Github") as gh_class:
        instance, user = _github_instance()
        instance.get_rate_limit.return_value = shape(0)
        gh_class.return_value = instance

        client = CommunityGitHubClient(store=configured_store)
        with pytest.raises(APIRateLimitError, match="rate limit exhausted") as captured:
            client.ensure_fork()
        assert "Resets at 2026-01-01" in str(captured.value)
        user.create_fork.assert_not_called()


def test_github_constructed_with_bounded_retry_and_explicit_timeout(
    configured_store: CredentialStore,
) -> None:
    from github.GithubRetry import GithubRetry

    with patch("puma.community.github_client.Github") as gh_class:
        gh_class.return_value = MagicMock()
        CommunityGitHubClient(store=configured_store)

    gh_class.assert_called_once()
    kwargs = gh_class.call_args.kwargs
    assert kwargs["timeout"] == 30
    retry = kwargs["retry"]
    assert isinstance(retry, GithubRetry)
    assert retry.total == 2
    assert {500, 502, 503, 504} <= set(retry.status_forcelist)
    assert 404 not in retry.status_forcelist
    assert 422 not in retry.status_forcelist


@pytest.mark.parametrize(
    "method_name",
    ["authenticated_user_login", "ensure_fork", "create_submission_branch"],
)
def test_transport_errors_map_to_github_error(
    configured_store: CredentialStore, method_name: str
) -> None:
    """``requests`` errors (RetryError after the bounded retry, timeouts) are not
    ``GithubException`` instances; they must still surface as ``GitHubError``."""
    from requests.exceptions import RetryError

    with patch("puma.community.github_client.Github") as gh_class:
        instance, _ = _github_instance()
        instance.get_user.side_effect = RetryError("Max retries exceeded with url: /user")
        instance.get_repo.side_effect = RetryError("Max retries exceeded with url: /repos")
        instance.get_rate_limit.side_effect = RetryError("Max retries exceeded")
        gh_class.return_value = instance

        client = CommunityGitHubClient(store=configured_store)
        kwargs = (
            {"fork_owner": "alice", "submission_id": "abc-123"}
            if method_name == "create_submission_branch"
            else {}
        )
        with pytest.raises(GitHubError) as captured:
            getattr(client, method_name)(**kwargs)
        assert not isinstance(captured.value, ConflictError)
        assert "RetryError" in str(captured.value)
        assert FAKE_TOKEN not in str(captured.value)


def test_open_pull_request_transport_error_is_not_a_conflict(
    configured_store: CredentialStore,
) -> None:
    from requests.exceptions import ConnectionError as RequestsConnectionError

    with patch("puma.community.github_client.Github") as gh_class:
        instance = MagicMock()
        upstream = MagicMock()
        upstream.create_pull.side_effect = RequestsConnectionError("connection reset")
        instance.get_repo.return_value = upstream
        gh_class.return_value = instance

        client = CommunityGitHubClient(store=configured_store)
        with pytest.raises(GitHubError) as captured:
            client.open_pull_request(
                fork_owner="alice",
                branch="submission/abc",
                submission_id="abc",
                title="t",
                body="b",
            )
        assert not isinstance(captured.value, ConflictError)


def test_write_submission_file_keeps_path_and_payload_unchanged(
    configured_store: CredentialStore,
) -> None:
    """Invariant: puma-community consumes ``submissions/<id>.json`` verbatim."""
    with patch("puma.community.github_client.Github") as gh_class:
        instance = MagicMock()
        fork = MagicMock()
        instance.get_repo.return_value = fork
        gh_class.return_value = instance

        client = CommunityGitHubClient(store=configured_store)
        client.write_submission_file(
            fork_owner="pumacp",
            branch="submission/abc-123",
            submission_id="abc-123",
            payload_json='{"schema_version": "1.0.0"}',
            commit_message="data(community): add submission abc-123",
        )
        instance.get_repo.assert_called_once_with("pumacp/puma-community")
        fork.create_file.assert_called_once_with(
            path="submissions/abc-123.json",
            message="data(community): add submission abc-123",
            content='{"schema_version": "1.0.0"}',
            branch="submission/abc-123",
        )


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
