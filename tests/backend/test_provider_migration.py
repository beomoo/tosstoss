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
CP3_INVARIANT_TABLES = (
    "provider_source_versions",
    "provider_identity_mappings",
)
CP3_C1_TABLES = (
    "provider_security_master_records",
    "provider_security_master_observations",
    "provider_identity_state_events",
    "provider_detail_batch_results",
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


def cp3_invariant_dump(database_url: str) -> dict[str, list[tuple[object, ...]]]:
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            return {
                table: [tuple(row) for row in connection.execute(text(f"SELECT * FROM {table}"))]
                for table in CP3_INVARIANT_TABLES
            }
    finally:
        engine.dispose()


def seed_valid_cp3_invariant_rows(database_url: str) -> None:
    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO canonical_requests VALUES "
                    "(:request_id, 'TOSS_OPEN_API', 'GET', '/api/v1/stocks/all', "
                    "'{\"market\":\"KR\"}', :request_hash, 'toss-source/0.1.0', "
                    '\'{"marker":"request"}\')'
                ),
                {"request_id": "request_invariant", "request_hash": "sha256:" + "1" * 64},
            )
            raw_rows = [
                {
                    "raw_id": "raw_original",
                    "raw_hash": "sha256:" + "2" * 64,
                    "raw_ref": "provider-raw:sha256/22/" + "2" * 64,
                    "fetched_at": "2026-08-25T01:00:00Z",
                    "payload": '{"marker":"raw-original"}',
                },
                {
                    "raw_id": "raw_amended",
                    "raw_hash": "sha256:" + "3" * 64,
                    "raw_ref": "provider-raw:sha256/33/" + "3" * 64,
                    "fetched_at": "2026-08-25T02:00:00Z",
                    "payload": '{"marker":"raw-amended"}',
                },
            ]
            connection.execute(
                text(
                    "INSERT INTO provider_raw_manifests VALUES "
                    "(:raw_id, 'request_invariant', 200, :raw_hash, :raw_ref, :fetched_at, "
                    '\'{"content_type":"application/json"}\', '
                    "'toss-source/0.1.0', :payload)"
                ),
                raw_rows,
            )
            source_rows = [
                {
                    "source_id": "source_original",
                    "raw_id": "raw_original",
                    "raw_hash": "sha256:" + "2" * 64,
                    "status": "ORIGINAL",
                    "parent": None,
                    "normalized_hash": "sha256:" + "4" * 64,
                    "payload": '{"marker":"source-original"}',
                },
                {
                    "source_id": "source_amended",
                    "raw_id": "raw_amended",
                    "raw_hash": "sha256:" + "3" * 64,
                    "status": "AMENDED",
                    "parent": "source_original",
                    "normalized_hash": "sha256:" + "5" * 64,
                    "payload": '{"marker":"source-amended"}',
                },
            ]
            connection.execute(
                text(
                    "INSERT INTO provider_source_versions VALUES "
                    "(:source_id, 'request_invariant', :raw_id, 'STOCK_DISCOVERY', 200, "
                    ":raw_hash, 'toss-source/0.1.0', :status, :parent, "
                    ":normalized_hash, :payload)"
                ),
                source_rows,
            )
            connection.execute(
                text(
                    "INSERT INTO provider_security_identities VALUES "
                    "('identity_invariant', 'TOSS_OPEN_API', 'KR', :anchor_hash, 'ACTIVE', "
                    "'UNRESOLVED', 'source_original', 'source_amended', "
                    "'toss-identity/0.1.0', '{\"marker\":\"identity\"}')"
                ),
                {"anchor_hash": "sha256:" + "6" * 64},
            )
            mapping_rows = [
                {
                    "mapping_id": "mapping_historical",
                    "source_id": "source_original",
                    "valid_from": None,
                    "valid_to": "2020-12-31",
                    "payload": '{"marker":"mapping-historical"}',
                },
                {
                    "mapping_id": "mapping_current",
                    "source_id": "source_amended",
                    "valid_from": "2021-01-01",
                    "valid_to": None,
                    "payload": '{"marker":"mapping-current"}',
                },
            ]
            connection.execute(
                text(
                    "INSERT INTO provider_identity_mappings VALUES "
                    "(:mapping_id, 'identity_invariant', 'issuer_kr_synthetic', "
                    "'security_kr_synthetic_common', 'VERIFIED', :source_id, "
                    "'2026-08-25T03:00:00Z', :valid_from, :valid_to, "
                    "'toss-identity/0.1.0', :payload)"
                ),
                mapping_rows,
            )
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
            "provider_security_master_records",
            "provider_security_master_observations",
            "provider_identity_state_events",
            "provider_detail_batch_results",
        }.issubset(tables)
        with engine.connect() as connection:
            assert connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one() == ("0004_phase_02_cp3_c1_security_master")
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


