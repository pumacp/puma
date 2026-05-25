"""Unit tests for the D26 fix.

Covers ``_collect_profile_extra`` (ProfileSnapshot.extra population) and
``_resolve_runner_puma_version`` (dynamic version lookup) in
``puma.orchestrator.runner``. These are the building blocks the
share-results builder requires (``builder.py:365`` needs
``extra['cpu_cores']``).
"""

from __future__ import annotations

import sys

import pytest

from puma.orchestrator.runner import (
    _collect_profile_extra,
    _resolve_runner_puma_version,
)

_EXPECTED_EXTRA_KEYS = {
    "cpu_cores",
    "cpu_physical_cores",
    "memory_total_gb",
    "platform",
    "python_version",
    "has_cuda",
    "cuda_device_name",
}


@pytest.mark.unit
class TestProfileSnapshotExtra:
    def test_profile_snapshot_extra_populated(self):
        extra = _collect_profile_extra()
        assert set(extra) == _EXPECTED_EXTRA_KEYS
        assert isinstance(extra["cpu_cores"], int)
        assert extra["cpu_cores"] > 0
        assert isinstance(extra["cpu_physical_cores"], int)
        assert isinstance(extra["memory_total_gb"], int)
        assert extra["memory_total_gb"] > 0
        assert isinstance(extra["platform"], str)
        assert extra["platform"]
        assert isinstance(extra["python_version"], str)
        assert extra["python_version"]
        assert isinstance(extra["has_cuda"], bool)
        assert isinstance(extra["cuda_device_name"], str)

    def test_profile_snapshot_puma_version_dynamic(self):
        version = _resolve_runner_puma_version()
        assert isinstance(version, str)
        assert version
        # The old hardcoded sentinel must be gone.
        assert version != "2.0.0-dev"

    def test_profile_snapshot_psutil_fallback(self, monkeypatch):
        # Mapping the module name to None in sys.modules makes
        # ``import psutil`` raise ImportError, simulating psutil absence.
        monkeypatch.setitem(sys.modules, "psutil", None)
        extra = _collect_profile_extra()
        # Shape is preserved and cpu_cores is still set via os.cpu_count().
        assert set(extra) == _EXPECTED_EXTRA_KEYS
        assert extra["cpu_cores"] > 0
        # psutil-derived fields degrade gracefully to zero.
        assert extra["cpu_physical_cores"] == 0
        assert extra["memory_total_gb"] == 0
