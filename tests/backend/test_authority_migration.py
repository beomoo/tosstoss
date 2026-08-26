from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError, OperationalError
from tests.backend.conftest import FIXTURE_DIR, alembic_config

from authority_test_helpers import (
    LATEST_REVISION_HASH,
    NOW,
    RETRIEVAL_FINGERPRINT,
    authority_bundle,
    authority_evidence,
    evidence_application,
    production_source_policy,
    seed_provider_lineage,
)
from toss_dashboard_api.contracts.authority import (
    LOCAL_DATA_STEWARD_AUTHENTICATION_CONTRACT_VERSION,
    AuthorityFreshnessResult,
    AuthorityRetrievalStatus,
    IssuerMachineDecisionState,
    ReviewerAuthenticationCounterAudit,
    ReviewerAuthenticationResult,
    ReviewerWebauthnCounterCapability,
    build_authority_evidence_observation,
    build_issuer_decision,
    reconstruct_current_webauthn_sign_count,
)
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


def _audit_hash(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def _seed_authentication_counter_ledger(engine):
    sessions = session_factory(engine)
    seed_provider_lineage(sessions)
    policy = production_source_policy()
    repository = SQLiteAuthorityLedgerRepository(
        sessions,
        production_policy_registry={policy.authority_source_policy_id: policy.policy_content_hash},
    )
    evidence = authority_evidence(policy)
    observation = build_authority_evidence_observation(
        evidence_id=evidence.evidence_id,
        fetched_at=NOW,
        raw_content_hash=evidence.raw_content_hash,
        authority_source_locator=evidence.authority_source_locator,
        authority_document_reference=evidence.authority_document_reference,
        retrieval_status=AuthorityRetrievalStatus.SUCCEEDED,
        secret_free_retrieval_fingerprint=RETRIEVAL_FINGERPRINT,
        safe_status_code="OK",
    )
    application = evidence_application(policy, evidence)
    bundle = authority_bundle(application)
    decision = build_issuer_decision(
        bundle=bundle,
        decision_state=IssuerMachineDecisionState.UNRESOLVED,
        reason_codes=("JURISDICTION_CONTRACT_REQUIRED",),
        latest_revision_check_hash=LATEST_REVISION_HASH,
        freshness_policy_version="conservative-approval-freshness/0.1.0",
        freshness_result=AuthorityFreshnessResult.CURRENT,
        collision_scan_hash=bundle.collision_scan_hash,
        evaluated_at=NOW,
    )
    repository.insert_or_verify_source_policy(policy)
    repository.insert_or_verify_evidence(evidence)
    repository.insert_or_verify_evidence_observation(observation)
    repository.insert_or_verify_evidence_application(application)
    repository.insert_or_verify_bundle(bundle)
    repository.insert_or_verify_decision(decision)

    principal = {
        "reviewer_principal_id": "reviewer_principal_counter_audit",
        "reviewer_role": "LOCAL_DATA_STEWARD",
        "principal_content_hash": _audit_hash("counter-principal"),
    }
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO reviewer_principals ("
                "reviewer_principal_id, contract_version, reviewer_role, principal_state, "
                "os_owner_sid_hash, enrollment_policy_version, principal_content_hash, "
                "registered_at, payload_json"
                ") VALUES ("
                ":reviewer_principal_id, :contract_version, :reviewer_role, 'ACTIVE', "
                ":sid_hash, :contract_version, :principal_content_hash, :registered_at, '{}'"
                ")"
            ),
            {
                **principal,
                "contract_version": LOCAL_DATA_STEWARD_AUTHENTICATION_CONTRACT_VERSION,
                "sid_hash": _audit_hash("owner-sid"),
                "registered_at": "2026-08-27T00:00:00Z",
            },
        )
    return decision, bundle, principal


