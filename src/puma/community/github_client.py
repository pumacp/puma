"""Narrow PyGithub wrapper for PUMA Community PR submissions.

This module is the only place that touches the GitHub API. It exposes the
exact operations ``puma share-results`` needs (fork, branch, file, PR) and
nothing more. The PAT is loaded from :class:`CredentialStore` and never
appears in ``repr()``, exception messages, or logs.
"""

from __future__ import annotations

import functools
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ParamSpec, TypeVar

from github import Auth, Github
from github.GithubException import GithubException
from github.GithubRetry import GithubRetry
from requests.exceptions import RequestException

from puma.community.credentials import CredentialStore

log = logging.getLogger("puma.community.github_client")

_FORK_POLL_TIMEOUT_S = 20
_FORK_POLL_INTERVAL_S = 1.0

# Per-request socket timeout. PyGithub's own default is 15 s; the explicit value
# keeps the publish path bounded even when GitHub is slow to answer.
_HTTP_TIMEOUT_S = 30
# PyGithub's default is ``GithubRetry(total=10)``, which sleeps silently on 403
# rate-limit answers until the limit resets (up to an hour) and on every 5xx.
# Two retries of transient server errors keep a brief outage from failing the
# submission while bounding the worst case to seconds, not an hour. Rate limits
# are checked up front via :meth:`CommunityGitHubClient.check_rate_limit`.
_RETRY_TOTAL = 2
_RETRY_STATUS_FORCELIST: tuple[int, ...] = (500, 502, 503, 504)
_RETRY_BACKOFF_FACTOR = 0.5

P = ParamSpec("P")
R = TypeVar("R")


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


def _build_retry() -> GithubRetry:
    """Bounded retry policy: transient 5xx only, two attempts, short backoff.

    ``GithubRetry`` always appends 403 to the forcelist so it can recognise
    GitHub's rate-limit answers; with ``total=2`` that wait is bounded as well.
    """
    return GithubRetry(
        total=_RETRY_TOTAL,
        status_forcelist=list(_RETRY_STATUS_FORCELIST),
        backoff_factor=_RETRY_BACKOFF_FACTOR,
    )


def _translate_request_errors(func: Callable[P, R]) -> Callable[P, R]:
    """Map transport-level failures to :class:`GitHubError`.

    When the bounded retry gives up, ``requests`` raises ``RetryError`` (or a
    connection/timeout error), none of which is a ``GithubException``. Without
    this mapping those escape the CLI's themed error handling.
    """

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return func(*args, **kwargs)
        except RequestException as exc:
            raise GitHubError(
                f"GitHub request failed ({type(exc).__name__}). "
                "Check connectivity and the API rate limit, then retry."
            ) from exc

    return wrapper


