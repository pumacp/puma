"""Tests for the PUMA Community local rate limiter."""

from __future__ import annotations

import sqlite3
import stat
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from puma.community.ratelimit import LocalRateLimiter


@pytest.fixture
def limiter(tmp_path: Path) -> LocalRateLimiter:
    return LocalRateLimiter(db_path=tmp_path / "ratelimit.db")


def test_can_submit_when_fresh(limiter: LocalRateLimiter) -> None:
    ok, reason = limiter.can_submit(submitter_alias="alice")
    assert ok is True
    assert reason == "ok"


def test_cooldown_blocks_within_window(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PUMA_RATE_LIMIT_COOLDOWN_S", "60")
    monkeypatch.setenv("PUMA_RATE_LIMIT_DAILY", "99")
    limiter = LocalRateLimiter(db_path=tmp_path / "ratelimit.db")
    limiter.record_submission(submitter_alias="alice", submission_id="sub-1")
    ok, reason = limiter.can_submit(submitter_alias="alice")
    assert ok is False
    assert "Cooldown active" in reason


def test_daily_limit_blocks_after_n(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PUMA_RATE_LIMIT_DAILY", "2")
    monkeypatch.setenv("PUMA_RATE_LIMIT_COOLDOWN_S", "0")
    db_path = tmp_path / "ratelimit.db"
    limiter = LocalRateLimiter(db_path=db_path)

    base = datetime.now(UTC) - timedelta(minutes=30)
    with sqlite3.connect(db_path) as conn:
        for i in range(2):
            conn.execute(
                "INSERT INTO submissions(submitter_alias, submission_id, timestamp_utc) "
                "VALUES (?, ?, ?)",
                (
                    "alice",
                    f"sub-{i}",
                    (base + timedelta(seconds=i)).isoformat(),
                ),
            )
        conn.commit()

    ok, reason = limiter.can_submit(submitter_alias="alice")
    assert ok is False
    assert "Daily limit of 2 reached" in reason
    assert "Try again after" in reason


def test_old_submissions_do_not_count(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PUMA_RATE_LIMIT_DAILY", "1")
    monkeypatch.setenv("PUMA_RATE_LIMIT_COOLDOWN_S", "0")
    db_path = tmp_path / "ratelimit.db"
    limiter = LocalRateLimiter(db_path=db_path)

    stale = (datetime.now(UTC) - timedelta(hours=48)).isoformat()
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO submissions(submitter_alias, submission_id, timestamp_utc) "
            "VALUES (?, ?, ?)",
            ("alice", "old-sub", stale),
        )
        conn.commit()

    ok, _ = limiter.can_submit(submitter_alias="alice")
    assert ok is True
    assert limiter.recent_submissions(hours=24) == []


def test_recent_submissions_returns_correct_list(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PUMA_RATE_LIMIT_COOLDOWN_S", "0")
    limiter = LocalRateLimiter(db_path=tmp_path / "ratelimit.db")
    limiter.record_submission(submitter_alias="alice", submission_id="s1")
    limiter.record_submission(submitter_alias="alice", submission_id="s2")
    limiter.record_submission(submitter_alias="bob", submission_id="s3")
    rows = limiter.recent_submissions(hours=24)
    assert len(rows) == 3
    keys = {"submitter_alias", "submission_id", "timestamp_utc"}
    for row in rows:
        assert keys.issubset(row.keys())
    ids = {row["submission_id"] for row in rows}
    assert ids == {"s1", "s2", "s3"}


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only permission semantics")
def test_db_created_with_safe_permissions(tmp_path: Path) -> None:
    db_path = tmp_path / "ratelimit.db"
    LocalRateLimiter(db_path=db_path)
    assert db_path.exists()
    mode = stat.S_IMODE(db_path.stat().st_mode)
    assert mode == 0o600


def test_ratelimit_db_is_isolated_from_academic_db(tmp_path: Path, monkeypatch) -> None:
    """Rate limiter must NOT touch ``data/puma.db`` or any SQLAlchemy session."""
    db_path = tmp_path / "ratelimit.db"
    limiter = LocalRateLimiter(db_path=db_path)
    limiter.record_submission(submitter_alias="alice", submission_id="x")
    # ratelimit DB is the only file written under tmp_path.
    files_written = list(tmp_path.glob("**/*"))
    assert all(p.name in {"ratelimit.db"} or p.is_dir() for p in files_written)
