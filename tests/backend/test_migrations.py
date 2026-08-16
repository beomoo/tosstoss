from pathlib import Path

from alembic import command
from sqlalchemy import create_engine, inspect, text
from tests.backend.conftest import alembic_config


def schema_fingerprint(database_url: str) -> tuple[tuple[str, tuple[str, ...]], ...]:
    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        return tuple(
            (table, tuple(column["name"] for column in inspector.get_columns(table)))
            for table in sorted(inspector.get_table_names())
        )
    finally:
        engine.dispose()


def test_upgrade_is_repeatable(workspace_tmp_path: Path) -> None:
    url = f"sqlite:///{(workspace_tmp_path / 'repeat.sqlite3').as_posix()}"
    config = alembic_config(url)
    command.upgrade(config, "head")
    first = schema_fingerprint(url)
    command.upgrade(config, "head")
    assert schema_fingerprint(url) == first


def test_downgrade_and_reupgrade(workspace_tmp_path: Path) -> None:
    url = f"sqlite:///{(workspace_tmp_path / 'roundtrip.sqlite3').as_posix()}"
    config = alembic_config(url)
    command.upgrade(config, "head")
    expected = schema_fingerprint(url)
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    assert schema_fingerprint(url) == expected
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            assert (
                connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                == "0001_phase_01"
            )
    finally:
        engine.dispose()