def _insert_counter_credential(
    engine,
    principal,
    *,
    credential_id: str,
    counter_capability: str,
    registration_sign_count: int | None,
):
    credential = {
        "webauthn_credential_id": credential_id,
        "credential_id_fingerprint": _audit_hash(credential_id + "-id"),
        "public_key_fingerprint": _audit_hash(credential_id + "-public"),
        "counter_capability": counter_capability,
    }
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO reviewer_webauthn_credentials ("
                "webauthn_credential_id, contract_version, reviewer_principal_id, "
                "reviewer_role, principal_content_hash, credential_id_fingerprint, "
                "cose_public_key_canonical, public_key_fingerprint, public_key_algorithm, "
                "authenticator_aaguid, authenticator_attachment, "
                "authenticator_transports_json, counter_capability, "
                "registration_sign_count, rp_id, resident_key_required, "
                "user_verification_required, registration_policy_version, "
                "credential_content_hash, registered_at, payload_json"
                ") VALUES ("
                ":webauthn_credential_id, :contract_version, :reviewer_principal_id, "
                ":reviewer_role, :principal_content_hash, :credential_id_fingerprint, "
                ":cose_public_key_canonical, :public_key_fingerprint, 'ES256', NULL, "
                "'platform', :authenticator_transports_json, :counter_capability, "
                ":registration_sign_count, "
                "'localhost', 1, 1, :contract_version, :credential_content_hash, "
                "'2026-08-27T00:00:00Z', '{}'"
                ")"
            ),
            {
                **principal,
                **credential,
                "contract_version": LOCAL_DATA_STEWARD_AUTHENTICATION_CONTRACT_VERSION,
                "registration_sign_count": registration_sign_count,
                "cose_public_key_canonical": '{"kty":2}',
                "authenticator_transports_json": '["internal"]',
                "credential_content_hash": _audit_hash(credential_id + "-content"),
            },
        )
    return credential


