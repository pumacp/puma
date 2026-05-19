"""Dry-run saver for PUMA Community submissions.

Persists a submission payload as JSON without touching the network. The output
directory is ``data/community/submissions/`` by default (relative to the current
working directory); override via the ``output_dir`` parameter or the
``PUMA_DRY_RUN_DIR`` environment variable.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

log = logging.getLogger("puma.community.dry_run_saver")

_DIR_MODE: int = 0o700
_FILE_MODE: int = 0o600


def _default_output_dir() -> Path:
    override = os.environ.get("PUMA_DRY_RUN_DIR")
    if override:
        return Path(override)
    return Path("data") / "community" / "submissions"


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if sys.platform != "win32":
        try:
            path.chmod(_DIR_MODE)
        except OSError as exc:  # pragma: no cover — defensive
            log.debug("could not tighten dry-run dir mode: %s", exc)


def _resolve_submission_id(payload: dict[str, Any]) -> str:
    sid = payload.get("submission_id")
    if not sid:
        raise ValueError("payload is missing 'submission_id'")
    return str(sid)


def save_dry_run(
    *,
    payload: dict[str, Any],
    output_dir: Path | None = None,
) -> Path:
    """Write ``payload`` as ``<output_dir>/<submission_id>.json``.

    Refuses to overwrite an existing file unless ``PUMA_DRY_RUN_OVERWRITE=1``.
    Returns the absolute path of the written file.
    """
    target_dir = Path(output_dir) if output_dir is not None else _default_output_dir()
    _ensure_dir(target_dir)
    submission_id = _resolve_submission_id(payload)
    target = (target_dir / f"{submission_id}.json").resolve()

    overwrite = os.environ.get("PUMA_DRY_RUN_OVERWRITE") == "1"
    if target.exists() and not overwrite:
        raise FileExistsError(
            f"{target} already exists. Set PUMA_DRY_RUN_OVERWRITE=1 to replace it."
        )

    if sys.platform == "win32":
        target.write_text(
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False),
            encoding="utf-8",
        )
    else:
        flags = os.O_CREAT | os.O_WRONLY | os.O_TRUNC
        fd = os.open(target, flags, _FILE_MODE)
        try:
            os.write(
                fd,
                json.dumps(
                    payload, indent=2, sort_keys=True, ensure_ascii=False
                ).encode("utf-8"),
            )
        finally:
            os.close(fd)
        os.chmod(target, _FILE_MODE)
    log.info("saved dry-run submission to %s", target)
    return target


__all__ = ["save_dry_run"]
