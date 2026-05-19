"""Database session management.

Schema lifecycle is driven by Alembic migrations (see
``specs/storage-migrations.spec.md``). ``init_db`` invokes
``alembic upgrade head`` programmatically; there is no fallback to
``Base.metadata.create_all`` (decision I3). If ``alembic.ini`` is not
reachable from the working directory, ``init_db`` raises a clear
``RuntimeError`` rather than silently bootstrapping the schema by other
means.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

if TYPE_CHECKING:
    from alembic.config import Config

_DEFAULT_DB = Path("data/puma.db")
_ALEMBIC_INI = Path("alembic.ini")
_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def _alembic_config_for(url: str) -> Config:
    """Build an Alembic ``Config`` bound to ``url``.

    Loads ``alembic.ini`` from the current working directory and overrides
    its ``sqlalchemy.url`` with the caller-provided one. Raises
    ``RuntimeError`` if the config file is not found, so the failure mode
    is explicit (decision I3 — no silent fallback).
    """
    from alembic.config import Config

    if not _ALEMBIC_INI.exists():
        raise RuntimeError(
            f"Alembic configuration not found at {_ALEMBIC_INI.resolve()}. "
            "init_db() requires alembic.ini reachable from the working "
            "directory. Run from the project root or set CWD accordingly."
        )
    cfg = Config(str(_ALEMBIC_INI))
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
    _engine.execute = lambda sql: _engine.connect().execute(text(sql))
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