def _insert_counter_authentication_event(
    engine,
    decision,
    bundle,
    principal,
    credential,
    *,
    event_suffix: str,
    authenticated_at: str,
    previous_sign_count: int | None,
    asserted_sign_count: int | None,
    authentication_result: str = "VERIFIED",
    counter_verified: int = 1,
) -> None:
    challenge_id = f"approval_challenge_{event_suffix}"
    consumption_id = f"challenge_consumption_{event_suffix}"
    event_id = f"authentication_event_{event_suffix}"
    values = {
        **principal,
        **credential,
        "contract_version": LOCAL_DATA_STEWARD_AUTHENTICATION_CONTRACT_VERSION,
        "issuer_approval_challenge_id": challenge_id,
        "challenge_consumption_id": consumption_id,
        "authentication_event_id": event_id,
        "issuer_decision_id": decision.issuer_decision_id,
        "authority_bundle_id": bundle.authority_bundle_id,
        "expected_decision_content_hash": decision.decision_content_hash,
        "expected_bundle_content_hash": bundle.bundle_content_hash,
        "provider_security_identity_id": bundle.provider_security_identity_id,
        "proposed_issuer_id": bundle.proposed_issuer_id,
        "challenge_digest": _audit_hash(challenge_id + "-digest"),
        "challenge_binding_hash": _audit_hash(challenge_id + "-binding"),
        "consumption_content_hash": _audit_hash(consumption_id + "-content"),
        "authentication_content_hash": _audit_hash(event_id + "-content"),
        "authenticated_at": authenticated_at,
        "previous_sign_count": previous_sign_count,
        "asserted_sign_count": asserted_sign_count,
        "authentication_result": authentication_result,
        "counter_verified": counter_verified,
        "safe_result_code": ("OK" if authentication_result == "VERIFIED" else "COUNTER_ROLLBACK"),
        "terminal_result": (
            "SUCCEEDED" if authentication_result == "VERIFIED" else "FAILED_CLOSED"
        ),
    }
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO issuer_approval_challenges ("
                "issuer_approval_challenge_id, contract_version, challenge_digest, "
                "challenge_binding_hash, reviewer_principal_id, reviewer_role, "
                "principal_content_hash, issuer_decision_id, authority_bundle_id, "
                "expected_decision_content_hash, expected_bundle_content_hash, "
                "provider_security_identity_id, proposed_issuer_id, requested_disposition, "
                "predecessor_approval_event_id, predecessor_link_id, successor_decision_id, "
                "rp_id, allowed_origin, user_verification_required, "
                "authentication_policy_version, issued_at, expires_at, payload_json"
                ") VALUES ("
                ":issuer_approval_challenge_id, :contract_version, :challenge_digest, "
                ":challenge_binding_hash, :reviewer_principal_id, :reviewer_role, "
                ":principal_content_hash, :issuer_decision_id, :authority_bundle_id, "
                ":expected_decision_content_hash, :expected_bundle_content_hash, "
                ":provider_security_identity_id, :proposed_issuer_id, 'APPROVED', "
                "NULL, NULL, NULL, 'localhost', 'http://localhost:3000', 1, "
                ":contract_version, '2026-08-27T01:00:00Z', "
                "'2026-08-27T01:04:59Z', '{}'"
                ")"
            ),
            values,
        )
        connection.execute(
            text(
                "INSERT INTO issuer_approval_challenge_consumptions ("
                "challenge_consumption_id, contract_version, issuer_approval_challenge_id, "
                "terminal_result, safe_result_code, consumption_content_hash, "
                "consumed_at, payload_json"
                ") VALUES ("
                ":challenge_consumption_id, :contract_version, "
                ":issuer_approval_challenge_id, :terminal_result, :safe_result_code, "
                ":consumption_content_hash, :authenticated_at, '{}'"
                ")"
            ),
            values,
        )
        connection.execute(
            text(
                "INSERT INTO reviewer_authentication_events ("
                "authentication_event_id, contract_version, issuer_approval_challenge_id, "
                "challenge_consumption_id, reviewer_principal_id, reviewer_role, "
                "webauthn_credential_id, credential_id_fingerprint, "
                "public_key_fingerprint, issuer_decision_id, authority_bundle_id, "
                "expected_decision_content_hash, expected_bundle_content_hash, "
                "requested_disposition, authentication_result, "
                "authentication_policy_version, rp_id, exact_origin, "
                "user_presence_verified, user_verification_verified, origin_verified, "
                "rp_id_hash_verified, signature_verified, counter_capability, "
                "previous_sign_count, asserted_sign_count, counter_verified, "
                "replay_rejected, safe_result_code, authentication_content_hash, "
                "authenticated_at, payload_json"
                ") VALUES ("
                ":authentication_event_id, :contract_version, "
                ":issuer_approval_challenge_id, :challenge_consumption_id, "
                ":reviewer_principal_id, :reviewer_role, :webauthn_credential_id, "
                ":credential_id_fingerprint, :public_key_fingerprint, "
                ":issuer_decision_id, :authority_bundle_id, "
                ":expected_decision_content_hash, :expected_bundle_content_hash, "
                "'APPROVED', :authentication_result, :contract_version, 'localhost', "
                "'http://localhost:3000', 1, 1, 1, 1, 1, :counter_capability, "
                ":previous_sign_count, :asserted_sign_count, :counter_verified, 1, "
                ":safe_result_code, :authentication_content_hash, :authenticated_at, '{}'"
                ")"
            ),
            values,
        )


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
        credential_columns = {
            str(column["name"]) for column in inspector.get_columns("reviewer_webauthn_credentials")
        }
        assert "registration_sign_count" in credential_columns
        assert "sign_count" not in credential_columns
        authentication_columns = {
            str(column["name"])
            for column in inspector.get_columns("reviewer_authentication_events")
        }
        assert {
            "counter_capability",
            "previous_sign_count",
            "asserted_sign_count",
            "counter_verified",
        }.issubset(authentication_columns)
        assert _revision(url) == REVISION_0005
    finally:
        engine.dispose()


