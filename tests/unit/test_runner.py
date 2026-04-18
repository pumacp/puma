"""Unit tests for puma.orchestrator — RunSpec parsing and Runner (dry-run mode)."""

from __future__ import annotations

import pytest

from puma.orchestrator.runspec import RunSpec


def _spec_dict(**overrides) -> dict:
    base = {
        "id": "test_run_v1",
        "description": "Unit test",
        "scenario": "triage_jira",
        "sample_size": 5,
        "models": ["qwen2.5:3b"],
        "adaptation": {"strategy": ["zero-shot"]},
        "inference": {"temperature": 0.0, "seed": 42},
        "metrics": ["f1_macro"],
    }
    base.update(overrides)
    return base


@pytest.mark.unit
class TestRunSpecFromYaml:
    def test_round_trip_yaml(self, tmp_path):
        import yaml

        spec_dict = _spec_dict()
        yaml_file = tmp_path / "spec.yaml"
        yaml_file.write_text(yaml.dump(spec_dict))
        spec = RunSpec.from_yaml(str(yaml_file))
        assert spec.id == "test_run_v1"
        assert spec.scenario == "triage_jira"

    def test_invalid_yaml_raises(self, tmp_path):
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text("scenario: unknown_scenario\nid: x\nmodels: [m]")
        with pytest.raises(ValueError, match="scenario"):
            RunSpec.from_yaml(str(bad_file))


@pytest.mark.unit
class TestRunnerDryRun:
    def _run_spec(self, **overrides) -> RunSpec:
        return RunSpec(**_spec_dict(**overrides))

    def test_dry_run_completes_without_ollama(self, tmp_path):
        from puma.orchestrator.runner import Runner

        spec = self._run_spec(sample_size=3)
        runner = Runner(spec, db_path=tmp_path / "test.db", dry_run=True)
        summary = runner.run()
        assert "run_id" in summary
        assert summary["n_predictions"] >= 0

    def test_dry_run_creates_results_dir(self, tmp_path):
        import puma.orchestrator.runner as runner_mod
        from puma.orchestrator.runner import Runner

        orig_root = runner_mod.RESULTS_ROOT
        runner_mod.RESULTS_ROOT = tmp_path / "results"
        try:
            spec = self._run_spec(sample_size=3)
            runner = Runner(spec, db_path=tmp_path / "test.db", dry_run=True)
            summary = runner.run()
            run_dir = runner_mod.RESULTS_ROOT / summary["run_id"]
            assert run_dir.exists()
            assert (run_dir / "runspec.yaml").exists()
            assert (run_dir / "metrics.json").exists()
        finally:
            runner_mod.RESULTS_ROOT = orig_root

    def test_dry_run_creates_db_tables(self, tmp_path):
        import sqlite3

        from puma.orchestrator.runner import Runner

        db_file = tmp_path / "test.db"
        spec = self._run_spec(sample_size=3)
        runner = Runner(spec, db_path=db_file, dry_run=True)
        runner.run()
        assert db_file.exists()
        conn = sqlite3.connect(db_file)
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        conn.close()
        assert "runs" in tables
        assert "predictions" in tables
        assert "metrics" in tables

    def test_dry_run_run_status_done(self, tmp_path):
        import sqlite3

        from puma.orchestrator.runner import Runner

        db_file = tmp_path / "test.db"
        spec = self._run_spec(sample_size=3)
        runner = Runner(spec, db_path=db_file, dry_run=True)
        summary = runner.run()
        conn = sqlite3.connect(db_file)
        row = conn.execute(
            "SELECT status FROM runs WHERE run_id = ?", (summary["run_id"],)
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == "done"

    def test_spec_hash_in_run_id(self, tmp_path):
        from puma.orchestrator.runner import Runner

        spec = self._run_spec()
        runner = Runner(spec, db_path=tmp_path / "test.db", dry_run=True)
        assert spec.spec_hash() in runner.run_id

    def test_perturbations_generate_extra_predictions(self, tmp_path):
        from puma.orchestrator.runner import Runner

        spec = self._run_spec(sample_size=3, perturbations=["typos_5pct"])
        runner = Runner(spec, db_path=tmp_path / "test.db", dry_run=True)
        summary = runner.run()
        # Each instance should produce 2 predictions: original + typos_5pct
        assert summary["n_predictions"] >= 3
