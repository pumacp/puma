"""D40 regression: the real GitHub client against an in-process fake GitHub API.

``puma share-results`` hung after the review panel for the inaugural submission
(puma-community PR 8) because the upstream owner cannot fork their own
repository, and because PyGithub's default retry sleeps silently on rate-limit
answers. These tests run :class:`CommunityGitHubClient` unmodified against a
local HTTP server that speaks the handful of REST endpoints the client uses.
No request leaves the machine.
"""

from __future__ import annotations

import functools
import json
import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest
from github import Github

from puma.community import github_client
from puma.community.credentials import CredentialStore
from puma.community.github_client import (
    APIRateLimitError,
    CommunityGitHubClient,
    GitHubError,
)

UPSTREAM_OWNER = "pumacp"
UPSTREAM_REPO = "puma-community"
UPSTREAM = f"{UPSTREAM_OWNER}/{UPSTREAM_REPO}"
FAKE_TOKEN = "ghp_" + "b" * 36


class FakeGitHub:
    """Scripted GitHub REST subset. ``scenario`` selects the fork behaviour."""

    def __init__(self, *, login: str, scenario: str = "user", remaining: int = 4000) -> None:
        self.login = login
        self.scenario = scenario
        self.remaining = remaining
        self.calls: list[tuple[str, str, dict[str, Any] | None]] = []
        self.fork_created = False
        server_self = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args: Any) -> None:  # silence the test log
                return

            def _base(self) -> str:
                return f"http://{self.headers['Host']}"

            def _send(self, code: int, body: Any, headers: dict[str, str] | None = None) -> None:
                data = json.dumps(body).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                for key, value in (headers or {}).items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(data)

            def _body(self) -> dict[str, Any] | None:
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b""
                return json.loads(raw) if raw else None

            def _repo(self, owner: str, fork: bool) -> dict[str, Any]:
                base = self._base()
                repo: dict[str, Any] = {
                    "id": 1,
                    "name": UPSTREAM_REPO,
                    "full_name": f"{owner}/{UPSTREAM_REPO}",
                    "fork": fork,
                    "owner": {"login": owner, "id": 1, "url": f"{base}/users/{owner}"},
                    "url": f"{base}/repos/{owner}/{UPSTREAM_REPO}",
                    "default_branch": "main",
                }
                if fork:
                    repo["parent"] = self._repo(UPSTREAM_OWNER, False)
                return repo

            def do_GET(self) -> None:
                path = self.path.split("?")[0]
                server_self.calls.append(("GET", path, None))
                base = self._base()
                if path == "/rate_limit":
                    core = {
                        "limit": 5000,
                        "used": 0,
                        "remaining": server_self.remaining,
                        "reset": int(time.time()) + 3600,
                    }
                    return self._send(
                        200,
                        {
                            "resources": {"core": core, "search": core, "graphql": core},
                            "rate": core,
                        },
                    )
                if path == "/user":
                    return self._send(
                        200, {"login": server_self.login, "id": 1, "url": f"{base}/user"}
                    )
                if path == f"/repos/{UPSTREAM}":
                    return self._send(200, self._repo(UPSTREAM_OWNER, False))
                if path == f"/repos/{server_self.login}/{UPSTREAM_REPO}":
                    if server_self.fork_created:
                        return self._send(200, self._repo(server_self.login, True))
                    return self._send(404, {"message": "Not Found"})
                if path.endswith("/branches/main"):
                    return self._send(
                        200, {"name": "main", "commit": {"sha": "f" * 40, "url": base}}
                    )
                if "/branches/" in path:
                    return self._send(404, {"message": "Branch not found"})
                return self._send(404, {"message": f"unhandled GET {path}"})

            def do_POST(self) -> None:
                path = self.path.split("?")[0]
                body = self._body()
                server_self.calls.append(("POST", path, body))
                base = self._base()
                if path.endswith("/forks"):
                    if server_self.scenario == "secondary-limit":
                        return self._send(
                            403,
                            {
                                "message": "You have exceeded a secondary rate limit. Please wait a few minutes before you try again."
                            },
                            {"Retry-After": "0"},
                        )
                    if server_self.scenario == "server-error":
                        return self._send(503, {"message": "Service Unavailable"})
                    server_self.fork_created = True
                    return self._send(202, self._repo(server_self.login, True))
                if path.endswith("/git/refs"):
                    return self._send(
                        201,
                        {
                            "ref": "refs/heads/x",
                            "url": base,
                            "object": {"sha": "f" * 40, "type": "commit", "url": base},
                        },
                    )
                if path.endswith("/pulls"):
                    return self._send(
                        201,
                        {
                            "number": 42,
                            "id": 42,
                            "html_url": f"https://github.com/{UPSTREAM}/pull/42",
                            "url": f"{base}/repos/{UPSTREAM}/pulls/42",
                        },
                    )
                return self._send(404, {"message": f"unhandled POST {path}"})

            def do_PUT(self) -> None:
                path = self.path.split("?")[0]
                body = self._body()
                server_self.calls.append(("PUT", path, body))
                base = self._base()
                return self._send(
                    201,
                    {
                        "content": {
                            "path": path.split("/contents/")[-1],
                            "sha": "a" * 40,
                            "url": base,
                        },
                        "commit": {"sha": "b" * 40, "url": base},
                    },
                )

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.base_url = f"http://127.0.0.1:{self._server.server_address[1]}"
        threading.Thread(target=self._server.serve_forever, daemon=True).start()

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()

    def writes(self) -> list[tuple[str, str]]:
        return [(method, path) for method, path, _ in self.calls if method != "GET"]

    def fork_posts(self) -> int:
        return sum(
            1 for method, path, _ in self.calls if method == "POST" and path.endswith("/forks")
        )


