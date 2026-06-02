"""Local PUMA Community status aggregation (read-only, never raises).

Composes a :class:`CommunityStatus` snapshot from three purely-local sources:

1. **Authentication** — whether a GitHub credential is present in the local
   credential store (:class:`puma.community.credentials.CredentialStore`). This
   is a presence check only; it makes **no** network call. The GitHub *username*
   is not derivable locally (it would require an ``api.github.com`` round-trip,
   which this layer must not make), so ``authenticated_as`` is reported only when
   a local cache provides it — otherwise it stays ``None``.
2. **Last submission** — read from an optional cache file at
   ``~/.puma/last_submission.json`` if present. PUMA does not write this file
   today; ``share-results`` may populate it in a future phase. When absent or
   malformed, the ``last_*`` fields are ``None``.
3. **Channel configuration counts** — derived from the channels passed in (which
   should already be enriched via
   :func:`puma.community.channels.enrich_with_local_state`).

Every public function here is defensive: missing credentials, a missing or
broken cache file, or unreadable permissions degrade to ``None`` / ``False``
rather than raising.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from puma.community.channels import Channel

log = logging.getLogger("puma.community.status")

_GITHUB_SERVICE = "github"


@dataclass(frozen=True)
class CommunityStatus:
    """A local snapshot of PUMA Community state."""

    authenticated: bool
    authenticated_as: str | None
    last_local_submission_id: str | None
    last_local_submission_timestamp: str | None
    configured_channel_count: int
    total_channel_count: int


def _last_submission_path() -> Path:
    """Return the conventional local submission-cache path (``~/.puma/...``).

    Uses :meth:`Path.home` so tests can isolate it by overriding ``HOME``.
    """
    return Path.home() / ".puma" / "last_submission.json"


def _detect_authentication() -> tuple[bool, str | None]:
    """Return ``(authenticated, username_or_None)`` without any network call.

    ``authenticated`` is True when a GitHub token is present in the local
    credential store. The username is not locally available (resolving it needs
    a GitHub API call), so the second element is always ``None`` here. Never
    raises: any credential-store error degrades to ``(False, None)``.
    """
    try:
        from puma.community.credentials import CredentialStore

        token = CredentialStore().get(_GITHUB_SERVICE)
    except Exception as exc:  # status must never raise — degrade to unauthenticated
        log.debug("auth detection failed, treating as unauthenticated: %s", exc)
        return False, None
    return bool(token), None


def _read_last_submission() -> tuple[str | None, str | None]:
    """Return ``(submission_id, timestamp)`` from the cache, or ``(None, None)``.

    Never raises: a missing file, malformed JSON, missing keys, or an OS error
    all degrade to ``(None, None)``.
    """
    path = _last_submission_path()
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None, None
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return None, None
    if not isinstance(data, dict):
        return None, None
    sub_id = data.get("submission_id")
    ts = data.get("timestamp")
    sub_id = sub_id if isinstance(sub_id, str) else None
    ts = ts if isinstance(ts, str) else None
    return sub_id, ts


def collect_status(channels: tuple[Channel, ...]) -> CommunityStatus:
    """Compose a :class:`CommunityStatus`. Never raises.

    ``channels`` should be enriched (``is_local_configured`` populated) so the
    configured-count reflects the local environment.
    """
    authenticated, username = _detect_authentication()
    sub_id, ts = _read_last_submission()
    configured = sum(1 for ch in channels if ch.is_local_configured)
    return CommunityStatus(
        authenticated=authenticated,
        authenticated_as=username,
        last_local_submission_id=sub_id,
        last_local_submission_timestamp=ts,
        configured_channel_count=configured,
        total_channel_count=len(channels),
    )


__all__ = ["CommunityStatus", "collect_status"]
