from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from alembic import command
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine.reflection import Inspector
from tests.backend.conftest import alembic_config

ColumnFingerprint = tuple[str, str, bool, bool, str | None]
NamedColumnsFingerprint = tuple[str, tuple[str, ...]]
ForeignKeyFingerprint = tuple[
    str,
    tuple[str, ...],
    str,
    str,
    tuple[str, ...],
    tuple[tuple[str, str], ...],
]
IndexFingerprint = tuple[str, tuple[str, ...], bool]
TableFingerprint = tuple[
    str,
    tuple[ColumnFingerprint, ...],
    NamedColumnsFingerprint,
    tuple[NamedColumnsFingerprint, ...],
    tuple[ForeignKeyFingerprint, ...],
    tuple[IndexFingerprint, ...],
    tuple[tuple[str, str], ...],
]


def _column_names(value: Sequence[str] | None) -> tuple[str, ...]:
    return tuple(value or ())


def _constraint_name(value: object) -> str:
    return value if isinstance(value, str) else ""


def _options(value: object) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, Mapping):
        return ()
    return tuple(sorted((str(key), repr(item)) for key, item in value.items()))


def _table_fingerprint(inspector: Inspector, table: str) -> TableFingerprint:
    columns: tuple[ColumnFingerprint, ...] = tuple(
        sorted(
            (
                str(column["name"]),
                str(column["type"]).upper(),
                bool(column["nullable"]),
                bool(column.get("primary_key", False)),
                None if column.get("default") is None else str(column["default"]),
            )
            for column in inspector.get_columns(table)
        )
    )
    primary_key = inspector.get_pk_constraint(table)
    pk_fingerprint: NamedColumnsFingerprint = (
        _constraint_name(primary_key.get("name")),
        _column_names(primary_key.get("constrained_columns")),
    )
    unique_constraints: tuple[NamedColumnsFingerprint, ...] = tuple(
        sorted(
            (
                _constraint_name(constraint.get("name")),
                _column_names(constraint.get("column_names")),
            )
            for constraint in inspector.get_unique_constraints(table)
        )
    )
    foreign_keys: tuple[ForeignKeyFingerprint, ...] = tuple(
        sorted(
            (
                _constraint_name(foreign_key.get("name")),
                _column_names(foreign_key.get("constrained_columns")),
                _constraint_name(foreign_key.get("referred_schema")),
                str(foreign_key["referred_table"]),
                _column_names(foreign_key.get("referred_columns")),
                _options(foreign_key.get("options")),
            )
            for foreign_key in inspector.get_foreign_keys(table)
        )
    )
    indexes: tuple[IndexFingerprint, ...] = tuple(
        sorted(
            (
                _constraint_name(index.get("name")),
                _column_names(index.get("column_names")),
                bool(index.get("unique", False)),
            )
            for index in inspector.get_indexes(table)
        )
    )
    checks = tuple(
        sorted(
            (
                _constraint_name(check.get("name")),
                str(check.get("sqltext", "")),
            )
            for check in inspector.get_check_constraints(table)
        )
    )
    return (
        table,
        columns,
        pk_fingerprint,
        unique_constraints,
        foreign_keys,
        indexes,
        checks,
    )


def schema_fingerprint(database_url: str) -> tuple[TableFingerprint, ...]:
    """Reflect every schema property whose loss can change data integrity."""

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        return tuple(
            _table_fingerprint(inspector, table) for table in sorted(inspector.get_table_names())
        )
    finally:
        engine.dispose()


