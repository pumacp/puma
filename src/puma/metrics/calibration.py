"""Calibration metrics: ECE, MCE, Brier score, confidence extraction from logprobs."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np


def expected_calibration_error(
    confidences: list[float],
    corrects: list[bool],
    n_bins: int = 10,
) -> float:
    """Expected Calibration Error (ECE) via equal-width bins on [0, 1]."""
    if not confidences:
        raise ValueError("expected_calibration_error: empty inputs")
    if len(confidences) != len(corrects):
        raise ValueError("expected_calibration_error: length mismatch")

    confs = np.array(confidences, dtype=float)
    hits = np.array(corrects, dtype=float)
    n = len(confs)

    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    for lo, hi in zip(bins[:-1], bins[1:], strict=True):
        mask = (confs >= lo) & (confs < hi) if hi < 1.0 else (confs >= lo) & (confs <= hi)
        if mask.sum() == 0:
            continue
        bin_conf = float(confs[mask].mean())
        bin_acc = float(hits[mask].mean())
        ece += (mask.sum() / n) * abs(bin_conf - bin_acc)

    return float(ece)


def maximum_calibration_error(
    confidences: list[float],
    corrects: list[bool],
    n_bins: int = 10,
) -> float:
    """Maximum Calibration Error (MCE) — worst-case bin gap."""
    if not confidences:
        raise ValueError("maximum_calibration_error: empty inputs")
    if len(confidences) != len(corrects):
        raise ValueError("maximum_calibration_error: length mismatch")

    confs = np.array(confidences, dtype=float)
    hits = np.array(corrects, dtype=float)

    bins = np.linspace(0.0, 1.0, n_bins + 1)
    mce = 0.0
    for lo, hi in zip(bins[:-1], bins[1:], strict=True):
        mask = (confs >= lo) & (confs < hi) if hi < 1.0 else (confs >= lo) & (confs <= hi)
        if mask.sum() == 0:
            continue
        gap = abs(float(confs[mask].mean()) - float(hits[mask].mean()))
        mce = max(mce, gap)

    return float(mce)


def brier_score(confidences: list[float], corrects: list[bool]) -> float:
    """Brier score: mean squared error between confidence and binary outcome."""
    if not confidences:
        raise ValueError("brier_score: empty inputs")
    confs = np.array(confidences, dtype=float)
    hits = np.array(corrects, dtype=float)
    return float(np.mean((confs - hits) ** 2))


def class_confidence_from_logprobs(
    logprobs: list,  # list[TokenLogprob]
    label_tokens: dict[str, list[str]],
) -> dict[str, float]:
    """Extract per-class confidence from Ollama logprobs via stable softmax.

    Applies softmax over the first token's candidates, then sums probabilities
    for token variants of each class label. Returns normalised probabilities.
    """
    if not logprobs:
        return {}

    first = logprobs[0]
    candidates: list[tuple[str, float]] = [(first.token, first.logprob)]
    candidates.extend((tl.token, tl.logprob) for tl in first.top_logprobs)

    max_lp = max(lp for _, lp in candidates)
    exps = [(tok, math.exp(lp - max_lp)) for tok, lp in candidates]
    total = sum(e for _, e in exps)
    probs = {tok: e / total for tok, e in exps}

    result: dict[str, float] = {}
    for label, tokens in label_tokens.items():
        result[label] = sum(probs.get(t, 0.0) for t in tokens)

    s = sum(result.values())
    return {k: v / s for k, v in result.items()} if s > 0 else result


def reliability_diagram(
    confidences: list[float],
    corrects: list[bool],
    output_path: Path | str,
    n_bins: int = 10,
) -> None:
    """Save a reliability diagram PNG to output_path."""
    import matplotlib.pyplot as plt

    confs = np.array(confidences, dtype=float)
    hits = np.array(corrects, dtype=float)
    bins = np.linspace(0.0, 1.0, n_bins + 1)

    bin_confs, bin_accs, bin_counts = [], [], []
    for lo, hi in zip(bins[:-1], bins[1:], strict=True):
        mask = (confs >= lo) & (confs <= hi)
        if mask.sum() > 0:
            bin_confs.append(float(confs[mask].mean()))
            bin_accs.append(float(hits[mask].mean()))
            bin_counts.append(int(mask.sum()))

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot([0, 1], [0, 1], "k--", label="Perfect calibration")
    ax.bar(bin_confs, bin_accs, width=0.1, alpha=0.7, label="Accuracy per bin")
    ax.set_xlabel("Confidence")
    ax.set_ylabel("Accuracy")
    ax.set_title("Reliability Diagram")
    ax.legend()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    fig.tight_layout()
    fig.savefig(str(output_path))
    plt.close(fig)
