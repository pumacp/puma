"""Strip reasoning-style ``<think>...</think>`` blocks from model outputs.

Reasoning models (e.g. deepseek-r1) emit chain-of-thought inside
``<think>`` tags before the final answer. Per-scenario regex extractors
otherwise pick up incidental matches inside the reasoning (e.g. the word
"critical" in passing). Calling :func:`strip_reasoning` on the raw output
before parsing restores the same extraction path used for plain
instruction-tuned models.
"""

from __future__ import annotations

import re

_CLOSED_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_UNCLOSED_THINK_TO_END_RE = re.compile(r"<think>.*$", re.DOTALL | re.IGNORECASE)
_STRAY_CLOSE_THINK_RE = re.compile(r"</think>", re.IGNORECASE)


def strip_reasoning(raw: str) -> str:
    """Remove ``<think>`` reasoning blocks from a model response.

    Closed ``<think>...</think>`` blocks are removed in their entirety. An
    unclosed ``<think>`` (model truncated mid-reasoning) discards everything
    from the tag to end of string — the answer is assumed to appear before
    the block in that case. Stray ``</think>`` tokens are also stripped.
    """
    cleaned = _CLOSED_THINK_RE.sub("", raw)
    cleaned = _UNCLOSED_THINK_TO_END_RE.sub("", cleaned)
    cleaned = _STRAY_CLOSE_THINK_RE.sub("", cleaned)
    return cleaned
