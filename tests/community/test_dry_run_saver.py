"""Tests for the dry-run saver."""

from __future__ import annotations

import json
import stat
import sys
from pathlib import Path

import pytest

from puma.community.dry_run_saver import save_dry_run


def _payload(submission_id: str = "abc-123") -> dict:
    return {
        "submission_id": submission_id,
        "schema_version": "1.0.0",
        "data": {"hello": "world"},
    }


def test_saves_json_at_expected_path(tmp_path: Path) -> None:
    target = tmp_path / "submissions"
    path = save_dry_run(payload=_payload(), output_dir=target)
    assert path == (target / "abc-123.json").resolve()
    assert path.exists()
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk["submission_id"] == "abc-123"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only permission semantics")
def test_creates_parent_directory_with_safe_mode_on_posix(tmp_path: Path) -> None:
    target = tmp_path / "submissions"
    save_dry_run(payload=_payload(), output_dir=target)
    dir_mode = stat.S_IMODE(target.stat().st_mode)
    file_mode = stat.S_IMODE((target / "abc-123.json").stat().st_mode)
    assert dir_mode == 0o700
    assert file_mode == 0o600


def test_refuses_to_overwrite_existing_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("PUMA_DRY_RUN_OVERWRITE", raising=False)
    save_dry_run(payload=_payload(), output_dir=tmp_path)
    with pytest.raises(FileExistsError):
        save_dry_run(payload=_payload(), output_dir=tmp_path)


def test_overwrite_when_env_set(tmp_path: Path, monkeypatch) -> None:
    save_dry_run(payload=_payload(), output_dir=tmp_path)
    monkeypatch.setenv("PUMA_DRY_RUN_OVERWRITE", "1")
    p2 = save_dry_run(payload=_payload(), output_dir=tmp_path)
    assert p2.exists()


def test_output_dir_override_via_param(tmp_path: Path) -> None:
    custom = tmp_path / "custom-dir" / "subs"
    path = save_dry_run(payload=_payload(), output_dir=custom)
    assert str(custom) in str(path)


def test_output_dir_override_via_env(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PUMA_DRY_RUN_DIR", str(tmp_path / "env-dir"))
    path = save_dry_run(payload=_payload())
    assert str(tmp_path / "env-dir") in str(path)


def test_rejects_payload_without_submission_id(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        save_dry_run(payload={"schema_version": "1.0.0"}, output_dir=tmp_path)
