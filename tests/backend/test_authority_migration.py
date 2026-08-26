from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DBAPIError, OperationalError
from tests.backend.conftest import FIXTURE_DIR, alembic_config

from authority_test_helpers import production_source_policy, seed_provider_lineage
from toss_dashboard_api.fixtures.importer import FixtureImporter
from toss_dashboard_api.repositories.authority import SQLiteAuthorityLedgerRepository
from toss_dashboard_api.repositories.fixture import FixtureRepository
from toss_dashboard_api.repositories.sqlite import SQLiteMetadataRepository
from toss_dashboard_api.storage.database import (
    create_database_engine,
    session_factory,
)

REVISION_0004 = "0004_phase_02_cp3_c1_security_master"
REVISION_0005 = "0005_phase_02_cp3_c2_b_issuer_authority"


def _sha256_literal(*chunks: str) -> str:
    return "".join(chunks)


MIGRATION_HASHES = {
    "0001_phase_01_foundation.py": _sha256_literal(
        "6eba164e",
        "f2f8bab4",
        "25830768",
        "05255268",
        "e4daba29",
        "311e8f6e",
        "956f4177",
        "c0445762",
    ),
    "0002_phase_02_cp3_foundation.py": _sha256_literal(
        "4b6b7169",
        "99c5f3f6",
        "b52be1e8",
        "5a53685c",
        "14c181fb",
        "4991e9ea",
        "d8920807",
        "17abaee6",
    ),
    "0003_phase_02_cp3_b_invariants.py": _sha256_literal(
        "b59e74b5",
        "e817b6a5",
        "606d9f89",
        "f1f57eec",
        "3e0ba361",
        "6918d117",
        "d3cc28af",
        "4f5c420b",
    ),
    "0004_phase_02_cp3_c1_security_master.py": _sha256_literal(
        "cd1cbcae",
        "309f1e56",
        "ba923e64",
        "63863749",
        "c79a84b4",
        "c1049980",
        "1f5da28b",
        "0a3a0f4f",
    ),
}
AUTHORITY_TABLES = {
    "authority_source_policies",
    "reviewer_principals",
    "reviewer_webauthn_credentials",
    "reviewer_webauthn_credential_events",
    "issuer_approval_challenges",
    "issuer_approval_challenge_consumptions",
    "reviewer_authentication_events",
    "authority_evidence",
    "authority_evidence_observations",
    "authority_evidence_relations",
    "authority_evidence_applications",
    "authority_bundles",
    "authority_bundle_evidence_applications",
    "authority_bundle_scope_results",
    "authority_bundle_provider_observations",
    "authority_identifier_claims",
    "issuer_decisions",
    "issuer_approval_events",
    "issuer_approval_evidence_observations",
    "issuer_authority_links",
    "issuer_authority_link_heads",
}
IMMUTABLE_AUTHORITY_TABLES = AUTHORITY_TABLES - {"issuer_authority_link_heads"}


def _revision(database_url: str) -> str:
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            return str(
                connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            )
    finally:
        engine.dispose()


def _old_table_dump(database_url: str) -> dict[str, tuple[tuple[Any, ...], ...]]:
    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        tables = sorted(set(inspector.get_table_names()) - AUTHORITY_TABLES - {"alembic_version"})
        result: dict[str, tuple[tuple[Any, ...], ...]] = {}
        with engine.connect() as connection:
            for table_name in tables:
                primary_key = tuple(
                    inspector.get_pk_constraint(table_name).get("constrained_columns") or ()
                )
                order_clause = (
                    " ORDER BY " + ", ".join(f'"{name}"' for name in primary_key)
                    if primary_key
                    else ""
                )
                rows = connection.exec_driver_sql(
                    f'SELECT * FROM "{table_name}"{order_clause}'
                ).fetchall()
                result[table_name] = tuple(tuple(row) for row in rows)
        return result
    finally:
        engine.dispose()


def test_predecessor_migration_hashes_remain_exact() -> None:
    versions = Path(__file__).resolve().parents[2] / "services" / "api" / "alembic" / "versions"

    assert {
        name: hashlib.sha256((versions / name).read_bytes()).hexdigest()
        for name in MIGRATION_HASHES
    } == MIGRATION_HASHES


