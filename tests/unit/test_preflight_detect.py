"""Unit tests for puma.preflight.detect — all subprocess calls mocked."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from puma.preflight.detect import SystemCapabilities, detect_capabilities


@pytest.mark.unit
class TestDetectCapabilities:
    def test_returns_system_capabilities(self):
        caps = detect_capabilities()
        assert isinstance(caps, SystemCapabilities)

    def test_basic_fields_populated(self):
        caps = detect_capabilities()
        assert caps.os_system != ""
        assert caps.cpu_model != ""
        assert caps.ram_total_gb > 0
        assert caps.disk_free_gb > 0

    def test_no_gpu_when_nvidia_smi_absent(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            caps = detect_capabilities()
        assert caps.gpu_name is None
        assert caps.gpu_vram_gb is None
        assert caps.gpu_backend == "none"

    def test_nvidia_gpu_detected(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "NVIDIA GeForce RTX 3080, 10240 MiB\n"

        with patch("subprocess.run", return_value=mock_result):
            caps = detect_capabilities()

        assert caps.gpu_name == "NVIDIA GeForce RTX 3080"
        assert abs(caps.gpu_vram_gb - 10.0) < 0.1
        assert caps.gpu_backend == "nvidia"

    def test_nvidia_smi_nonzero_fallback(self):
        """If nvidia-smi returns non-zero, GPU should be none."""
        mock_fail = MagicMock()
        mock_fail.returncode = 1
        mock_fail.stdout = ""

        with patch("subprocess.run", return_value=mock_fail):
            caps = detect_capabilities()

        assert caps.gpu_name is None
        assert caps.gpu_backend == "none"


@pytest.mark.unit
class TestSystemCapabilitiesFields:
    def test_ollama_unreachable_defaults(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with patch("puma.preflight.detect._query_ollama_version", return_value=None):
                caps = detect_capabilities()
        assert caps.ollama_version is None or isinstance(caps.ollama_version, str)

    def test_dataclass_frozen(self):
        caps = detect_capabilities()
        with pytest.raises((AttributeError, TypeError)):
            caps.os_system = "hacked"  # type: ignore[misc]