@pytest.fixture
def credential_store(tmp_path, monkeypatch) -> CredentialStore:
    monkeypatch.setenv("PUMA_CONFIG_DIR", str(tmp_path / "puma-config"))
    store = CredentialStore()
    store.set("github", FAKE_TOKEN)
    return store


def _client_against(fake: FakeGitHub, monkeypatch, store: CredentialStore) -> CommunityGitHubClient:
    monkeypatch.setattr(github_client, "Github", functools.partial(Github, base_url=fake.base_url))
    # Fork readiness polls would otherwise sleep a real second between attempts.
    monkeypatch.setattr(github_client, "_FORK_POLL_INTERVAL_S", 0.01)
    return CommunityGitHubClient(store=store)


@pytest.fixture
def fake_factory() -> Iterator[Any]:
    servers: list[FakeGitHub] = []

    def make(**kwargs: Any) -> FakeGitHub:
        fake = FakeGitHub(**kwargs)
        servers.append(fake)
        return fake

    yield make
    for fake in servers:
        fake.close()


def _publish(client: CommunityGitHubClient, submission_id: str) -> tuple[str, str, Any]:
    owner = client.ensure_fork()
    branch = client.create_submission_branch(fork_owner=owner, submission_id=submission_id)
    client.write_submission_file(
        fork_owner=owner,
        branch=branch,
        submission_id=submission_id,
        payload_json="{}",
        commit_message=f"data(community): add submission {submission_id}",
    )
    result = client.open_pull_request(
        fork_owner=owner, branch=branch, submission_id=submission_id, title="t", body="b"
    )
    return owner, branch, result


@pytest.mark.integration
def test_upstream_owner_publishes_on_upstream_without_forking(
    fake_factory, monkeypatch, credential_store
) -> None:
    fake = fake_factory(login=UPSTREAM_OWNER)
    client = _client_against(fake, monkeypatch, credential_store)

    started = time.monotonic()
    owner, branch, result = _publish(client, "abc-123")

    assert time.monotonic() - started < 10, "owner path must not wait for a fork"
    assert owner == UPSTREAM_OWNER
    assert branch == "submission/abc-123"
    assert fake.fork_posts() == 0
    assert fake.writes() == [
        ("POST", f"/repos/{UPSTREAM}/git/refs"),
        ("PUT", f"/repos/{UPSTREAM}/contents/submissions/abc-123.json"),
        ("POST", f"/repos/{UPSTREAM}/pulls"),
    ]
    pr_body = next(body for method, path, body in fake.calls if path.endswith("/pulls"))
    assert pr_body == {
        "title": "t",
        "body": "b",
        "head": f"{UPSTREAM_OWNER}:submission/abc-123",
        "base": "main",
    }
    assert result.pr_number == 42 and result.fork_owner == UPSTREAM_OWNER


@pytest.mark.integration
def test_ordinary_user_forks_once_and_opens_pr_from_fork(
    fake_factory, monkeypatch, credential_store
) -> None:
    fake = fake_factory(login="alice")
    client = _client_against(fake, monkeypatch, credential_store)

    owner, _branch, result = _publish(client, "abc-123")

    assert owner == "alice"
    assert fake.fork_posts() == 1
    assert fake.writes() == [
        ("POST", f"/repos/{UPSTREAM}/forks"),
        ("POST", f"/repos/alice/{UPSTREAM_REPO}/git/refs"),
        ("PUT", f"/repos/alice/{UPSTREAM_REPO}/contents/submissions/abc-123.json"),
        ("POST", f"/repos/{UPSTREAM}/pulls"),
    ]
    pr_body = next(body for method, path, body in fake.calls if path.endswith("/pulls"))
    assert pr_body["head"] == "alice:submission/abc-123"
    assert result.pr_url == f"https://github.com/{UPSTREAM}/pull/42"


@pytest.mark.integration
def test_exhausted_rate_limit_fails_fast_before_any_write(
    fake_factory, monkeypatch, credential_store
) -> None:
    fake = fake_factory(login="alice", remaining=0)
    client = _client_against(fake, monkeypatch, credential_store)

    with pytest.raises(APIRateLimitError, match="rate limit exhausted"):
        client.ensure_fork()
    assert fake.writes() == []


@pytest.mark.integration
@pytest.mark.parametrize("scenario", ["secondary-limit", "server-error"])
def test_failing_fork_request_is_bounded_and_surfaces_as_github_error(
    fake_factory, monkeypatch, credential_store, scenario: str
) -> None:
    """PyGithub's default would retry ten times and sleep for minutes; the bounded
    policy gives up after three attempts and the failure is a GitHubError."""
    fake = fake_factory(login="alice", scenario=scenario)
    client = _client_against(fake, monkeypatch, credential_store)

    started = time.monotonic()
    with pytest.raises(GitHubError) as captured:
        client.ensure_fork()

    assert time.monotonic() - started < 15
    assert fake.fork_posts() <= 3
    assert "RetryError" in str(captured.value)
    assert FAKE_TOKEN not in str(captured.value)