def test_blank_database_upgrades_through_exact_0005_schema(
    workspace_tmp_path: Path,
) -> None:
    url = f"sqlite:///{(workspace_tmp_path / 'authority-blank.sqlite3').as_posix()}"
    command.upgrade(alembic_config(url), "head")
    engine = create_engine(url)
    try:
        inspector = inspect(engine)
        assert AUTHORITY_TABLES.issubset(set(inspector.get_table_names()))
        evidence_columns = {
            str(column["name"]) for column in inspector.get_columns("authority_evidence")
        }
        assert {
            "authority_source_locator",
            "authority_document_reference",
            "raw_content_hash",
            "raw_claim_value_json",
            "normalized_claim_value_json",
            "authority_time_missing_reasons_json",
        }.issubset(evidence_columns)
        assert _revision(url) == REVISION_0005
    finally:
        engine.dispose()


def test_existing_0004_rows_survive_0005_upgrade_byte_for_byte(
    workspace_tmp_path: Path,
) -> None:
    url = f"sqlite:///{(workspace_tmp_path / 'authority-existing.sqlite3').as_posix()}"
    config = alembic_config(url)
    command.upgrade(config, REVISION_0004)
    engine = create_database_engine(url)
    try:
        sessions = session_factory(engine)
        FixtureImporter(sessions).import_repository(FixtureRepository(FIXTURE_DIR))
        seed_provider_lineage(sessions)
    finally:
        engine.dispose()
    before = _old_table_dump(url)

    command.upgrade(config, REVISION_0005)

    assert _old_table_dump(url) == before
    assert _revision(url) == REVISION_0005


def test_0005_downgrade_and_reupgrade_is_disposable_and_symmetric(
    workspace_tmp_path: Path,
) -> None:
    url = f"sqlite:///{(workspace_tmp_path / 'authority-roundtrip.sqlite3').as_posix()}"
    config = alembic_config(url)
    command.upgrade(config, REVISION_0004)
    before = _old_table_dump(url)
    command.upgrade(config, REVISION_0005)
    command.downgrade(config, REVISION_0004)
    engine = create_engine(url)
    try:
        assert AUTHORITY_TABLES.isdisjoint(set(inspect(engine).get_table_names()))
    finally:
        engine.dispose()
    assert _old_table_dump(url) == before
    assert _revision(url) == REVISION_0004

    command.upgrade(config, REVISION_0005)
    engine = create_engine(url)
    try:
        assert AUTHORITY_TABLES.issubset(set(inspect(engine).get_table_names()))
    finally:
        engine.dispose()
    assert _old_table_dump(url) == before
    assert _revision(url) == REVISION_0005


def test_0005_mid_migration_failure_cleans_only_new_objects_and_retries(
    workspace_tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url = f"sqlite:///{(workspace_tmp_path / 'authority-mid-failure.sqlite3').as_posix()}"
    config = alembic_config(url)
    command.upgrade(config, REVISION_0004)
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE authority_migration_sentinel "
                "(sentinel_id INTEGER PRIMARY KEY, marker TEXT NOT NULL)"
            )
            connection.exec_driver_sql(
                "INSERT INTO authority_migration_sentinel VALUES (1, 'preserve-me')"
            )
    finally:
        engine.dispose()
    before = _old_table_dump(url)
    original_execute = Operations.execute
    create_count = 0

    def fail_late(
        operations: Operations,
        sqltext: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        nonlocal create_count
        rendered = str(sqltext)
        if rendered.startswith("CREATE TABLE authority_"):
            create_count += 1
            if create_count == 6:
                raise OperationalError(
                    "simulated 0005 DDL failure",
                    {},
                    RuntimeError("simulated"),
                )
        return original_execute(operations, sqltext, *args, **kwargs)

    with monkeypatch.context() as context:
        context.setattr(Operations, "execute", fail_late)
        with pytest.raises(OperationalError, match="simulated 0005 DDL failure"):
            command.upgrade(config, REVISION_0005)

    engine = create_engine(url)
    try:
        tables = set(inspect(engine).get_table_names())
        assert AUTHORITY_TABLES.isdisjoint(tables)
        with engine.connect() as connection:
            assert connection.exec_driver_sql(
                "SELECT marker FROM authority_migration_sentinel"
            ).scalar_one() == ("preserve-me")
    finally:
        engine.dispose()
    assert _revision(url) == REVISION_0004
    assert _old_table_dump(url) == before

    command.upgrade(config, REVISION_0005)
    assert _revision(url) == REVISION_0005


def test_0005_preexisting_authority_object_is_preserved_fail_closed(
    workspace_tmp_path: Path,
) -> None:
    url = f"sqlite:///{(workspace_tmp_path / 'authority-collision.sqlite3').as_posix()}"
    config = alembic_config(url)
    command.upgrade(config, REVISION_0004)
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE authority_source_policies (sentinel TEXT NOT NULL)"
            )
            connection.exec_driver_sql(
                "INSERT INTO authority_source_policies VALUES ('preserve-me')"
            )
    finally:
        engine.dispose()

    with pytest.raises(RuntimeError, match="refuses to replace pre-existing"):
        command.upgrade(config, REVISION_0005)

    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            assert connection.exec_driver_sql(
                "SELECT sentinel FROM authority_source_policies"
            ).scalar_one() == ("preserve-me")
    finally:
        engine.dispose()
    assert _revision(url) == REVISION_0004


