"""Data layer: the only code that opens SQLite for writing (ADR 0001)."""

from __future__ import annotations

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker


def make_engine(db_path: str) -> Engine:
    engine = create_engine(f"sqlite:///{db_path}")

    @event.listens_for(engine, "connect")
    def _pragmas(dbapi_conn, _record):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    return engine


def migrate(engine: Engine) -> None:
    """Bring the schema to the latest Alembic revision."""
    cfg = Config()
    cfg.set_main_option("script_location", "pidm:migrations")
    with engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "head")


def session_factory(engine: Engine) -> sessionmaker:
    # autoflush off: nothing reaches SQLite until commit (ADR 0002).
    return sessionmaker(engine, autoflush=False, expire_on_commit=False)


def open_db(db_path: str) -> sessionmaker:
    engine = make_engine(db_path)
    migrate(engine)
    return session_factory(engine)
