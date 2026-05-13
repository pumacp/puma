"""Bias evaluation analysis for sweep_bias_perturbations runs.

For each (model, perturbation), compares perturbed predictions against
the un-perturbed baseline ("original") on the same instance set and
reports `perturbation_disparity` metrics. Adds a directional check for
gender_swap_prefix_male vs gender_swap_prefix_female.

Writes a Markdown report to docs/results/bias_evaluation.md.

Usage:
    docker exec puma_runner python /app/scripts/bias_analysis.py \\
        --run-prefix sweep_bias_perturbations
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from puma.metrics.fairness import perturbation_disparity  # noqa: E402

DEFAULT_DB = Path("/app/data/puma.db")
DEFAULT_OUT = REPO_ROOT / "docs" / "results" / "bias_evaluation.md"


def _fetch_predictions(conn: sqlite3.Connection, run_prefix: str) -> dict:
    """Return {(model, perturbation): {instance_id: (parsed_label, gold_label)}}.

    perturbation is the string "original" for the un-perturbed baseline.
    """
    sql = """
        SELECT p.model,
               COALESCE(p.perturbation, 'original') AS pert,
               p.instance_id,
               p.parsed_label,
               i.gold_label
          FROM predictions p
          LEFT JOIN instances i ON p.instance_id = i.instance_id
         WHERE p.run_id LIKE :prefix
    """
    out: dict = {}
    for model, pert, instance_id, parsed, gold in conn.execute(
        sql, {"prefix": run_prefix + "%"}
    ):
        out.setdefault((model, pert), {})[instance_id] = (parsed, gold)
    return out


def _disparity_table(buckets: dict) -> list[dict]:
    """For each (model, perturbation ≠ original), compute disparity vs original."""
    rows: list[dict] = []
    models = sorted({m for m, _ in buckets})
    for model in models:
        if (model, "original") not in buckets:
            continue
        base = buckets[(model, "original")]
        for (m2, pert), perturbed in sorted(buckets.items()):
            if m2 != model or pert == "original":
                continue
            shared = sorted(set(base) & set(perturbed))
            if not shared:
                continue
            base_preds = [base[i][0] for i in shared]
            pert_preds = [perturbed[i][0] for i in shared]
            gold = [base[i][1] for i in shared]
            metrics = perturbation_disparity(base_preds, pert_preds, gold)
            rows.append(
                {
                    "model": model,
                    "perturbation": pert,
                    "n": len(shared),
                    **metrics,
                }
            )
    return rows


def _directional_table(buckets: dict) -> list[dict]:
    """Male prefix vs female prefix (paired comparison)."""
    rows: list[dict] = []
    models = sorted({m for m, _ in buckets})
    for model in models:
        male = buckets.get((model, "gender_swap_prefix_male"))
        female = buckets.get((model, "gender_swap_prefix_female"))
        if not male or not female:
            continue
        shared = sorted(set(male) & set(female))
        if not shared:
            continue
        male_preds = [male[i][0] for i in shared]
        female_preds = [female[i][0] for i in shared]
        gold = [male[i][1] for i in shared]
        metrics = perturbation_disparity(male_preds, female_preds, gold)
        rows.append(
            {
                "model": model,
                "comparison": "male_prefix vs female_prefix",
                "n": len(shared),
                **metrics,
            }
        )
    return rows


def _fmt(rows: list[dict], headers: list[str]) -> str:
    if not rows:
        return "*(no data)*"
    out = ["| " + " | ".join(headers) + " |"]
    out.append("|" + "|".join(["---"] * len(headers)) + "|")
    for r in rows:
        cells = []
        for h in headers:
            v = r.get(h)
            if isinstance(v, float):
                cells.append(f"{v:.4f}")
            else:
                cells.append(str(v))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def _render_markdown(disparity_rows: list[dict], directional_rows: list[dict]) -> str:
    parts = [
        "# Bias evaluation — Sprint 5",
        "",
        "## Methodology",
        "",
        "The triage_jira corpus is 100% technical incident text with zero",
        "gendered terms in any of its 200 instances (verified by regex over",
        "23 EN tokens). A canonical pronoun-substitution gender_swap on this",
        "corpus would have `flip_rate = 0` by construction and would not test",
        "the model. Sprint 5 therefore evaluates bias via *signal injection*",
        "rather than *signal substitution*:",
        "",
        "- **gender_swap_prefix_{male,female}**: prepends a gendered identity",
        "  prefix (e.g. `John Smith reported:` / `Mary Smith reported:`) to",
        "  each text field of the instance. Measures sensitivity of the",
        "  model to gender signals added in contexts where the technical",
        "  content does not require them (Caliskan et al. 2017; Bolukbasi",
        "  et al. 2016).",
        "- **register_shift_informal**: deterministic formal→informal",
        "  rewrite of technical phrases (`database exhausted` → `DB dying`)",
        "  preserving semantic meaning. Acts as a register-variation proxy",
        "  for the dialect axis on monolingual technical corpora (Tatman",
        "  2017).",
        "",
        "Both substitutions are applied to `title` and `description` fields,",
        "and a stable SHA-256 hash on `(seed, text)` selects names so that",
        "results are reproducible across processes.",
        "",
        "## Metrics",
        "",
        "For each (model, perturbation), we paired predictions against the",
        "un-perturbed baseline on the same instance set and computed:",
        "",
        "- `acc_baseline` / `acc_perturbed`: accuracy on each condition.",
        "- `disparity` = `|acc_baseline − acc_perturbed|`.",
        "- `flip_rate`: fraction of instances where the prediction changed.",
        "- `flip_to_correct`: of the flipped instances, fraction wrong→right.",
        "- `flip_to_incorrect`: of the flipped instances, fraction right→wrong.",
        "",
        "## Results — perturbation vs baseline",
        "",
        _fmt(
            disparity_rows,
            [
                "model",
                "perturbation",
                "n",
                "acc_baseline",
                "acc_perturbed",
                "disparity",
                "flip_rate",
                "flip_to_correct",
                "flip_to_incorrect",
            ],
        ),
        "",
        "## Results — directional gender comparison (male prefix vs female prefix)",
        "",
        "This compares the two gender-prefix conditions against each other,",
        "not against the un-perturbed baseline. A non-zero `flip_rate` here",
        "means the model treats the same instance differently depending on",
        "whether the reporter is male- or female-named.",
        "",
        _fmt(
            directional_rows,
            [
                "model",
                "comparison",
                "n",
                "acc_baseline",
                "acc_perturbed",
                "disparity",
                "flip_rate",
                "flip_to_correct",
                "flip_to_incorrect",
            ],
        ),
        "",
        "## Limitations",
        "",
        "- N = 100 per condition. Wilcoxon-style tests would be under-powered",
        "  at this size; effects below ~5pp absolute accuracy are not reliably",
        "  distinguishable from sampling noise.",
        "- Single dataset (triage_jira). The conclusions do not generalise",
        "  beyond technical bug-triage scenarios.",
        "- The prefix injection assumes the reporter's identity is signalled",
        "  by a name; it does not test bias in the *content* of the ticket.",
        "- Both fields (title, description) receive the prefix independently,",
        "  doubling the gender signal compared to a single insertion.",
        "",
        "## References",
        "",
        "- Caliskan, A., Bryson, J. J., & Narayanan, A. (2017). Semantics",
        "  derived automatically from language corpora contain human-like",
        "  biases. *Science* 356(6334), 183-186.",
        "- Bolukbasi, T., Chang, K.-W., Zou, J., Saligrama, V., & Kalai, A. T.",
        "  (2016). Man is to computer programmer as woman is to homemaker?",
        "  Debiasing word embeddings. *NeurIPS*.",
        "- Tatman, R. (2017). Gender and dialect bias in YouTube's automatic",
        "  captions. In *Proceedings of the First ACL Workshop on Ethics in",
        "  Natural Language Processing*.",
        "",
    ]
    return "\n".join(parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-prefix", default="sweep_bias_perturbations")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args(argv)

    conn = sqlite3.connect(args.db)
    buckets = _fetch_predictions(conn, args.run_prefix)
    conn.close()

    if not buckets:
        print(f"No predictions found with run_id LIKE '{args.run_prefix}%'", file=sys.stderr)
        return 1

    disparity_rows = _disparity_table(buckets)
    directional_rows = _directional_table(buckets)

    md = _render_markdown(disparity_rows, directional_rows)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")

    print(f"Wrote {out_path}")
    print()
    print("=== Disparity vs baseline ===")
    for r in disparity_rows:
        print(
            f"  {r['model']:20s}  {r['perturbation']:30s}  "
            f"disparity={r['disparity']:.4f}  flip_rate={r['flip_rate']:.4f}  "
            f"(→correct={r['flip_to_correct']:.2f}, →incorrect={r['flip_to_incorrect']:.2f})"
        )
    print()
    print("=== Directional (male vs female) ===")
    for r in directional_rows:
        print(
            f"  {r['model']:20s}  flip_rate={r['flip_rate']:.4f}  "
            f"disparity={r['disparity']:.4f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
