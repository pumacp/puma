"""``puma.resources`` precedence and call-site wiring (D42 prototype)."""

from __future__ import annotations

from pathlib import Path

import pytest

from puma import resources

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _layout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    source_root, bundled_root = (tmp_path / n for n in ("source", "bundled"))
    for root in (source_root, bundled_root):
        (root / "config").mkdir(parents=True)
    monkeypatch.setattr(resources, "SOURCE_ROOT", source_root)
    monkeypatch.setattr(resources, "BUNDLED_ROOT", bundled_root)
    return source_root, bundled_root


@pytest.mark.unit
def test_search_order_is_source_tree_then_bundle(tmp_path, monkeypatch):
    source_root, bundled_root = _layout(tmp_path, monkeypatch)
    assert resources.search_roots() == (source_root, bundled_root)


@pytest.mark.unit
def test_source_tree_wins_over_bundled_copy(tmp_path, monkeypatch):
    source_root, bundled_root = _layout(tmp_path, monkeypatch)
    (source_root / "config" / "profiles.yaml").write_text("source", encoding="utf-8")
    (bundled_root / "config" / "profiles.yaml").write_text("bundled", encoding="utf-8")
    assert resources.resolve("config/profiles.yaml") == source_root / "config" / "profiles.yaml"


@pytest.mark.unit
def test_bundled_copy_used_when_source_tree_lacks_the_file(tmp_path, monkeypatch):
    _, bundled_root = _layout(tmp_path, monkeypatch)
    (bundled_root / "config" / "profiles.yaml").write_text("bundled", encoding="utf-8")
    assert resources.resolve("config/profiles.yaml") == bundled_root / "config" / "profiles.yaml"


@pytest.mark.unit
def test_missing_everywhere_returns_the_source_tree_path(tmp_path, monkeypatch):
    source_root, _ = _layout(tmp_path, monkeypatch)
    resolved = resources.resolve("config/profiles.yaml")
    assert resolved == source_root / "config" / "profiles.yaml"
    assert not resolved.exists()


@pytest.mark.unit
def test_source_root_is_the_repository_root_in_a_clone():
    assert resources.SOURCE_ROOT == _REPO_ROOT
    assert resources.BUNDLED_ROOT == _REPO_ROOT / "src" / "puma" / "_bundled"
    assert not resources.BUNDLED_ROOT.exists(), "no bundled copies may exist in the source tree"


@pytest.mark.unit
def test_every_bundled_pattern_matches_and_tawos_is_excluded():
    files = resources.bundled_files(_REPO_ROOT)
    relative = {p.relative_to(_REPO_ROOT).as_posix() for p in files}
    for pattern in resources.BUNDLED_PATTERNS:
        assert any(Path(r).match(pattern) for r in relative), f"no file matches {pattern}"
    assert "config/profiles.yaml" in relative
    assert "data/jira_balanced_200.csv" in relative
    assert "specs/prompts/triage_jira/zero_shot.jinja" in relative
    assert "alembic/versions/0001_initial_schema.py" in relative
    assert "src/puma/community/schema_data/submission.v1.json" not in relative  # package-data
    assert not any(r.startswith("data/tawos") for r in relative)
    assert len(files) == len(set(files))


@pytest.mark.unit
def test_call_sites_resolve_through_the_resolver():
    from puma.adaptation import base as adaptation_base
    from puma.community import builder
    from puma.datasets import jira_sr
    from puma.preflight import catalog, profile

    assert resources.resolve("config/profiles.yaml") == profile._PROFILES_PATH
    assert resources.resolve("config/models_catalog.yaml") == catalog._CATALOG_PATH
    assert resources.resolve("config/models_catalog.yaml") == builder._CATALOG_PATH
    assert resources.resolve("specs/prompts") == adaptation_base.PROMPTS_DIR
    assert resources.resolve("data/jira_balanced_200.csv") == jira_sr._CSV_PATH
    # In a clone every one of them is the repository file, exactly as before.
    assert profile._PROFILES_PATH == _REPO_ROOT / "config" / "profiles.yaml"
    assert adaptation_base.PROMPTS_DIR == _REPO_ROOT / "specs" / "prompts"
    assert jira_sr._CSV_PATH == _REPO_ROOT / "data" / "jira_balanced_200.csv"


@pytest.mark.unit
def test_in_source_tree_reports_whether_the_repository_file_exists(tmp_path, monkeypatch):
    source_root, _ = _layout(tmp_path, monkeypatch)
    assert not resources.in_source_tree("alembic")
    (source_root / "alembic").mkdir()
    assert resources.in_source_tree("alembic")


@pytest.mark.unit
def test_alembic_config_in_source_tree_requires_ini_in_cwd(tmp_path, monkeypatch):
    """A clone keeps the develop behaviour: alembic.ini comes from the cwd or init fails."""
    from puma.storage import db

    assert resources.in_source_tree("alembic")  # the test suite runs from a clone
    cfg = db._alembic_config_for("sqlite:///x.db")  # pytest runs from the repository root
    assert cfg.config_file_name == "alembic.ini"
    assert cfg.get_main_option("sqlalchemy.url") == "sqlite:///x.db"

    monkeypatch.chdir(tmp_path)
    with pytest.raises(RuntimeError, match="Alembic configuration not found"):
        db._alembic_config_for("sqlite:///x.db")


@pytest.mark.unit
def test_alembic_config_without_source_tree_uses_bundled_migrations(tmp_path, monkeypatch):
    """An installed wheel has no source tree: the bundled migrations are used
    programmatically and init_db still runs Alembic, never create_all."""
    from unittest.mock import patch

    from sqlalchemy import create_engine, inspect

    from puma.storage import db
    from puma.storage.models import Base

    monkeypatch.setattr(resources, "SOURCE_ROOT", tmp_path / "no-source-tree")
    monkeypatch.setattr(resources, "BUNDLED_ROOT", _REPO_ROOT)  # stands in for puma/_bundled
    monkeypatch.chdir(tmp_path)
    assert not (tmp_path / "alembic.ini").exists()

    cfg = db._alembic_config_for("sqlite:///x.db")
    assert cfg.config_file_name is None
    assert Path(cfg.get_main_option("script_location")) == _REPO_ROOT / "alembic"

    db_path = tmp_path / "wheel.db"
    with patch.object(Base.metadata, "create_all") as mock_create_all:
        db.init_db(db_path)
    assert mock_create_all.call_count == 0
    tables = set(inspect(create_engine(f"sqlite:///{db_path}")).get_table_names())
    assert tables == set(Base.metadata.tables.keys()) | {"alembic_version"}
