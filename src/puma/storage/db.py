"""Database session management.

Schema lifecycle is driven by Alembic migrations (see
``specs/storage-migrations.spec.md``). ``init_db`` invokes
``alembic upgrade head`` programmatically; there is no fallback to
``Base.metadata.create_all`` (decision I3). ``alembic.ini`` is loaded from
the working directory when it is there. Otherwise a source tree raises a
clear ``RuntimeError`` (AC-08), and an installed wheel, which has no source
tree, uses the bundled migrations under ``puma/_bundled/alembic``.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

if TYPE_CHECKING:
    from alembic.config import Config

_DEFAULT_DB = Path("data/puma.db")
_ALEMBIC_INI = Path("alembic.ini")
_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def _alembic_config_for(url: str) -> Config:
    """Build an Alembic ``Config`` bound to ``url``.

    When ``alembic.ini`` exists in the current working directory it is loaded,
    as it always was. Otherwise, in a source tree (``<repository root>/alembic``
    exists) a ``RuntimeError`` is raised so the failure mode stays explicit
    (decision I3 — no silent fallback), and in an installed wheel, which has
    no source tree, the configuration is built programmatically with
    ``script_location`` pointing at the bundled migrations
    (``puma/_bundled/alembic``). Either way ``sqlalchemy.url`` is overridden
    with the caller-provided one.
    """
    from alembic.config import Config

    from puma.resources import in_source_tree, resolve

    if _ALEMBIC_INI.exists():
        cfg = Config(str(_ALEMBIC_INI))
    elif in_source_tree("alembic"):
        raise RuntimeError(
            f"Alembic configuration not found at {_ALEMBIC_INI.resolve()}. "
            "init_db() requires alembic.ini reachable from the working "
            "directory. Run from the project root or set CWD accordingly."
        )
    else:
        cfg = Config()
        cfg.set_main_option("script_location", str(resolve("alembic")))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def init_db(db_path: Path | str = _DEFAULT_DB) -> None:
    """Apply Alembic migrations to ``db_path`` and bind the session factory.

    Replaces the legacy ``Base.metadata.create_all`` bootstrap with a
    programmatic ``alembic upgrade head``. Idempotent on warm databases.
    """
    from alembic import command

    global _engine, _SessionLocal
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    url = f"sqlite:///{path}"

    cfg = _alembic_config_for(url)
    command.upgrade(cfg, "head")

    _engine = create_engine(url, connect_args={"check_same_thread": False})
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)


def get_engine() -> Engine:
    if _engine is None:
        init_db()
    assert _engine is not None  # init_db() always sets _engine
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    if _SessionLocal is None:
        init_db()
    assert _SessionLocal is not None  # init_db() always sets _SessionLocal
    return _SessionLocal


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Provide a transactional session scope."""
    factory = get_session_factory()
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
