"""Gender-swap via identity prefix.

Prepends a gendered name prefix to the input text. Measures model
sensitivity to gender signals added in contexts where the main content
does not require them — a common scenario in PMO/ticketing systems where
the technical content of an issue is unrelated to the reporter's gender
but a model may nonetheless shift its behaviour when that signal is added.

The triage_jira corpus is 100% technical incident text with 0 pronouns,
so a textbook pronoun-substitution gender_swap would be a no-op. The
prefix variant is the canonical workaround in the bias-evaluation
literature for technical corpora where the natural text lacks gender
markers.

References:
    Caliskan, A., Bryson, J. J., & Narayanan, A. (2017). Semantics
    derived automatically from language corpora contain human-like
    biases. Science, 356(6334), 183-186.

    Bolukbasi, T., Chang, K.-W., Zou, J., Saligrama, V., & Kalai, A. T.
    (2016). Man is to computer programmer as woman is to homemaker?
    Debiasing word embeddings. NeurIPS.
"""

from __future__ import annotations

import hashlib

MALE_NAMES: list[str] = ["John", "Michael", "David", "James", "Robert"]
FEMALE_NAMES: list[str] = ["Mary", "Patricia", "Jennifer", "Linda", "Elizabeth"]


def _stable_index(text: str, seed: int, modulus: int) -> int:
    """Process-stable hash → index in [0, modulus).

    Python's builtin `hash()` is randomised per-process (PYTHONHASHSEED),
    so it cannot be used here without breaking determinism across
    invocations. SHA-256 is content-stable.
    """
    digest = hashlib.sha256(f"{seed}:{text}".encode()).digest()
    return int.from_bytes(digest[:4], "big") % modulus


def apply_male_prefix(text: str, seed: int = 0) -> str:
    """Prepend a male-gendered identity prefix to text.

    Deterministic across processes for any given (text, seed) pair.
    """
    name = MALE_NAMES[_stable_index(text, seed, len(MALE_NAMES))]
    return f"{name} Smith reported: {text}"


def apply_female_prefix(text: str, seed: int = 0) -> str:
    """Prepend a female-gendered identity prefix to text.

    Deterministic across processes for any given (text, seed) pair.
    """
    name = FEMALE_NAMES[_stable_index(text, seed, len(FEMALE_NAMES))]
    return f"{name} Smith reported: {text}"
