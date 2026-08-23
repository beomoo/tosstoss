from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from toss_dashboard_api.storage.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def database_url() -> str:
    command_line = context.get_x_argument(as_dictionary=True)
    value = command_line.get("database_url") or os.environ.get("DASHBOARD_DATABASE_URL")
    if value is None:
        value = config.get_main_option("sqlalchemy.url")
    if not (value.startswith("sqlite:///") or value.startswith("sqlite+pysqlite:///")):
        raise RuntimeError("Phase 1 migrations support SQLite only")
    return value


def run_migrations_offline() -> None:
    context.configure(
        url=database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = database_url().replace("%", "%%")
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        # SQLAlchemy 2 autobegins on PRAGMA. Commit it before Alembic opens its
        # migration transaction, otherwise SQLite DDL can persist while the
        # alembic_version row is rolled back when the connection closes.
        connection.commit()
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
