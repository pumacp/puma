"""Generate Phase B comparative plots from `data/puma.db`.

Produces three PNGs in `docs/results/figures/`:

  plot1_performance_by_model_and_scenario.png
    Three panels (one per scenario), bars per model. Native metric on
    the y-axis (F1, MAE, accuracy). Models with parse_failure_rate
    >= 0.30 are drawn with a hatched red fill labeled "INVALID".

  plot2_pareto_quality_vs_co2.png
    Three panels (one per scenario), scatter of native quality vs
    log-scaled g CO2. Marker size encodes duration. Each point labeled
    with its model tag.

  plot3_duration_variability.png
    Box plot of per-run duration per model (3 points each, across the
    three scenarios). Models sorted by max/min ratio descending so
    high-variance models surface visually on the left.

The script reads only from `data/puma.db` (the same source the
analysis document cites) and is reproducible: given the same DB state
it produces identical PNGs.

Usage (from repo root):

    docker compose exec -T puma_runner python scripts/generate_phase_b_plots.py

If the database has no `b3_sweep%` rows the script exits non-zero.
"""

from __future__ import annotations

import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "data" / "puma.db"
FIGURES_DIR = REPO_ROOT / "docs" / "results" / "figures"

SCENARIOS = ("triage_jira", "estimation_tawos", "prioritization_jira")
SCENARIO_METRIC = {
    "triage_jira": ("f1_macro", "F1-macro", "higher"),
    "estimation_tawos": ("mae", "MAE (story points)", "lower"),
    "prioritization_jira": ("accuracy", "Accuracy", "higher"),
}
INVALID_PFR = 0.30  # threshold above which a run is treated as invalid


def load_sweep(db_path: Path) -> list[dict]:
    """Load all b3_sweep runs joined to their metrics and emissions."""
    if not db_path.exists():
        sys.exit(f"DB not found: {db_path}")
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute(
        """
        SELECT r.run_id,
               json_extract(r.spec_yaml, '$.models[0]') AS model,
               json_extract(r.spec_yaml, '$.scenario')   AS scenario,
               e.duration_s, e.kwh, e.co2_kg
        FROM runs r
        LEFT JOIN emissions e ON r.run_id = e.run_id
        WHERE r.run_id LIKE 'b3_sweep%'
        ORDER BY scenario, model
        """
    )
    rows = cur.fetchall()
    if not rows:
        sys.exit("No b3_sweep runs found in DB; was the sweep executed?")

    out = []
    for run_id, model, scenario, dur, kwh, co2 in rows:
        cur.execute("SELECT metric_name, value FROM metrics WHERE run_id=?", (run_id,))
        m = dict(cur.fetchall())
        out.append(
            {
                "run_id": run_id,
                "model": model,
                "scenario": scenario,
                "duration_s": dur or 0.0,
                "kwh": kwh or 0.0,
                "co2_kg": co2 or 0.0,
                "g_co2": (co2 or 0.0) * 1000,
                "f1_macro": m.get("f1_macro"),
                "mae": m.get("mae"),
                "accuracy": m.get("accuracy"),
                "parse_failure_rate": m.get("parse_failure_rate", 0.0),
            }
        )
    return out