def test_webauthn_counter_history_reconstructs_5_6_7_after_restart(
    workspace_tmp_path: Path,
) -> None:
    path = workspace_tmp_path / "authority-counter-history.sqlite3"
    url = f"sqlite:///{path.as_posix()}"
    command.upgrade(alembic_config(url), REVISION_0005)
    engine = create_database_engine(url)
    try:
        decision, bundle, principal = _seed_authentication_counter_ledger(engine)
        credential = _insert_counter_credential(
            engine,
            principal,
            credential_id="credential_counter_supported",
            counter_capability="SIGN_COUNT_SUPPORTED",
            registration_sign_count=5,
        )
        _insert_counter_authentication_event(
            engine,
            decision,
            bundle,
            principal,
            credential,
            event_suffix="counter_6",
            authenticated_at="2026-08-27T01:01:00Z",
            previous_sign_count=5,
            asserted_sign_count=6,
        )
        _insert_counter_authentication_event(
            engine,
            decision,
            bundle,
            principal,
            credential,
            event_suffix="counter_7",
            authenticated_at="2026-08-27T01:02:00Z",
            previous_sign_count=6,
            asserted_sign_count=7,
        )
    finally:
        engine.dispose()

    restarted = create_database_engine(url)
    try:
        with restarted.connect() as connection:
            registration_count = connection.execute(
                text(
                    "SELECT registration_sign_count FROM reviewer_webauthn_credentials "
                    "WHERE webauthn_credential_id = 'credential_counter_supported'"
                )
            ).scalar_one()
            rows = connection.execute(
                text(
                    "SELECT authentication_event_id, contract_version, "
                    "counter_capability, previous_sign_count, asserted_sign_count, "
                    "counter_verified, authentication_result, authenticated_at "
                    "FROM reviewer_authentication_events "
                    "WHERE webauthn_credential_id = 'credential_counter_supported' "
                    "ORDER BY authentication_event_id DESC"
                )
            ).mappings()
            events = tuple(
                ReviewerAuthenticationCounterAudit(
                    authentication_event_id=str(row["authentication_event_id"]),
                    contract_version=str(row["contract_version"]),
                    counter_capability=ReviewerWebauthnCounterCapability(
                        str(row["counter_capability"])
                    ),
                    previous_sign_count=int(row["previous_sign_count"]),
                    asserted_sign_count=int(row["asserted_sign_count"]),
                    counter_verified=bool(row["counter_verified"]),
                    authentication_result=ReviewerAuthenticationResult(
                        str(row["authentication_result"])
                    ),
                    authenticated_at=datetime.fromisoformat(
                        str(row["authenticated_at"]).replace("Z", "+00:00")
                    ),
                )
                for row in rows
            )
        assert registration_count == 5
        assert len(events) == 2
        assert (
            reconstruct_current_webauthn_sign_count(
                counter_capability=(ReviewerWebauthnCounterCapability.SIGN_COUNT_SUPPORTED),
                registration_sign_count=int(registration_count),
                authentication_events=events,
            )
            == 7
        )
    finally:
        restarted.dispose()


@pytest.mark.parametrize("asserted_sign_count", [5, 4])
def test_webauthn_verified_counter_equality_or_rollback_fails_closed(
    workspace_tmp_path: Path,
    asserted_sign_count: int,
) -> None:
    path = workspace_tmp_path / f"authority-counter-invalid-{asserted_sign_count}.sqlite3"
    url = f"sqlite:///{path.as_posix()}"
    command.upgrade(alembic_config(url), REVISION_0005)
    engine = create_database_engine(url)
    try:
        decision, bundle, principal = _seed_authentication_counter_ledger(engine)
        credential = _insert_counter_credential(
            engine,
            principal,
            credential_id="credential_counter_rollback",
            counter_capability="SIGN_COUNT_SUPPORTED",
            registration_sign_count=5,
        )
        with pytest.raises(IntegrityError):
            _insert_counter_authentication_event(
                engine,
                decision,
                bundle,
                principal,
                credential,
                event_suffix=f"invalid_verified_{asserted_sign_count}",
                authenticated_at="2026-08-27T01:03:00Z",
                previous_sign_count=5,
                asserted_sign_count=asserted_sign_count,
            )
        _insert_counter_authentication_event(
            engine,
            decision,
            bundle,
            principal,
            credential,
            event_suffix=f"rejected_audit_{asserted_sign_count}",
            authenticated_at="2026-08-27T01:04:00Z",
            previous_sign_count=5,
            asserted_sign_count=asserted_sign_count,
            authentication_result="REJECTED",
            counter_verified=0,
        )
        with engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT authentication_result, previous_sign_count, "
                    "asserted_sign_count, counter_verified "
                    "FROM reviewer_authentication_events"
                )
            ).one()
        assert tuple(row) == ("REJECTED", 5, asserted_sign_count, 0)
    finally:
        engine.dispose()


