"""Unit tests for puma.community.channels (S12.13 / E8)."""

from __future__ import annotations

import pytest

from puma.community.channels import (
    CHANNELS,
    detect_local_configuration,
    enrich_with_local_state,
)

_ALL_VARS = ("HF_TOKEN", "ZENODO_TOKEN", "KAGGLE_KEY", "DISCORD_WEBHOOK", "TELEGRAM_BOT_TOKEN")


@pytest.mark.unit
class TestChannelsRegistry:
    def test_channels_registry_has_five_entries(self):
        assert len(CHANNELS) == 5

    def test_channels_registry_includes_hf_zenodo_kaggle_discord_telegram(self):
        names = " ".join(c.name for c in CHANNELS).lower()
        for token in ("hugging face", "zenodo", "kaggle", "discord", "telegram"):
            assert token in names
        secrets = {c.requires_secret for c in CHANNELS}
        assert set(_ALL_VARS) <= secrets


@pytest.mark.unit
class TestDetectLocalConfiguration:
    def test_detect_local_configuration_true_when_env_set(self, monkeypatch):
        monkeypatch.setenv("HF_TOKEN", "hf_dummy")
        hf = next(c for c in CHANNELS if c.requires_secret == "HF_TOKEN")
        assert detect_local_configuration(hf) is True

    def test_detect_local_configuration_false_when_env_unset(self, monkeypatch):
        monkeypatch.delenv("HF_TOKEN", raising=False)
        hf = next(c for c in CHANNELS if c.requires_secret == "HF_TOKEN")
        assert detect_local_configuration(hf) is False

    def test_enrich_with_local_state_marks_configured_correctly(self, monkeypatch):
        for var in _ALL_VARS:
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("DISCORD_WEBHOOK", "https://discord.com/api/webhooks/1/abc")
        enriched = enrich_with_local_state(CHANNELS)
        by_secret = {c.requires_secret: c.is_local_configured for c in enriched}
        assert by_secret["DISCORD_WEBHOOK"] is True
        assert by_secret["HF_TOKEN"] is False
        # The static registry is never mutated by enrichment.
        assert all(c.is_local_configured is False for c in CHANNELS)
