"""Wilcoxon signed-rank pairwise comparison across models in a PUMA DB.

Iterates over scenarios, picks the top-K performers by primary metric
(F1-macro for classification, -MAE for regression), and compares each
pair using ``wilcoxon_signed_rank_models`` on per-instance correctness
indicators (Demšar, 2006).

Example:
    docker exec puma_runner python /app/scripts/wilcoxon_topmodels.py \\
        --run-prefix "wilcoxon_" --top-k 2 \\
        --scenarios triage_jira

The script intentionally takes a ``--run-prefix`` filter so it can be
re-targeted at any cohort of runs in the project's DB (e.g. a future
B.3 re-run). On v2.1.0 the canonical B.3 sweep predictions are not
preserved in the local DB; aggregate analysis lives in
``docs/results/phase_b_analysis.md`` and per-prediction Wilcoxon
re-analysis would require re-ingesting the sweep (left as future work).
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import Iterable

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from puma.metrics.statistical_tests import wilcoxon_signed_rank_models

DEFAULT_DB = Path("/app/data/puma.db")
DEFAULT_SCENARIOS = ("triage_jira", "estimation_tawos", "prioritization_jira")


def _top_models(
    conn: sqlite3.Connection,
    scenario: str,
    run_prefix: str,
    top_k: int,
) -> list[tuple[str, float]]:
    """Return ``[(model, metric), ...]`` ranked best-first for a scenario."""
    if scenario == "estimation_tawos":
        metric_name = "mae_sp"
        order = "ASC"
    else:
        metric_name = "f1_macro"
        order = "DESC"

    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT p.model, AVG(m.value) AS score
        FROM metrics m
        JOIN predictions p ON p.run_id = m.run_id
        JOIN runs r ON r.run_id = m.run_id
        WHERE r.run_id LIKE ?
          AND m.metric_name = ?
          AND p.run_id IN (
              SELECT run_id FROM predictions
              WHERE run_id = m.run_id LIMIT 1
          )
        GROUP BY p.model
        ORDER BY score {order}
        LIMIT ?
        """,
        (run_prefix + "%", metric_name, top_k),
    )
    return [(row[0], float(row[1])) for row in cur.fetchall()]


def _paired_predictions(
    conn: sqlite3.Connection,
    scenario: str,
    model_a: str,
    model_b: str,
    run_prefix: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Join predictions from both models on the same instance set.

    Picks the most-recent run per model matching the prefix.
    """
    cur = conn.cursor()

    def latest_run_for(model: str) -> str | None:
        cur.execute(
            """SELECT p.run_id FROM predictions p JOIN runs r ON p.run_id = r.run_id
               WHERE p.model = ? AND r.run_id LIKE ?
               ORDER BY r.started_at DESC LIMIT 1""",
            (model, run_prefix + "%"),
        )
        row = cur.fetchone()
        return row[0] if row else None

    run_a = latest_run_for(model_a)
    run_b = latest_run_for(model_b)
    if not run_a or not run_b:
        return np.array([]), np.array([]), np.array([])

    cur.execute(
        """
        SELECT pa.instance_id, pa.parsed_label, pb.parsed_label, i.gold_label
        FROM predictions pa
        JOIN predictions pb ON pa.instance_id = pb.instance_id
        JOIN instances i ON i.instance_id = pa.instance_id
        WHERE pa.run_id = ? AND pb.run_id = ?
          AND pa.perturbation IS NULL AND pb.perturbation IS NULL
        """,
        (run_a, run_b),
    )
    rows = cur.fetchall()
    if not rows:
        return np.array([]), np.array([]), np.array([])

    preds_a = np.array([r[1] for r in rows], dtype=object)
    preds_b = np.array([r[2] for r in rows], dtype=object)
    gold = np.array([r[3] for r in rows], dtype=object)
    return preds_a, preds_b, gold


def run_analysis(
    db_path: Path,
    run_prefix: str,
    scenarios: Iterable[str],
    top_k: int,
) -> None:
    conn = sqlite3.connect(str(db_path))

    for scenario in scenarios:
        print(f"\n=== {scenario} (run prefix: {run_prefix!r}) ===")
        cur = conn.cursor()
        cur.execute(
            """SELECT DISTINCT p.model
               FROM predictions p
               JOIN runs r ON p.run_id = r.run_id
               JOIN metrics m ON m.run_id = r.run_id
               WHERE r.run_id LIKE ? AND m.metric_name IN ('f1_macro','mae_sp')""",
            (run_prefix + "%",),
        )
        # rank by simply using the runs prefix and metric name directly
        metric_name = "mae_sp" if scenario == "estimation_tawos" else "f1_macro"
        order = "ASC" if metric_name == "mae_sp" else "DESC"
        cur.execute(
            f"""SELECT p.model, AVG(m.value) AS score
                FROM predictions p
                JOIN metrics m ON m.run_id = p.run_id
                JOIN runs r ON r.run_id = p.run_id
                WHERE r.run_id LIKE ? AND m.metric_name = ?
                GROUP BY p.model
                ORDER BY score {order}
                LIMIT ?""",
            (run_prefix + "%", metric_name, top_k),
        )
        ranked = [(row[0], float(row[1])) for row in cur.fetchall()]
        if not ranked:
            print(f"  no models matched. Skipping.")
            continue

        print(f"  Ranked top-{top_k} by {metric_name}:")
        for model, score in ranked:
            print(f"    {model}: {score:.4f}")

        if len(ranked) < 2:
            print("  Only one model available; pairwise test skipped.")
            continue

        print(f"\n  Pairwise Wilcoxon signed-rank (two-sided, α=0.05):")
        for i, (m_a, _) in enumerate(ranked):
            for m_b, _ in ranked[i + 1 :]:
                preds_a, preds_b, gold = _paired_predictions(
                    conn, scenario, m_a, m_b, run_prefix
                )
                if preds_a.size == 0:
                    print(f"    {m_a} vs {m_b}: no paired predictions available")
                    continue
                result = wilcoxon_signed_rank_models(preds_a, preds_b, gold)
                marker = "*" if result["p_value"] < 0.05 else " "
                print(
                    f"    {m_a} vs {m_b}: "
                    f"p={result['p_value']:.4f}{marker} "
                    f"(n_pairs={result['n_pairs']}, "
                    f"mean_diff={result['mean_diff']:+.3f}, "
                    f"n_total={preds_a.size})"
                )

    conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument(
        "--run-prefix",
        type=str,
        default="b3_sweep",
        help="Filter runs by run_id LIKE prefix%% (default: 'b3_sweep')",
    )
    parser.add_argument(
        "--scenarios",
        nargs="+",
        default=list(DEFAULT_SCENARIOS),
        help="Scenarios to analyse (default: all three PMO scenarios)",
    )
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()

    if not args.db.exists():
        print(f"DB not found: {args.db}", file=sys.stderr)
        return 1

    run_analysis(args.db, args.run_prefix, args.scenarios, args.top_k)
    return 0


if __name__ == "__main__":
    sys.exit(main())