def test_existing_cp3b_rows_survive_0003_downgrade_and_reupgrade(
    workspace_tmp_path: Path,
) -> None:
    url = f"sqlite:///{(workspace_tmp_path / 'cp3-invariant-roundtrip.sqlite3').as_posix()}"
    config = alembic_config(url)
    command.upgrade(config, "0001_phase_01")
    engine = create_engine(url)
    try:
        FixtureImporter(session_factory(engine)).import_repository(FixtureRepository(FIXTURE_DIR))
    finally:
        engine.dispose()
    command.upgrade(config, "0002_phase_02_cp3_foundation")
    seed_valid_cp3_invariant_rows(url)
    expected = cp3_invariant_dump(url)

    command.upgrade(config, "0003_phase_02_cp3_b_invariants")
    assert cp3_invariant_dump(url) == expected
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            index_sql = {
                str(name): str(sql)
                for name, sql in connection.execute(
                    text(
                        "SELECT name, sql FROM sqlite_master "
                        "WHERE type = 'index' AND name LIKE 'uq_provider_%'"
                    )
                )
            }
        assert (
            "revision_status = 'ORIGINAL'" in index_sql["uq_provider_source_versions_original_root"]
        )
        assert "supersedes_id IS NOT NULL" in index_sql["uq_provider_source_versions_supersedes"]
        assert (
            "mapping_status = 'VERIFIED' AND valid_to IS NULL"
            in index_sql["uq_provider_identity_mappings_current_verified"]
        )
    finally:
        engine.dispose()

    command.downgrade(config, "0002_phase_02_cp3_foundation")
    assert cp3_invariant_dump(url) == expected
    engine = create_engine(url)
    try:
        assert not {
            index["name"]
            for table in CP3_INVARIANT_TABLES
            for index in inspect(engine).get_indexes(table)
            if str(index["name"]).startswith("uq_provider_")
        }
    finally:
        engine.dispose()

    command.upgrade(config, "0003_phase_02_cp3_b_invariants")
    assert cp3_invariant_dump(url) == expected


def test_0004_mid_migration_failure_cleans_only_new_tables_and_is_retryable(
    workspace_tmp_path: Path,
) -> None:
    url = f"sqlite:///{(workspace_tmp_path / 'cp3-c1-mid-failure.sqlite3').as_posix()}"
    config = alembic_config(url)
    command.upgrade(config, "0001_phase_01")
    engine = create_engine(url)
    try:
        FixtureImporter(session_factory(engine)).import_repository(FixtureRepository(FIXTURE_DIR))
    finally:
        engine.dispose()
    command.upgrade(config, "0002_phase_02_cp3_foundation")
    seed_valid_cp3_invariant_rows(url)
    command.upgrade(config, "0003_phase_02_cp3_b_invariants")
    expected_phase_one = phase_one_dump(url)
    expected_cp3 = cp3_invariant_dump(url)

    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE provider_identity_state_events (sentinel TEXT)"))
    finally:
        engine.dispose()

    with pytest.raises(OperationalError):
        command.upgrade(config, "0004_phase_02_cp3_c1_security_master")

    engine = create_engine(url)
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        assert inspector.get_columns("provider_identity_state_events")[0]["name"] == "sentinel"
        assert {
            "provider_security_master_records",
            "provider_security_master_observations",
            "provider_detail_batch_results",
        }.isdisjoint(tables)
        with engine.connect() as connection:
            assert (
                connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                == "0003_phase_02_cp3_b_invariants"
            )
        with engine.begin() as connection:
            connection.execute(text("DROP TABLE provider_identity_state_events"))
    finally:
        engine.dispose()
    assert phase_one_dump(url) == expected_phase_one
    assert cp3_invariant_dump(url) == expected_cp3

    command.upgrade(config, "head")
    engine = create_engine(url)
    try:
        assert set(CP3_C1_TABLES).issubset(set(inspect(engine).get_table_names()))
    finally:
        engine.dispose()
    assert phase_one_dump(url) == expected_phase_one
    assert cp3_invariant_dump(url) == expected_cp3


