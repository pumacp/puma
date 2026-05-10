"""Integration tests for Alembic migrations.

Implements acceptance criteria AC-01 through AC-10 of
``specs/storage-migrations.spec.md``. Authored under TDD per rule §0.6:
every test in this module fails until A.1.2-A.1.6 land Alembic configuration,
the initial migration, the CLI sub-Typer refactor, and the rewired
``init_db()``.

Each test is self-contained and uses ``tmp_path`` to isolate the database
file. ``alembic.ini`` is loaded from the process CWD (the project root when
pytest runs from there) and ``sqlalchemy.url`` is overridden per test via
``Config.set_main_option`` to point at the temporary path.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from alembic import command
from alembic.autogenerate import produce_migrations
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Float, Numeric, String, create_engine, inspect, text


def _alembic_cfg(db_path) -> Config:
    """Load the project's ``alembic.ini`` and override the DB URL."""
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return cfg


@pytest.mark.integration
def test_upgrade_from_empty_db(tmp_path):
    """AC-01: ``alembic upgrade head`` on an empty SQLite file populates
    exactly ``Base.metadata.tables.keys() ∪ {"alembic_version"}``."""
    from puma.storage.models import Base

    db_path = tmp_path / "test.db"
    assert not db_path.exists()

    cfg = _alembic_cfg(db_path)
    command.upgrade(cfg, "head")

    assert db_path.exists()
    engine = create_engine(f"sqlite:///{db_path}")
    actual = set(inspect(engine).get_table_names())
    expected = set(Base.metadata.tables.keys()) | {"alembic_version"}
    assert actual == expected, (
        f"Missing tables: {sorted(expected - actual)}; "
        f"unexpected tables: {sorted(actual - expected)}"
    )


@pytest.mark.integration
def test_downgrade_base(tmp_path):
    """AC-02: ``alembic downgrade base`` removes all ORM tables.

    Behavior of the ``alembic_version`` table after ``downgrade base`` is
    documented empirically in A.1.5/A.1.7 (current Alembic 1.18.x leaves the
    table in place with zero rows). The assert below reflects that observed
    behavior; if A.1.5 finds a different shape, this test must be updated
    inline with a comment recording the new observation.
    """
    from puma.storage.models import Base

    db_path = tmp_path / "test.db"
    cfg = _alembic_cfg(db_path)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")

    engine = create_engine(f"sqlite:///{db_path}")
    tables = set(inspect(engine).get_table_names())

    for orm_table in Base.metadata.tables.keys():
        assert orm_table not in tables, (
            f"ORM table {orm_table!r} should be dropped after downgrade base"
        )

    # Documented behavior: alembic_version persists with zero rows.
    if "alembic_version" in tables:
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM alembic_version")).scalar()
        assert count == 0, (
            f"alembic_version expected empty after downgrade base; got {count} rows"
        )


@pytest.mark.integration
def test_downgrade_then_upgrade_idempotent(tmp_path):
    """AC-03: ``downgrade base`` + ``upgrade head`` leaves the schema
    bit-equivalent to the post-initial-upgrade state."""
    db_path = tmp_path / "test.db"
    cfg = _alembic_cfg(db_path)
    command.upgrade(cfg, "head")

    engine = create_engine(f"sqlite:///{db_path}")

    def snapshot():
        ins = inspect(engine)
        tables = sorted(ins.get_table_names())
        cols = {t: sorted(c["name"] for c in ins.get_columns(t)) for t in tables}
        return tables, cols

    before = snapshot()
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    after = snapshot()

    assert before == after, "Schema after downgrade+upgrade cycle differs from initial"


@pytest.mark.integration
def test_double_upgrade_head_is_noop(tmp_path):
    """AC-04: ``alembic upgrade head`` invoked twice is idempotent and
    non-destructive. Tables and ``alembic_version`` row identical."""
    db_path = tmp_path / "test.db"
    cfg = _alembic_cfg(db_path)
    command.upgrade(cfg, "head")

    engine = create_engine(f"sqlite:///{db_path}")

    def state():
        ins = inspect(engine)
        tables = sorted(ins.get_table_names())
        with engine.connect() as conn:
            row = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
        return tables, (row[0] if row else None)

    before = state()
    command.upgrade(cfg, "head")  # second call must not raise
    after = state()
    assert before == after


