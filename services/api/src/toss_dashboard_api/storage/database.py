from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker


def _sqlite_path(database_url: str) -> Path | None:
    if database_url in {"sqlite:///:memory:", "sqlite+pysqlite:///:memory:"}:
        return None
    prefix = (
        "sqlite+pysqlite:///" if database_url.startswith("sqlite+pysqlite:///") else "sqlite:///"
    )
    raw = database_url.removeprefix(prefix).split("?", maxsplit=1)[0]
    return Path(raw).expanduser().resolve()


def create_database_engine(database_url: str) -> Engine:
    if not (
        database_url.startswith("sqlite:///") or database_url.startswith("sqlite+pysqlite:///")
    ):
        raise ValueError("Phase 1 supports SQLite only")
    path = _sqlite_path(database_url)
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(database_url, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection: object, _connection_record: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