def test_0003_fails_closed_on_preexisting_multiple_source_roots(
    workspace_tmp_path: Path,
) -> None:
    url = f"sqlite:///{(workspace_tmp_path / 'invalid-source-roots.sqlite3').as_posix()}"
    config = alembic_config(url)
    command.upgrade(config, "0001_phase_01")
    engine = create_engine(url)
    try:
        FixtureImporter(session_factory(engine)).import_repository(FixtureRepository(FIXTURE_DIR))
    finally:
        engine.dispose()
    command.upgrade(config, "0002_phase_02_cp3_foundation")
    seed_valid_cp3_invariant_rows(url)
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO provider_raw_manifests VALUES "
                    "('raw_second_root', 'request_invariant', 201, :raw_hash, :raw_ref, "
                    "'2026-08-25T04:00:00Z', '{}', 'toss-source/0.1.0', '{}')"
                ),
                {
                    "raw_hash": "sha256:" + "7" * 64,
                    "raw_ref": "provider-raw:sha256/77/" + "7" * 64,
                },
            )
            connection.execute(
                text(
                    "INSERT INTO provider_source_versions VALUES "
                    "('source_second_root', 'request_invariant', 'raw_second_root', "
                    "'STOCK_DISCOVERY', 201, :raw_hash, 'toss-source/0.1.0', "
                    "'ORIGINAL', NULL, :normalized_hash, '{}')"
                ),
                {
                    "raw_hash": "sha256:" + "7" * 64,
                    "normalized_hash": "sha256:" + "8" * 64,
                },
            )
    finally:
        engine.dispose()

    with pytest.raises(RuntimeError, match="one original root"):
        command.upgrade(config, "0003_phase_02_cp3_b_invariants")

    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            assert connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one() == ("0002_phase_02_cp3_foundation")
        assert not {
            index["name"]
            for index in inspect(engine).get_indexes("provider_source_versions")
            if str(index["name"]).startswith("uq_provider_")
        }
    finally:
        engine.dispose()


def test_0003_fails_closed_on_preexisting_overlapping_verified_mappings(
    workspace_tmp_path: Path,
) -> None:
    url = f"sqlite:///{(workspace_tmp_path / 'invalid-mapping-overlap.sqlite3').as_posix()}"
    config = alembic_config(url)
    command.upgrade(config, "0001_phase_01")
    engine = create_engine(url)
    try:
        FixtureImporter(session_factory(engine)).import_repository(FixtureRepository(FIXTURE_DIR))
    finally:
        engine.dispose()
    command.upgrade(config, "0002_phase_02_cp3_foundation")
    seed_valid_cp3_invariant_rows(url)
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO provider_identity_mappings VALUES "
                    "('mapping_overlap', 'identity_invariant', 'issuer_us_synthetic', "
                    "'security_us_synthetic_common', 'VERIFIED', 'source_amended', "
                    "'2026-08-25T04:00:00Z', '2022-01-01', NULL, "
                    "'toss-identity/0.1.0', '{}')"
                )
            )
    finally:
        engine.dispose()

    with pytest.raises(RuntimeError, match="intervals overlap"):
        command.upgrade(config, "0003_phase_02_cp3_b_invariants")

    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            assert connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one() == ("0002_phase_02_cp3_foundation")
        assert not {
            index["name"]
            for index in inspect(engine).get_indexes("provider_identity_mappings")
            if str(index["name"]).startswith("uq_provider_")
        }
    finally:
        engine.dispose()


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


def test_cp3_foundation_migration_file_is_byte_identical() -> None:
    migration = PROJECT_ROOT / "services/api/alembic/versions/0002_phase_02_cp3_foundation.py"
    assert hashlib.sha256(migration.read_bytes()).hexdigest() == "".join(
        (
            "4b6b7169",
            "99c5f3f6",
            "b52be1e8",
            "5a53685c",
            "14c181fb",
            "4991e9ea",
            "d8920807",
            "17abaee6",
        )
    )


def test_cp3_b_invariants_migration_file_is_byte_identical() -> None:
    migration = PROJECT_ROOT / "services/api/alembic/versions/0003_phase_02_cp3_b_invariants.py"
    assert hashlib.sha256(migration.read_bytes()).hexdigest() == "".join(
        (
            "b59e74b5",
            "e817b6a5",
            "606d9f89",
            "f1f57eec",
            "3e0ba361",
            "6918d117",
            "d3cc28af",
            "4f5c420b",
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