@pytest.mark.integration
def test_cli_db_migrate_delegates_to_alembic(tmp_path):
    """AC-05: ``puma db migrate`` delegates to Alembic. ``Base.metadata.create_all``
    must NOT be called (decision I3, no fallback)."""
    from typer.testing import CliRunner

    from puma.cli import app
    from puma.storage.models import Base

    db_path = tmp_path / "test.db"
    runner = CliRunner()

    with patch.object(Base.metadata, "create_all") as mock_create_all:
        result = runner.invoke(app, ["db", "migrate", "--db", str(db_path)])

    assert result.exit_code == 0, (
        f"`puma db migrate` failed: exit={result.exit_code} stdout={result.stdout!r}"
    )
    assert mock_create_all.call_count == 0, (
        f"Base.metadata.create_all called {mock_create_all.call_count} times during "
        "`puma db migrate`; decision I3 forbids fallback to create_all."
    )

    # Schema actually applied via the alembic path
    engine = create_engine(f"sqlite:///{db_path}")
    actual = set(inspect(engine).get_table_names())
    expected = set(Base.metadata.tables.keys()) | {"alembic_version"}
    assert expected.issubset(actual), f"Missing tables after migrate: {expected - actual}"


@pytest.mark.integration
def test_cli_db_status_preserved(tmp_path):
    """AC-06: ``puma db status`` preserved as a sub-Typer subcommand of
    ``db_app`` (decision S1).

    Two parts:
    1. Structural — ``db_app`` is exported from ``puma.cli`` as a Typer
       sub-application with ``status`` registered alongside ``migrate``,
       ``downgrade``, and ``history``.
    2. Behavioural — invoking ``puma db status --db <missing_path>`` produces
       the documented ``not found`` guidance preserved from the prior
       implementation.
    """
    import typer

    from puma.cli import app, db_app  # ImportError pre-refactor → test fails

    assert isinstance(db_app, typer.Typer), "`db` must be a sub-Typer per decision S1"
    cmd_names = {ci.name for ci in db_app.registered_commands}
    for required in ("migrate", "downgrade", "history", "status"):
        assert required in cmd_names, (
            f"`{required}` missing from db_app.registered_commands: {cmd_names}"
        )

    # Behaviour: status against a non-existent DB shows guidance
    from typer.testing import CliRunner

    runner = CliRunner()
    db_path = tmp_path / "missing.db"
    result = runner.invoke(app, ["db", "status", "--db", str(db_path)])
    assert result.exit_code == 0, f"`puma db status` failed: {result.stdout!r}"
    assert "missing.db" in result.stdout
    assert "not found" in result.stdout.lower(), (
        f"`status` output should contain 'not found' guidance: {result.stdout!r}"
    )


@pytest.mark.integration
def test_init_db_invokes_alembic_and_callers_unaffected(tmp_path):
    """AC-07: ``init_db()`` runs ``alembic upgrade head`` and the schema is
    immediately usable from existing call sites (decision I3).

    Caller compatibility check mirrors:
      - ``orchestrator/runner.py:48`` → query against ``runs`` table
      - ``orchestrator/compare.py:13`` → query against ``metrics`` table
    """
    from puma.storage.db import init_db

    db_path = tmp_path / "test.db"
    init_db(db_path)

    engine = create_engine(f"sqlite:///{db_path}")

    # alembic_version populated with the head revision
    with engine.connect() as conn:
        row = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
    assert row is not None and row[0], "alembic_version not populated by init_db()"

    cfg = _alembic_cfg(db_path)
    expected_head = ScriptDirectory.from_config(cfg).get_current_head()
    assert row[0] == expected_head, (
        f"alembic_version stores {row[0]!r} but ScriptDirectory head is {expected_head!r}"
    )

    # Caller a (runner.py:48 mirror) — must not raise
    with engine.connect() as conn:
        conn.execute(text("SELECT COUNT(*) FROM runs"))
    # Caller b (compare.py:13 mirror) — must not raise
    with engine.connect() as conn:
        conn.execute(text("SELECT COUNT(*) FROM metrics"))


@pytest.mark.integration
def test_init_db_raises_on_missing_alembic_ini(tmp_path, monkeypatch):
    """AC-08: ``init_db()`` raises a clear error when ``alembic.ini`` is not
    reachable from the CWD; no silent fallback to ``Base.metadata.create_all``."""
    from puma.storage.db import init_db
    from puma.storage.models import Base

    monkeypatch.chdir(tmp_path)
    assert not (tmp_path / "alembic.ini").exists()

    db_path = tmp_path / "test.db"

    with patch.object(Base.metadata, "create_all") as mock_create_all:
        with pytest.raises(Exception) as exc_info:
            init_db(db_path)

    msg = str(exc_info.value).lower()
    assert "alembic" in msg, (
        f"Error message must mention alembic config: got {exc_info.value!r}"
    )
    assert any(token in msg for token in ("not found", "missing", "no such file")), (
        f"Error message must indicate the file is missing: got {exc_info.value!r}"
    )
    assert mock_create_all.call_count == 0, (
        "init_db() must NOT fall back to Base.metadata.create_all when "
        "alembic.ini is missing (decision I3)."
    )


