"""Text perturbation generators: typos, case, truncation, reorder, tech-noise."""

from __future__ import annotations

import random

HOMOGLYPHS: dict[str, str] = {
    "a": "4", "e": "3", "i": "1", "o": "0", "s": "5", "t": "7",
    "b": "6", "g": "9", "l": "1", "z": "2", "A": "4", "E": "3",
    "I": "1", "O": "0", "S": "5", "T": "7", "B": "8", "G": "6",
}


def typos(text: str, rate: float = 0.05, seed: int = 42) -> str:
    """Substitute characters with visual homologs at the given rate."""
    if not text:
        return text
    rng = random.Random(seed)
    chars = list(text)
    candidates = [i for i, c in enumerate(chars) if c in HOMOGLYPHS]
    n_subs = max(1, int(len(candidates) * rate)) if candidates else 0
    indices = rng.sample(candidates, min(n_subs, len(candidates)))
    for idx in indices:
        chars[idx] = HOMOGLYPHS[chars[idx]]
    return "".join(chars)


def case_change(text: str, mode: str = "upper", seed: int = 42) -> str:
    """Transform text case: 'upper', 'lower', or 'random' (per-word)."""
    if mode == "upper":
        return text.upper()
    if mode == "lower":
        return text.lower()
    if mode == "random":
        rng = random.Random(seed)
        return "".join(c.upper() if rng.random() > 0.5 else c.lower() for c in text)
    raise ValueError(f"Unknown mode '{mode}'. Use 'upper', 'lower', or 'random'.")


def truncate(text: str, keep: float = 0.5, from_: str = "end") -> str:
    """Truncate text to keep fraction of original length.

    Args:
        text: Input string.
        keep: Fraction of characters to keep (0 < keep ≤ 1).
        from_: 'end' removes from the end; 'middle' removes the middle section.
    """
    if not text or keep >= 1.0:
        return text
    n = max(1, int(len(text) * keep))
    if from_ == "end":
        return text[:n]
    if from_ == "middle":
        half = n // 2
        return text[:half] + text[len(text) - (n - half):]
    raise ValueError(f"Unknown from_ '{from_}'. Use 'end' or 'middle'.")


def reorder_fields(instance: dict, order: list[str]) -> dict:
    """Return a new dict with text fields concatenated in the given order.

    Fields not in `order` are preserved unchanged.
    """
    reordered = {}
    for key in order:
        if key in instance:
            reordered[key] = instance[key]
    for key, val in instance.items():
        if key not in reordered:
            reordered[key] = val
    return reordered


def tech_noise(
    text: str,
    terms: list[str] | None = None,
    insertions: int = 3,
    seed: int = 42,
) -> str:
    """Insert technical noise tokens (TODO, FIXME, deprecated) at random word positions."""
    if terms is None:
        terms = ["TODO", "FIXME", "deprecated"]
    if not text.strip():
        return text
    rng = random.Random(seed)
    words = text.split()
    for _ in range(insertions):
        pos = rng.randint(0, len(words))
        words.insert(pos, rng.choice(terms))
    return " ".join(words)
