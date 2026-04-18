"""Benchmark run history persistence (CSV-based, legacy)."""

import csv
import os
import platform
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil

RESULTS_DIR = Path("results")
HISTORY_FILE = RESULTS_DIR / "benchmark_history.csv"


def get_system_info() -> dict[str, Any]:
    try:
        cpu_info = platform.processor() or platform.machine()
    except Exception:
        cpu_info = "Unknown"

    try:
        cpu_count = psutil.cpu_count(logical=False)
        cpu_threads = psutil.cpu_count(logical=True)
    except Exception:
        cpu_count = cpu_threads = None

    try:
        ram_gb = round(psutil.virtual_memory().total / (1024**3), 2)
    except Exception:
        ram_gb = None

    try:
        disk_gb = round(psutil.disk_usage("/").total / (1024**3), 2)
    except Exception:
        disk_gb = None

    return {
        "os_system": platform.system(),
        "os_release": platform.release(),
        "cpu_model": cpu_info,
        "cpu_cores_physical": cpu_count,
        "cpu_threads": cpu_threads,
        "ram_total_gb": ram_gb,
        "disk_total_gb": disk_gb,
        "python_version": platform.python_version(),
    }


def get_ollama_model_info(host: str = "http://localhost:11434") -> dict[str, Any]:
    try:
        import requests

        resp = requests.get(f"{host}/api/tags", timeout=5)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            if models:
                m = models[0]
                return {
                    "model_name": m.get("name", "unknown"),
                    "model_size_gb": round(m.get("size", 0) / (1024**3), 2),
                }
    except Exception:
        pass
    return {
        "model_name": os.environ.get("LLM_MODEL", "unknown"),
        "model_size_gb": None,
    }


def _init_history_file() -> None:
    if not HISTORY_FILE.exists():
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        headers = [
            "timestamp", "task_type", "model_name", "model_size_gb",
            "os_system", "os_release", "cpu_model", "cpu_cores_physical",
            "ram_total_gb", "metric_name", "metric_value", "target_value", "status",
        ]
        HISTORY_FILE.write_text(",".join(headers) + "\n")


def save_to_history(
    task_type: str,
    model_name: str,
    model_size_gb: float | None,
    metric_name: str,
    metric_value: float,
    target_value: float,
    status: str,
) -> None:
    _init_history_file()
    info = get_system_info()
    row = [
        datetime.now().isoformat(),
        task_type,
        model_name,
        str(model_size_gb) if model_size_gb is not None else "",
        info["os_system"],
        info["os_release"],
        info["cpu_model"],
        str(info["cpu_cores_physical"]) if info["cpu_cores_physical"] is not None else "",
        str(info["ram_total_gb"]) if info["ram_total_gb"] is not None else "",
        metric_name,
        str(metric_value),
        str(target_value),
        status,
    ]
    with open(HISTORY_FILE, "a", encoding="utf-8") as fh:
        fh.write(",".join(row) + "\n")


def get_history() -> list:
    if not HISTORY_FILE.exists():
        return []
    with open(HISTORY_FILE, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))
