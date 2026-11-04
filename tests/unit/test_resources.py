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
    from puma.preflight import catalog, profile

    assert resources.resolve("config/profiles.yaml") == profile._PROFILES_PATH
    assert resources.resolve("config/models_catalog.yaml") == catalog._CATALOG_PATH
    assert resources.resolve("config/models_catalog.yaml") == builder._CATALOG_PATH
    assert resources.resolve("specs/prompts") == adaptation_base.PROMPTS_DIR
    # In a clone every one of them is the repository file, exactly as before.
    assert profile._PROFILES_PATH == _REPO_ROOT / "config" / "profiles.yaml"
    assert adaptation_base.PROMPTS_DIR == _REPO_ROOT / "specs" / "prompts"


@pytest.mark.unit
def test_in_source_tree_reports_whether_the_repository_file_exists(tmp_path, monkeypatch):
    source_root, _ = _layout(tmp_path, monkeypatch)
    assert not resources.in_source_tree("alembic")
    (source_root / "alembic").mkdir()
    assert resources.in_source_tree("alembic")


def _cwd_layout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, Path]:
    """Source tree, bundle and an empty working directory, all under tmp_path."""
    source_root, bundled_root = _layout(tmp_path, monkeypatch)
    workdir = tmp_path / "cwd"
    workdir.mkdir()
    monkeypatch.chdir(workdir)
    for variable in resources.DOMAIN_ENV_VARS.values():
        monkeypatch.delenv(variable, raising=False)
    return source_root, bundled_root, workdir


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.mark.unit
def test_resolve_cwd_prefers_the_working_directory_over_source_and_bundle(tmp_path, monkeypatch):
    source_root, bundled_root, workdir = _cwd_layout(tmp_path, monkeypatch)
    _write(workdir / "data" / "tawos_clean.csv", "cwd")
    _write(source_root / "data" / "tawos_clean.csv", "source")
    _write(bundled_root / "data" / "tawos_clean.csv", "bundled")
    resolved = resources.resolve_cwd("data/tawos_clean.csv")
    assert resolved == Path("data/tawos_clean.csv")  # the relative path, as before bundling
    assert not resolved.is_absolute()
    assert resolved.read_text(encoding="utf-8") == "cwd"


@pytest.mark.unit
def test_resolve_cwd_falls_back_to_source_tree_then_bundle(tmp_path, monkeypatch):
    source_root, bundled_root, _ = _cwd_layout(tmp_path, monkeypatch)
    _write(source_root / "data" / "jira_balanced_200.csv", "source")
    _write(bundled_root / "data" / "jira_balanced_200.csv", "bundled")
    assert resources.resolve_cwd("data/jira_balanced_200.csv") == (
        source_root / "data" / "jira_balanced_200.csv"
    )
    (source_root / "data" / "jira_balanced_200.csv").unlink()
    assert resources.resolve_cwd("data/jira_balanced_200.csv") == (
        bundled_root / "data" / "jira_balanced_200.csv"
    )


@pytest.mark.unit
def test_resolve_cwd_returns_the_relative_path_when_nothing_exists(tmp_path, monkeypatch):
    _cwd_layout(tmp_path, monkeypatch)
    resolved = resources.resolve_cwd("data/tawos_clean.csv")
    assert resolved == Path("data/tawos_clean.csv")
    assert not resolved.exists()


@pytest.mark.unit
def test_puma_data_dir_wins_over_the_working_directory_when_the_file_exists_there(
    tmp_path, monkeypatch
):
    _, _, workdir = _cwd_layout(tmp_path, monkeypatch)
    _write(workdir / "data" / "tawos_clean.csv", "cwd")
    override = _write(tmp_path / "datasets" / "tawos_clean.csv", "override").parent
    monkeypatch.setenv("PUMA_DATA_DIR", str(override))
    assert resources.domain_override("data/tawos_clean.csv") == override / "tawos_clean.csv"
    assert resources.resolve_cwd("data/tawos_clean.csv") == override / "tawos_clean.csv"
    # A file absent from the override directory still comes from the working directory.
    _write(workdir / "data" / "jira_balanced_200.csv", "cwd")
    assert resources.resolve_cwd("data/jira_balanced_200.csv") == Path("data/jira_balanced_200.csv")
    # Other domains are not affected by PUMA_DATA_DIR.
    assert resources.domain_override("specs/runs/x.yaml") is None


