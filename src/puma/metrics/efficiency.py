"""Efficiency metrics: latency percentiles, throughput, memory sampling."""

from __future__ import annotations

import numpy as np


def percentiles(latencies_ms: list[float]) -> dict[str, float]:
    """Compute p50, p95, p99 latency percentiles from a list of measurements."""
    if not latencies_ms:
        raise ValueError("percentiles: empty latency list")
    arr = np.array(latencies_ms, dtype=float)
    return {
        "p50": float(np.percentile(arr, 50)),
        "p95": float(np.percentile(arr, 95)),
        "p99": float(np.percentile(arr, 99)),
        "mean": float(np.mean(arr)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
    }


def throughput(n_instances: int, duration_s: float) -> float:
    """Compute throughput in instances/minute."""
    if duration_s <= 0:
        raise ValueError("throughput: duration_s must be positive")
    return (n_instances / duration_s) * 60.0


def parse_ollama_timings(raw: dict) -> dict[str, float]:
    """Extract latency fields from an Ollama API response dict."""
    total_ns = raw.get("total_duration", 0)
    load_ns = raw.get("load_duration", 0)
    eval_ns = raw.get("eval_duration", 0)
    eval_count = raw.get("eval_count", 0)
    prompt_eval_count = raw.get("prompt_eval_count", 0)

    tokens_per_sec = (eval_count / (eval_ns / 1e9)) if eval_ns > 0 else 0.0

    return {
        "total_ms": total_ns / 1e6,
        "load_ms": load_ns / 1e6,
        "eval_ms": eval_ns / 1e6,
        "eval_count": eval_count,
        "prompt_eval_count": prompt_eval_count,
        "tokens_per_sec": tokens_per_sec,
    }
