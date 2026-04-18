"""Compare metrics across two or more runs from the SQLite database."""

from __future__ import annotations

from pathlib import Path


def compare_runs(run_ids: list[str], db_path: Path | str = "data/puma.db") -> dict:
    """Query metrics for run_ids and return a comparison dict + markdown table."""
    from puma.storage.db import init_db, session_scope
    from puma.storage.models import Metric, Run

    init_db(db_path)

    run_metrics: dict[str, dict[str, float]] = {}
    run_statuses: dict[str, str] = {}

    with session_scope() as db:
        for run_id in run_ids:
            run = db.get(Run, run_id)
            run_statuses[run_id] = run.status if run else "not_found"
            rows = db.query(Metric).filter(Metric.run_id == run_id).all()
            run_metrics[run_id] = {r.metric_name: r.value for r in rows}

    all_metric_names = sorted({k for v in run_metrics.values() for k in v})

    table_lines = ["| Metric | " + " | ".join(run_ids) + " |"]
    table_lines.append("|--------|" + "--------|" * len(run_ids))
    for metric in all_metric_names:
        vals = [f"{run_metrics[r].get(metric, 'n/a'):.4f}"
                if isinstance(run_metrics[r].get(metric), float) else "n/a"
                for r in run_ids]
        table_lines.append(f"| {metric} | " + " | ".join(vals) + " |")

    diffs: dict[str, float] = {}
    if len(run_ids) == 2:
        r1, r2 = run_ids
        for m in all_metric_names:
            v1 = run_metrics[r1].get(m)
            v2 = run_metrics[r2].get(m)
            if isinstance(v1, float) and isinstance(v2, float):
                diffs[m] = v2 - v1

    return {
        "run_ids": run_ids,
        "run_statuses": run_statuses,
        "metrics": run_metrics,
        "markdown_table": "\n".join(table_lines),
        "diffs": diffs,
    }
