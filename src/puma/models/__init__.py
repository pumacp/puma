"""Read-only model discovery and curated-catalog package.

Exposes the curated-catalog adapter (:func:`load_curated`, :class:`CuratedModel`,
:func:`merge_with_local`). The Ollama HTTP client lives in
:mod:`puma.models.client` and is imported directly by callers that need it.
"""

from __future__ import annotations

from puma.models.catalog import CuratedModel, load_curated, merge_with_local

__all__ = ["CuratedModel", "load_curated", "merge_with_local"]
