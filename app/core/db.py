"""Database connection management, PRAGMAs, and transactions (SYSTEM_DESIGN §7, §8)."""

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import Connection


def create_engine_for(url: str) -> Engine:
    """Create a SQLAlchemy Engine for the database URL with proper SQLite PRAGMAs and WAL mode."""
    version_tuple = tuple(map(int, sqlite3.sqlite_version.split(".")[:3]))
    if version_tuple < (3, 37, 0):
        raise RuntimeError(
            f"SQLite 3.37.0+ required for STRICT tables, found {sqlite3.sqlite_version}"
        )

    if url.startswith("sqlite:///"):
        db_path_str = url[len("sqlite:///") :].split("?")[0]
        if db_path_str and db_path_str != ":memory:" and not db_path_str.startswith(":memory:"):
            Path(db_path_str).resolve().parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(url)

    @event.listens_for(engine, "connect")
    def connect(dbapi_connection: Any, connection_record: Any) -> None:
        dbapi_connection.isolation_level = None
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA busy_timeout=5000;")
        cursor.close()

    @event.listens_for(engine, "begin")
    def do_begin(conn: Connection) -> None:
        mode = conn.get_execution_options().get("sqlite_begin", "DEFERRED")
        conn.exec_driver_sql(f"BEGIN {mode}")

    return engine


@contextmanager
def read_tx(engine: Engine) -> Generator[Connection, None, None]:
    """Yield a Connection inside a DEFERRED transaction."""
    conn = engine.connect().execution_options(sqlite_begin="DEFERRED")
    try:
        with conn.begin():
            yield conn
    finally:
        conn.close()


@contextmanager
def write_tx(engine: Engine) -> Generator[Connection, None, None]:
    """Yield a Connection inside an IMMEDIATE transaction."""
    conn = engine.connect().execution_options(sqlite_begin="IMMEDIATE")
    try:
        with conn.begin():
            yield conn
    finally:
        conn.close()


def run_migrations(url: str) -> None:
    """Run programmatic Alembic migrations against the target database URL."""
    base_dir = Path(__file__).resolve().parents[2]
    migrations_dir = base_dir / "migrations"
    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", str(migrations_dir))
    alembic_cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(alembic_cfg, "head")
