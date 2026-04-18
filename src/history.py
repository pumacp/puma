import platform
import psutil
import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Allow importing from src/puma package
_src_root = str(Path(__file__).parent.parent)
if _src_root not in sys.path:
    sys.path.insert(0, _src_root)

RESULTS_DIR = Path("results")
HISTORY_FILE = RESULTS_DIR / "benchmark_history.csv"

SYSTEM_PROMPT = (
    "Eres un experto en gestión de proyectos TIC. "
    "Analiza el título y descripción de la incidencia y responde ÚNICAMENTE "
    "con una de estas palabras exactas: Critical, Major, Minor o Trivial. "
    "No añadas ninguna explicación ni puntuación extra."
)

def get_system_info() -> Dict[str, Any]:
    """Collect system/hardware information."""
    try:
        cpu_info = platform.processor()
        if not cpu_info:
            cpu_info = platform.machine()
    except Exception:
        cpu_info = "Unknown"

    try:
        cpu_count = psutil.cpu_count(logical=False)
        cpu_threads = psutil.cpu_count(logical=True)
    except Exception:
        cpu_count = cpu_threads = None

    try:
        memory = psutil.virtual_memory()
        ram_gb = round(memory.total / (1024**3), 2)
    except Exception:
        ram_gb = None

    try:
        disk = psutil.disk_usage('/')
        disk_gb = round(disk.total / (1024**3), 2)
    except Exception:
        disk_gb = None

    return {
        "os_system": platform.system(),
        "os_release": platform.release(),
        "os_version": platform.version(),
        "cpu_model": cpu_info,
        "cpu_cores_physical": cpu_count,
        "cpu_threads": cpu_threads,
        "ram_total_gb": ram_gb,
        "disk_total_gb": disk_gb,
        "python_version": platform.python_version(),
    }

def get_ollama_model_info(host: str = "http://ollama:11434") -> Optional[Dict[str, Any]]:
    """Get installed LLM model information from Ollama."""
    try:
        import requests
        response = requests.get(f"{host}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            if models:
                model = models[0]
                return {
                    "model_name": model.get("name", "unknown"),
                    "model_size_gb": round(model.get("size", 0) / (1024**3), 2),
                    "model_modified": model.get("modified_at", ""),
                }
    except Exception:
        pass
    return {
        "model_name": os.environ.get("LLM_MODEL", "unknown"),
        "model_size_gb": None,
        "model_modified": None,
    }

def init_history_file():
    """Initialize CSV history file with headers if it doesn't exist."""
    if not HISTORY_FILE.exists():
        headers = [
            "timestamp",
            "task_type",
            "model_name",
            "model_size_gb",
            "os_system",
            "os_release",
            "cpu_model",
            "cpu_cores_physical",
            "ram_total_gb",
            "metric_name",
            "metric_value",
            "target_value",
            "status",
        ]
        HISTORY_FILE.write_text(",".join(headers) + "\n")

def save_to_history(
    task_type: str,
    model_name: str,
    model_size_gb: Optional[float],
    metric_name: str,
    metric_value: float,
    target_value: float,
    status: str
):
    """Append a record to the benchmark history CSV."""
    init_history_file()

    system_info = get_system_info()
    timestamp = datetime.now().isoformat()

    row = [
        timestamp,
        task_type,
        model_name,
        str(model_size_gb) if model_size_gb else "",
        system_info["os_system"],
        system_info["os_release"],
        system_info["cpu_model"],
        str(system_info["cpu_cores_physical"]) if system_info["cpu_cores_physical"] else "",
        str(system_info["ram_total_gb"]) if system_info["ram_total_gb"] else "",
        metric_name,
        str(metric_value),
        str(target_value),
        status,
    ]

    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(",".join(row) + "\n")

def get_history() -> list:
    """Read and return all history records."""
    if not HISTORY_FILE.exists():
        return []

    import csv
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)

def print_history():
    """Print formatted benchmark history."""
    history = get_history()
    if not history:
        print("No benchmark history found.")
        return

    print("\n" + "="*80)
    print("BENCHMARK HISTORY")
    print("="*80)

    for i, record in enumerate(history, 1):
        print(f"\n--- Record {i} ---")
        print(f"  Date: {record['timestamp']}")
        print(f"  Task: {record['task_type']}")
        print(f"  Model: {record['model_name']} ({record['model_size_gb']} GB)")
        print(f"  Machine: {record['os_system']} {record['os_release']}")
        print(f"  CPU: {record['cpu_model']} ({record['cpu_cores_physical']} cores)")
        print(f"  RAM: {record['ram_total_gb']} GB")
        print(f"  Metric: {record['metric_name']} = {record['metric_value']} (target: {record['target_value']})")
        print(f"  Status: {record['status']}")

if __name__ == "__main__":
    print_history()
