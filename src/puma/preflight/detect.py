"""Hardware capability detection for PUMA preflight."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass

import psutil


@dataclass(frozen=True)
class SystemCapabilities:
    os_system: str
    os_arch: str
    python_version: str
    cpu_model: str
    cpu_cores_physical: int
    cpu_threads: int
    cpu_freq_mhz: float
    ram_total_gb: float
    ram_available_gb: float
    disk_free_gb: float
    gpu_name: str | None
    gpu_vram_gb: float | None
    gpu_backend: str  # "nvidia" | "rocm" | "metal" | "none"
    ollama_version: str | None
    ollama_reachable: bool


def _query_nvidia() -> tuple[str | None, float | None]:
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None, None
        first_line = result.stdout.strip().splitlines()[0]
        parts = first_line.split(",", 1)
        name = parts[0].strip()
        vram_str = parts[1].strip() if len(parts) > 1 else ""
        vram_mib = float("".join(c for c in vram_str if c.isdigit() or c == "."))
        return name, round(vram_mib / 1024, 1)
    except (FileNotFoundError, NotADirectoryError, OSError, subprocess.TimeoutExpired, ValueError):
        return None, None


def _query_rocm() -> tuple[str | None, float | None]:
    try:
        result = subprocess.run(
            ["rocm-smi", "--showproductname", "--showmeminfo", "vram"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return None, None
        return "AMD ROCm GPU", None
    except (FileNotFoundError, NotADirectoryError, OSError, subprocess.TimeoutExpired):
        return None, None


def _query_metal() -> tuple[str | None, float | None]:
    try:
        result = subprocess.run(
            ["system_profiler", "SPDisplaysDataType"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return None, None
        for line in result.stdout.splitlines():
            if "Chipset Model" in line or "Chip" in line:
                name = line.split(":")[-1].strip()
                return name, None
        return "Apple Metal GPU", None
    except (FileNotFoundError, NotADirectoryError, OSError, subprocess.TimeoutExpired):
        return None, None


def _query_ollama_version() -> str | None:
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, NotADirectoryError, OSError, subprocess.TimeoutExpired):
        pass
    return None


def _query_ollama_reachable() -> bool:
    try:
        import urllib.request

        with urllib.request.urlopen(  # noqa: S310
            "http://localhost:11434/api/version", timeout=3
        ):
            return True
    except Exception:
        return False


def detect_capabilities() -> SystemCapabilities:
    """Detect host hardware and return a SystemCapabilities snapshot."""
    # GPU detection in priority order
    gpu_name, gpu_vram_gb, gpu_backend = None, None, "none"

    name, vram = _query_nvidia()
    if name:
        gpu_name, gpu_vram_gb, gpu_backend = name, vram, "nvidia"
    else:
        name, vram = _query_rocm()
        if name:
            gpu_name, gpu_vram_gb, gpu_backend = name, vram, "rocm"
        else:
            name, vram = _query_metal()
            if name:
                gpu_name, gpu_vram_gb, gpu_backend = name, vram, "metal"

    # Fallback: env vars injected by start_puma.sh when running inside Docker
    if gpu_backend == "none":
        env_backend = os.environ.get("PUMA_GPU_BACKEND", "").strip()
        env_name = os.environ.get("PUMA_GPU_NAME", "").strip()
        env_vram = os.environ.get("PUMA_GPU_VRAM_GB", "").strip()
        if env_backend and env_backend != "none":
            gpu_backend = env_backend
            gpu_name = env_name or "Unknown GPU"
            try:
                gpu_vram_gb = float(env_vram) if env_vram else None
            except ValueError:
                gpu_vram_gb = None

    try:
        cpu_freq = psutil.cpu_freq()
        freq_mhz = round(cpu_freq.current, 1) if cpu_freq else 0.0
    except Exception:
        freq_mhz = 0.0

    try:
        ram = psutil.virtual_memory()
        ram_total = round(ram.total / (1024**3), 2)
        ram_avail = round(ram.available / (1024**3), 2)
    except Exception:
        ram_total = ram_avail = 0.0

    try:
        disk_free = round(shutil.disk_usage(".").free / (1024**3), 2)
    except Exception:
        disk_free = 0.0

    try:
        cpu_model = platform.processor() or platform.machine() or "Unknown"
    except Exception:
        cpu_model = "Unknown"

    return SystemCapabilities(
        os_system=platform.system(),
        os_arch=platform.machine(),
        python_version=platform.python_version(),
        cpu_model=cpu_model,
        cpu_cores_physical=psutil.cpu_count(logical=False) or 1,
        cpu_threads=psutil.cpu_count(logical=True) or 1,
        cpu_freq_mhz=freq_mhz,
        ram_total_gb=ram_total,
        ram_available_gb=ram_avail,
        disk_free_gb=disk_free,
        gpu_name=gpu_name,
        gpu_vram_gb=gpu_vram_gb,
        gpu_backend=gpu_backend,
        ollama_version=_query_ollama_version(),
        ollama_reachable=_query_ollama_reachable(),
    )
