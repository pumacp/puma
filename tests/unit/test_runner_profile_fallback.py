"""Unit tests for the D24 fix.

Covers ``_resolve_run_profile`` in ``puma.orchestrator.runner``: specs that
declare ``profile_required`` keep precedence, while specs that omit it fall
back to the existing hardware auto-detection (``select_profile``) so
``Run.profile`` is never left NULL (which the share-results builder rejects
at ``builder.py:320-321``).
"""

from __future__ import annotations

import types

import pytest
from structlog.testing import capture_logs

from puma.orchestrator.runner import _resolve_run_profile


def _spec(profile_required):
    """Minimal stand-in exposing only the attribute the resolver reads."""
    return types.SimpleNamespace(profile_required=profile_required)


def _patch_autodetect(monkeypatch, profile_name):
    monkeypatch.setattr(
        "puma.preflight.detect.detect_capabilities",
        lambda: object(),
    )
    monkeypatch.setattr(
        "puma.preflight.profile.select_profile",
        lambda _caps: types.SimpleNamespace(name=profile_name),
    )


@pytest.mark.unit
class TestRunnerProfileFallback:
    def test_runner_uses_spec_profile_when_declared(self, monkeypatch):
        # Auto-detect is patched to a distinct value to prove it is NOT used.
        _patch_autodetect(monkeypatch, "gpu-mid")
        result = _resolve_run_profile(_spec("gpu-entry"))
        assert result == "gpu-entry"

    def test_runner_falls_back_to_autodetect_when_spec_omits(self, monkeypatch):
        _patch_autodetect(monkeypatch, "gpu-mid")
        result = _resolve_run_profile(_spec(None))
        assert result == "gpu-mid"

    def test_runner_logs_info_when_falling_back(self, monkeypatch):
        _patch_autodetect(monkeypatch, "gpu-mid")
        with capture_logs() as logs:
            _resolve_run_profile(_spec(None))
        events = [e for e in logs if e.get("event") == "run.profile_autodetected"]
        assert len(events) == 1
        assert events[0]["profile"] == "gpu-mid"
        assert events[0]["log_level"] == "info"
