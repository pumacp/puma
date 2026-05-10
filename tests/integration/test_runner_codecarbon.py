"""Integration tests for CodeCarbon wiring in the Runner.

Tests 1-2 mock the EmissionsTracker to assert the runner calls .start()
and .stop() exactly when the spec flag dictates. Tests 3-5 execute a real
(dry-run) end-to-end pipeline to verify that an Emission row is persisted
with the expected fields and FK integrity.

All five tests fail until B.1.4.c.2 wires the orchestrator to consult
``spec.sustainability.codecarbon`` and persist an Emission row.
"""

from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from puma.orchestrator.runner import Runner
from puma.orchestrator.runspec import RunSpec


def _make_spec(*, codecarbon: bool = True, sample_size: int = 3) -> RunSpec:
    return RunSpec(
        id="test_codecarbon",
        description="B.1.4 test",
        scenario="triage_jira",
        sample_size=sample_size,
        models=["qwen2.5:1.5b"],
        adaptation={"strategy": ["contextual-anchoring"]},
        inference={"temperature": 0.0, "seed": 42, "max_tokens": 128},
        sustainability={"codecarbon": codecarbon},
    )


def _mock_tracker_factory() -> MagicMock:
    """Build a MagicMock tracker with realistic .final_emissions_data shape."""
    factory = MagicMock()
    instance = factory.return_value
    instance.start.return_value = None
    instance.stop.return_value = 0.0001  # kg CO2

    emission_data = MagicMock()
    emission_data.energy_consumed = 0.000010  # kWh
    emission_data.emissions = 0.0000001  # kg CO2
    emission_data.duration = 1.5  # seconds
    emission_data.cpu_energy = 0.000004
    emission_data.gpu_energy = 0.000000
    emission_data.ram_energy = 0.000006
    instance.final_emissions_data = emission_data
    return factory


@pytest.mark.integration
def test_runner_invokes_tracker_when_flag_true(tmp_path):
    """AC: Runner.run() with sustainability.codecarbon=True calls tracker
    .start() and .stop() exactly once each."""
    spec = _make_spec(codecarbon=True)
    db = tmp_path / "test.db"
    factory = _mock_tracker_factory()
    instance = factory.return_value

    with patch("codecarbon.EmissionsTracker", factory):
        runner = Runner(spec, db_path=db, dry_run=True)
        runner.run()

    factory.assert_called_once()
    instance.start.assert_called_once()
    instance.stop.assert_called_once()


@pytest.mark.integration
def test_runner_skips_tracker_when_flag_false(tmp_path):
    """AC: Runner.run() with sustainability.codecarbon=False never imports
    or instantiates the EmissionsTracker."""
    spec = _make_spec(codecarbon=False)
    db = tmp_path / "test.db"
    factory = _mock_tracker_factory()

    with patch("codecarbon.EmissionsTracker", factory):
        runner = Runner(spec, db_path=db, dry_run=True)
        runner.run()

    factory.assert_not_called()


@pytest.mark.integration
def test_emissions_row_persisted_after_real_run(tmp_path):
    """AC: After Runner.run() with codecarbon=True, exactly one Emission
    row exists in the DB for that run_id."""
    spec = _make_spec(codecarbon=True, sample_size=3)
    db = tmp_path / "test.db"

    runner = Runner(spec, db_path=db, dry_run=True)
    summary = runner.run()

    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM emissions WHERE run_id = ?", (summary["run_id"],))
    count = cur.fetchone()[0]
    assert count == 1, f"expected 1 emissions row for {summary['run_id']}, got {count}"


@pytest.mark.integration
def test_emissions_row_has_required_fields(tmp_path):
    """AC: The Emission row populates kwh, co2_kg, duration_s, cpu/gpu/ram
    energy, recorded_at — all non-null, all non-negative; duration > 0."""
    spec = _make_spec(codecarbon=True, sample_size=3)
    db = tmp_path / "test.db"

    runner = Runner(spec, db_path=db, dry_run=True)
    summary = runner.run()

    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT kwh, co2_kg, duration_s, cpu_energy, gpu_energy, ram_energy, recorded_at
        FROM emissions WHERE run_id = ?
        """,
        (summary["run_id"],),
    )
    row = cur.fetchone()
    assert row is not None
    kwh, co2_kg, duration_s, cpu_energy, gpu_energy, ram_energy, recorded_at = row

    assert duration_s is not None and duration_s > 0, f"duration_s must be > 0, got {duration_s}"
    assert recorded_at is not None, "recorded_at must not be null"
    for val, name in [
        (kwh, "kwh"),
        (co2_kg, "co2_kg"),
        (cpu_energy, "cpu_energy"),
        (gpu_energy, "gpu_energy"),
        (ram_energy, "ram_energy"),
    ]:
        assert val is not None, f"{name} is None"
        assert val >= 0, f"{name} negative: {val}"


@pytest.mark.integration
def test_emissions_row_fk_integrity(tmp_path):
    """AC: The run_id foreign key in emissions joins back to a row in runs."""
    spec = _make_spec(codecarbon=True, sample_size=3)
    db = tmp_path / "test.db"

    runner = Runner(spec, db_path=db, dry_run=True)
    summary = runner.run()

    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT e.run_id FROM emissions e
        JOIN runs r ON r.run_id = e.run_id
        WHERE e.run_id = ?
        """,
        (summary["run_id"],),
    )
    row = cur.fetchone()
    assert row is not None, "FK integrity violated: emissions row has no matching runs entry"
