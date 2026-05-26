"""Unit tests for the puma doctor environment checks (US-12.13)."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import httpx
import pytest

from puma.diagnostics.checks import (
    CheckResult,
    check_codecarbon_available,
    check_database_accessible,
    check_hardware_profile,
    check_ollama_models,
    check_ollama_reachable,
    check_python_version,
    check_required_baselines_present,
    run_all_checks,
)


class _FakeResp:
    def __init__(self, status_code: int = 200, payload: dict | None = None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPError(f"HTTP {self.status_code}")


@pytest.mark.unit
class TestChecks:
    def test_check_python_version_ok_on_current(self):
        assert check_python_version().status == "ok"

    def test_check_ollama_reachable_ok_when_200(self, monkeypatch):
        monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResp(200))
        assert check_ollama_reachable("http://h:11434").status == "ok"

    def test_check_ollama_reachable_fail_on_timeout(self, monkeypatch):
        def boom(*a, **k):
            raise httpx.TimeoutException("timeout")

        monkeypatch.setattr(httpx, "get", boom)
        result = check_ollama_reachable("http://h:11434")
        assert result.status == "fail"
        assert result.hint

    def test_check_ollama_reachable_fail_on_connection_error(self, monkeypatch):
        def boom(*a, **k):
            raise httpx.ConnectError("refused")

        monkeypatch.setattr(httpx, "get", boom)
        assert check_ollama_reachable("http://h:11434").status == "fail"

    def test_check_ollama_models_ok_when_all_present(self, monkeypatch):
        payload = {"models": [{"name": "qwen2.5:3b"}, {"name": "llama3:8b"}]}
        monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResp(200, payload))
        assert check_ollama_models("http://h:11434", ["qwen2.5:3b"]).status == "ok"

    def test_check_ollama_models_warn_when_some_missing(self, monkeypatch):
        payload = {"models": [{"name": "llama3:8b"}]}
        monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResp(200, payload))
        result = check_ollama_models("http://h:11434", ["qwen2.5:3b"])
        assert result.status == "warn"
        assert "qwen2.5:3b" in result.detail

    def test_check_ollama_models_fail_when_api_unreachable(self, monkeypatch):
        def boom(*a, **k):
            raise httpx.ConnectError("refused")

        monkeypatch.setattr(httpx, "get", boom)
        assert check_ollama_models("http://h:11434", ["qwen2.5:3b"]).status == "fail"

    def test_check_hardware_profile_reuses_existing_detector(self, monkeypatch):
        import puma.preflight.profile as prof

        called: dict[str, bool] = {}
        real = prof.select_profile

        def spy(caps, *a, **k):
            called["select_profile"] = True
            return real(caps, *a, **k)

        monkeypatch.setattr(prof, "select_profile", spy)
        result = check_hardware_profile()
        assert called.get("select_profile") is True
        assert result.status in ("ok", "warn")

    def test_check_codecarbon_available_ok_when_imported(self):
        assert check_codecarbon_available().status == "ok"

    def test_check_codecarbon_available_fail_when_missing(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "codecarbon", None)
        assert check_codecarbon_available().status == "fail"

    def test_check_database_accessible_ok_when_valid_sqlite(self, tmp_path):
        db = tmp_path / "ok.db"
        con = sqlite3.connect(db)
        con.execute("CREATE TABLE t (x INTEGER)")
        con.commit()
        con.close()
        assert check_database_accessible(db).status == "ok"

    def test_check_database_accessible_warn_when_missing(self, tmp_path):
        assert check_database_accessible(tmp_path / "nope.db").status == "warn"

    def test_check_database_accessible_fail_when_corrupt(self, tmp_path):
        bad = tmp_path / "bad.db"
        bad.write_bytes(b"this is definitely not a sqlite database")
        assert check_database_accessible(bad).status == "fail"

    def test_check_required_baselines_present_ok_when_both_exist(self, tmp_path):
        (tmp_path / "baseline_triage.yaml").write_text("x")
        (tmp_path / "baseline_estimation_canonical.yaml").write_text("x")
        assert check_required_baselines_present(tmp_path).status == "ok"

    def test_run_all_checks_runs_in_order_and_returns_all(self, monkeypatch):
        payload = {"models": [{"name": "qwen2.5:3b"}]}
        monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResp(200, payload))
        results = run_all_checks(db_path=Path("/tmp/x.db"), specs_dir=Path("/tmp"))
        assert [r.name for r in results] == [
            "Python",
            "CodeCarbon",
            "Ollama reachable",
            "Ollama models",
            "Hardware profile",
            "Database",
            "Baseline specs",
        ]
        assert all(isinstance(r, CheckResult) for r in results)

    def test_no_check_raises_on_any_input(self, monkeypatch):
        def boom(*a, **k):
            raise RuntimeError("network down")

        monkeypatch.setattr(httpx, "get", boom)
        results = [
            check_python_version(),
            check_codecarbon_available(),
            check_ollama_reachable("http://bad"),
            check_ollama_models("http://bad", ["x"]),
            check_hardware_profile(),
            check_database_accessible(Path("/no/such/path.db")),
            check_required_baselines_present(Path("/no/such/dir")),
        ]
        assert all(isinstance(r, CheckResult) for r in results)
