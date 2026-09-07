from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from workstation_core.config import get_settings
from workstation_core.models_orm import Base


def make_engine(database_url: str | None = None) -> Engine:
    url = database_url or get_settings().database_url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    if url.startswith("sqlite:///") and url != "sqlite:///:memory:":
        db_path = Path(url.replace("sqlite:///", "", 1))
        db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url, connect_args=connect_args, future=True)
    if url.startswith("sqlite"):
        from sqlalchemy import event

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            if url != "sqlite:///:memory:":
                # WAL mode allows the control API and the worker process(es)
                # to read/write the same SQLite file concurrently without
                # "database is locked" errors under normal load.
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

    return engine


_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


def init_db(database_url: str | None = None, create_all: bool = False) -> Engine:
    """Initialise the process-wide engine/session factory.

    `create_all` is only used by tests and local dev bootstrap; real
    deployments manage schema via Alembic migrations (database/migrations).
    """
    global _engine, _SessionLocal
    _engine = make_engine(database_url)
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)
    if create_all:
        Base.metadata.create_all(_engine)
    return _engine


def get_engine() -> Engine:
    if _engine is None:
        init_db()
    return _engine  # type: ignore[return-value]


def get_sessionmaker() -> sessionmaker:
    if _SessionLocal is None:
        init_db()
    return _SessionLocal  # type: ignore[return-value]


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: one session per request, always closed."""
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()


def session_scope() -> Session:
    """For non-request contexts (worker loop, GPU monitor)."""
    return get_sessionmaker()()