class CommunityGitHubClient:
    """Thin wrapper for the operations PUMA Community needs."""

    UPSTREAM_OWNER = "pumacp"
    UPSTREAM_REPO = "puma-community"

    def __init__(self, store: CredentialStore | None = None) -> None:
        self._store = store if store is not None else CredentialStore()
        token = self._store.get("github")
        if not token:
            raise AuthenticationError("No GitHub token configured. Run: puma auth login github")
        self._client = Github(
            auth=Auth.Token(token),
            timeout=_HTTP_TIMEOUT_S,
            retry=_build_retry(),
        )

    @property
    def upstream_full_name(self) -> str:
        return f"{self.UPSTREAM_OWNER}/{self.UPSTREAM_REPO}"

    def __repr__(self) -> str:
        return f"CommunityGitHubClient(authenticated={self._client is not None})"

    # ── public API ──────────────────────────────────────────────────────────

    @_translate_request_errors
    def authenticated_user_login(self) -> str:
        try:
            return str(self._client.get_user().login)
        except GithubException as exc:
            if exc.status in (401, 403):
                raise AuthenticationError(
                    "GitHub authentication failed. Run: puma auth login github"
                ) from exc
            raise GitHubError(f"GitHub error while verifying user: {exc.status}") from exc

    @_translate_request_errors
    def check_rate_limit(self) -> None:
        try:
            limits: Any = self._client.get_rate_limit()
        except GithubException as exc:
            raise GitHubError(f"Cannot read rate limit: {exc.status}") from exc
        # PyGithub < 2.7 returns ``RateLimit`` with the buckets as attributes
        # (``.core``); 2.7+ returns ``RateLimitOverview`` and nests them under
        # ``.resources``. Accept both so the pin in requirements.txt and a
        # resolver-chosen newer release behave the same.
        core = getattr(limits, "core", None)
        if core is None:
            core = limits.resources.core
        if core.remaining <= 0:
            reset = getattr(core, "reset", None)
            raise APIRateLimitError(f"GitHub API rate limit exhausted. Resets at {reset}.")

    def _is_fork_of_upstream(self, repo: object) -> bool:
        """True iff ``repo`` is a fork whose parent is the upstream repository.

        A same-named repository that is not a fork (or forks another project)
        is not usable as the submission target and is treated as "no fork".
        """
        if not getattr(repo, "fork", False):
            return False
        parent = getattr(repo, "parent", None)
        if parent is None:
            return False
        return str(parent.full_name) == self.upstream_full_name

    @_translate_request_errors
    def ensure_fork(self) -> str:
        """Return the owner login to push the submission branch to.

        The upstream owner pushes straight to ``pumacp/puma-community`` (a
        repository cannot be forked into its own account); every other user
        gets their fork, created on demand. GitHub fork creation is
        asynchronous: ``create_fork`` returns immediately, but the repository
        may take several seconds to become readable. We poll for up to
        ``_FORK_POLL_TIMEOUT_S`` seconds before raising.

        The API rate limit is checked first so an exhausted limit surfaces as
        :class:`APIRateLimitError` instead of a long silent wait.
        """
        self.check_rate_limit()
        try:
            user = self._client.get_user()
            login = str(user.login)
        except GithubException as exc:
            raise AuthenticationError("Cannot identify authenticated user.") from exc

        if login == self.UPSTREAM_OWNER:
            log.info("authenticated as upstream owner %s; publishing without a fork", login)
            return login

        try:
            candidate = user.get_repo(self.UPSTREAM_REPO)
            if self._is_fork_of_upstream(candidate):
                return str(candidate.owner.login)
            log.info(
                "%s/%s exists but is not a fork of %s; requesting a fork",
                login,
                self.UPSTREAM_REPO,
                self.upstream_full_name,
            )
        except GithubException as exc:
            if exc.status != 404:
                raise GitHubError(f"Cannot inspect fork: {exc.status}") from exc

        try:
            upstream = self._client.get_repo(self.upstream_full_name)
            user.create_fork(upstream)  # type: ignore[union-attr]
        except GithubException as exc:
            raise GitHubError(f"Fork creation failed: {exc.status}") from exc

        deadline = time.monotonic() + _FORK_POLL_TIMEOUT_S
        while time.monotonic() < deadline:
            try:
                fork = user.get_repo(self.UPSTREAM_REPO)
                if self._is_fork_of_upstream(fork):
                    return str(fork.owner.login)
            except GithubException:
                pass
            time.sleep(_FORK_POLL_INTERVAL_S)
        raise GitHubError(
            f"Fork creation did not complete within {_FORK_POLL_TIMEOUT_S}s. Retry later."
        )

    @_translate_request_errors
    def create_submission_branch(
        self,
        *,
        fork_owner: str,
        submission_id: str,
    ) -> str:
        branch_name = f"submission/{submission_id}"
        try:
            upstream = self._client.get_repo(self.upstream_full_name)
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

    @_translate_request_errors
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

    @_translate_request_errors
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
            upstream = self._client.get_repo(self.upstream_full_name)
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
