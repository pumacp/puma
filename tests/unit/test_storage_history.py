"""Unit tests for storage.history helpers."""

import pytest

from puma.storage.history import get_system_info


@pytest.mark.unit
class TestGetSystemInfo:
    def test_returns_dict(self):
        info = get_system_info()
        assert isinstance(info, dict)

    def test_required_keys(self):
        info = get_system_info()
        for key in ("os_system", "cpu_model", "ram_total_gb", "python_version"):
            assert key in info

    def test_ram_positive(self):
        info = get_system_info()
        if info["ram_total_gb"] is not None:
            assert info["ram_total_gb"] > 0