def test_webauthn_no_counter_state_uses_null_without_fake_advancement(
    workspace_tmp_path: Path,
) -> None:
    path = workspace_tmp_path / "authority-no-counter.sqlite3"
    url = f"sqlite:///{path.as_posix()}"
    command.upgrade(alembic_config(url), REVISION_0005)
    engine = create_database_engine(url)
    try:
        decision, bundle, principal = _seed_authentication_counter_ledger(engine)
        credential = _insert_counter_credential(
            engine,
            principal,
            credential_id="credential_no_usable_counter",
            counter_capability="NO_USABLE_COUNTER",
            registration_sign_count=None,
        )
        _insert_counter_authentication_event(
            engine,
            decision,
            bundle,
            principal,
            credential,
            event_suffix="no_counter",
            authenticated_at="2026-08-27T01:04:30Z",
            previous_sign_count=None,
            asserted_sign_count=None,
        )
        with engine.connect() as connection:
            credential_row = connection.execute(
                text(
                    "SELECT counter_capability, registration_sign_count "
                    "FROM reviewer_webauthn_credentials"
                )
            ).one()
            event_row = connection.execute(
                text(
                    "SELECT counter_capability, previous_sign_count, "
                    "asserted_sign_count, counter_verified, authentication_result "
                    "FROM reviewer_authentication_events"
                )
            ).one()
        assert tuple(credential_row) == ("NO_USABLE_COUNTER", None)
        assert tuple(event_row) == (
            "NO_USABLE_COUNTER",
            None,
            None,
            1,
            "VERIFIED",
        )
    finally:
        engine.dispose()


@pytest.mark.parametrize("operation", ["UPDATE", "DELETE"])
def test_webauthn_registration_counter_row_remains_append_only(
    workspace_tmp_path: Path,
    operation: str,
) -> None:
    path = workspace_tmp_path / f"authority-counter-credential-{operation}.sqlite3"
    url = f"sqlite:///{path.as_posix()}"
    command.upgrade(alembic_config(url), REVISION_0005)
    engine = create_database_engine(url)
    try:
        _decision_value, _bundle_value, principal = _seed_authentication_counter_ledger(engine)
        _insert_counter_credential(
            engine,
            principal,
            credential_id="credential_immutable_registration",
            counter_capability="SIGN_COUNT_SUPPORTED",
            registration_sign_count=5,
        )
        statement = (
            "UPDATE reviewer_webauthn_credentials SET registration_sign_count = 6 "
            "WHERE webauthn_credential_id = 'credential_immutable_registration'"
            if operation == "UPDATE"
            else "DELETE FROM reviewer_webauthn_credentials "
            "WHERE webauthn_credential_id = 'credential_immutable_registration'"
        )
        with pytest.raises(DBAPIError, match="append-only"):
            with engine.begin() as connection:
                connection.execute(text(statement))
    finally:
        engine.dispose()


@pytest.mark.parametrize("operation", ["UPDATE", "DELETE"])
def test_webauthn_authentication_counter_history_remains_append_only(
    workspace_tmp_path: Path,
    operation: str,
) -> None:
    path = workspace_tmp_path / f"authority-counter-event-{operation}.sqlite3"
    url = f"sqlite:///{path.as_posix()}"
    command.upgrade(alembic_config(url), REVISION_0005)
    engine = create_database_engine(url)
    try:
        decision, bundle, principal = _seed_authentication_counter_ledger(engine)
        credential = _insert_counter_credential(
            engine,
            principal,
            credential_id="credential_immutable_history",
            counter_capability="SIGN_COUNT_SUPPORTED",
            registration_sign_count=5,
        )
        _insert_counter_authentication_event(
            engine,
            decision,
            bundle,
            principal,
            credential,
            event_suffix="immutable_history",
            authenticated_at="2026-08-27T01:04:45Z",
            previous_sign_count=5,
            asserted_sign_count=6,
        )
        statement = (
            "UPDATE reviewer_authentication_events SET asserted_sign_count = 7 "
            "WHERE authentication_event_id = 'authentication_event_immutable_history'"
            if operation == "UPDATE"
            else "DELETE FROM reviewer_authentication_events "
            "WHERE authentication_event_id = 'authentication_event_immutable_history'"
        )
        with pytest.raises(DBAPIError, match="append-only"):
            with engine.begin() as connection:
                connection.execute(text(statement))
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