def plot_performance(runs: list[dict], out: Path) -> None:
    """Plot 1: native metric per model, three panels per scenario."""
    fig, axes = plt.subplots(3, 1, figsize=(11, 10), sharex=False)

    by_scenario = defaultdict(list)
    for r in runs:
        by_scenario[r["scenario"]].append(r)

    for ax, scenario in zip(axes, SCENARIOS, strict=True):
        metric_key, metric_label, direction = SCENARIO_METRIC[scenario]
        rs = by_scenario.get(scenario, [])

        def sort_key(r):
            v = r[metric_key]
            if v is None:
                return float("inf") if direction == "higher" else float("-inf")
            return -v if direction == "higher" else v

        rs_sorted = sorted(rs, key=sort_key)

        labels = [r["model"] for r in rs_sorted]
        values = [r[metric_key] if r[metric_key] is not None else 0.0 for r in rs_sorted]
        invalid = [r["parse_failure_rate"] >= INVALID_PFR for r in rs_sorted]

        bar_colors = ["#cc4444" if inv else "#4477aa" for inv in invalid]
        hatches = ["//" if inv else "" for inv in invalid]

        bars = ax.bar(labels, values, color=bar_colors)
        for bar, h in zip(bars, hatches, strict=True):
            bar.set_hatch(h)
            bar.set_edgecolor("black")

        ax.set_title(f"{scenario} — {metric_label} ({direction} = better)")
        ax.set_ylabel(metric_label)
        ax.tick_params(axis="x", rotation=30)
        for label in ax.get_xticklabels():
            label.set_horizontalalignment("right")

        for i, (bar, v, inv) in enumerate(zip(bars, values, invalid, strict=True)):
            if inv:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height(),
                    "INVALID",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                    color="#cc4444",
                    fontweight="bold",
                )
            else:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height(),
                    f"{v:.3f}",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                )

    valid_patch = mpatches.Patch(color="#4477aa", label="parse_failure_rate < 0.30")
    invalid_patch = mpatches.Patch(
        facecolor="#cc4444", hatch="//", edgecolor="black",
        label=f"parse_failure_rate >= {INVALID_PFR}",
    )
    fig.legend(handles=[valid_patch, invalid_patch], loc="upper right", fontsize=9)
    fig.suptitle("Phase B sweep — performance per model and scenario", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(out, dpi=120)
    plt.close(fig)


def plot_pareto(runs: list[dict], out: Path) -> None:
    """Plot 2: quality vs g CO2 (log x), three panels per scenario."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    by_scenario = defaultdict(list)
    for r in runs:
        by_scenario[r["scenario"]].append(r)

    for ax, scenario in zip(axes, SCENARIOS, strict=True):
        metric_key, metric_label, direction = SCENARIO_METRIC[scenario]
        rs = [r for r in by_scenario.get(scenario, []) if r["parse_failure_rate"] < INVALID_PFR]

        xs = [r["g_co2"] for r in rs]
        ys = [r[metric_key] for r in rs]
        sizes = [max(20.0, r["duration_s"] / 5.0) for r in rs]

        ax.scatter(xs, ys, s=sizes, alpha=0.6, edgecolor="black")
        for r in rs:
            ax.annotate(
                r["model"],
                (r["g_co2"], r[metric_key]),
                textcoords="offset points",
                xytext=(6, 4),
                fontsize=8,
            )
        ax.set_xscale("log")
        ax.set_xlabel("CO₂ per run (g, log scale)")
        ax.set_ylabel(metric_label)
        ax.set_title(f"{scenario}\n({direction} = better)")
        ax.grid(True, which="both", alpha=0.2)

    fig.suptitle(
        "Phase B sweep — quality vs CO₂ cost (gemma4:e2b excluded; pfr ≥ 0.30)",
        fontsize=12,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(out, dpi=120)
    plt.close(fig)


def plot_variability(runs: list[dict], out: Path) -> None:
    """Plot 3: per-model duration boxplot, sorted by max/min ratio."""
    by_model = defaultdict(list)
    for r in runs:
        by_model[r["model"]].append(r["duration_s"])

    items = []
    for model, durs in by_model.items():
        if not durs or min(durs) <= 0:
            continue
        ratio = max(durs) / min(durs)
        items.append((model, durs, ratio))
    items.sort(key=lambda x: -x[2])

    labels = [f"{m}\nratio={r:.1f}×" for m, _, r in items]
    data = [d for _, d, _ in items]

    fig, ax = plt.subplots(figsize=(11, 6))
    ax.boxplot(data, tick_labels=labels, showfliers=True, widths=0.6)
    for i, (_, durs, _) in enumerate(items):
        xs = [i + 1] * len(durs)
        ax.scatter(xs, durs, color="#cc4444", zorder=3, s=20, alpha=0.7)
    ax.set_ylabel("duration per run (s)")
    ax.set_title("Phase B sweep — per-model duration spread (3 scenarios per box)")
    ax.set_yscale("log")
    ax.grid(True, axis="y", which="both", alpha=0.2)
    ax.tick_params(axis="x", rotation=20)
    for label in ax.get_xticklabels():
        label.set_horizontalalignment("right")

    fig.tight_layout()
    fig.savefig(out, dpi=120)
    plt.close(fig)


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    runs = load_sweep(DB_PATH)
    print(f"loaded {len(runs)} sweep runs from {DB_PATH}")

    p1 = FIGURES_DIR / "plot1_performance_by_model_and_scenario.png"
    p2 = FIGURES_DIR / "plot2_pareto_quality_vs_co2.png"
    p3 = FIGURES_DIR / "plot3_duration_variability.png"

    plot_performance(runs, p1)
    print(f"wrote {p1.relative_to(REPO_ROOT)}")
    plot_pareto(runs, p2)
    print(f"wrote {p2.relative_to(REPO_ROOT)}")
    plot_variability(runs, p3)
    print(f"wrote {p3.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
