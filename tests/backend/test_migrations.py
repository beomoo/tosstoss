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
            "canonical_requests": {
                "canonical_request_id": ("VARCHAR(128)", False, True),
                "provider": ("VARCHAR(32)", False, False),
                "method": ("VARCHAR(8)", False, False),
                "path_template": ("VARCHAR(256)", False, False),
                "canonical_query_json": ("TEXT", False, False),
                "canonical_query_hash": ("VARCHAR(71)", False, False),
                "provider_contract_version": ("VARCHAR(64)", False, False),
                "payload_json": ("TEXT", False, False),
            },
            "provider_raw_manifests": {
                "raw_response_id": ("VARCHAR(128)", False, True),
                "canonical_request_id": ("VARCHAR(128)", False, False),
                "http_status": ("INTEGER", False, False),
                "raw_content_hash": ("VARCHAR(71)", False, False),
                "raw_storage_ref": ("VARCHAR(128)", False, False),
                "fetched_at": ("VARCHAR(35)", False, False),
                "response_metadata_json": ("TEXT", False, False),
                "provider_contract_version": ("VARCHAR(64)", False, False),
                "payload_json": ("TEXT", False, False),
            },
            "provider_source_versions": {
                "source_version_id": ("VARCHAR(128)", False, True),
                "canonical_request_id": ("VARCHAR(128)", False, False),
                "raw_response_id": ("VARCHAR(128)", False, False),
                "dataset": ("VARCHAR(64)", False, False),
                "http_status": ("INTEGER", False, False),
                "raw_content_hash": ("VARCHAR(71)", False, False),
                "provider_contract_version": ("VARCHAR(64)", False, False),
                "revision_status": ("VARCHAR(32)", False, False),
                "supersedes_id": ("VARCHAR(128)", True, False),
                "normalized_content_hash": ("VARCHAR(71)", False, False),
                "payload_json": ("TEXT", False, False),
            },
            "collection_attempts": {
                "attempt_id": ("VARCHAR(128)", False, True),
                "provider": ("VARCHAR(32)", False, False),
                "dataset": ("VARCHAR(64)", False, False),
                "canonical_request_id": ("VARCHAR(128)", True, False),
                "started_at": ("VARCHAR(35)", False, False),
                "finished_at": ("VARCHAR(35)", True, False),
                "status": ("VARCHAR(32)", False, False),
                "records_received": ("INTEGER", False, False),
                "records_rejected": ("INTEGER", False, False),
                "safe_result_code": ("VARCHAR(64)", False, False),
                "payload_json": ("TEXT", False, False),
            },
            "provider_audit_events": {
                "audit_event_id": ("VARCHAR(128)", False, True),
                "attempt_id": ("VARCHAR(128)", False, False),
                "source_version_id": ("VARCHAR(128)", True, False),
                "event_type": ("VARCHAR(64)", False, False),
                "safe_status": ("VARCHAR(64)", False, False),
                "record_count": ("INTEGER", False, False),
                "occurred_at": ("VARCHAR(35)", False, False),
                "payload_json": ("TEXT", False, False),
            },
            "provider_security_identities": {
                "provider_security_identity_id": ("VARCHAR(128)", False, True),
                "provider": ("VARCHAR(32)", False, False),
                "market": ("VARCHAR(8)", False, False),
                "allocation_anchor_hash": ("VARCHAR(71)", False, False),
                "identity_state": ("VARCHAR(32)", False, False),
                "mapping_status": ("VARCHAR(32)", False, False),
                "first_source_version_id": ("VARCHAR(128)", False, False),
                "latest_source_version_id": ("VARCHAR(128)", False, False),
                "provider_contract_version": ("VARCHAR(64)", False, False),
                "payload_json": ("TEXT", False, False),
            },
            "provider_identifier_history": {
                "identifier_history_id": ("VARCHAR(128)", False, True),
                "provider_security_identity_id": ("VARCHAR(128)", False, False),
                "identifier_kind": ("VARCHAR(32)", False, False),
                "identifier_value": ("VARCHAR(128)", False, False),
                "valid_from": ("DATE", True, False),
                "valid_to": ("DATE", True, False),
                "source_version_id": ("VARCHAR(128)", False, False),
                "revision_reason": ("VARCHAR(32)", False, False),
                "provider_contract_version": ("VARCHAR(64)", False, False),
                "payload_json": ("TEXT", False, False),
            },
            "provider_identity_mappings": {
                "mapping_id": ("VARCHAR(128)", False, True),
                "provider_security_identity_id": ("VARCHAR(128)", False, False),
                "issuer_id": ("VARCHAR(128)", True, False),
                "security_id": ("VARCHAR(128)", True, False),
                "mapping_status": ("VARCHAR(32)", False, False),
                "evidence_source_version_id": ("VARCHAR(128)", False, False),
                "approved_at": ("VARCHAR(35)", True, False),
                "valid_from": ("DATE", True, False),
                "valid_to": ("DATE", True, False),
                "provider_contract_version": ("VARCHAR(64)", False, False),
                "payload_json": ("TEXT", False, False),
            },
            "provider_latest_pointers": {
                "latest_pointer_id": ("VARCHAR(128)", False, True),
                "dataset": ("VARCHAR(64)", False, False),
                "provider_security_identity_id": ("VARCHAR(128)", False, False),
                "normalized_record_id": ("VARCHAR(128)", False, False),
                "source_version_id": ("VARCHAR(128)", False, False),
                "accepted_observed_at": ("VARCHAR(35)", True, False),
                "accepted_observed_date": ("DATE", True, False),
                "state_hash": ("VARCHAR(71)", False, False),
                "provider_contract_version": ("VARCHAR(64)", False, False),
                "payload_json": ("TEXT", False, False),
            },
            "provider_security_master_records": {
                "normalized_record_id": ("VARCHAR(128)", False, True),
                "provider": ("VARCHAR(32)", False, False),
                "market": ("VARCHAR(8)", False, False),
                "provider_listing_market": ("VARCHAR(32)", False, False),
                "symbol": ("VARCHAR(32)", False, False),
                "status": ("VARCHAR(32)", False, False),
                "normalized_content_hash": ("VARCHAR(71)", False, False),
                "provider_contract_version": ("VARCHAR(64)", False, False),
                "payload_json": ("TEXT", False, False),
            },
            "provider_security_master_observations": {
                "observation_id": ("VARCHAR(128)", False, True),
                "source_version_id": ("VARCHAR(128)", False, False),
                "normalized_record_id": ("VARCHAR(128)", True, False),
                "provider_security_identity_id": ("VARCHAR(128)", True, False),
                "provider": ("VARCHAR(32)", False, False),
                "market": ("VARCHAR(8)", False, False),
                "symbol": ("VARCHAR(32)", False, False),
                "staging_state": ("VARCHAR(32)", False, False),
                "reconciliation_outcome": ("VARCHAR(32)", False, False),
                "eligible_for_mapping": ("INTEGER", False, False),
                "provider_contract_version": ("VARCHAR(64)", False, False),
                "payload_json": ("TEXT", False, False),
            },
            "provider_identity_state_events": {
                "state_event_id": ("VARCHAR(128)", False, True),
                "provider_security_identity_id": ("VARCHAR(128)", False, False),
                "source_version_id": ("VARCHAR(128)", False, False),
                "identity_state": ("VARCHAR(32)", False, False),
                "staging_state": ("VARCHAR(32)", False, False),
                "reason_code": ("VARCHAR(64)", False, False),
                "provider_contract_version": ("VARCHAR(64)", False, False),
                "payload_json": ("TEXT", False, False),
            },
            "provider_detail_batch_results": {
                "batch_result_id": ("VARCHAR(128)", False, True),
                "source_version_id": ("VARCHAR(128)", False, False),
                "requested_count": ("INTEGER", False, False),
                "received_count": ("INTEGER", False, False),
                "missing_count": ("INTEGER", False, False),
                "status": ("VARCHAR(32)", False, False),
                "provider_contract_version": ("VARCHAR(64)", False, False),
                "payload_json": ("TEXT", False, False),
            },
        }
        assert set(inspector.get_table_names()) == (
            set(expected_columns) | AUTHORITY_TABLES | {"alembic_version"}
        )
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
            "canonical_requests": ("canonical_request_id",),
            "provider_raw_manifests": ("raw_response_id",),
            "provider_source_versions": ("source_version_id",),
            "collection_attempts": ("attempt_id",),
            "provider_audit_events": ("audit_event_id",),
            "provider_security_identities": ("provider_security_identity_id",),
            "provider_identifier_history": ("identifier_history_id",),
            "provider_identity_mappings": ("mapping_id",),
            "provider_latest_pointers": ("latest_pointer_id",),
            "provider_security_master_records": ("normalized_record_id",),
            "provider_security_master_observations": ("observation_id",),
            "provider_identity_state_events": ("state_event_id",),
            "provider_detail_batch_results": ("batch_result_id",),
        }
        expected_uniques = {
            "issuers": {("corp_code",), ("cik",)},
            "securities": {("market", "exchange", "ticker", "share_class")},
            "source_records": {("source_system", "source_type", "external_id")},
            "data_quality_statuses": {("issuer_id", "source_system", "dataset")},
            "fixture_import_runs": {("manifest_digest",)},
            "canonical_requests": set(),
            "provider_raw_manifests": {("canonical_request_id", "http_status", "raw_content_hash")},
            "provider_source_versions": {
                (
                    "canonical_request_id",
                    "http_status",
                    "raw_content_hash",
                    "provider_contract_version",
                )
            },
            "collection_attempts": set(),
            "provider_audit_events": set(),
            "provider_security_identities": {("provider", "allocation_anchor_hash")},
            "provider_identifier_history": {
                (
                    "provider_security_identity_id",
                    "identifier_kind",
                    "identifier_value",
                    "source_version_id",
                )
            },
            "provider_identity_mappings": set(),
            "provider_latest_pointers": {("dataset", "provider_security_identity_id")},
            "provider_security_master_records": {("normalized_content_hash",)},
            "provider_security_master_observations": {
                (
                    "source_version_id",
                    "symbol",
                    "staging_state",
                    "reconciliation_outcome",
                )
            },
            "provider_identity_state_events": {
                (
                    "provider_security_identity_id",
                    "source_version_id",
                    "identity_state",
                    "staging_state",
                    "reason_code",
                )
            },
            "provider_detail_batch_results": {("source_version_id",)},
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

        expected_indexes = {
            "provider_source_versions": {
                (
                    "uq_provider_source_versions_original_root",
                    ("canonical_request_id",),
                    True,
                ),
                (
                    "uq_provider_source_versions_supersedes",
                    ("supersedes_id",),
                    True,
                ),
            },
            "provider_identity_mappings": {
                (
                    "uq_provider_identity_mappings_current_verified",
                    ("provider_security_identity_id",),
                    True,
                )
            },
        }
        for table in expected_columns:
            reflected_indexes = {
                (
                    _constraint_name(index.get("name")),
                    _column_names(index.get("column_names")),
                    bool(index.get("unique", False)),
                )
                for index in inspector.get_indexes(table)
            }
            assert reflected_indexes == expected_indexes.get(table, set())

        expected_foreign_keys = {
            "securities": {("issuer_id",): ("issuers", ("issuer_id",))},
            "source_records": {("supersedes_id",): ("source_records", ("source_record_id",))},
            "data_quality_statuses": {("issuer_id",): ("issuers", ("issuer_id",))},
            "provider_raw_manifests": {
                ("canonical_request_id",): ("canonical_requests", ("canonical_request_id",))
            },
            "provider_source_versions": {
                ("canonical_request_id",): ("canonical_requests", ("canonical_request_id",)),
                ("raw_response_id",): ("provider_raw_manifests", ("raw_response_id",)),
                ("supersedes_id",): ("provider_source_versions", ("source_version_id",)),
            },
            "collection_attempts": {
                ("canonical_request_id",): ("canonical_requests", ("canonical_request_id",))
            },
            "provider_audit_events": {
                ("attempt_id",): ("collection_attempts", ("attempt_id",)),
                ("source_version_id",): ("provider_source_versions", ("source_version_id",)),
            },
            "provider_security_identities": {
                ("first_source_version_id",): (
                    "provider_source_versions",
                    ("source_version_id",),
                ),
                ("latest_source_version_id",): (
                    "provider_source_versions",
                    ("source_version_id",),
                ),
            },
            "provider_identifier_history": {
                ("provider_security_identity_id",): (
                    "provider_security_identities",
                    ("provider_security_identity_id",),
                ),
                ("source_version_id",): ("provider_source_versions", ("source_version_id",)),
            },
            "provider_identity_mappings": {
                ("provider_security_identity_id",): (
                    "provider_security_identities",
                    ("provider_security_identity_id",),
                ),
                ("issuer_id",): ("issuers", ("issuer_id",)),
                ("security_id",): ("securities", ("security_id",)),
                ("evidence_source_version_id",): (
                    "provider_source_versions",
                    ("source_version_id",),
                ),
            },
            "provider_latest_pointers": {
                ("provider_security_identity_id",): (
                    "provider_security_identities",
                    ("provider_security_identity_id",),
                ),
                ("source_version_id",): ("provider_source_versions", ("source_version_id",)),
            },
            "provider_security_master_observations": {
                ("source_version_id",): ("provider_source_versions", ("source_version_id",)),
                ("normalized_record_id",): (
                    "provider_security_master_records",
                    ("normalized_record_id",),
                ),
                ("provider_security_identity_id",): (
                    "provider_security_identities",
                    ("provider_security_identity_id",),
                ),
            },
            "provider_identity_state_events": {
                ("provider_security_identity_id",): (
                    "provider_security_identities",
                    ("provider_security_identity_id",),
                ),
                ("source_version_id",): ("provider_source_versions", ("source_version_id",)),
            },
            "provider_detail_batch_results": {
                ("source_version_id",): ("provider_source_versions", ("source_version_id",)),
            },
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
                == "0005_phase_02_cp3_c2_b_issuer_authority"
            )
    finally:
        engine.dispose()
