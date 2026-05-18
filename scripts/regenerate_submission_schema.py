#!/usr/bin/env python3
"""Regenerate or verify the on-disk PUMA Community submission JSON Schema.

Usage::

    python scripts/regenerate_submission_schema.py

Behaviour:
  * If ``src/puma/community/schema_data/submission.v1.json`` is missing, write it.
  * If the file is present and byte-identical to the Pydantic-generated schema,
    exit 0 with no output.
  * If the file is present and different, print a unified diff to stdout and
    exit 1 (CI drift detector).

Designed to run from the repository root, both in developer shells and in the
``puma_runner`` container.
"""

from __future__ import annotations

import difflib
import json
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "src" / "puma" / "community" / "schema_data" / "submission.v1.json"

# Ensure the src/ layout is importable when running the script directly.
sys.path.insert(0, str(REPO_ROOT / "src"))

from puma.community.schema import Submission  # noqa: E402

log = logging.getLogger("puma.community.schema.regenerate")
logging.basicConfig(level=logging.INFO, format="%(message)s")


def _serialize(schema: dict[str, object]) -> str:
    return json.dumps(schema, indent=2, sort_keys=False) + "\n"


def main() -> int:
    expected = _serialize(Submission.export_json_schema())

    if not SCHEMA_PATH.exists():
        SCHEMA_PATH.parent.mkdir(parents=True, exist_ok=True)
        SCHEMA_PATH.write_text(expected, encoding="utf-8")
        log.info("Wrote new schema at %s", SCHEMA_PATH.relative_to(REPO_ROOT))
        return 0

    actual = SCHEMA_PATH.read_text(encoding="utf-8")
    if actual == expected:
        return 0

    diff = difflib.unified_diff(
        actual.splitlines(keepends=True),
        expected.splitlines(keepends=True),
        fromfile=str(SCHEMA_PATH.relative_to(REPO_ROOT)) + " (on disk)",
        tofile=str(SCHEMA_PATH.relative_to(REPO_ROOT)) + " (generated)",
    )
    sys.stdout.writelines(diff)
    log.error("Schema drift detected — re-run this script to update the on-disk artifact.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
