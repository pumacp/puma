"""Model catalog reader — single source of truth for model metadata.

The catalog (``config/models_catalog.yaml``) lists every supported Ollama
model with its hardware requirements (size, VRAM/RAM implications via
parameter count and context window) and the set of execution profiles it is
compatible with. ``models_for_profile`` derives the dispatch list for a
given profile dynamically from this catalog.

Before B.1.3, ``config/profiles.yaml`` carried a manually-curated
``models[]`` list per profile. Maintaining two sources caused 17 silent
``(profile, tag)`` pairs to drift apart. After B.1.3, profiles.yaml only
encodes hardware thresholds; ``models[]`` is computed at lookup time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

_CATALOG_PATH = Path(__file__).parent.parent.parent.parent / "config" / "models_catalog.yaml"


@dataclass(frozen=True)
class ModelEntry:
    """Immutable view of a single catalog row."""

    ollama_tag: str
    params_b: float
    gguf_size_gb: float
    context_window: int
    logprobs_supported: bool
    profiles_compatible: list[str] = field(default_factory=list)
    timeout_s: int = 120
    notes: str | None = None


@lru_cache(maxsize=1)
def load_catalog(path: Path = _CATALOG_PATH) -> tuple[ModelEntry, ...]:
    """Load and cache the model catalog.

    Returns a tuple (immutable) so callers cannot accidentally mutate the
    cached value. ``lru_cache`` keys on ``path`` so test fixtures pointing
    at temporary files do not pollute the production cache.
    """
    with open(path, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    entries = []
    for row in raw.get("models", []):
        entries.append(
            ModelEntry(
                ollama_tag=row["ollama_tag"],
                params_b=float(row["params_b"]),
                gguf_size_gb=float(row["gguf_size_gb"]),
                context_window=int(row["context_window"]),
                logprobs_supported=bool(row.get("logprobs_supported", False)),
                profiles_compatible=list(row.get("profiles_compatible", [])),
                timeout_s=int(row.get("timeout_s", 120)),
                notes=row.get("notes"),
            )
        )
    return tuple(entries)


def models_for_profile(profile_name: str) -> list[ModelEntry]:
    """Return every catalog entry whose ``profiles_compatible`` includes ``profile_name``.

    Unknown profile names yield an empty list (no exception). The list is a
    fresh copy on each call so callers may filter or sort it without
    affecting future lookups.
    """
    return [m for m in load_catalog() if profile_name in m.profiles_compatible]


def get_model_by_tag(tag: str) -> ModelEntry | None:
    """Return the catalog entry for ``tag``, or ``None`` if absent."""
    for m in load_catalog():
        if m.ollama_tag == tag:
            return m
    return None
