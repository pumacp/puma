"""Read-only environment health checks for ``puma doctor``.

Every check returns a :class:`CheckResult` and NEVER raises — problems are
reported as ``warn``/``fail`` statuses. Strictly side-effect-free: no writes,
no inference, no codecarbon tracker, and every HTTP request carries a short
timeout.
"""

from __future__ import annotations

import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import httpx

Status = Literal["ok", "warn", "fail"]

_DEFAULT_ENDPOINT = "http://localhost:11434"
_DEFAULT_REQUIRED_MODELS = ("qwen2.5:3b",)


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: Status
    detail: str
    hint: str | None = None


def check_python_version() -> CheckResult:
    info = sys.version_info
    detail = f"{info.major}.{info.minor}.{info.micro}"
    if (info.major, info.minor) >= (3, 11):
        return CheckResult("Python", "ok", detail)
    return CheckResult("Python", "fail", detail, hint="PUMA requires Python >= 3.11.")


def check_codecarbon_available() -> CheckResult:
    from importlib.metadata import PackageNotFoundError, version

    try:
        import codecarbon  # noqa: F401 — import-only availability probe (no tracker started)

        ver = version("codecarbon")
    except (ImportError, PackageNotFoundError):
        return CheckResult(
            "CodeCarbon", "fail", "not importable", hint="pip install 'codecarbon>=3.0'"
        )
    try:
        major = int(ver.split(".")[0])
    except (ValueError, IndexError):
        major = 0
    if major >= 3:
        return CheckResult("CodeCarbon", "ok", ver)
    return CheckResult("CodeCarbon", "warn", f"{ver} (< 3.0)", hint="pip install -U codecarbon")


def check_ollama_reachable(
    endpoint: str = _DEFAULT_ENDPOINT, timeout_s: float = 2.0
) -> CheckResult:
    url = f"{endpoint.rstrip('/')}/api/tags"
    try:
        resp = httpx.get(url, timeout=timeout_s)
    except Exception as exc:
        return CheckResult(
            "Ollama reachable",
            "fail",
            f"{endpoint}: {type(exc).__name__}",
            hint="Start Ollama (e.g. `ollama serve`) or set OLLAMA_HOST.",
        )
    if resp.status_code == 200:
        return CheckResult("Ollama reachable", "ok", endpoint)
    return CheckResult(
        "Ollama reachable",
        "fail",
        f"{endpoint}: HTTP {resp.status_code}",
        hint="Start Ollama or check OLLAMA_HOST.",
    )


def check_ollama_models(endpoint: str, required: list[str]) -> CheckResult:
    url = f"{endpoint.rstrip('/')}/api/tags"
    try:
        resp = httpx.get(url, timeout=2.0)
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
    except Exception as exc:
        return CheckResult(
            "Ollama models",
            "fail",
            f"API unreachable: {type(exc).__name__}",
            hint="Start Ollama; the model check needs /api/tags.",
        )
    present = {str(m.get("name", "")) for m in data.get("models", [])}
    missing = [r for r in required if not any(p == r or p.startswith(f"{r}:") for p in present)]
    if not missing:
        return CheckResult("Ollama models", "ok", f"{len(required)} present")
    return CheckResult(
        "Ollama models",
        "warn",
        f"missing: {', '.join(missing)}",
        hint="; ".join(f"ollama pull {m}" for m in missing),
    )


def check_hardware_profile() -> CheckResult:
    try:
        from puma.preflight.detect import detect_capabilities
        from puma.preflight.profile import InsufficientHardwareError, select_profile

        try:
            profile = select_profile(detect_capabilities())
        except InsufficientHardwareError as exc:
            return CheckResult("Hardware profile", "warn", str(exc))
        return CheckResult("Hardware profile", "ok", profile.name)
    except Exception as exc:
        return CheckResult(
            "Hardware profile", "warn", f"detection unavailable: {type(exc).__name__}"
        )


def check_database_accessible(db_path: Path) -> CheckResult:
    path = Path(db_path)
    if not path.exists():
        return CheckResult("Database", "warn", f"{path} (created on first run)")
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            con.execute("SELECT name FROM sqlite_master LIMIT 1")
        finally:
            con.close()
    except Exception as exc:
        return CheckResult(
            "Database",
            "fail",
            f"{path}: {type(exc).__name__}",
            hint="Database file may be corrupt; back it up and recreate.",
        )
    return CheckResult("Database", "ok", str(path))


def check_required_baselines_present(specs_dir: Path) -> CheckResult:
    specs = Path(specs_dir)
    expected = ("baseline_triage.yaml", "baseline_estimation_canonical.yaml")
    present = [name for name in expected if (specs / name).exists()]
    if len(present) == len(expected):
        return CheckResult("Baseline specs", "ok", "both present")
    if present:
        missing = [n for n in expected if n not in present]
        return CheckResult("Baseline specs", "warn", f"missing: {', '.join(missing)}")
    return CheckResult(
        "Baseline specs",
        "fail",
        f"both missing in {specs}",
        hint="Expected baseline_triage.yaml and baseline_estimation_canonical.yaml.",
    )


def run_all_checks(
    *,
    ollama_endpoint: str = _DEFAULT_ENDPOINT,
    required_models: list[str] | None = None,
    db_path: Path | None = None,
    specs_dir: Path | None = None,
) -> list[CheckResult]:
    """Run all environment checks in a sensible order and return their results."""
    models = required_models if required_models is not None else list(_DEFAULT_REQUIRED_MODELS)
    db = db_path if db_path is not None else Path("data/puma.db")
    specs = specs_dir if specs_dir is not None else Path("specs/runs")
    return [
        check_python_version(),
        check_codecarbon_available(),
        check_ollama_reachable(ollama_endpoint),
        check_ollama_models(ollama_endpoint, models),
        check_hardware_profile(),
        check_database_accessible(db),
        check_required_baselines_present(specs),
    ]
