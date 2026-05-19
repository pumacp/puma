"""Local rate limiter for PUMA Community submissions.

Tracks recent submissions in a stdlib ``sqlite3`` database, completely isolated
from the academic PUMA SQLite at ``data/puma.db``. Two limits are enforced:

* **Daily limit** — at most N submissions per rolling 24h window
  (default 5, override via ``PUMA_RATE_LIMIT_DAILY``).
* **Cooldown** — minimum S seconds between consecutive submissions
  (default 60, override via ``PUMA_RATE_LIMIT_COOLDOWN_S``).

The DB lives at ``~/.cache/puma/ratelimit.db`` (or the path injected by the
caller for tests). The file is created with mode 0600 on POSIX.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

log = logging.getLogger("puma.community.ratelimit")

_DEFAULT_DAILY: int = 5
_DEFAULT_COOLDOWN_S: int = 60
_DIR_MODE: int = 0o700
_FILE_MODE: int = 0o600

_SCHEMA: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS submissions (
        submitter_alias TEXT NOT NULL,
        submission_id   TEXT NOT NULL PRIMARY KEY,
        timestamp_utc   TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_ts ON submissions(timestamp_utc)",
)


def _default_db_path() -> Path:
    """Return ``~/.cache/puma/ratelimit.db`` (or ``PUMA_CACHE_DIR`` override)."""
    override = os.environ.get("PUMA_CACHE_DIR")
    if override:
        return Path(override) / "ratelimit.db"
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA")
        base = Path(local) if local else Path.home() / "AppData" / "Local"
        return base / "puma" / "cache" / "ratelimit.db"
    return Path.home() / ".cache" / "puma" / "ratelimit.db"


def _read_int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        log.warning("env %s=%r is not an integer; falling back to %d.", name, raw, default)
        return default


class LocalRateLimiter:
    """Tracks recent submissions in a dedicated sqlite3 DB."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = Path(db_path) if db_path is not None else _default_db_path()
        self._daily_limit = _read_int_env("PUMA_RATE_LIMIT_DAILY", _DEFAULT_DAILY)
        self._cooldown_s = _read_int_env("PUMA_RATE_LIMIT_COOLDOWN_S", _DEFAULT_COOLDOWN_S)
        self._initialise()

    @property
    def db_path(self) -> Path:
        return self._db_path

    @property
    def daily_limit(self) -> int:
        return self._daily_limit

    @property
    def cooldown_seconds(self) -> int:
        return self._cooldown_s

    # ── public API ──────────────────────────────────────────────────────────

    def can_submit(self, *, submitter_alias: str) -> tuple[bool, str]:
        now = datetime.now(UTC)
        with self._connect() as conn:
            last_ts = self._last_timestamp(conn, submitter_alias)
            if last_ts is not None:
                elapsed = (now - last_ts).total_seconds()
                if elapsed < self._cooldown_s:
                    remaining = int(self._cooldown_s - elapsed)
                    return False, f"Cooldown active. Try again in {remaining} seconds."

            window_start = now - timedelta(hours=24)
            recent = self._count_since(conn, submitter_alias, window_start)
            if recent >= self._daily_limit:
                oldest = self._oldest_in_window(conn, submitter_alias, window_start)
                if oldest is not None:
                    next_slot = oldest + timedelta(hours=24)
                    return (
                        False,
                        f"Daily limit of {self._daily_limit} reached. "
                        f"Try again after {next_slot.isoformat()}.",
                    )
                return (
                    False,
                    f"Daily limit of {self._daily_limit} reached.",
                )

        return True, "ok"

    def record_submission(self, *, submitter_alias: str, submission_id: str) -> None:
        ts = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO submissions(submitter_alias, submission_id, timestamp_utc) "
                "VALUES (?, ?, ?)",
                (submitter_alias, submission_id, ts),
            )
            conn.commit()
        log.info("recorded submission %s for %s at %s", submission_id, submitter_alias, ts)

    def recent_submissions(self, *, hours: int = 24) -> list[dict[str, Any]]:
        cutoff = (datetime.now(UTC) - timedelta(hours=hours)).isoformat()
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT submitter_alias, submission_id, timestamp_utc "
                "FROM submissions WHERE timestamp_utc >= ? ORDER BY timestamp_utc DESC",
                (cutoff,),
            ).fetchall()
        return [
            {
                "submitter_alias": row[0],
                "submission_id": row[1],
                "timestamp_utc": row[2],
            }
            for row in rows
        ]

    # ── internals ───────────────────────────────────────────────────────────

    def _initialise(self) -> None:
        parent = self._db_path.parent
        parent.mkdir(parents=True, exist_ok=True)
        if sys.platform != "win32":
            try:
                parent.chmod(_DIR_MODE)
            except OSError as exc:  # pragma: no cover — defensive
                log.debug("could not tighten cache dir mode: %s", exc)
        is_new = not self._db_path.exists()
        with self._connect() as conn:
            for stmt in _SCHEMA:
                conn.execute(stmt)
            conn.commit()
        if is_new and sys.platform != "win32":
            os.chmod(self._db_path, _FILE_MODE)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _last_timestamp(self, conn: sqlite3.Connection, alias: str) -> datetime | None:
        row = conn.execute(
            "SELECT timestamp_utc FROM submissions WHERE submitter_alias = ? "
            "ORDER BY timestamp_utc DESC LIMIT 1",
            (alias,),
        ).fetchone()
        if row is None:
            return None
        return datetime.fromisoformat(row[0])

    def _count_since(self, conn: sqlite3.Connection, alias: str, since: datetime) -> int:
        row = conn.execute(
            "SELECT COUNT(*) FROM submissions WHERE submitter_alias = ? AND timestamp_utc >= ?",
            (alias, since.isoformat()),
        ).fetchone()
        return int(row[0])

    def _oldest_in_window(
        self, conn: sqlite3.Connection, alias: str, since: datetime
    ) -> datetime | None:
        row = conn.execute(
            "SELECT timestamp_utc FROM submissions "
            "WHERE submitter_alias = ? AND timestamp_utc >= ? "
            "ORDER BY timestamp_utc ASC LIMIT 1",
            (alias, since.isoformat()),
        ).fetchone()
        if row is None:
            return None
        return datetime.fromisoformat(row[0])


__all__ = ["LocalRateLimiter"]
