"""Tests for the PUMA Community credential store."""

from __future__ import annotations

import logging
import stat
import sys
from pathlib import Path

import pytest

from puma.community.credentials import (
    CredentialStore,
    InsecurePermissionsError,
    InvalidTokenFormatError,
    mask_token,
)

VALID_GITHUB_PAT = "ghp_" + "a" * 36
VALID_GITHUB_FINEGRAINED = "github_pat_" + "a" * 82
VALID_HF_TOKEN = "hf_" + "b" * 36
VALID_DISCORD = "https://discord.com/api/webhooks/12345/" + "x" * 40
VALID_ZENODO = "z" * 60
VALID_TELEGRAM_BOT = "1234567890:" + "x" * 35
VALID_TELEGRAM_CHAT = "-1001234567890"


@pytest.fixture
def store(tmp_path: Path, monkeypatch) -> CredentialStore:
    """Isolated credential store rooted in ``tmp_path``."""
    monkeypatch.setenv("PUMA_CONFIG_DIR", str(tmp_path / "puma-config"))
    return CredentialStore()


def test_create_credentials_file_with_correct_mode(store: CredentialStore) -> None:
    store.set("github", VALID_GITHUB_PAT)
    assert store.path.exists()
    if sys.platform != "win32":
        mode = stat.S_IMODE(store.path.stat().st_mode)
        assert mode == 0o600, f"expected 0600, got {oct(mode)}"


def test_get_returns_none_for_missing_service(store: CredentialStore) -> None:
    assert store.get("github") is None


def test_set_persists_value(store: CredentialStore) -> None:
    store.set("github", VALID_GITHUB_PAT)
    assert store.get("github") == VALID_GITHUB_PAT


def test_set_validates_github_pat_format(store: CredentialStore) -> None:
    with pytest.raises(InvalidTokenFormatError):
        store.set("github", "not-a-github-token")


def test_set_validates_github_fine_grained_pat(store: CredentialStore) -> None:
    store.set("github", VALID_GITHUB_FINEGRAINED)
    assert store.get("github") == VALID_GITHUB_FINEGRAINED


def test_set_validates_huggingface_token_format(store: CredentialStore) -> None:
    with pytest.raises(InvalidTokenFormatError):
        store.set("huggingface", "hf_short")
    store.set("huggingface", VALID_HF_TOKEN)
    assert store.get("huggingface") == VALID_HF_TOKEN


def test_set_validates_discord_webhook_url(store: CredentialStore) -> None:
    with pytest.raises(InvalidTokenFormatError):
        store.set("discord_webhook", "https://example.com/not-discord")
    store.set("discord_webhook", VALID_DISCORD)


def test_set_validates_zenodo_and_telegram_formats(store: CredentialStore) -> None:
    store.set("zenodo", VALID_ZENODO)
    store.set("telegram_bot", VALID_TELEGRAM_BOT)
    store.set("telegram_chat_id", VALID_TELEGRAM_CHAT)
    with pytest.raises(InvalidTokenFormatError):
        store.set("zenodo", "too-short")
    with pytest.raises(InvalidTokenFormatError):
        store.set("telegram_chat_id", "abc")


def test_unknown_service_raises(store: CredentialStore) -> None:
    with pytest.raises(InvalidTokenFormatError):
        store.set("unknown_service", "anything")


def test_delete_removes_token(store: CredentialStore) -> None:
    store.set("github", VALID_GITHUB_PAT)
    assert store.delete("github") is True
    assert store.get("github") is None
    assert store.delete("github") is False


def test_list_services_does_not_return_values(store: CredentialStore) -> None:
    store.set("github", VALID_GITHUB_PAT)
    store.set("huggingface", VALID_HF_TOKEN)
    services = store.list_services()
    assert set(services) == {"github", "huggingface"}
    assert VALID_GITHUB_PAT not in services
    assert VALID_HF_TOKEN not in services


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only permission semantics")
def test_insecure_permissions_raise_on_posix(store: CredentialStore) -> None:
    store.set("github", VALID_GITHUB_PAT)
    store.path.chmod(0o644)
    assert store.verify_permissions() is False
    with pytest.raises(InsecurePermissionsError):
        store.get("github")


def test_logging_never_includes_token_value(
    store: CredentialStore, caplog: pytest.LogCaptureFixture
) -> None:
    """Set + get + delete + list — no log record may contain the raw token."""
    with caplog.at_level(logging.DEBUG, logger="puma.community.credentials"):
        store.set("github", VALID_GITHUB_PAT)
        store.get("github")
        store.list_services()
        store.delete("github")
    for record in caplog.records:
        message = record.getMessage()
        assert VALID_GITHUB_PAT not in message
        assert "ghp_aaaaaaaa" not in message  # any token-prefix substring


def test_mask_token_format() -> None:
    assert mask_token(VALID_GITHUB_PAT).startswith("ghp_***")
    assert mask_token(VALID_GITHUB_PAT).endswith(VALID_GITHUB_PAT[-4:])
    assert mask_token("") == "***"
    short_masked = mask_token("abc")
    assert "abc" not in short_masked  # short tokens fully redacted
    plain = mask_token("plaintoken1234")
    assert plain.endswith("1234")
    assert "plaintoken" not in plain


def test_real_config_directory_is_never_touched(
    tmp_path: Path, monkeypatch
) -> None:
    """Sanity check: with PUMA_CONFIG_DIR set, nothing is written outside tmp_path."""
    monkeypatch.setenv("PUMA_CONFIG_DIR", str(tmp_path / "puma-config"))
    store = CredentialStore()
    store.set("github", VALID_GITHUB_PAT)
    assert str(tmp_path) in str(store.path)
    assert "~/.config/puma" not in str(store.path.resolve())
