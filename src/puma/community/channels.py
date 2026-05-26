"""Static registry of PUMA Community distribution channels (read-only).

The PUMA Community public repository (``github.com/pumacp/puma-community``) runs
GitHub Actions workflows that mirror accepted submissions to external archives
(Hugging Face, Zenodo, Kaggle) and post notifications (Discord, Telegram). This
module is a *local, read-only* view of those channels: it knows their names,
kinds, targets, the workflow file that implements each one in the puma-community
repo, and which local environment variable a maintainer would set to drive the
corresponding workflow.

It makes **no network calls**. ``is_local_configured`` is derived purely from
``os.environ`` — it reports whether the relevant secret is present in the local
environment, never whether the remote workflow is healthy.

The registry is intentionally a Python constant for v4.0.0; externalising it to
YAML is a possible post-v4.0.0 change.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from typing import Literal

ChannelKind = Literal["mirror", "notification", "validation"]


@dataclass(frozen=True)
class Channel:
    """One PUMA Community distribution channel.

    Attributes:
        name: Human-readable channel name (e.g. ``"Hugging Face Datasets"``).
        kind: ``"mirror"`` (archives the dataset), ``"notification"`` (announces
            it), or ``"validation"`` (checks it).
        target: Where the channel publishes/announces (descriptive).
        workflow_file: The GitHub Actions workflow file in the puma-community
            repo that implements this channel.
        docs_url: Link to the docs section describing this channel.
        requires_secret: The repository/local secret env var the workflow needs,
            or ``None`` if the channel needs no secret.
        is_local_configured: Whether ``requires_secret`` is set in the local
            environment. Populated by :func:`enrich_with_local_state`; ``False``
            on the static registry entries.
    """

    name: str
    kind: ChannelKind
    target: str
    workflow_file: str
    docs_url: str
    requires_secret: str | None
    is_local_configured: bool = False


_DOCS_BASE = "https://pumacp.github.io/puma/publication_workflow/#channels"


CHANNELS: tuple[Channel, ...] = (
    Channel(
        name="Hugging Face Datasets",
        kind="mirror",
        target="datasets/pumacp/puma-community",
        workflow_file="mirror-huggingface.yml",
        docs_url=_DOCS_BASE,
        requires_secret="HF_TOKEN",
    ),
    Channel(
        name="Zenodo",
        kind="mirror",
        target="zenodo.org/communities/puma",
        workflow_file="mirror-zenodo.yml",
        docs_url=_DOCS_BASE,
        requires_secret="ZENODO_TOKEN",
    ),
    Channel(
        name="Kaggle",
        kind="mirror",
        target="datasets/pumacp/puma-community",
        workflow_file="mirror-kaggle.yml",
        docs_url=_DOCS_BASE,
        requires_secret="KAGGLE_KEY",
    ),
    Channel(
        name="Discord",
        kind="notification",
        target="PUMA Community server (#submissions)",
        workflow_file="notify-discord.yml",
        docs_url=_DOCS_BASE,
        requires_secret="DISCORD_WEBHOOK",
    ),
    Channel(
        name="Telegram",
        kind="notification",
        target="PUMA Community channel",
        workflow_file="notify-telegram.yml",
        docs_url=_DOCS_BASE,
        requires_secret="TELEGRAM_BOT_TOKEN",
    ),
)


def detect_local_configuration(channel: Channel) -> bool:
    """Return whether ``channel`` is locally configured.

    A channel is "configured" when its ``requires_secret`` environment variable
    is present and non-empty. A channel that needs no secret
    (``requires_secret is None``) is considered configured. Pure function: reads
    only ``os.environ``, no side effects, no network.
    """
    if channel.requires_secret is None:
        return True
    return bool(os.environ.get(channel.requires_secret))


def enrich_with_local_state(channels: tuple[Channel, ...]) -> list[Channel]:
    """Return copies of ``channels`` with ``is_local_configured`` populated."""
    return [replace(ch, is_local_configured=detect_local_configuration(ch)) for ch in channels]


__all__ = [
    "CHANNELS",
    "Channel",
    "ChannelKind",
    "detect_local_configuration",
    "enrich_with_local_state",
]
