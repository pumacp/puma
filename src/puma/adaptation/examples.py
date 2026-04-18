"""Few-shot example selector: stratified, deterministic."""

from __future__ import annotations

import pandas as pd


def select_examples(
    df: pd.DataFrame,
    k: int,
    seed: int = 42,
    stratify_by: str | None = None,
    exclude_index: int | None = None,
) -> list[dict]:
    """Return k examples from df, stratified by class if requested.

    Args:
        df: Source DataFrame.
        k: Number of examples to select.
        seed: Random seed for reproducibility.
        stratify_by: Column name to stratify on (e.g. "priority").
        exclude_index: DataFrame row index to exclude (the target instance).

    Returns:
        List of row dicts.
    """
    pool = df.copy()
    if exclude_index is not None and exclude_index in pool.index:
        pool = pool.drop(index=exclude_index)

    if stratify_by and stratify_by in pool.columns:
        classes = pool[stratify_by].unique().tolist()
        per_class = max(1, k // len(classes))
        remainder = k - per_class * len(classes)
        selected: list[pd.DataFrame] = []
        rng = pd.Series(range(len(pool))).sample(frac=1, random_state=seed)
        for i, cls in enumerate(classes):
            cls_df = pool[pool[stratify_by] == cls]
            n = per_class + (1 if i < remainder else 0)
            sampled = cls_df.sample(n=min(n, len(cls_df)), random_state=seed)
            selected.append(sampled)
        result_df = pd.concat(selected).sample(frac=1, random_state=seed).head(k)
        _ = rng  # unused but keeps seed usage consistent
    else:
        result_df = pool.sample(n=min(k, len(pool)), random_state=seed)

    return result_df.to_dict("records")
