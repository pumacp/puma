"""Unit tests for puma.community.status (S12.13 / E8)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from puma.community.channels import CHANNELS, enrich_with_local_state
from puma.community.status import CommunityStatus, collect_status

_CHANNEL_VARS = ("HF_TOKEN", "ZENODO_TOKEN", "KAGGLE_KEY", "DISCORD_WEBHOOK", "TELEGRAM_BOT_TOKEN")


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    """Isolate HOME (cache + default credential dir) and clear channel env vars."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("PUMA_CONFIG_DIR", raising=False)
    for var in _CHANNEL_VARS:
        monkeypatch.delenv(var, raising=False)
    return tmp_path


def _enriched():
    return tuple(enrich_with_local_state(CHANNELS))


def _write_cache(home: Path, payload: object) -> None:
    cache = home / ".puma" / "last_submission.json"
    cache.parent.mkdir(parents=True, exist_ok=True)
    text = payload if isinstance(payload, str) else json.dumps(payload)
    cache.write_text(text, encoding="utf-8")


@pytest.mark.unit
class TestCollectStatus:
    def test_collect_status_returns_unauthenticated_when_no_credentials(self, isolated):
        status = collect_status(_enriched())
        assert status.authenticated is False
        assert status.authenticated_as is None
        assert status.configured_channel_count == 0
        assert status.total_channel_count == 5

    def test_collect_status_reads_last_submission_when_cache_present(self, isolated):
        _write_cache(
            isolated,
            {"submission_id": "abcd1234-xyz", "timestamp": "2026-05-26T10:00:00Z"},
        )
        status = collect_status(_enriched())
        assert status.last_local_submission_id == "abcd1234-xyz"
        assert status.last_local_submission_timestamp == "2026-05-26T10:00:00Z"

    def test_collect_status_handles_missing_cache_gracefully(self, isolated):
        status = collect_status(_enriched())
        assert status.last_local_submission_id is None
        assert status.last_local_submission_timestamp is None

    def test_collect_status_counts_configured_channels_correctly(self, isolated, monkeypatch):
        monkeypatch.setenv("HF_TOKEN", "x")
        monkeypatch.setenv("ZENODO_TOKEN", "y")
        status = collect_status(_enriched())
        assert status.configured_channel_count == 2

    @pytest.mark.parametrize(
        "payload",
        ["{not valid json", "{}", "[]", '{"submission_id": 123}'],
    )
    def test_collect_status_never_raises_on_bad_cache(self, isolated, payload):
        _write_cache(isolated, payload)
        status = collect_status(_enriched())
        assert isinstance(status, CommunityStatus)
        # Broken/incomplete/wrong-typed cache must degrade to None, not raise.
        assert status.last_local_submission_id is None

    def test_collect_status_never_raises_when_cache_is_a_directory(self, isolated):
        # Reading a directory raises IsADirectoryError (an OSError); must degrade.
        (isolated / ".puma" / "last_submission.json").mkdir(parents=True)
        status = collect_status(_enriched())
        assert status.last_local_submission_id is None

    def test_collect_status_never_raises_when_credential_store_errors(self, isolated, monkeypatch):
        def boom(self, service):  # test stub
            raise RuntimeError("store exploded")

        monkeypatch.setattr("puma.community.credentials.CredentialStore.get", boom)
        status = collect_status(_enriched())
        assert status.authenticated is False