def test_every_immutable_authority_table_has_update_and_delete_trigger(
    workspace_tmp_path: Path,
) -> None:
    url = f"sqlite:///{(workspace_tmp_path / 'authority-triggers.sqlite3').as_posix()}"
    command.upgrade(alembic_config(url), REVISION_0005)
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            triggers = {
                str(row[0])
                for row in connection.exec_driver_sql(
                    "SELECT name FROM sqlite_master WHERE type = 'trigger'"
                )
            }
    finally:
        engine.dispose()
    expected = {
        f"trg_{table_name}_append_only_{operation}"
        for table_name in IMMUTABLE_AUTHORITY_TABLES
        for operation in ("update", "delete")
    }

    assert expected.issubset(triggers)
    assert not {
        "trg_issuer_authority_link_heads_append_only_update",
        "trg_issuer_authority_link_heads_append_only_delete",
    }.intersection(triggers)


@pytest.mark.parametrize("operation", ["UPDATE", "DELETE"])
def test_append_only_trigger_fails_closed_for_persisted_ledger_row(
    workspace_tmp_path: Path,
    operation: str,
) -> None:
    url = f"sqlite:///{(workspace_tmp_path / f'authority-{operation}.sqlite3').as_posix()}"
    command.upgrade(alembic_config(url), REVISION_0005)
    engine = create_database_engine(url)
    sessions = session_factory(engine)
    policy = production_source_policy()
    SQLiteAuthorityLedgerRepository(
        sessions,
        production_policy_registry={policy.authority_source_policy_id: policy.policy_content_hash},
    ).insert_or_verify_source_policy(policy)
    statement = (
        "UPDATE authority_source_policies SET field_owner = 'tampered' "
        "WHERE authority_source_policy_id = :policy_id"
        if operation == "UPDATE"
        else "DELETE FROM authority_source_policies WHERE authority_source_policy_id = :policy_id"
    )
    try:
        with pytest.raises(DBAPIError, match="append-only"):
            with engine.begin() as connection:
                connection.execute(
                    text(statement),
                    {"policy_id": policy.authority_source_policy_id},
                )
    finally:
        engine.dispose()


def test_identifier_claim_lookup_is_not_a_unique_winner_index(
    workspace_tmp_path: Path,
) -> None:
    url = f"sqlite:///{(workspace_tmp_path / 'authority-claims.sqlite3').as_posix()}"
    command.upgrade(alembic_config(url), REVISION_0005)
    engine = create_engine(url)
    try:
        indexes = inspect(engine).get_indexes("authority_identifier_claims")
        identifier_index = next(
            index
            for index in indexes
            if index["name"] == "ix_authority_identifier_claims_identifier"
        )
        assert bool(identifier_index["unique"]) is False
        unique_columns = {
            tuple(constraint["column_names"])
            for constraint in inspect(engine).get_unique_constraints("authority_identifier_claims")
        }
        assert ("identifier_kind", "normalized_identifier_value") not in unique_columns
    finally:
        engine.dispose()


def test_phase_one_public_database_revision_mask_remains_compatible(
    workspace_tmp_path: Path,
) -> None:
    path = workspace_tmp_path / "authority-public-revision.sqlite3"
    url = f"sqlite:///{path.as_posix()}"
    command.upgrade(alembic_config(url), REVISION_0005)
    engine = create_database_engine(url)
    try:
        repository = SQLiteMetadataRepository(session_factory(engine), engine)
        assert repository.database_revision() == "0001_phase_01"
        assert _revision(url) == REVISION_0005
    finally:
        engine.dispose()
