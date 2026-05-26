"""Read-only Ollama model-discovery client (``list`` / ``show``).

Strictly side-effect free: queries Ollama's HTTP API with a short timeout and
never pulls, runs, or mutates anything. Mirrors the ``httpx`` usage and broad
error-mapping pattern of :mod:`puma.diagnostics.checks`: connection/timeout
failures are surfaced as :class:`OllamaUnreachable` rather than allowed to
propagate as raw ``httpx`` errors, so the CLI never hangs and renders a clean
themed error panel instead.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


class OllamaUnreachable(RuntimeError):
    """The Ollama HTTP API could not be reached (connection refused/timeout)."""


class ModelNotFound(LookupError):
    """The requested model is not pulled locally (Ollama returned HTTP 404)."""


@dataclass(frozen=True)
class LocalModel:
    """Metadata for a single model pulled locally in Ollama."""

    name: str
    size_bytes: int
    digest: str
    modified_at: str
    parameter_size: str | None = None
    quantization: str | None = None
    family: str | None = None


def _tags_url(endpoint: str) -> str:
    return f"{endpoint.rstrip('/')}/api/tags"


def _show_url(endpoint: str) -> str:
    return f"{endpoint.rstrip('/')}/api/show"


def _parse_tag(entry: dict[str, Any]) -> LocalModel:
    details = entry.get("details") or {}
    return LocalModel(
        name=str(entry.get("name", "")),
        size_bytes=int(entry.get("size", 0) or 0),
        digest=str(entry.get("digest", "")),
        modified_at=str(entry.get("modified_at", "")),
        parameter_size=details.get("parameter_size"),
        quantization=details.get("quantization_level"),
        family=details.get("family"),
    )


def list_local_models(endpoint: str, timeout_s: float = 3.0) -> list[LocalModel]:
    """Return the models pulled locally in Ollama, sorted by name.

    Queries ``{endpoint}/api/tags``. Raises :class:`OllamaUnreachable` on any
    connection/timeout/HTTP error.
    """
    try:
        resp = httpx.get(_tags_url(endpoint), timeout=timeout_s)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        raise OllamaUnreachable(
            f"Ollama not reachable at {endpoint}: {type(exc).__name__}"
        ) from exc
    models = [_parse_tag(entry) for entry in data.get("models", [])]
    return sorted(models, key=lambda m: m.name)


def _lookup_tag_row(endpoint: str, name: str, timeout_s: float) -> LocalModel | None:
    """Find the ``/api/tags`` row for ``name`` (for size/digest/modified_at)."""
    try:
        for model in list_local_models(endpoint, timeout_s):
            if model.name == name:
                return model
    except OllamaUnreachable:
        return None
    return None


def show_local_model(endpoint: str, name: str, timeout_s: float = 3.0) -> LocalModel:
    """Return detailed metadata for one locally-pulled model.

    Queries ``{endpoint}/api/show`` (POST ``{"name": name}``) for the rich
    ``details`` (parameter size, quantization, family) and merges in the
    ``/api/tags`` row for size/digest/modified_at. Raises :class:`ModelNotFound`
    on HTTP 404, :class:`OllamaUnreachable` on any other connection/HTTP error.
    """
    try:
        resp = httpx.post(_show_url(endpoint), json={"name": name}, timeout=timeout_s)
    except Exception as exc:
        raise OllamaUnreachable(
            f"Ollama not reachable at {endpoint}: {type(exc).__name__}"
        ) from exc
    if resp.status_code == 404:
        raise ModelNotFound(
            f"Model {name!r} is not pulled locally. Fetch it with: ollama pull {name}"
        )
    try:
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:
        raise OllamaUnreachable(
            f"Ollama returned an error for {name!r}: {type(exc).__name__}"
        ) from exc
    details = payload.get("details") or {}
    base = _lookup_tag_row(endpoint, name, timeout_s)
    return LocalModel(
        name=name,
        size_bytes=base.size_bytes if base else 0,
        digest=base.digest if base else "",
        modified_at=base.modified_at if base else "",
        parameter_size=details.get("parameter_size"),
        quantization=details.get("quantization_level"),
        family=details.get("family"),
    )