@pytest.mark.unit
def test_puma_specs_dir_wins_for_run_specs_when_the_file_exists_there(tmp_path, monkeypatch):
    source_root, _, workdir = _cwd_layout(tmp_path, monkeypatch)
    _write(workdir / "specs" / "runs" / "baseline_triage.yaml", "cwd")
    _write(source_root / "specs" / "runs" / "smoke_triage.yaml", "source")
    override = _write(tmp_path / "specs-override" / "runs" / "baseline_triage.yaml", "o").parents[1]
    monkeypatch.setenv("PUMA_SPECS_DIR", str(override))
    assert resources.resolve_cwd("specs/runs/baseline_triage.yaml") == (
        override / "runs" / "baseline_triage.yaml"
    )
    assert resources.resolve_cwd("specs/runs") == override / "runs"
    # Not in the override: working directory, then source tree.
    assert resources.resolve_cwd("specs/runs/smoke_triage.yaml") == (
        source_root / "specs" / "runs" / "smoke_triage.yaml"
    )


@pytest.mark.unit
def test_unset_or_empty_variables_change_nothing(tmp_path, monkeypatch):
    _, _, workdir = _cwd_layout(tmp_path, monkeypatch)
    _write(workdir / "data" / "tawos_clean.csv", "cwd")
    assert resources.domain_override("data/tawos_clean.csv") is None
    assert resources.resolve_cwd("data/tawos_clean.csv") == Path("data/tawos_clean.csv")
    monkeypatch.setenv("PUMA_DATA_DIR", "")
    monkeypatch.setenv("PUMA_SPECS_DIR", "")
    assert resources.domain_override("data/tawos_clean.csv") is None
    assert resources.resolve_cwd("data/tawos_clean.csv") == Path("data/tawos_clean.csv")


@pytest.mark.unit
def test_package_relative_lookups_ignore_the_working_directory_and_the_variables(
    tmp_path, monkeypatch
):
    source_root, bundled_root, workdir = _cwd_layout(tmp_path, monkeypatch)
    _write(workdir / "config" / "profiles.yaml", "cwd")
    _write(bundled_root / "config" / "profiles.yaml", "bundled")
    monkeypatch.setenv("PUMA_DATA_DIR", str(workdir))
    monkeypatch.setenv("PUMA_SPECS_DIR", str(workdir))
    assert resources.resolve("config/profiles.yaml") == bundled_root / "config" / "profiles.yaml"
    _write(source_root / "config" / "profiles.yaml", "source")
    assert resources.resolve("config/profiles.yaml") == source_root / "config" / "profiles.yaml"
    assert resources.DOMAIN_ENV_VARS == {"data": "PUMA_DATA_DIR", "specs": "PUMA_SPECS_DIR"}


@pytest.mark.unit
def test_working_directory_call_sites_use_resolve_cwd():
    from puma.datasets import jira_sr, tawos

    assert resources.resolve_cwd("data/jira_balanced_200.csv") == jira_sr._CSV_PATH
    assert resources.resolve_cwd("data/tawos_clean.csv") == tawos._CSV_PATH
    # The suite runs from the repository root: the relative paths of 378b34d.
    assert Path("data/jira_balanced_200.csv") == jira_sr._CSV_PATH
    assert Path("data/tawos_clean.csv") == tawos._CSV_PATH
    assert Path("db/jira_sr.csv") == jira_sr._DB_CSV  # checked first by load(), unchanged


@pytest.mark.unit
def test_alembic_ini_in_the_working_directory_is_loaded_first(tmp_path, monkeypatch):
    from puma.storage import db

    cfg = db._alembic_config_for("sqlite:///x.db")  # repository root: alembic.ini is here
    assert cfg.config_file_name == "alembic.ini"
    assert cfg.get_main_option("sqlalchemy.url") == "sqlite:///x.db"
    # An installed wheel (no source tree) run from a directory with its own alembic.ini
    # also loads that file, as the code did before the data was bundled.
    monkeypatch.setattr(resources, "SOURCE_ROOT", tmp_path / "no-source-tree")
    monkeypatch.chdir(tmp_path)
    (tmp_path / "alembic.ini").write_text("[alembic]\nscript_location = x\n", encoding="utf-8")
    cfg = db._alembic_config_for("sqlite:///x.db")
    assert cfg.config_file_name == "alembic.ini"


@pytest.mark.unit
def test_alembic_config_in_source_tree_without_ini_in_cwd_raises(tmp_path, monkeypatch):
    from puma.storage import db

    assert resources.in_source_tree("alembic")
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