def _assert_expected_schema(database_url: str) -> None:
    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        expected_columns: dict[str, dict[str, tuple[str, bool, bool]]] = {
            "issuers": {
                "issuer_id": ("VARCHAR(128)", False, True),
                "jurisdiction": ("VARCHAR(8)", False, False),
                "corp_code": ("VARCHAR(32)", True, False),
                "cik": ("VARCHAR(32)", True, False),
                "normalized_content_hash": ("VARCHAR(71)", False, False),
                "payload_json": ("TEXT", False, False),
            },
            "securities": {
                "security_id": ("VARCHAR(128)", False, True),
                "issuer_id": ("VARCHAR(128)", False, False),
                "market": ("VARCHAR(8)", False, False),
                "exchange": ("VARCHAR(32)", False, False),
                "ticker": ("VARCHAR(32)", False, False),
                "share_class": ("VARCHAR(32)", False, False),
                "normalized_content_hash": ("VARCHAR(71)", False, False),
                "payload_json": ("TEXT", False, False),
            },
            "source_records": {
                "source_record_id": ("VARCHAR(128)", False, True),
                "source_system": ("VARCHAR(64)", False, False),
                "source_type": ("VARCHAR(32)", False, False),
                "external_id": ("VARCHAR(128)", False, False),
                "supersedes_id": ("VARCHAR(128)", True, False),
                "raw_content_hash": ("VARCHAR(71)", False, False),
                "normalized_content_hash": ("VARCHAR(71)", False, False),
                "payload_json": ("TEXT", False, False),
            },
            "data_quality_statuses": {
                "quality_status_id": ("VARCHAR(128)", False, True),
                "issuer_id": ("VARCHAR(128)", False, False),
                "source_system": ("VARCHAR(64)", False, False),
                "dataset": ("VARCHAR(64)", False, False),
                "normalized_content_hash": ("VARCHAR(71)", False, False),
                "payload_json": ("TEXT", False, False),
            },
            "fixture_import_runs": {
                "import_run_id": ("INTEGER", False, True),
                "manifest_digest": ("VARCHAR(71)", False, False),
                "fixture_version": ("VARCHAR(32)", False, False),
                "imported_at": ("DATETIME", False, False),
            },
        }
        assert set(inspector.get_table_names()) == set(expected_columns) | {"alembic_version"}
        for table, expected in expected_columns.items():
            reflected = {
                str(column["name"]): (
                    str(column["type"]).upper(),
                    bool(column["nullable"]),
                    bool(column.get("primary_key", False)),
                )
                for column in inspector.get_columns(table)
            }
            assert reflected == expected

        expected_primary_keys = {
            "issuers": ("issuer_id",),
            "securities": ("security_id",),
            "source_records": ("source_record_id",),
            "data_quality_statuses": ("quality_status_id",),
            "fixture_import_runs": ("import_run_id",),
        }
        expected_uniques = {
            "issuers": {("corp_code",), ("cik",)},
            "securities": {("market", "exchange", "ticker", "share_class")},
            "source_records": {("source_system", "source_type", "external_id")},
            "data_quality_statuses": {("issuer_id", "source_system", "dataset")},
            "fixture_import_runs": {("manifest_digest",)},
        }
        for table, expected_pk in expected_primary_keys.items():
            assert (
                _column_names(inspector.get_pk_constraint(table).get("constrained_columns"))
                == expected_pk
            )
            assert {
                _column_names(constraint.get("column_names"))
                for constraint in inspector.get_unique_constraints(table)
            } == expected_uniques[table]

        expected_foreign_keys = {
            "securities": {("issuer_id",): ("issuers", ("issuer_id",))},
            "source_records": {("supersedes_id",): ("source_records", ("source_record_id",))},
            "data_quality_statuses": {("issuer_id",): ("issuers", ("issuer_id",))},
        }
        for table in expected_columns:
            reflected_foreign_keys = {
                _column_names(foreign_key.get("constrained_columns")): (
                    str(foreign_key["referred_table"]),
                    _column_names(foreign_key.get("referred_columns")),
                )
                for foreign_key in inspector.get_foreign_keys(table)
            }
            assert reflected_foreign_keys == expected_foreign_keys.get(table, {})
    finally:
        engine.dispose()


def test_upgrade_is_repeatable(workspace_tmp_path: Path) -> None:
    url = f"sqlite:///{(workspace_tmp_path / 'repeat.sqlite3').as_posix()}"
    config = alembic_config(url)
    command.upgrade(config, "head")
    first = schema_fingerprint(url)
    _assert_expected_schema(url)
    command.upgrade(config, "head")
    assert schema_fingerprint(url) == first
    _assert_expected_schema(url)


def test_downgrade_and_reupgrade(workspace_tmp_path: Path) -> None:
    url = f"sqlite:///{(workspace_tmp_path / 'roundtrip.sqlite3').as_posix()}"
    config = alembic_config(url)
    command.upgrade(config, "head")
    expected = schema_fingerprint(url)
    _assert_expected_schema(url)
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    assert schema_fingerprint(url) == expected
    _assert_expected_schema(url)
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            assert (
                connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                == "0001_phase_01"
            )
    finally:
        engine.dispose()
