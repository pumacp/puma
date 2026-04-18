"""Smoke tests for the PUMA Streamlit dashboard using AppTest."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

APP_PATH = Path(__file__).parent.parent.parent / "src" / "puma" / "dashboard" / "app.py"


def _seed_db(db_path: Path) -> str:
    """Create minimal DB state and return a run_id."""
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            spec_hash TEXT,
            spec_yaml TEXT,
            profile TEXT,
            started_at TEXT,
            finished_at TEXT,
            status TEXT
        );
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT,
            scope TEXT,
            metric_name TEXT,
            value REAL,
            computed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT,
            instance_id TEXT,
            model TEXT,
            strategy TEXT,
            prompt_hash TEXT,
            raw_response TEXT,
            parsed_label TEXT,
            gold_label TEXT,
            latency_ms REAL,
            tokens_in INTEGER,
            tokens_out INTEGER,
            perturbation TEXT,
            seed INTEGER,
            recorded_at TEXT
        );
        CREATE TABLE IF NOT EXISTS instances (
            instance_id TEXT PRIMARY KEY,
            dataset TEXT,
            source_id TEXT,
            input_text TEXT,
            gold_label TEXT
        );
        CREATE TABLE IF NOT EXISTS profile_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT,
            os TEXT,
            cpu TEXT,
            ram_gb REAL,
            gpu TEXT,
            vram_gb REAL,
            ollama_version TEXT,
            puma_version TEXT,
            snapshot_at TEXT
        );
        CREATE TABLE IF NOT EXISTS emissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT,
            kwh REAL,
            co2_kg REAL,
            duration_s REAL,
            recorded_at TEXT
        );
    """)
    run_id = "smoke_run_001__abcdef__20260418T000000"
    conn.execute(
        "INSERT INTO runs VALUES (?,?,?,?,?,?,?)",
        (run_id, "abcdef", "{}", "cpu-lite", "2026-04-18T00:00:00", "2026-04-18T00:01:00", "done"),
    )
    conn.execute(
        "INSERT INTO metrics (run_id,scope,metric_name,value) VALUES (?,?,?,?)",
        (run_id, "global", "f1_macro", 0.72),
    )
    conn.execute(
        "INSERT INTO metrics (run_id,scope,metric_name,value) VALUES (?,?,?,?)",
        (run_id, "global", "accuracy", 0.75),
    )
    conn.execute(
        "INSERT INTO metrics (run_id,scope,metric_name,value) VALUES (?,?,?,?)",
        (run_id, "global", "parse_failure_rate", 0.05),
    )
    conn.execute(
        "INSERT INTO predictions (run_id,instance_id,model,strategy,prompt_hash,"
        "raw_response,parsed_label,gold_label,latency_ms,tokens_in,tokens_out,seed)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (run_id, "INST-001", "qwen2.5:3b", "zero-shot", "abc123",
         "The answer is Critical.", "Critical", "Critical", 350.0, 120, 30, 42),
    )
    conn.commit()
    conn.close()
    return run_id


@pytest.mark.smoke
class TestDashboardSmoke:
    """Smoke-level tests: app loads and all views render without exceptions."""

    def _at(self, tmp_path: Path):
        from streamlit.testing.v1 import AppTest

        db = tmp_path / "puma.db"
        _seed_db(db)
        at = AppTest.from_file(str(APP_PATH))
        at.secrets = {}
        return at, db

    def _run_with_db(self, at, db_path: Path):
        """Patch DB_PATH in the module namespace then run."""
        import puma.dashboard.app as app_mod
        import puma.dashboard.data as data_mod

        orig_app = app_mod.DB_PATH
        orig_data = data_mod._DEFAULT_DB
        app_mod.DB_PATH = db_path
        data_mod._DEFAULT_DB = db_path
        try:
            at.run(timeout=30)
        finally:
            app_mod.DB_PATH = orig_app
            data_mod._DEFAULT_DB = orig_data
        return at

    def test_app_loads_without_error(self, tmp_path):
        at, db = self._at(tmp_path)
        result = self._run_with_db(at, db)
        assert not result.exception, f"App raised: {result.exception}"

    def test_overview_has_title(self, tmp_path):
        at, db = self._at(tmp_path)
        result = self._run_with_db(at, db)
        assert not result.exception
        # Overview renders at least a title element
        assert len(result.title) >= 1

    def test_no_data_renders_info(self, tmp_path):
        from streamlit.testing.v1 import AppTest

        empty_db = tmp_path / "empty.db"
        at = AppTest.from_file(str(APP_PATH))

        import puma.dashboard.app as app_mod
        import puma.dashboard.data as data_mod

        orig_app = app_mod.DB_PATH
        orig_data = data_mod._DEFAULT_DB
        app_mod.DB_PATH = empty_db
        data_mod._DEFAULT_DB = empty_db
        try:
            at.run(timeout=30)
        finally:
            app_mod.DB_PATH = orig_app
            data_mod._DEFAULT_DB = orig_data
        assert not at.exception
