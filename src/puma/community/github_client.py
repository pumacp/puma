"""Narrow PyGithub wrapper for PUMA Community PR submissions.

This module is the only place that touches the GitHub API. It exposes the
exact operations ``puma share-results`` needs (fork, branch, file, PR) and
nothing more. The PAT is loaded from :class:`CredentialStore` and never
appears in ``repr()``, exception messages, or logs.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from github import Auth, Github
from github.GithubException import GithubException

from puma.community.credentials import CredentialStore

log = logging.getLogger("puma.community.github_client")

_FORK_POLL_TIMEOUT_S = 20
_FORK_POLL_INTERVAL_S = 1.0


@dataclass(frozen=True)
class SubmissionPRResult:
    pr_url: str
    pr_number: int
    fork_owner: str
    branch_name: str


class GitHubError(Exception):
    """Base class for community GitHub failures."""


class AuthenticationError(GitHubError):
    """No PAT configured or PAT is invalid."""


class ConflictError(GitHubError):
    """A PR, branch, or file with the same name already exists."""


class APIRateLimitError(GitHubError):
    """GitHub's API rate limit is exhausted; ``reset`` carries the reset time."""


class CommunityGitHubClient:
    """Thin wrapper for the operations PUMA Community needs."""

    UPSTREAM_OWNER = "pumacp"
    UPSTREAM_REPO = "puma-community"

    def __init__(self, store: CredentialStore | None = None) -> None:
        self._store = store if store is not None else CredentialStore()
        token = self._store.get("github")
        if not token:
            raise AuthenticationError("No GitHub token configured. Run: puma auth login github")
        self._client = Github(auth=Auth.Token(token))

    def __repr__(self) -> str:
        return f"CommunityGitHubClient(authenticated={self._client is not None})"

    # ── public API ──────────────────────────────────────────────────────────

    def authenticated_user_login(self) -> str:
        try:
            return str(self._client.get_user().login)
        except GithubException as exc:
            if exc.status in (401, 403):
                raise AuthenticationError(
                    "GitHub authentication failed. Run: puma auth login github"
                ) from exc
            raise GitHubError(f"GitHub error while verifying user: {exc.status}") from exc

    def check_rate_limit(self) -> None:
        try:
            core = self._client.get_rate_limit().core
        except GithubException as exc:
            raise GitHubError(f"Cannot read rate limit: {exc.status}") from exc
        if core.remaining <= 0:
            reset = getattr(core, "reset", None)
            raise APIRateLimitError(f"GitHub API rate limit exhausted. Resets at {reset}.")

    def ensure_fork(self) -> str:
        """Return the owner login of the user's fork, creating one if needed.

        GitHub fork creation is asynchronous: ``create_fork`` returns immediately,
        but the repository may take several seconds to become readable. We poll
        for up to ``_FORK_POLL_TIMEOUT_S`` seconds before raising.
        """
        try:
            user = self._client.get_user()
        except GithubException as exc:
            raise AuthenticationError("Cannot identify authenticated user.") from exc

        try:
            fork = user.get_repo(self.UPSTREAM_REPO)
            if getattr(fork, "fork", False):
                return str(fork.owner.login)
        except GithubException as exc:
            if exc.status != 404:
                raise GitHubError(f"Cannot inspect fork: {exc.status}") from exc

        try:
            upstream = self._client.get_repo(f"{self.UPSTREAM_OWNER}/{self.UPSTREAM_REPO}")
            self._client.get_user().create_fork(upstream)  # type: ignore[union-attr]
        except GithubException as exc:
            raise GitHubError(f"Fork creation failed: {exc.status}") from exc

        deadline = time.monotonic() + _FORK_POLL_TIMEOUT_S
        while time.monotonic() < deadline:
            try:
                fork = user.get_repo(self.UPSTREAM_REPO)
                if getattr(fork, "fork", False):
                    return str(fork.owner.login)
            except GithubException:
                pass
            time.sleep(_FORK_POLL_INTERVAL_S)
        raise GitHubError(
            f"Fork creation did not complete within {_FORK_POLL_TIMEOUT_S}s. Retry later."
        )

    def create_submission_branch(
        self,
        *,
        fork_owner: str,
        submission_id: str,
    ) -> str:
        branch_name = f"submission/{submission_id}"
        try:
            upstream = self._client.get_repo(f"{self.UPSTREAM_OWNER}/{self.UPSTREAM_REPO}")
            fork = self._client.get_repo(f"{fork_owner}/{self.UPSTREAM_REPO}")
            base_sha = upstream.get_branch("main").commit.sha
        except GithubException as exc:
            raise GitHubError(f"Cannot read upstream main HEAD: {exc.status}") from exc

        try:
            fork.get_branch(branch_name)
            raise ConflictError(f"Branch {branch_name} already exists on fork {fork_owner}.")
        except GithubException as exc:
            if exc.status != 404:
                raise GitHubError(f"Cannot inspect branch: {exc.status}") from exc

        try:
            fork.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base_sha)
        except GithubException as exc:
            raise GitHubError(f"Branch creation failed: {exc.status}") from exc
        log.info("created branch %s on fork %s", branch_name, fork_owner)
        return branch_name

    def write_submission_file(
        self,
        *,
        fork_owner: str,
        branch: str,
        submission_id: str,
        payload_json: str,
        commit_message: str,
    ) -> None:
        try:
            fork = self._client.get_repo(f"{fork_owner}/{self.UPSTREAM_REPO}")
        except GithubException as exc:
            raise GitHubError(f"Cannot access fork: {exc.status}") from exc

        file_path = f"submissions/{submission_id}.json"
        try:
            fork.create_file(
                path=file_path,
                message=commit_message,
                content=payload_json,
                branch=branch,
            )
        except GithubException as exc:
            if exc.status == 422:
                raise ConflictError(f"File {file_path} already exists on branch {branch}.") from exc
            raise GitHubError(f"File write failed: {exc.status}") from exc
        log.info("wrote %s on %s@%s", file_path, fork_owner, branch)

    def open_pull_request(
        self,
        *,
        fork_owner: str,
        branch: str,
        submission_id: str,
        title: str,
        body: str,
    ) -> SubmissionPRResult:
        try:
            upstream = self._client.get_repo(f"{self.UPSTREAM_OWNER}/{self.UPSTREAM_REPO}")
            pr = upstream.create_pull(
                title=title,
                body=body,
                head=f"{fork_owner}:{branch}",
                base="main",
            )
        except GithubException as exc:
            if exc.status == 422:
                raise ConflictError("A pull request from this branch already exists.") from exc
            raise GitHubError(f"PR creation failed: {exc.status}") from exc
        log.info("opened PR #%d at %s", pr.number, pr.html_url)
        return SubmissionPRResult(
            pr_url=str(pr.html_url),
            pr_number=int(pr.number),
            fork_owner=fork_owner,
            branch_name=branch,
        )


__all__ = [
    "APIRateLimitError",
    "AuthenticationError",
    "CommunityGitHubClient",
    "ConflictError",
    "GitHubError",
    "SubmissionPRResult",
]
