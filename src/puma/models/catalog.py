"""Curated-catalog adapter for ``puma models recommended``.

The catalog data is the project's single source of truth,
``config/models_catalog.yaml``, read here via :mod:`puma.preflight.catalog`
(no second YAML parser is introduced). Each
:class:`~puma.preflight.catalog.ModelEntry` is adapted into a display-shaped
:class:`CuratedModel`, and the curated set is paired with the models actually
pulled into Ollama by :func:`merge_with_local`.

**Field gap (tracked as D30).** The YAML does not (yet) encode the validation
provenance fields ``validated_for``, ``status`` and ``rationale``. Until a
schema sprint adds them, every entry is presented with conservative defaults
(``validated_for={"triage", "estimation"}``, ``status="experimental"``) and the
``rationale`` is derived from the catalog ``notes``. The YAML itself is NOT
modified by this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from puma.preflight.catalog import ModelEntry, load_catalog

if TYPE_CHECKING:
    from puma.models.client import LocalModel

# Defaults for fields absent from config/models_catalog.yaml (see D30).
_DEFAULT_VALIDATED_FOR: frozenset[str] = frozenset({"triage", "estimation"})
_DEFAULT_STATUS = "experimental"
_RATIONALE_MAX = 120


@dataclass(frozen=True)
class CuratedModel:
    """A catalog entry adapted for display in ``puma models recommended``."""

    name: str
    family: str
    parameter_size_b: float
    gguf_size_gb: float
    context_window: int
    validated_for: frozenset[str]
    status: str
    rationale: str


def _family_from_tag(tag: str) -> str:
    """Derive a family label from an Ollama tag (``qwen2.5:3b`` -> ``Qwen2.5``)."""
    base = tag.split(":", 1)[0]
    return base[:1].upper() + base[1:] if base else tag


def _rationale_from_notes(notes: str | None) -> str:
    """Collapse multi-line catalog ``notes`` into a single short rationale."""
    if not notes:
        return ""
    collapsed = " ".join(notes.split())
    if len(collapsed) <= _RATIONALE_MAX:
        return collapsed
    return collapsed[: _RATIONALE_MAX - 1].rstrip() + "…"


def _to_curated(entry: ModelEntry) -> CuratedModel:
    return CuratedModel(
        name=entry.ollama_tag,
        family=_family_from_tag(entry.ollama_tag),
        parameter_size_b=entry.params_b,
        gguf_size_gb=entry.gguf_size_gb,
        context_window=entry.context_window,
        validated_for=_DEFAULT_VALIDATED_FOR,
        status=_DEFAULT_STATUS,
        rationale=_rationale_from_notes(entry.notes),
    )


def load_curated(path: Path | None = None) -> tuple[CuratedModel, ...]:
    """Load the curated catalog from ``config/models_catalog.yaml``.

    ``path`` overrides the default catalog location (used by tests); when
    ``None`` the packaged catalog is used. Read-only — never mutates the YAML.
    """
    entries = load_catalog() if path is None else load_catalog(path)
    return tuple(_to_curated(entry) for entry in entries)


def merge_with_local(
    curated: tuple[CuratedModel, ...],
    local: list[LocalModel],
) -> list[tuple[CuratedModel, LocalModel | None]]:
    """Pair each curated model with its locally-pulled counterpart (or ``None``)."""
    by_name = {model.name: model for model in local}
    return [(model, by_name.get(model.name)) for model in curated]
