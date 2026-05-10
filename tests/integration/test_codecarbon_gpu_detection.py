"""Integration tests for D15 — CodeCarbon GPU detection inside the runner container.

Pre-D15 the runner container had no GPU passthrough; pynvml could not
load ``libnvidia-ml.so.1`` and CodeCarbon reported ``gpu_energy = 0``
on every emission row. Post-D15 the container declares the same CDI
device passthrough as ``puma_ollama`` and the orchestrator uses
``tracking_mode='machine'`` so whole-host GPU energy (dominated by
Ollama inference during a run) is captured.

Tests are gated on ``requires_gpu`` so they automatically skip on hosts
without an NVIDIA GPU (e.g. the CI runners).
"""

from __future__ import annotations

import sqlite3

import pytest

from puma.orchestrator.runner import Runner
from puma.orchestrator.runspec import RunSpec


def _has_nvidia_gpu() -> bool:
    """True iff pynvml can talk to a real GPU on this host."""
    try:
        import pynvml

        pynvml.nvmlInit()
        return pynvml.nvmlDeviceGetCount() > 0
    except Exception:
        return False


_HOST_HAS_GPU = _has_nvidia_gpu()


@pytest.mark.requires_gpu
@pytest.mark.skipif(not _HOST_HAS_GPU, reason="No NVIDIA GPU passthrough available")
def test_pynvml_initializes_inside_container() -> None:
    """The container must expose libnvidia-ml.so so pynvml can talk to the driver."""
    import pynvml

    pynvml.nvmlInit()
    n = pynvml.nvmlDeviceGetCount()
    assert n >= 1, f"Expected at least one GPU, got {n}"
    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
    name = pynvml.nvmlDeviceGetName(handle)
    assert name, "GPU device name was empty"


@pytest.mark.requires_gpu
@pytest.mark.skipif(not _HOST_HAS_GPU, reason="No NVIDIA GPU passthrough available")
def test_codecarbon_measures_gpu_energy() -> None:
    """CodeCarbon's whole-machine tracker must accumulate GPU energy.

    Asserts on ``_total_gpu_energy`` (the actual output) rather than
    ``_gpu_ids`` (a CodeCarbon-internal attribute that varies between
    tracking modes).
    """
    from codecarbon import EmissionsTracker

    tracker = EmissionsTracker(
        project_name="puma_d15_test",
        tracking_mode="machine",
        save_to_file=False,
        log_level="error",
        allow_multiple_runs=True,
    )
    tracker.start()
    import time

    time.sleep(2)
    tracker.stop()

    total_gpu_energy = getattr(tracker, "_total_gpu_energy", None)
    # CodeCarbon wraps the value in an Energy type; .kWh exposes the float.
    kwh = getattr(total_gpu_energy, "kWh", None) if total_gpu_energy is not None else None
    assert kwh is not None and kwh > 0, (
        f"CodeCarbon did not accumulate GPU energy "
        f"(_total_gpu_energy={total_gpu_energy!r}, kWh={kwh!r})"
    )


@pytest.mark.requires_gpu
@pytest.mark.skipif(not _HOST_HAS_GPU, reason="No NVIDIA GPU passthrough available")
def test_emissions_row_has_positive_gpu_energy(tmp_path) -> None:
    """End-to-end: a real Runner pass with codecarbon=True yields gpu_energy > 0.

    Uses ``dry_run=True`` so the run completes quickly without invoking
    Ollama. The codecarbon tracker still measures real machine energy
    during the dry-run window, which on a host with an idle GPU is
    small but non-zero (the GPU draws baseline power).
    """
    spec = RunSpec(
        id="d15_gpu_check",
        description="D15 smoke",
        scenario="triage_jira",
        sample_size=3,
        models=["qwen2.5:1.5b"],
        adaptation={"strategy": ["zero-shot"]},
        inference={"temperature": 0.0, "seed": 42, "max_tokens": 32},
        sustainability={"codecarbon": True},
    )
    db = tmp_path / "test.db"
    summary = Runner(spec, db_path=db, dry_run=True).run()

    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute(
        "SELECT gpu_energy, kwh, co2_kg, duration_s FROM emissions WHERE run_id = ?",
        (summary["run_id"],),
    )
    row = cur.fetchone()
    assert row is not None, "no emissions row persisted"
    gpu_energy, kwh, co2_kg, duration_s = row

    assert duration_s > 0, f"duration must be positive, got {duration_s}"
    assert kwh >= 0, f"kwh must be non-negative, got {kwh}"
    assert co2_kg >= 0, f"co2_kg must be non-negative, got {co2_kg}"
    assert gpu_energy is not None and gpu_energy > 0, (
        f"GPU energy must be positive after D15 fix; got {gpu_energy!r}. "
        "If this fails, either GPU passthrough is missing or "
        "tracking_mode reverted to 'process'."
    )