@pytest.mark.integration
def test_initial_migration_matches_orm_schema(tmp_path):
    """AC-09: per-column schema parity between migration result and ORM.

    Verified per column: (a) type family, (b) nullability, (c) primary-key
    membership, (d) foreign-key targets, (e) parameterized type attributes
    (``length`` / ``precision`` / ``scale``) ONLY when the ORM declared them
    explicitly. Catches silent schema drift without false negatives from
    SQLite's type-name reporting.
    """
    from puma.storage.models import Base

    db_path = tmp_path / "test.db"
    cfg = _alembic_cfg(db_path)
    command.upgrade(cfg, "head")

    engine = create_engine(f"sqlite:///{db_path}")
    inspector = inspect(engine)

    for table_name, orm_table in Base.metadata.tables.items():
        actual_cols = {c["name"]: c for c in inspector.get_columns(table_name)}

        # Build column → set[(referred_table, referred_col)]
        fk_map: dict[str, set[tuple[str, str]]] = {}
        for fk in inspector.get_foreign_keys(table_name):
            for local_col, ref_col in zip(
                fk["constrained_columns"], fk["referred_columns"], strict=True
            ):
                fk_map.setdefault(local_col, set()).add(
                    (fk["referred_table"], ref_col)
                )

        for orm_col in orm_table.columns:
            assert orm_col.name in actual_cols, (
                f"Column {table_name}.{orm_col.name} missing from migration"
            )
            actual = actual_cols[orm_col.name]

            # (a) type family — accept dialectal concretions (e.g., SQLite
            # reflects String columns as VARCHAR, which is a subclass of
            # String). isinstance still catches real type-family changes
            # (String → Integer would fail).
            assert isinstance(actual["type"], type(orm_col.type)), (
                f"{table_name}.{orm_col.name} type-family mismatch: "
                f"actual={actual['type'].__class__.__name__}, "
                f"orm={orm_col.type.__class__.__name__}"
            )

            # (b) nullability
            assert actual["nullable"] == orm_col.nullable, (
                f"{table_name}.{orm_col.name} nullability mismatch: "
                f"actual={actual['nullable']}, orm={orm_col.nullable}"
            )

            # (c) primary-key membership (inspector returns int order; coerce to bool)
            actual_pk = bool(actual.get("primary_key", 0))
            assert actual_pk == orm_col.primary_key, (
                f"{table_name}.{orm_col.name} PK membership mismatch: "
                f"actual={actual_pk}, orm={orm_col.primary_key}"
            )

            # (d) foreign keys
            orm_fks = {
                (fk.column.table.name, fk.column.name) for fk in orm_col.foreign_keys
            }
            actual_fks = fk_map.get(orm_col.name, set())
            assert orm_fks == actual_fks, (
                f"{table_name}.{orm_col.name} FK mismatch: "
                f"actual={actual_fks}, orm={orm_fks}"
            )

            # (e) parameterized type attrs — only when ORM declared them explicitly
            if isinstance(orm_col.type, String) and orm_col.type.length is not None:
                actual_len = getattr(actual["type"], "length", None)
                assert actual_len == orm_col.type.length, (
                    f"{table_name}.{orm_col.name} String length mismatch: "
                    f"actual={actual_len}, orm={orm_col.type.length}"
                )
            if isinstance(orm_col.type, (Numeric, Float)):
                if orm_col.type.precision is not None:
                    actual_prec = getattr(actual["type"], "precision", None)
                    assert actual_prec == orm_col.type.precision, (
                        f"{table_name}.{orm_col.name} precision mismatch: "
                        f"actual={actual_prec}, orm={orm_col.type.precision}"
                    )
                orm_scale = getattr(orm_col.type, "scale", None)
                if orm_scale is not None:
                    actual_scale = getattr(actual["type"], "scale", None)
                    assert actual_scale == orm_scale, (
                        f"{table_name}.{orm_col.name} scale mismatch: "
                        f"actual={actual_scale}, orm={orm_scale}"
                    )


@pytest.mark.integration
def test_initial_migration_has_no_pending_changes(tmp_path):
    """AC-10: ``0001_initial_schema`` is a complete capture of the ORM —
    autogenerate against the post-upgrade DB produces no diff."""
    from puma.storage.models import Base

    db_path = tmp_path / "test.db"
    cfg = _alembic_cfg(db_path)
    command.upgrade(cfg, "head")

    engine = create_engine(f"sqlite:///{db_path}")
    with engine.connect() as conn:
        ctx = MigrationContext.configure(
            connection=conn,
            opts={
                "compare_type": True,
                "compare_server_default": True,
                "target_metadata": Base.metadata,
            },
        )
        diff = produce_migrations(ctx, Base.metadata)

    assert diff.upgrade_ops.is_empty(), (
        f"0001_initial_schema has pending diffs: {diff.upgrade_ops.as_diffs()}"
    )
