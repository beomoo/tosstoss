from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError
from tests.backend.conftest import FIXTURE_DIR, alembic_config

from toss_dashboard_api.fixtures.importer import FixtureImporter
from toss_dashboard_api.repositories.fixture import FixtureRepository
from toss_dashboard_api.storage.database import session_factory
from toss_dashboard_api.storage.provider_raw import ProviderRawStore

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PHASE_ONE_TABLES = (
    "issuers",
    "securities",
    "source_records",
    "data_quality_statuses",
    "fixture_import_runs",
)


def phase_one_dump(database_url: str) -> dict[str, list[tuple[object, ...]]]:
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            return {
                table: [tuple(row) for row in connection.execute(text(f"SELECT * FROM {table}"))]
                for table in PHASE_ONE_TABLES
            }
    finally:
        engine.dispose()


def test_blank_database_upgrades_to_cp3_head(workspace_tmp_path: Path) -> None:
    url = f"sqlite:///{(workspace_tmp_path / 'blank.sqlite3').as_posix()}"
    command.upgrade(alembic_config(url), "head")
    engine = create_engine(url)
    try:
        tables = set(inspect(engine).get_table_names())
        assert {
            "canonical_requests",
            "provider_raw_manifests",
            "provider_source_versions",
            "collection_attempts",
            "provider_audit_events",
            "provider_security_identities",
            "provider_identifier_history",
            "provider_identity_mappings",
            "provider_latest_pointers",
        }.issubset(tables)
        with engine.connect() as connection:
            assert connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one() == ("0002_phase_02_cp3_foundation")
    finally:
        engine.dispose()


def test_existing_phase_one_fixture_rows_survive_upgrade_byte_for_byte(
    workspace_tmp_path: Path,
) -> None:
    url = f"sqlite:///{(workspace_tmp_path / 'existing.sqlite3').as_posix()}"
    config = alembic_config(url)
    command.upgrade(config, "0001_phase_01")
    engine = create_engine(url)
    try:
        FixtureImporter(session_factory(engine)).import_repository(FixtureRepository(FIXTURE_DIR))
    finally:
        engine.dispose()
    before = phase_one_dump(url)
    command.upgrade(config, "head")
    assert phase_one_dump(url) == before


def test_cp3_downgrade_and_reupgrade_preserves_phase_one_rows(
    workspace_tmp_path: Path,
) -> None:
    url = f"sqlite:///{(workspace_tmp_path / 'cp3-roundtrip.sqlite3').as_posix()}"
    config = alembic_config(url)
    command.upgrade(config, "0001_phase_01")
    engine = create_engine(url)
    try:
        FixtureImporter(session_factory(engine)).import_repository(FixtureRepository(FIXTURE_DIR))
    finally:
        engine.dispose()
    expected = phase_one_dump(url)
    command.upgrade(config, "head")
    command.downgrade(config, "0001_phase_01")
    assert phase_one_dump(url) == expected
    command.upgrade(config, "head")
    assert phase_one_dump(url) == expected


def test_failed_cp3_upgrade_leaves_revision_and_prior_schema_unchanged(
    workspace_tmp_path: Path,
) -> None:
    url = f"sqlite:///{(workspace_tmp_path / 'failed.sqlite3').as_posix()}"
    config = alembic_config(url)
    command.upgrade(config, "0001_phase_01")
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE canonical_requests (sentinel INTEGER)"))
    finally:
        engine.dispose()
    with pytest.raises(OperationalError):
        command.upgrade(config, "head")
    engine = create_engine(url)
    try:
        tables = set(inspect(engine).get_table_names())
        assert "provider_raw_manifests" not in tables
        with engine.connect() as connection:
            assert connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one() == ("0001_phase_01")
    finally:
        engine.dispose()


def test_mid_migration_failure_removes_partial_cp3_schema_and_preserves_phase_one(
    workspace_tmp_path: Path,
) -> None:
    url = f"sqlite:///{(workspace_tmp_path / 'mid-failure.sqlite3').as_posix()}"
    config = alembic_config(url)
    command.upgrade(config, "0001_phase_01")
    engine = create_engine(url)
    try:
        FixtureImporter(session_factory(engine)).import_repository(FixtureRepository(FIXTURE_DIR))
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE provider_identity_mappings (sentinel TEXT)"))
    finally:
        engine.dispose()
    phase_one_before = phase_one_dump(url)

    with pytest.raises(OperationalError):
        command.upgrade(config, "head")

    engine = create_engine(url)
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        assert inspector.get_columns("provider_identity_mappings")[0]["name"] == "sentinel"
        assert {
            "canonical_requests",
            "provider_raw_manifests",
            "provider_source_versions",
            "collection_attempts",
            "provider_audit_events",
            "provider_security_identities",
            "provider_identifier_history",
            "provider_latest_pointers",
        }.isdisjoint(tables)
        with engine.connect() as connection:
            assert connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one() == ("0001_phase_01")
        with engine.begin() as connection:
            connection.execute(text("DROP TABLE provider_identity_mappings"))
    finally:
        engine.dispose()
    assert phase_one_dump(url) == phase_one_before

    command.upgrade(config, "head")
    engine = create_engine(url)
    try:
        assert "provider_latest_pointers" in set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
    assert phase_one_dump(url) == phase_one_before


def test_database_downgrade_never_deletes_raw_files(workspace_tmp_path: Path) -> None:
    url = f"sqlite:///{(workspace_tmp_path / 'raw-safe.sqlite3').as_posix()}"
    config = alembic_config(url)
    command.upgrade(config, "head")
    store = ProviderRawStore(workspace_tmp_path / "raw")
    persisted = store.persist(b"append-only-raw")
    command.downgrade(config, "0001_phase_01")
    assert store.read(persisted.raw_storage_ref) == b"append-only-raw"


def test_phase_one_migration_file_is_byte_identical() -> None:
    migration = PROJECT_ROOT / "services/api/alembic/versions/0001_phase_01_foundation.py"
    assert hashlib.sha256(migration.read_bytes()).hexdigest() == "".join(
        (
            "6eba164e",
            "f2f8bab4",
            "25830768",
            "05255268",
            "e4daba29",
            "311e8f6e",
            "956f4177",
            "c0445762",
        )
    )


def test_public_openapi_snapshot_bytes_are_unchanged() -> None:
    snapshot = PROJECT_ROOT / "contracts/openapi.json"
    assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == "".join(
        (
            "7b86c202",
            "7f47e1e1",
            "b0e5e546",
            "d8c5568b",
            "fc581c6c",
            "6b3fb1e4",
            "f0ca761b",
            "1506864d",
        )
    )
