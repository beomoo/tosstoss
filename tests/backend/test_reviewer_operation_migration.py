from __future__ import annotations

import hashlib
import importlib.util
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.operations import Operations
from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError, OperationalError
from tests.backend.conftest import alembic_config
from tests.backend.test_authority_migration import (
    _insert_counter_authentication_event,
    _seed_authentication_counter_ledger,
    _seed_nonreviewer_authority_ledger,
)

from toss_dashboard_api.repositories.sqlite import SQLiteMetadataRepository
from toss_dashboard_api.storage.database import create_database_engine, session_factory

REVISION_0005 = "0005_phase_02_cp3_c2_b_issuer_authority"
REVISION_0006 = "0006_phase_02_cp3_c2_b2_c_reviewer_operations"
REVISION_0006_PATH = (
    Path(__file__).resolve().parents[2]
    / "services"
    / "api"
    / "alembic"
    / "versions"
    / "0006_phase_02_cp3_c2_b2_c_reviewer_operations.py"
)
FROZEN_MIGRATION_BLOBS = {
    "0001_phase_01_foundation.py": "d00355c2456021e6ffb195e50833adc32c74a4ad",
    "0002_phase_02_cp3_foundation.py": "53f40664eca2ea2466cc6154b8579c5db506e0ba",
    "0003_phase_02_cp3_b_invariants.py": "47d5a69009949b155211cd68209640136a7cacd9",
    "0004_phase_02_cp3_c1_security_master.py": "91b4d96a445be23e7aa55e08b9310dc7334a026d",
    "0005_phase_02_cp3_c2_b_issuer_authority.py": "81976b8f70a1f6107526a13acadf23f369b196e3",
}
NEW_TABLES = {
    "reviewer_credential_operations",
    "reviewer_credential_operation_challenges",
    "reviewer_credential_operation_challenge_consumptions",
    "reviewer_credential_operation_authentication_events",
    "reviewer_webauthn_credential_event_authorizations",
    "reviewer_credential_operation_outcomes",
}
REQUIRED_INDEXES = {
    "uq_reviewer_principals_active_local_steward",
    "uq_reviewer_principals_exact_owner_binding",
    "uq_reviewer_credentials_exact_target",
    "uq_reviewer_credentials_exact_content",
    "uq_reviewer_credentials_exact_registration",
    "uq_reviewer_credential_events_exact_authorization",
    "uq_reviewer_credential_events_root",
    "uq_reviewer_credential_operations_exact_binding",
    "uq_reviewer_credential_operations_exact_subject",
    "uq_reviewer_credential_operations_root",
    "uq_reviewer_credential_operations_successor",
    "uq_reviewer_credential_operation_challenges_exact_operation_step",
    "uq_reviewer_credential_operation_challenges_exact_binding",
    "uq_reviewer_credential_operation_challenge_step",
    "ix_reviewer_credential_operation_challenge_expiry",
    "uq_reviewer_credential_operation_consumptions_exact_terminal",
    "uq_reviewer_credential_operation_consumptions_exact_registration",
    "uq_reviewer_credential_operation_authentication_exact_result",
    "uq_reviewer_credential_operation_outcomes_exact_terminal",
    "uq_reviewer_credential_operation_outcomes_exact_success",
    "uq_reviewer_credential_event_authorization_step",
    "ix_reviewer_authentication_counter_chain",
    "ix_reviewer_credential_operation_counter_chain",
}
INSERT_GUARDS = {
    "trg_reviewer_credential_operations_insert_guard",
    "trg_reviewer_credential_operation_challenges_insert_guard",
    "trg_reviewer_credential_operation_consumptions_insert_guard",
    "trg_reviewer_webauthn_credentials_requires_registration_proof",
    "trg_reviewer_webauthn_credential_events_requires_authorization",
    "trg_reviewer_webauthn_credential_events_chain_guard",
    "trg_reviewer_credential_operation_authentication_active_guard",
    "trg_reviewer_credential_operation_outcomes_insert_guard",
    "trg_reviewer_authentication_events_credential_active_guard",
    "trg_reviewer_authentication_events_counter_union_guard",
    "trg_reviewer_credential_operation_authentication_counter_union_guard",
}

OPERATION_INSERT = text(
    "INSERT INTO reviewer_credential_operations ("
    "reviewer_credential_operation_id, contract_version, operation_content_hash, "
    "reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash, "
    "operation_type, target_webauthn_credential_id, target_credential_id_fingerprint, "
    "expected_credential_state_hash, initial_challenge_id, initial_challenge_purpose, "
    "predecessor_operation_id, operation_policy_version, created_at, payload_json"
    ") VALUES ("
    ":operation_id, 'reviewer-credential-operation/0.1.0', :operation_hash, "
    ":principal_id, 'LOCAL_DATA_STEWARD', :principal_hash, :sid_hash, :operation_type, "
    ":target_id, :target_fingerprint, :expected_state, :challenge_id, "
    ":challenge_purpose, :predecessor_id, 'credential-operation-policy/0.1.0', "
    ":created_at, '{}'"
    ")"
)
CHALLENGE_INSERT = text(
    "INSERT INTO reviewer_credential_operation_challenges ("
    "reviewer_credential_operation_challenge_id, contract_version, challenge_digest, "
    "challenge_binding_hash, challenge_nonce_length, reviewer_credential_operation_id, "
    "operation_content_hash, reviewer_principal_id, reviewer_role, "
    "principal_content_hash, os_owner_sid_hash, operation_type, challenge_purpose, "
    "expected_credential_state_hash, target_webauthn_credential_id, "
    "target_credential_id_fingerprint, prerequisite_authentication_event_id, "
    "prerequisite_authentication_content_hash, prerequisite_authentication_result, "
    "rp_id, allowed_origin, client_data_type, user_verification_required, "
    "platform_attachment_required, resident_key_required, authentication_policy_version, "
    "issued_at, expires_at, payload_json"
    ") VALUES ("
    ":challenge_id, 'reviewer-credential-operation-challenge/0.1.0', :challenge_digest, "
    ":challenge_binding_hash, 32, :operation_id, :operation_hash, :principal_id, "
    "'LOCAL_DATA_STEWARD', :principal_hash, :sid_hash, :operation_type, "
    ":challenge_purpose, :expected_state, :target_id, :target_fingerprint, "
    ":prerequisite_auth_id, :prerequisite_auth_hash, :prerequisite_auth_result, "
    "'localhost', 'http://localhost:3000', :client_data_type, 1, "
    ":platform_required, :resident_required, 'credential-authentication-policy/0.1.0', "
    ":issued_at, :expires_at, '{}'"
    ")"
)
CONSUMPTION_INSERT = text(
    "INSERT INTO reviewer_credential_operation_challenge_consumptions ("
    "challenge_consumption_id, contract_version, reviewer_credential_operation_challenge_id, "
    "reviewer_credential_operation_id, reviewer_principal_id, operation_type, "
    "challenge_purpose, challenge_binding_hash, terminal_result, safe_result_code, "
    "client_data_type_verified, challenge_verified, origin_verified, "
    "cross_origin_false_verified, rp_id_hash_verified, user_presence_verified, "
    "user_verification_verified, platform_authenticator_verified, resident_key_verified, "
    "public_key_material_verified, registered_webauthn_credential_id, "
    "registered_credential_content_hash, registered_credential_id_fingerprint, "
    "registered_public_key_fingerprint, registered_rp_id, registered_counter_capability, "
    "registered_sign_count, terminal_operation_outcome_id, "
    "terminal_operation_outcome_result, outcome_expected_credential_state_hash, "
    "outcome_resulting_credential_state_hash, continuation_challenge_id, "
    "continuation_challenge_purpose, consumption_content_hash, consumed_at, payload_json"
    ") VALUES ("
    ":consumption_id, 'reviewer-credential-operation-consumption/0.1.0', :challenge_id, "
    ":operation_id, :principal_id, :operation_type, :challenge_purpose, "
    ":challenge_binding_hash, :terminal_result, :safe_result_code, :client_type_ok, "
    ":challenge_ok, :origin_ok, :cross_origin_ok, :rp_ok, :up_ok, :uv_ok, "
    ":platform_ok, :resident_ok, :key_ok, :registered_id, :credential_hash, "
    ":credential_fingerprint, :public_key_fingerprint, :registered_rp_id, "
    ":counter_capability, :registration_sign_count, :outcome_id, :outcome_result, "
    ":outcome_expected_state, :outcome_resulting_state, :continuation_id, "
    ":continuation_purpose, "
    ":consumption_hash, :consumed_at, '{}'"
    ")"
)
OPERATION_AUTH_INSERT = text(
    "INSERT INTO reviewer_credential_operation_authentication_events ("
    "credential_operation_authentication_event_id, contract_version, "
    "reviewer_credential_operation_challenge_id, challenge_binding_hash, "
    "challenge_consumption_id, challenge_consumption_content_hash, challenge_purpose, "
    "challenge_terminal_result, reviewer_credential_operation_id, operation_content_hash, "
    "operation_type, expected_credential_state_hash, reviewer_principal_id, reviewer_role, "
    "principal_content_hash, os_owner_sid_hash, authorizing_webauthn_credential_id, "
    "credential_id_fingerprint, public_key_fingerprint, authentication_result, "
    "authentication_policy_version, rp_id, exact_origin, user_presence_verified, "
    "user_verification_verified, origin_verified, rp_id_hash_verified, signature_verified, "
    "counter_capability, previous_sign_count, asserted_sign_count, counter_verified, "
    "replay_rejected, safe_result_code, authentication_content_hash, authenticated_at, "
    "payload_json"
    ") VALUES ("
    ":auth_id, 'reviewer-credential-operation-authentication/0.1.0', :challenge_id, "
    ":challenge_binding_hash, :consumption_id, :consumption_hash, "
    "'AUTHORIZATION_ASSERTION', :terminal_result, :operation_id, :operation_hash, "
    ":operation_type, :expected_state, :principal_id, 'LOCAL_DATA_STEWARD', "
    ":principal_hash, :sid_hash, :credential_id, :credential_fingerprint, "
    ":public_key_fingerprint, :authentication_result, "
    "'credential-authentication-policy/0.1.0', 'localhost', 'http://localhost:3000', "
    ":up_ok, :uv_ok, :origin_ok, :rp_ok, :signature_ok, :counter_capability, "
    ":previous_sign_count, :asserted_sign_count, :counter_ok, :replay_ok, "
    ":safe_result_code, :auth_hash, :authenticated_at, '{}'"
    ")"
)
AUTHORIZATION_INSERT = text(
    "INSERT INTO reviewer_webauthn_credential_event_authorizations ("
    "credential_event_id, contract_version, credential_event_content_hash, "
    "webauthn_credential_id, webauthn_credential_content_hash, reviewer_principal_id, "
    "reviewer_role, principal_content_hash, os_owner_sid_hash, event_type, "
    "reviewer_credential_operation_id, operation_content_hash, operation_type, "
    "authorization_kind, registration_consumption_id, "
    "registration_consumption_content_hash, registration_challenge_purpose, "
    "registration_terminal_result, credential_operation_authentication_event_id, "
    "credential_operation_authentication_content_hash, "
    "credential_operation_authentication_result, credential_operation_outcome_id, "
    "credential_operation_outcome_content_hash, credential_operation_outcome_result, "
    "expected_credential_state_hash, resulting_credential_state_hash, "
    "authorization_content_hash, recorded_at, payload_json"
    ") VALUES ("
    ":event_id, 'reviewer-credential-event-authorization/0.1.0', :event_hash, "
    ":credential_id, :credential_hash, :principal_id, 'LOCAL_DATA_STEWARD', "
    ":principal_hash, :sid_hash, :event_type, :operation_id, :operation_hash, "
    ":operation_type, :authorization_kind, :registration_consumption_id, "
    ":registration_consumption_hash, :registration_purpose, :registration_result, "
    ":auth_id, :auth_hash, :auth_result, :outcome_id, :outcome_hash, 'SUCCEEDED', "
    ":expected_state, :resulting_state, :authorization_hash, :recorded_at, '{}'"
    ")"
)
CREDENTIAL_INSERT = text(
    "INSERT INTO reviewer_webauthn_credentials ("
    "webauthn_credential_id, contract_version, reviewer_principal_id, reviewer_role, "
    "principal_content_hash, credential_id_fingerprint, cose_public_key_canonical, "
    "public_key_fingerprint, public_key_algorithm, authenticator_aaguid, "
    "authenticator_attachment, authenticator_transports_json, counter_capability, "
    "registration_sign_count, rp_id, resident_key_required, user_verification_required, "
    "registration_policy_version, credential_content_hash, registered_at, payload_json"
    ") VALUES ("
    ":credential_id, 'issuer-steward-webauthn/0.1.0', :principal_id, "
    "'LOCAL_DATA_STEWARD', :principal_hash, :credential_fingerprint, "
    "'synthetic-public-cose-key', :public_key_fingerprint, 'ES256', NULL, 'platform', "
    "'[\"internal\"]', :counter_capability, :registration_sign_count, 'localhost', "
    "1, 1, 'registration-policy/0.1.0', :credential_hash, :registered_at, '{}'"
    ")"
)
EVENT_INSERT = text(
    "INSERT INTO reviewer_webauthn_credential_events ("
    "credential_event_id, contract_version, webauthn_credential_id, "
    "reviewer_principal_id, event_type, structured_reason_code, "
    "supersedes_credential_event_id, credential_event_content_hash, occurred_at, payload_json"
    ") VALUES ("
    ":event_id, 'issuer-steward-webauthn/0.1.0', :credential_id, :principal_id, "
    ":event_type, :reason, :predecessor_event_id, :event_hash, :occurred_at, '{}'"
    ")"
)
OUTCOME_INSERT = text(
    "INSERT INTO reviewer_credential_operation_outcomes ("
    "credential_operation_outcome_id, contract_version, outcome_content_hash, "
    "reviewer_credential_operation_id, operation_content_hash, reviewer_principal_id, "
    "reviewer_role, principal_content_hash, os_owner_sid_hash, operation_type, "
    "terminal_result, terminal_consumption_id, terminal_consumption_content_hash, "
    "terminal_challenge_purpose, terminal_challenge_result, "
    "authorization_authentication_event_id, authorization_authentication_content_hash, "
    "authorization_authentication_result, registration_consumption_id, "
    "registration_consumption_content_hash, registration_challenge_purpose, "
    "registration_terminal_result, expected_credential_state_hash, "
    "resulting_credential_state_hash, safe_result_code, completed_at, payload_json"
    ") VALUES ("
    ":outcome_id, 'reviewer-credential-operation-outcome/0.1.0', :outcome_hash, "
    ":operation_id, :operation_hash, :principal_id, 'LOCAL_DATA_STEWARD', "
    ":principal_hash, :sid_hash, :operation_type, :outcome_result, :consumption_id, "
    ":consumption_hash, :challenge_purpose, :terminal_result, :auth_id, :auth_hash, "
    ":auth_result, :registration_consumption_id, :registration_consumption_hash, "
    ":registration_purpose, :registration_result, :expected_state, :resulting_state, "
    ":safe_result_code, :completed_at, '{}'"
    ")"
)


def _h(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def _git_blob_id(path: Path) -> str:
    payload = path.read_bytes()
    return hashlib.sha1(
        f"blob {len(payload)}\0".encode("ascii") + payload,
        usedforsecurity=False,
    ).hexdigest()


def _revision(url: str) -> str:
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            return str(
                connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            )
    finally:
        engine.dispose()


@pytest.fixture
def ledger_engine(workspace_tmp_path: Path) -> Iterator[Engine]:
    url = f"sqlite:///{(workspace_tmp_path / 'reviewer-ledger.sqlite3').as_posix()}"
    command.upgrade(alembic_config(url), REVISION_0006)
    engine = create_database_engine(url)
    try:
        yield engine
    finally:
        engine.dispose()


def _principal_values(suffix: str = "primary") -> dict[str, Any]:
    return {
        "principal_id": f"reviewer-principal-{suffix}",
        "principal_hash": _h(f"principal-{suffix}"),
        "sid_hash": _h(f"synthetic-sid-{suffix}"),
    }


def _seed_principal(engine: Engine, suffix: str = "primary") -> dict[str, Any]:
    values = _principal_values(suffix)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO reviewer_principals ("
                "reviewer_principal_id, contract_version, reviewer_role, principal_state, "
                "os_owner_sid_hash, enrollment_policy_version, principal_content_hash, "
                "registered_at, payload_json"
                ") VALUES ("
                ":principal_id, 'issuer-steward-webauthn/0.1.0', "
                "'LOCAL_DATA_STEWARD', 'ACTIVE', :sid_hash, 'enrollment-policy/0.1.0', "
                ":principal_hash, '2026-08-28T00:00:00Z', '{}'"
                ")"
            ),
            values,
        )
    return values


def _operation_values(
    principal: dict[str, Any],
    *,
    suffix: str,
    operation_type: str,
    expected_state: str,
    predecessor_id: str | None = None,
    target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    purpose = (
        "REGISTRATION_CREATE" if operation_type == "FIRST_ENROLLMENT" else "AUTHORIZATION_ASSERTION"
    )
    return {
        **principal,
        "operation_id": f"operation-{suffix}",
        "operation_hash": _h(f"operation-{suffix}"),
        "operation_type": operation_type,
        "target_id": None if target is None else target["credential_id"],
        "target_fingerprint": None if target is None else target["credential_fingerprint"],
        "expected_state": expected_state,
        "challenge_id": f"challenge-{suffix}-initial",
        "challenge_purpose": purpose,
        "predecessor_id": predecessor_id,
        "created_at": "2026-08-28T00:01:00Z",
    }


def _challenge_values(
    operation: dict[str, Any],
    *,
    challenge_id: str | None = None,
    purpose: str | None = None,
    prerequisite: dict[str, Any] | None = None,
    issued_at: str = "2026-08-28T00:01:00Z",
    expires_at: str = "2026-08-28T00:06:00Z",
) -> dict[str, Any]:
    selected_id = challenge_id or str(operation["challenge_id"])
    selected_purpose = purpose or str(operation["challenge_purpose"])
    registration = selected_purpose == "REGISTRATION_CREATE"
    return {
        **operation,
        "challenge_id": selected_id,
        "challenge_purpose": selected_purpose,
        "challenge_digest": _h(selected_id + "-digest"),
        "challenge_binding_hash": _h(selected_id + "-binding"),
        "prerequisite_auth_id": None if prerequisite is None else prerequisite["auth_id"],
        "prerequisite_auth_hash": None if prerequisite is None else prerequisite["auth_hash"],
        "prerequisite_auth_result": None if prerequisite is None else "VERIFIED",
        "client_data_type": "webauthn.create" if registration else "webauthn.get",
        "platform_required": 1 if registration else None,
        "resident_required": 1 if registration else None,
        "issued_at": issued_at,
        "expires_at": expires_at,
    }


def _issue_operation(
    engine: Engine,
    principal: dict[str, Any],
    *,
    suffix: str,
    operation_type: str,
    expected_state: str,
    predecessor_id: str | None = None,
    target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    operation = _operation_values(
        principal,
        suffix=suffix,
        operation_type=operation_type,
        expected_state=expected_state,
        predecessor_id=predecessor_id,
        target=target,
    )
    challenge = _challenge_values(operation)
    with engine.begin() as connection:
        connection.execute(OPERATION_INSERT, operation)
        connection.execute(CHALLENGE_INSERT, challenge)
    return {**operation, "initial_challenge": challenge}


def _mapped_outcome(terminal_result: str) -> str:
    return {
        "SUCCEEDED": "SUCCEEDED",
        "EXPIRED": "EXPIRED",
        "INVALID_SIGNATURE": "REJECTED",
        "USER_PRESENCE_ABSENT": "REJECTED",
        "USER_VERIFICATION_ABSENT": "REJECTED",
        "INVALID_REGISTRATION": "REJECTED",
        "BINDING_MISMATCH": "FAILED_CLOSED",
        "ORIGIN_RP_MISMATCH": "FAILED_CLOSED",
        "COUNTER_REJECTED": "FAILED_CLOSED",
        "REPLAY_REJECTED": "FAILED_CLOSED",
        "FAILED_CLOSED": "FAILED_CLOSED",
    }[terminal_result]


def _consumption_values(
    operation: dict[str, Any],
    challenge: dict[str, Any],
    *,
    suffix: str,
    terminal_result: str,
    resulting_state: str,
    outcome_id: str | None,
    continuation_id: str | None = None,
    credential: dict[str, Any] | None = None,
    consumed_at: str = "2026-08-28T00:05:59Z",
) -> dict[str, Any]:
    success = terminal_result == "SUCCEEDED"
    registration_success = success and challenge["challenge_purpose"] == "REGISTRATION_CREATE"
    common_ok = 1 if success else 0
    if terminal_result in {"INVALID_REGISTRATION", "INVALID_SIGNATURE"}:
        common_ok = 1
    up_ok = 0 if terminal_result == "USER_PRESENCE_ABSENT" else common_ok
    uv_ok = 0 if terminal_result == "USER_VERIFICATION_ABSENT" else common_ok
    outcome_result = None if outcome_id is None else _mapped_outcome(terminal_result)
    return {
        **operation,
        **challenge,
        "consumption_id": f"consumption-{suffix}",
        "terminal_result": terminal_result,
        "safe_result_code": terminal_result,
        "client_type_ok": common_ok,
        "challenge_ok": common_ok,
        "origin_ok": common_ok,
        "cross_origin_ok": common_ok,
        "rp_ok": common_ok,
        "up_ok": up_ok,
        "uv_ok": uv_ok,
        "platform_ok": 1 if registration_success else None,
        "resident_ok": 1 if registration_success else None,
        "key_ok": 1 if registration_success else None,
        "registered_id": None if credential is None else credential["credential_id"],
        "credential_hash": None if credential is None else credential["credential_hash"],
        "credential_fingerprint": (
            None if credential is None else credential["credential_fingerprint"]
        ),
        "public_key_fingerprint": (
            None if credential is None else credential["public_key_fingerprint"]
        ),
        "registered_rp_id": None if credential is None else "localhost",
        "counter_capability": None if credential is None else credential["counter_capability"],
        "registration_sign_count": (
            None if credential is None else credential["registration_sign_count"]
        ),
        "outcome_id": outcome_id,
        "outcome_result": outcome_result,
        "outcome_expected_state": None if outcome_id is None else operation["expected_state"],
        "outcome_resulting_state": None if outcome_id is None else resulting_state,
        "continuation_id": continuation_id,
        "continuation_purpose": None if continuation_id is None else "REGISTRATION_CREATE",
        "consumption_hash": _h(f"consumption-{suffix}"),
        "consumed_at": consumed_at,
    }


def _outcome_values(
    operation: dict[str, Any],
    consumption: dict[str, Any],
    *,
    suffix: str,
    outcome_hash: str | None = None,
    auth: dict[str, Any] | None = None,
) -> dict[str, Any]:
    registration = consumption["challenge_purpose"] == "REGISTRATION_CREATE"
    return {
        **operation,
        "outcome_id": consumption["outcome_id"],
        "outcome_hash": outcome_hash or _h(f"outcome-{suffix}"),
        "outcome_result": consumption["outcome_result"],
        "consumption_id": consumption["consumption_id"],
        "consumption_hash": consumption["consumption_hash"],
        "challenge_purpose": consumption["challenge_purpose"],
        "terminal_result": consumption["terminal_result"],
        "auth_id": None if auth is None else auth["auth_id"],
        "auth_hash": None if auth is None else auth["auth_hash"],
        "auth_result": None if auth is None else auth["authentication_result"],
        "registration_consumption_id": (consumption["consumption_id"] if registration else None),
        "registration_consumption_hash": (
            consumption["consumption_hash"] if registration else None
        ),
        "registration_purpose": "REGISTRATION_CREATE" if registration else None,
        "registration_result": consumption["terminal_result"] if registration else None,
        "resulting_state": consumption["outcome_resulting_state"],
        "safe_result_code": consumption["safe_result_code"],
        "completed_at": consumption["consumed_at"],
    }


def _terminalize_failure(
    engine: Engine,
    operation: dict[str, Any],
    challenge: dict[str, Any],
    *,
    suffix: str,
    terminal_result: str,
    auth: dict[str, Any] | None = None,
    consumed_at: str = "2026-08-28T00:05:59Z",
) -> tuple[dict[str, Any], dict[str, Any]]:
    outcome_id = f"outcome-{suffix}"
    consumption = _consumption_values(
        operation,
        challenge,
        suffix=suffix,
        terminal_result=terminal_result,
        resulting_state=str(operation["expected_state"]),
        outcome_id=outcome_id,
        consumed_at=consumed_at,
    )
    outcome = _outcome_values(operation, consumption, suffix=suffix, auth=auth)
    with engine.begin() as connection:
        connection.execute(CONSUMPTION_INSERT, consumption)
        connection.execute(OUTCOME_INSERT, outcome)
    return consumption, outcome


def _credential_values(
    principal: dict[str, Any],
    *,
    suffix: str,
    counter_capability: str = "SIGN_COUNT_SUPPORTED",
    registration_sign_count: int | None = 5,
) -> dict[str, Any]:
    if counter_capability == "NO_USABLE_COUNTER":
        registration_sign_count = None
    return {
        **principal,
        "credential_id": f"Y3JlZGVudGlhbC0{suffix}",
        "credential_hash": _h(f"credential-{suffix}"),
        "credential_fingerprint": _h(f"credential-id-{suffix}"),
        "public_key_fingerprint": _h(f"public-key-{suffix}"),
        "counter_capability": counter_capability,
        "registration_sign_count": registration_sign_count,
        "registered_at": "2026-08-28T00:05:59Z",
    }


def _authorization_values(
    operation: dict[str, Any],
    credential: dict[str, Any],
    *,
    event_id: str,
    event_hash: str,
    event_type: str,
    authorization_kind: str,
    outcome_id: str,
    outcome_hash: str,
    resulting_state: str,
    registration_consumption: dict[str, Any] | None,
    auth: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        **operation,
        **credential,
        "event_id": event_id,
        "event_hash": event_hash,
        "event_type": event_type,
        "authorization_kind": authorization_kind,
        "registration_consumption_id": (
            None if registration_consumption is None else registration_consumption["consumption_id"]
        ),
        "registration_consumption_hash": (
            None
            if registration_consumption is None
            else registration_consumption["consumption_hash"]
        ),
        "registration_purpose": (
            None if registration_consumption is None else "REGISTRATION_CREATE"
        ),
        "registration_result": None if registration_consumption is None else "SUCCEEDED",
        "auth_id": None if auth is None else auth["auth_id"],
        "auth_hash": None if auth is None else auth["auth_hash"],
        "auth_result": None if auth is None else "VERIFIED",
        "outcome_id": outcome_id,
        "outcome_hash": outcome_hash,
        "resulting_state": resulting_state,
        "authorization_hash": _h(f"authorization-{event_id}"),
        "recorded_at": "2026-08-28T00:05:59Z",
    }


def _event_values(
    credential: dict[str, Any],
    *,
    event_id: str,
    event_hash: str,
    event_type: str,
    predecessor_event_id: str | None,
) -> dict[str, Any]:
    return {
        **credential,
        "event_id": event_id,
        "event_hash": event_hash,
        "event_type": event_type,
        "reason": event_type,
        "predecessor_event_id": predecessor_event_id,
        "occurred_at": "2026-08-28T00:05:59Z",
    }


def _complete_registration(
    engine: Engine,
    operation: dict[str, Any],
    challenge: dict[str, Any],
    principal: dict[str, Any],
    *,
    suffix: str,
    resulting_state: str,
    auth: dict[str, Any] | None = None,
    replace_target: dict[str, Any] | None = None,
    counter_capability: str = "SIGN_COUNT_SUPPORTED",
    registration_sign_count: int | None = 5,
) -> tuple[dict[str, Any], dict[str, Any]]:
    credential = _credential_values(
        principal,
        suffix=suffix,
        counter_capability=counter_capability,
        registration_sign_count=registration_sign_count,
    )
    event_id = f"credential-event-{suffix}-registered"
    event_hash = _h(event_id)
    credential["root_event_id"] = event_id
    credential["root_event_hash"] = event_hash
    outcome_id = f"outcome-{suffix}-success"
    outcome_hash = _h(outcome_id)
    consumption = _consumption_values(
        operation,
        challenge,
        suffix=f"{suffix}-registration-success",
        terminal_result="SUCCEEDED",
        resulting_state=resulting_state,
        outcome_id=outcome_id,
        credential=credential,
    )
    authorization_kind = (
        "BOOTSTRAP_REGISTRATION"
        if operation["operation_type"] == "FIRST_ENROLLMENT"
        else "AUTHORIZED_REGISTRATION"
    )
    registered_authorization = _authorization_values(
        operation,
        credential,
        event_id=event_id,
        event_hash=event_hash,
        event_type="REGISTERED",
        authorization_kind=authorization_kind,
        outcome_id=outcome_id,
        outcome_hash=outcome_hash,
        resulting_state=resulting_state,
        registration_consumption=consumption,
        auth=auth,
    )
    registered_event = _event_values(
        credential,
        event_id=event_id,
        event_hash=event_hash,
        event_type="REGISTERED",
        predecessor_event_id=None,
    )
    outcome = _outcome_values(
        operation,
        consumption,
        suffix=f"{suffix}-success",
        outcome_hash=outcome_hash,
        auth=auth,
    )
    with engine.begin() as connection:
        connection.execute(CONSUMPTION_INSERT, consumption)
        connection.execute(AUTHORIZATION_INSERT, registered_authorization)
        if replace_target is not None:
            superseded_event_id = f"credential-event-{suffix}-superseded"
            superseded_event_hash = _h(superseded_event_id)
            superseded_authorization = _authorization_values(
                operation,
                replace_target,
                event_id=superseded_event_id,
                event_hash=superseded_event_hash,
                event_type="SUPERSEDED",
                authorization_kind="AUTHORIZED_SUPERSESSION",
                outcome_id=outcome_id,
                outcome_hash=outcome_hash,
                resulting_state=resulting_state,
                registration_consumption=None,
                auth=auth,
            )
            superseded_event = _event_values(
                replace_target,
                event_id=superseded_event_id,
                event_hash=superseded_event_hash,
                event_type="SUPERSEDED",
                predecessor_event_id=str(replace_target["root_event_id"]),
            )
            connection.execute(AUTHORIZATION_INSERT, superseded_authorization)
        connection.execute(CREDENTIAL_INSERT, credential)
        connection.execute(EVENT_INSERT, registered_event)
        if replace_target is not None:
            connection.execute(EVENT_INSERT, superseded_event)
        connection.execute(OUTCOME_INSERT, outcome)
    return credential, outcome


def _operation_auth_values(
    operation: dict[str, Any],
    challenge: dict[str, Any],
    consumption: dict[str, Any],
    credential: dict[str, Any],
    *,
    suffix: str,
    previous_sign_count: int | None,
    asserted_sign_count: int | None,
    authentication_result: str = "VERIFIED",
) -> dict[str, Any]:
    verified = authentication_result == "VERIFIED"
    return {
        **operation,
        **challenge,
        **credential,
        "consumption_id": consumption["consumption_id"],
        "consumption_hash": consumption["consumption_hash"],
        "terminal_result": consumption["terminal_result"],
        "auth_id": f"operation-auth-{suffix}",
        "auth_hash": _h(f"operation-auth-{suffix}"),
        "authentication_result": authentication_result,
        "up_ok": 1 if verified else 0,
        "uv_ok": 1 if verified else 0,
        "origin_ok": 1 if verified else 0,
        "rp_ok": 1 if verified else 0,
        "signature_ok": 1 if verified else 0,
        "previous_sign_count": previous_sign_count,
        "asserted_sign_count": asserted_sign_count,
        "counter_ok": 1 if verified else 0,
        "replay_ok": 1 if verified else 0,
        "safe_result_code": "OK" if verified else "REJECTED",
        "authenticated_at": "2026-08-28T00:03:00Z",
    }


def _authorize_management(
    engine: Engine,
    operation: dict[str, Any],
    credential: dict[str, Any],
    *,
    suffix: str,
    previous_sign_count: int | None,
    asserted_sign_count: int | None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    initial = operation["initial_challenge"]
    continuation_id = f"challenge-{suffix}-registration"
    consumption = _consumption_values(
        operation,
        initial,
        suffix=f"{suffix}-assertion-success",
        terminal_result="SUCCEEDED",
        resulting_state=str(operation["expected_state"]),
        outcome_id=None,
        continuation_id=continuation_id,
        consumed_at="2026-08-28T00:02:00Z",
    )
    auth = _operation_auth_values(
        operation,
        initial,
        consumption,
        credential,
        suffix=suffix,
        previous_sign_count=previous_sign_count,
        asserted_sign_count=asserted_sign_count,
    )
    continuation = _challenge_values(
        operation,
        challenge_id=continuation_id,
        purpose="REGISTRATION_CREATE",
        prerequisite=auth,
        issued_at="2026-08-28T00:03:00Z",
        expires_at="2026-08-28T00:08:00Z",
    )
    with engine.begin() as connection:
        connection.execute(CONSUMPTION_INSERT, consumption)
        connection.execute(OPERATION_AUTH_INSERT, auth)
        connection.execute(CHALLENGE_INSERT, continuation)
    return auth, continuation, consumption


def _complete_revoke(
    engine: Engine,
    operation: dict[str, Any],
    credential: dict[str, Any],
    *,
    suffix: str,
    resulting_state: str,
    previous_sign_count: int | None,
    asserted_sign_count: int | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    challenge = operation["initial_challenge"]
    outcome_id = f"outcome-{suffix}-revoke"
    outcome_hash = _h(outcome_id)
    consumption = _consumption_values(
        operation,
        challenge,
        suffix=f"{suffix}-revoke-success",
        terminal_result="SUCCEEDED",
        resulting_state=resulting_state,
        outcome_id=outcome_id,
        consumed_at="2026-08-28T00:02:00Z",
    )
    auth = _operation_auth_values(
        operation,
        challenge,
        consumption,
        credential,
        suffix=f"{suffix}-revoke",
        previous_sign_count=previous_sign_count,
        asserted_sign_count=asserted_sign_count,
    )
    event_id = f"credential-event-{suffix}-revoked"
    event_hash = _h(event_id)
    authorization = _authorization_values(
        operation,
        credential,
        event_id=event_id,
        event_hash=event_hash,
        event_type="REVOKED",
        authorization_kind="AUTHORIZED_REVOCATION",
        outcome_id=outcome_id,
        outcome_hash=outcome_hash,
        resulting_state=resulting_state,
        registration_consumption=None,
        auth=auth,
    )
    event = _event_values(
        credential,
        event_id=event_id,
        event_hash=event_hash,
        event_type="REVOKED",
        predecessor_event_id=str(credential["root_event_id"]),
    )
    outcome = _outcome_values(
        operation,
        consumption,
        suffix=f"{suffix}-revoke",
        outcome_hash=outcome_hash,
        auth=auth,
    )
    with engine.begin() as connection:
        connection.execute(CONSUMPTION_INSERT, consumption)
        connection.execute(OPERATION_AUTH_INSERT, auth)
        connection.execute(AUTHORIZATION_INSERT, authorization)
        connection.execute(EVENT_INSERT, event)
        connection.execute(OUTCOME_INSERT, outcome)
    return auth, outcome


def _seed_first_credential(
    engine: Engine,
    *,
    suffix: str = "first",
    counter_capability: str = "SIGN_COUNT_SUPPORTED",
    registration_sign_count: int | None = 5,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    principal = _seed_principal(engine)
    empty_state = _h("principal-empty-state")
    active_state = _h(f"principal-active-state-{suffix}")
    operation = _issue_operation(
        engine,
        principal,
        suffix=f"{suffix}-enrollment",
        operation_type="FIRST_ENROLLMENT",
        expected_state=empty_state,
    )
    credential, outcome = _complete_registration(
        engine,
        operation,
        operation["initial_challenge"],
        principal,
        suffix=suffix,
        resulting_state=active_state,
        counter_capability=counter_capability,
        registration_sign_count=registration_sign_count,
    )
    return principal, operation, credential, outcome


def _active_credentials(connection: Any, principal_id: str) -> tuple[str, ...]:
    rows = connection.execute(
        text(
            "SELECT credential.webauthn_credential_id "
            "FROM reviewer_webauthn_credentials credential "
            "JOIN reviewer_webauthn_credential_events root "
            "ON root.webauthn_credential_id = credential.webauthn_credential_id "
            "AND root.event_type = 'REGISTERED' "
            "AND root.supersedes_credential_event_id IS NULL "
            "JOIN reviewer_webauthn_credential_event_authorizations authorization "
            "ON authorization.credential_event_id = root.credential_event_id "
            "WHERE credential.reviewer_principal_id = :principal_id "
            "AND NOT EXISTS (SELECT 1 FROM reviewer_webauthn_credential_events successor "
            "WHERE successor.supersedes_credential_event_id = root.credential_event_id) "
            "ORDER BY credential.webauthn_credential_id"
        ),
        {"principal_id": principal_id},
    )
    return tuple(str(row[0]) for row in rows)


def _seed_issuer_context_and_first_credential(
    engine: Engine,
) -> tuple[
    Any,
    Any,
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    decision, bundle, issuer_principal = _seed_authentication_counter_ledger(engine)
    with engine.connect() as connection:
        sid_hash = str(
            connection.execute(
                text(
                    "SELECT os_owner_sid_hash FROM reviewer_principals "
                    "WHERE reviewer_principal_id=:reviewer_principal_id"
                ),
                issuer_principal,
            ).scalar_one()
        )
    principal = {
        "principal_id": issuer_principal["reviewer_principal_id"],
        "principal_hash": issuer_principal["principal_content_hash"],
        "sid_hash": sid_hash,
    }
    operation = _issue_operation(
        engine,
        principal,
        suffix="issuer-context-first",
        operation_type="FIRST_ENROLLMENT",
        expected_state=_h("issuer-context-empty"),
    )
    credential, outcome = _complete_registration(
        engine,
        operation,
        operation["initial_challenge"],
        principal,
        suffix="issuer-context-first",
        resulting_state=_h("issuer-context-active"),
    )
    issuer_credential = {
        "webauthn_credential_id": credential["credential_id"],
        "credential_id_fingerprint": credential["credential_fingerprint"],
        "public_key_fingerprint": credential["public_key_fingerprint"],
        "counter_capability": credential["counter_capability"],
    }
    return (
        decision,
        bundle,
        issuer_principal,
        principal,
        credential,
        issuer_credential,
        outcome,
    )


def test_0006_revision_and_down_revision_are_exact() -> None:
    spec = importlib.util.spec_from_file_location("reviewer_operations_0006", REVISION_0006_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == REVISION_0006
    assert module.down_revision == REVISION_0005


def test_frozen_0001_through_0005_git_blobs_remain_exact() -> None:
    versions = REVISION_0006_PATH.parent
    assert {
        name: _git_blob_id(versions / name) for name in FROZEN_MIGRATION_BLOBS
    } == FROZEN_MIGRATION_BLOBS


def test_blank_database_upgrades_0001_through_0006_with_exact_inventory(
    workspace_tmp_path: Path,
) -> None:
    baseline_url = f"sqlite:///{(workspace_tmp_path / 'blank-0005-baseline.sqlite3').as_posix()}"
    command.upgrade(alembic_config(baseline_url), REVISION_0005)
    baseline_engine = create_engine(baseline_url)
    try:
        with baseline_engine.connect() as connection:
            baseline_objects = {
                (str(row[0]), str(row[1]))
                for row in connection.exec_driver_sql(
                    "SELECT type, name FROM sqlite_master "
                    "WHERE type IN ('table', 'index', 'trigger') "
                    "AND name NOT LIKE 'sqlite_autoindex_%'"
                )
            }
    finally:
        baseline_engine.dispose()

    url = f"sqlite:///{(workspace_tmp_path / 'blank-0006.sqlite3').as_posix()}"
    command.upgrade(alembic_config(url), REVISION_0006)
    engine = create_engine(url)
    try:
        inspector = inspect(engine)
        assert NEW_TABLES == NEW_TABLES.intersection(inspector.get_table_names())
        with engine.connect() as connection:
            objects = {
                (str(row[0]), str(row[1]))
                for row in connection.exec_driver_sql(
                    "SELECT type, name FROM sqlite_master "
                    "WHERE type IN ('table', 'index', 'trigger') "
                    "AND name NOT LIKE 'sqlite_autoindex_%'"
                )
            }
            assert {("index", name) for name in REQUIRED_INDEXES}.issubset(objects)
            expected_append_only = {
                ("trigger", f"trg_{table}_{operation}")
                for table in NEW_TABLES
                for operation in ("append_only_update", "append_only_delete")
            }
            assert expected_append_only.issubset(objects)
            assert {("trigger", name) for name in INSERT_GUARDS}.issubset(objects)
            expected_additions = (
                {("table", name) for name in NEW_TABLES}
                | {("index", name) for name in REQUIRED_INDEXES}
                | expected_append_only
                | {("trigger", name) for name in INSERT_GUARDS}
            )
            assert objects - baseline_objects == expected_additions
            assert len(REQUIRED_INDEXES) == 23
            assert len(expected_append_only | {("trigger", name) for name in INSERT_GUARDS}) == 23
            assert tuple(connection.exec_driver_sql("PRAGMA foreign_key_check")) == ()
        assert _revision(url) == REVISION_0006
    finally:
        engine.dispose()


def test_populated_nonreviewer_0005_upgrades_without_row_change(
    workspace_tmp_path: Path,
) -> None:
    url = f"sqlite:///{(workspace_tmp_path / 'populated-0005.sqlite3').as_posix()}"
    config = alembic_config(url)
    command.upgrade(config, REVISION_0005)
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO issuers (issuer_id, jurisdiction, corp_code, cik, "
                    "normalized_content_hash, payload_json) "
                    "VALUES ('issuer-nonreviewer-sentinel', 'KR', '12345678', NULL, "
                    ":content_hash, :payload_json)"
                ),
                {"content_hash": _h("issuer-sentinel"), "payload_json": '{"sentinel":true}'},
            )
            before = tuple(
                connection.execute(
                    text("SELECT * FROM issuers WHERE issuer_id='issuer-nonreviewer-sentinel'")
                ).one()
            )
        _seed_nonreviewer_authority_ledger(engine)
        with engine.connect() as connection:
            authority_before = (
                int(
                    connection.execute(text("SELECT COUNT(*) FROM authority_bundles")).scalar_one()
                ),
                int(connection.execute(text("SELECT COUNT(*) FROM issuer_decisions")).scalar_one()),
            )
            assert all(count > 0 for count in authority_before)
            for table_name in (
                "reviewer_principals",
                "reviewer_webauthn_credentials",
                "reviewer_webauthn_credential_events",
                "issuer_approval_challenges",
                "reviewer_authentication_events",
            ):
                assert (
                    connection.exec_driver_sql(f'SELECT COUNT(*) FROM "{table_name}"').scalar_one()
                    == 0
                )
    finally:
        engine.dispose()

    command.upgrade(config, REVISION_0006)

    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            after = tuple(
                connection.execute(
                    text("SELECT * FROM issuers WHERE issuer_id='issuer-nonreviewer-sentinel'")
                ).one()
            )
            authority_after = (
                int(
                    connection.execute(text("SELECT COUNT(*) FROM authority_bundles")).scalar_one()
                ),
                int(connection.execute(text("SELECT COUNT(*) FROM issuer_decisions")).scalar_one()),
            )
            assert tuple(connection.exec_driver_sql("PRAGMA foreign_key_check")) == ()
        assert after == before
        assert authority_after == authority_before
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    ("object_kind", "object_name", "ddl"),
    [
        (
            "table",
            "reviewer_credential_operations",
            "CREATE TABLE reviewer_credential_operations (sentinel TEXT NOT NULL)",
        ),
        (
            "index",
            "uq_reviewer_principals_exact_owner_binding",
            "CREATE UNIQUE INDEX uq_reviewer_principals_exact_owner_binding "
            "ON reviewer_principals (reviewer_principal_id)",
        ),
        (
            "trigger",
            "trg_reviewer_credential_operations_insert_guard",
            "CREATE TRIGGER trg_reviewer_credential_operations_insert_guard "
            "BEFORE INSERT ON reviewer_principals BEGIN SELECT 1; END",
        ),
    ],
)
def test_0006_object_name_collision_is_preserved_fail_closed(
    workspace_tmp_path: Path,
    object_kind: str,
    object_name: str,
    ddl: str,
) -> None:
    url = f"sqlite:///{(workspace_tmp_path / f'collision-{object_kind}.sqlite3').as_posix()}"
    config = alembic_config(url)
    command.upgrade(config, REVISION_0005)
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(ddl)
    finally:
        engine.dispose()

    with pytest.raises(RuntimeError, match="refuses to replace pre-existing reviewer objects"):
        command.upgrade(config, REVISION_0006)

    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            assert (
                connection.exec_driver_sql(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type=:kind AND name=:name",
                    {"kind": object_kind, "name": object_name},
                ).scalar_one()
                == 1
            )
    finally:
        engine.dispose()
    assert _revision(url) == REVISION_0005


def test_unexpected_preexisting_reviewer_lineage_fails_without_backfill(
    workspace_tmp_path: Path,
) -> None:
    url = f"sqlite:///{(workspace_tmp_path / 'unexpected-reviewer.sqlite3').as_posix()}"
    config = alembic_config(url)
    command.upgrade(config, REVISION_0005)
    engine = create_engine(url)
    principal = _principal_values("unexpected")
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO reviewer_principals (reviewer_principal_id, "
                    "contract_version, reviewer_role, principal_state, os_owner_sid_hash, "
                    "enrollment_policy_version, principal_content_hash, registered_at, "
                    "payload_json) VALUES (:principal_id, 'issuer-steward-webauthn/0.1.0', "
                    "'LOCAL_DATA_STEWARD', 'ACTIVE', :sid_hash, 'policy', :principal_hash, "
                    "'2026-08-28T00:00:00Z', '{}')"
                ),
                principal,
            )
    finally:
        engine.dispose()

    with pytest.raises(RuntimeError, match="without synthetic backfill"):
        command.upgrade(config, REVISION_0006)

    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT reviewer_principal_id FROM reviewer_principals")
                ).scalar_one()
                == principal["principal_id"]
            )
            assert NEW_TABLES.isdisjoint(inspect(engine).get_table_names())
    finally:
        engine.dispose()
    assert _revision(url) == REVISION_0005


def test_0006_late_ddl_failure_rolls_back_only_0006_objects_and_retries(
    workspace_tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url = f"sqlite:///{(workspace_tmp_path / 'late-ddl.sqlite3').as_posix()}"
    config = alembic_config(url)
    command.upgrade(config, REVISION_0005)
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE reviewer_0006_unrelated_sentinel "
                "(sentinel_id INTEGER PRIMARY KEY, marker TEXT NOT NULL)"
            )
            connection.exec_driver_sql(
                "INSERT INTO reviewer_0006_unrelated_sentinel VALUES (1, 'preserve-me')"
            )
    finally:
        engine.dispose()
    original_execute = Operations.execute

    def fail_late(
        operations: Operations,
        sqltext: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        rendered = str(sqltext)
        if rendered.startswith(
            "CREATE TRIGGER trg_reviewer_authentication_events_counter_union_guard"
        ):
            raise OperationalError("simulated late 0006 DDL failure", {}, RuntimeError("late"))
        return original_execute(operations, sqltext, *args, **kwargs)

    with monkeypatch.context() as context:
        context.setattr(Operations, "execute", fail_late)
        with pytest.raises(OperationalError, match="simulated late 0006 DDL failure"):
            command.upgrade(config, REVISION_0006)

    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            assert (
                connection.exec_driver_sql(
                    "SELECT marker FROM reviewer_0006_unrelated_sentinel"
                ).scalar_one()
                == "preserve-me"
            )
            objects = {
                (str(row[0]), str(row[1]))
                for row in connection.exec_driver_sql(
                    "SELECT type, name FROM sqlite_master "
                    "WHERE type IN ('table', 'index', 'trigger')"
                )
            }
            assert not ({("table", name) for name in NEW_TABLES} & objects)
            assert not ({("index", name) for name in REQUIRED_INDEXES} & objects)
    finally:
        engine.dispose()
    assert _revision(url) == REVISION_0005

    command.upgrade(config, REVISION_0006)
    assert _revision(url) == REVISION_0006


def test_empty_0006_downgrade_and_reupgrade_is_disposable(
    workspace_tmp_path: Path,
) -> None:
    url = f"sqlite:///{(workspace_tmp_path / 'empty-roundtrip.sqlite3').as_posix()}"
    config = alembic_config(url)
    command.upgrade(config, REVISION_0006)
    command.downgrade(config, REVISION_0005)
    engine = create_engine(url)
    try:
        assert NEW_TABLES.isdisjoint(inspect(engine).get_table_names())
    finally:
        engine.dispose()
    assert _revision(url) == REVISION_0005
    command.upgrade(config, REVISION_0006)
    assert _revision(url) == REVISION_0006


def test_phase_one_public_revision_mask_includes_0006(workspace_tmp_path: Path) -> None:
    url = f"sqlite:///{(workspace_tmp_path / 'public-revision.sqlite3').as_posix()}"
    command.upgrade(alembic_config(url), REVISION_0006)
    engine = create_database_engine(url)
    try:
        repository = SQLiteMetadataRepository(session_factory(engine), engine)
        assert repository.database_revision() == "0001_phase_01"
        assert _revision(url) == REVISION_0006
    finally:
        engine.dispose()


def _foreign_key_groups(
    connection: Any,
    table_name: str,
) -> list[tuple[str, tuple[str, ...], tuple[str, ...]]]:
    rows = connection.exec_driver_sql(f'PRAGMA foreign_key_list("{table_name}")').mappings()
    groups: dict[int, list[Any]] = {}
    for row in rows:
        groups.setdefault(int(row["id"]), []).append(row)
    result = []
    for group in groups.values():
        ordered = sorted(group, key=lambda row: int(row["seq"]))
        result.append(
            (
                str(ordered[0]["table"]),
                tuple(str(row["from"]) for row in ordered),
                tuple(str(row["to"]) for row in ordered),
            )
        )
    return result


def test_authorization_and_outcome_have_exact_trust_columns_and_operation_fks(
    ledger_engine: Engine,
) -> None:
    child_columns = (
        "reviewer_credential_operation_id",
        "operation_content_hash",
        "reviewer_principal_id",
        "reviewer_role",
        "principal_content_hash",
        "os_owner_sid_hash",
        "operation_type",
        "expected_credential_state_hash",
    )
    parent_columns = child_columns
    with ledger_engine.connect() as connection:
        for table_name in (
            "reviewer_webauthn_credential_event_authorizations",
            "reviewer_credential_operation_outcomes",
        ):
            columns = {
                str(row["name"]): row
                for row in connection.exec_driver_sql(
                    f'PRAGMA table_info("{table_name}")'
                ).mappings()
            }
            assert int(columns["reviewer_role"]["notnull"]) == 1
            assert int(columns["principal_content_hash"]["notnull"]) == 1
            assert int(columns["os_owner_sid_hash"]["notnull"]) == 1
            assert (
                "reviewer_credential_operations",
                child_columns,
                parent_columns,
            ) in _foreign_key_groups(connection, table_name)


def test_successful_outcome_authorization_exact_eleven_column_binding(
    ledger_engine: Engine,
) -> None:
    child = (
        "credential_operation_outcome_id",
        "credential_operation_outcome_content_hash",
        "reviewer_credential_operation_id",
        "operation_content_hash",
        "reviewer_principal_id",
        "reviewer_role",
        "principal_content_hash",
        "os_owner_sid_hash",
        "credential_operation_outcome_result",
        "expected_credential_state_hash",
        "resulting_credential_state_hash",
    )
    parent = (
        "credential_operation_outcome_id",
        "outcome_content_hash",
        "reviewer_credential_operation_id",
        "operation_content_hash",
        "reviewer_principal_id",
        "reviewer_role",
        "principal_content_hash",
        "os_owner_sid_hash",
        "terminal_result",
        "expected_credential_state_hash",
        "resulting_credential_state_hash",
    )
    with ledger_engine.connect() as connection:
        assert (
            "reviewer_credential_operation_outcomes",
            child,
            parent,
        ) in _foreign_key_groups(connection, "reviewer_webauthn_credential_event_authorizations")


def test_no_weaker_convenience_operation_identity_index_exists(
    ledger_engine: Engine,
) -> None:
    forbidden = {
        (
            "reviewer_credential_operation_id",
            "operation_content_hash",
            "reviewer_principal_id",
            "operation_type",
            "expected_credential_state_hash",
        ),
        (
            "reviewer_credential_operation_id",
            "operation_content_hash",
            "reviewer_principal_id",
            "expected_credential_state_hash",
        ),
    }
    with ledger_engine.connect() as connection:
        unique_indexes = [
            row
            for row in connection.exec_driver_sql(
                "PRAGMA index_list('reviewer_credential_operations')"
            ).mappings()
            if int(row["unique"]) == 1
        ]
        unique_columns = {
            tuple(
                str(info["name"])
                for info in connection.exec_driver_sql(
                    f"PRAGMA index_info('{row['name']}')"
                ).mappings()
            )
            for row in unique_indexes
        }
    assert forbidden.isdisjoint(unique_columns)


def test_authorization_kind_is_exact_four_token_five_row_matrix(
    ledger_engine: Engine,
) -> None:
    with ledger_engine.connect() as connection:
        sql = str(
            connection.exec_driver_sql(
                "SELECT sql FROM sqlite_master WHERE type='table' "
                "AND name='reviewer_webauthn_credential_event_authorizations'"
            ).scalar_one()
        )
    for token in (
        "BOOTSTRAP_REGISTRATION",
        "AUTHORIZED_REGISTRATION",
        "AUTHORIZED_SUPERSESSION",
        "AUTHORIZED_REVOCATION",
    ):
        assert token in sql
    assert "AUTHORIZED_LIFECYCLE" not in sql
    for exact_row in (
        "operation_type = 'FIRST_ENROLLMENT' AND event_type = 'REGISTERED' "
        "AND authorization_kind = 'BOOTSTRAP_REGISTRATION'",
        "operation_type = 'ADD_CREDENTIAL' AND event_type = 'REGISTERED' "
        "AND authorization_kind = 'AUTHORIZED_REGISTRATION'",
        "operation_type = 'REPLACE_CREDENTIAL' AND event_type = 'REGISTERED' "
        "AND authorization_kind = 'AUTHORIZED_REGISTRATION'",
        "operation_type = 'REPLACE_CREDENTIAL' AND event_type = 'SUPERSEDED' "
        "AND authorization_kind = 'AUTHORIZED_SUPERSESSION'",
        "operation_type = 'REVOKE_CREDENTIAL' AND event_type = 'REVOKED' "
        "AND authorization_kind = 'AUTHORIZED_REVOCATION'",
    ):
        assert exact_row in sql


@pytest.mark.parametrize(
    "table_name",
    [
        "reviewer_credential_operations",
        "reviewer_credential_operation_challenges",
        "reviewer_credential_operation_challenge_consumptions",
        "reviewer_credential_operation_authentication_events",
        "reviewer_webauthn_credential_event_authorizations",
        "reviewer_credential_operation_outcomes",
    ],
)
def test_every_new_table_has_append_only_update_and_delete_triggers(
    ledger_engine: Engine,
    table_name: str,
) -> None:
    with ledger_engine.connect() as connection:
        triggers = {
            str(row[0])
            for row in connection.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name=:table_name",
                {"table_name": table_name},
            )
        }
    assert f"trg_{table_name}_append_only_update" in triggers
    assert f"trg_{table_name}_append_only_delete" in triggers


def _canonical_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


@pytest.mark.parametrize(
    "contract_kind",
    ["authorization", "outcome"],
)
@pytest.mark.parametrize(
    "field",
    ["reviewer_role", "principal_content_hash", "os_owner_sid_hash"],
)
def test_amended_trust_fields_are_in_immutable_hash_preimage_vectors(
    contract_kind: str,
    field: str,
) -> None:
    payload = {
        "contract_version": f"reviewer-{contract_kind}/0.1.0",
        "reviewer_credential_operation_id": "operation-vector",
        "operation_content_hash": _h("operation-vector"),
        "reviewer_principal_id": "principal-vector",
        "reviewer_role": "LOCAL_DATA_STEWARD",
        "principal_content_hash": _h("principal-vector"),
        "os_owner_sid_hash": _h("sid-vector"),
        "operation_type": "REVOKE_CREDENTIAL",
        "expected_credential_state_hash": _h("state-before"),
        "resulting_credential_state_hash": _h("state-after"),
    }
    baseline = _canonical_hash(payload)
    mutated = dict(payload)
    mutated[field] = f"mutated-{payload[field]}"
    assert _canonical_hash(mutated) != baseline


def test_schema_has_no_sqlite_sha_function_dependency(ledger_engine: Engine) -> None:
    with ledger_engine.connect() as connection:
        schema_sql = "\n".join(
            str(row[0] or "")
            for row in connection.exec_driver_sql(
                "SELECT sql FROM sqlite_master WHERE sql IS NOT NULL"
            )
        ).lower()
    migration_source = REVISION_0006_PATH.read_text(encoding="utf-8").lower()
    assert "sha256(" not in schema_sql
    assert "sha256(" not in migration_source


def test_operation_and_initial_challenge_commit_atomically(ledger_engine: Engine) -> None:
    principal = _seed_principal(ledger_engine)
    operation = _operation_values(
        principal,
        suffix="orphan-operation",
        operation_type="FIRST_ENROLLMENT",
        expected_state=_h("empty"),
    )
    with pytest.raises(IntegrityError):
        with ledger_engine.begin() as connection:
            connection.execute(OPERATION_INSERT, operation)

    with pytest.raises(DBAPIError, match="exact operation copy mismatch"):
        with ledger_engine.begin() as connection:
            connection.execute(CHALLENGE_INSERT, _challenge_values(operation))

    valid = _issue_operation(
        ledger_engine,
        principal,
        suffix="atomic-valid",
        operation_type="FIRST_ENROLLMENT",
        expected_state=_h("empty"),
    )
    with ledger_engine.connect() as connection:
        assert (
            connection.execute(
                text(
                    "SELECT initial_challenge_id FROM reviewer_credential_operations "
                    "WHERE reviewer_credential_operation_id=:operation_id"
                ),
                valid,
            ).scalar_one()
            == valid["challenge_id"]
        )


def test_challenge_fresh_32_bytes_and_maximum_five_minute_expiry(
    ledger_engine: Engine,
) -> None:
    principal = _seed_principal(ledger_engine)
    operation = _operation_values(
        principal,
        suffix="expiry-too-long",
        operation_type="FIRST_ENROLLMENT",
        expected_state=_h("empty"),
    )
    challenge = _challenge_values(
        operation,
        expires_at="2026-08-28T00:06:00.001Z",
    )
    with pytest.raises(IntegrityError):
        with ledger_engine.begin() as connection:
            connection.execute(OPERATION_INSERT, operation)
            connection.execute(CHALLENGE_INSERT, challenge)

    valid = _issue_operation(
        ledger_engine,
        principal,
        suffix="expiry-valid",
        operation_type="FIRST_ENROLLMENT",
        expected_state=_h("empty"),
    )
    with ledger_engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT challenge_nonce_length, issued_at, expires_at "
                "FROM reviewer_credential_operation_challenges "
                "WHERE reviewer_credential_operation_challenge_id=:challenge_id"
            ),
            valid,
        ).one()
    assert tuple(row) == (32, "2026-08-28T00:01:00Z", "2026-08-28T00:06:00Z")


def test_first_enrollment_success_has_exact_relational_registration_proof(
    ledger_engine: Engine,
) -> None:
    principal, operation, credential, outcome = _seed_first_credential(ledger_engine)
    with ledger_engine.connect() as connection:
        assert _active_credentials(connection, principal["principal_id"]) == (
            credential["credential_id"],
        )
        authorization = connection.execute(
            text(
                "SELECT authorization_kind, credential_operation_outcome_id, "
                "reviewer_role, principal_content_hash, os_owner_sid_hash "
                "FROM reviewer_webauthn_credential_event_authorizations"
            )
        ).one()
        assert tuple(authorization) == (
            "BOOTSTRAP_REGISTRATION",
            outcome["outcome_id"],
            "LOCAL_DATA_STEWARD",
            principal["principal_hash"],
            principal["sid_hash"],
        )
        assert (
            connection.execute(
                text("SELECT terminal_result FROM reviewer_credential_operation_outcomes")
            ).scalar_one()
            == "SUCCEEDED"
        )
        assert tuple(connection.exec_driver_sql("PRAGMA foreign_key_check")) == ()
    assert operation["operation_type"] == "FIRST_ENROLLMENT"


def test_failed_first_enrollment_consumes_and_terminalizes_without_synthetic_state(
    ledger_engine: Engine,
) -> None:
    principal = _seed_principal(ledger_engine)
    empty_state = _h("failed-first-empty")
    operation = _issue_operation(
        ledger_engine,
        principal,
        suffix="failed-first",
        operation_type="FIRST_ENROLLMENT",
        expected_state=empty_state,
    )
    consumption, outcome = _terminalize_failure(
        ledger_engine,
        operation,
        operation["initial_challenge"],
        suffix="failed-first",
        terminal_result="INVALID_REGISTRATION",
    )
    with ledger_engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT COUNT(*) FROM reviewer_webauthn_credentials")
            ).scalar_one()
            == 0
        )
        assert (
            connection.execute(
                text("SELECT COUNT(*) FROM reviewer_webauthn_credential_events")
            ).scalar_one()
            == 0
        )
        assert (
            connection.execute(
                text("SELECT COUNT(*) FROM reviewer_webauthn_credential_event_authorizations")
            ).scalar_one()
            == 0
        )
        assert connection.execute(
            text(
                "SELECT expected_credential_state_hash, resulting_credential_state_hash, "
                "terminal_result FROM reviewer_credential_operation_outcomes"
            )
        ).one() == (empty_state, empty_state, "REJECTED")
    assert consumption["outcome_id"] == outcome["outcome_id"]


def test_terminal_consumption_without_outcome_is_uncommittable(
    ledger_engine: Engine,
) -> None:
    principal = _seed_principal(ledger_engine)
    operation = _issue_operation(
        ledger_engine,
        principal,
        suffix="missing-outcome",
        operation_type="FIRST_ENROLLMENT",
        expected_state=_h("missing-outcome-empty"),
    )
    consumption = _consumption_values(
        operation,
        operation["initial_challenge"],
        suffix="missing-outcome",
        terminal_result="INVALID_REGISTRATION",
        resulting_state=str(operation["expected_state"]),
        outcome_id="outcome-never-inserted",
    )
    with pytest.raises(IntegrityError):
        with ledger_engine.begin() as connection:
            connection.execute(CONSUMPTION_INSERT, consumption)
    with ledger_engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT COUNT(*) FROM reviewer_credential_operation_challenge_consumptions")
            ).scalar_one()
            == 0
        )


def test_one_challenge_has_at_most_one_consumption(ledger_engine: Engine) -> None:
    principal = _seed_principal(ledger_engine)
    operation = _issue_operation(
        ledger_engine,
        principal,
        suffix="single-consumption",
        operation_type="FIRST_ENROLLMENT",
        expected_state=_h("single-empty"),
    )
    _terminalize_failure(
        ledger_engine,
        operation,
        operation["initial_challenge"],
        suffix="single-consumption-first",
        terminal_result="INVALID_REGISTRATION",
    )
    duplicate = _consumption_values(
        operation,
        operation["initial_challenge"],
        suffix="single-consumption-second",
        terminal_result="INVALID_REGISTRATION",
        resulting_state=str(operation["expected_state"]),
        outcome_id="outcome-second",
    )
    with pytest.raises(DBAPIError, match="already consumed"):
        with ledger_engine.begin() as connection:
            connection.execute(CONSUMPTION_INSERT, duplicate)


def test_exact_expiry_instant_must_terminalize_as_expired(ledger_engine: Engine) -> None:
    principal = _seed_principal(ledger_engine)
    operation = _issue_operation(
        ledger_engine,
        principal,
        suffix="exact-expiry",
        operation_type="FIRST_ENROLLMENT",
        expected_state=_h("expiry-empty"),
    )
    with pytest.raises(DBAPIError, match="expiry instant/result mismatch"):
        invalid = _consumption_values(
            operation,
            operation["initial_challenge"],
            suffix="exact-expiry-invalid",
            terminal_result="INVALID_REGISTRATION",
            resulting_state=str(operation["expected_state"]),
            outcome_id="outcome-expiry-invalid",
            consumed_at="2026-08-28T00:06:00Z",
        )
        with ledger_engine.begin() as connection:
            connection.execute(CONSUMPTION_INSERT, invalid)

    consumption, outcome = _terminalize_failure(
        ledger_engine,
        operation,
        operation["initial_challenge"],
        suffix="exact-expiry-valid",
        terminal_result="EXPIRED",
        consumed_at="2026-08-28T00:06:00Z",
    )
    assert consumption["terminal_result"] == "EXPIRED"
    assert outcome["outcome_result"] == "EXPIRED"


def test_failed_outcome_cannot_change_credential_state(ledger_engine: Engine) -> None:
    principal = _seed_principal(ledger_engine)
    operation = _issue_operation(
        ledger_engine,
        principal,
        suffix="failed-state-mismatch",
        operation_type="FIRST_ENROLLMENT",
        expected_state=_h("expected-empty"),
    )
    consumption = _consumption_values(
        operation,
        operation["initial_challenge"],
        suffix="failed-state-mismatch",
        terminal_result="INVALID_REGISTRATION",
        resulting_state=_h("invented-different-state"),
        outcome_id="outcome-state-mismatch",
    )
    with pytest.raises(IntegrityError):
        with ledger_engine.begin() as connection:
            connection.execute(CONSUMPTION_INSERT, consumption)


def test_public_credential_without_registration_proof_is_rejected(
    ledger_engine: Engine,
) -> None:
    principal = _seed_principal(ledger_engine)
    credential = _credential_values(principal, suffix="unproved")
    with pytest.raises(DBAPIError, match="requires exact successful registration proof"):
        with ledger_engine.begin() as connection:
            connection.execute(CREDENTIAL_INSERT, credential)


def test_lifecycle_event_without_authorization_is_rejected(ledger_engine: Engine) -> None:
    principal, _operation, credential, _outcome = _seed_first_credential(ledger_engine)
    event = _event_values(
        credential,
        event_id="credential-event-unapproved",
        event_hash=_h("credential-event-unapproved"),
        event_type="REVOKED",
        predecessor_event_id=str(credential["root_event_id"]),
    )
    with pytest.raises(DBAPIError, match="requires exact authorization companion"):
        with ledger_engine.begin() as connection:
            connection.execute(EVENT_INSERT, event)
    assert principal["principal_id"] == credential["principal_id"]


@pytest.mark.parametrize(
    "broken_fields",
    [
        {"prerequisite_auth_id": "partial"},
        {"prerequisite_auth_hash": _h("partial")},
        {"prerequisite_auth_result": "VERIFIED"},
    ],
)
def test_malformed_nullable_prerequisite_groups_are_rejected(
    ledger_engine: Engine,
    broken_fields: dict[str, Any],
) -> None:
    principal = _seed_principal(ledger_engine)
    operation = _operation_values(
        principal,
        suffix="nullable-group",
        operation_type="FIRST_ENROLLMENT",
        expected_state=_h("nullable-empty"),
    )
    challenge = _challenge_values(operation)
    challenge.update(broken_fields)
    with pytest.raises(IntegrityError):
        with ledger_engine.begin() as connection:
            connection.execute(OPERATION_INSERT, operation)
            connection.execute(CHALLENGE_INSERT, challenge)


@pytest.mark.parametrize(
    ("terminal_result", "expected_outcome"),
    [
        ("EXPIRED", "EXPIRED"),
        ("INVALID_SIGNATURE", "REJECTED"),
        ("USER_PRESENCE_ABSENT", "REJECTED"),
        ("USER_VERIFICATION_ABSENT", "REJECTED"),
        ("BINDING_MISMATCH", "FAILED_CLOSED"),
        ("ORIGIN_RP_MISMATCH", "FAILED_CLOSED"),
        ("COUNTER_REJECTED", "FAILED_CLOSED"),
        ("REPLAY_REJECTED", "FAILED_CLOSED"),
        ("FAILED_CLOSED", "FAILED_CLOSED"),
    ],
)
def test_assertion_failure_result_mapping_is_closed_and_state_preserving(
    ledger_engine: Engine,
    terminal_result: str,
    expected_outcome: str,
) -> None:
    principal, first_operation, credential, first_outcome = _seed_first_credential(ledger_engine)
    operation = _issue_operation(
        ledger_engine,
        principal,
        suffix=f"mapped-{terminal_result.lower()}",
        operation_type="REVOKE_CREDENTIAL",
        expected_state=str(first_outcome["resulting_state"]),
        predecessor_id=str(first_operation["operation_id"]),
        target=credential,
    )
    before_events: int
    with ledger_engine.connect() as connection:
        before_events = int(
            connection.execute(
                text("SELECT COUNT(*) FROM reviewer_webauthn_credential_events")
            ).scalar_one()
        )
    consumed_at = "2026-08-28T00:06:00Z" if terminal_result == "EXPIRED" else "2026-08-28T00:05:59Z"
    _consumption, outcome = _terminalize_failure(
        ledger_engine,
        operation,
        operation["initial_challenge"],
        suffix=f"mapped-{terminal_result.lower()}",
        terminal_result=terminal_result,
        consumed_at=consumed_at,
    )
    with ledger_engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT terminal_result, expected_credential_state_hash, "
                "resulting_credential_state_hash FROM reviewer_credential_operation_outcomes "
                "WHERE credential_operation_outcome_id=:outcome_id"
            ),
            outcome,
        ).one()
        assert tuple(row) == (
            expected_outcome,
            operation["expected_state"],
            operation["expected_state"],
        )
        assert (
            connection.execute(
                text("SELECT COUNT(*) FROM reviewer_webauthn_credential_events")
            ).scalar_one()
            == before_events
        )
        assert _active_credentials(connection, principal["principal_id"]) == (
            credential["credential_id"],
        )


def test_invalid_signature_appends_attributable_rejected_audit_and_outcome(
    ledger_engine: Engine,
) -> None:
    principal, first_operation, credential, first_outcome = _seed_first_credential(ledger_engine)
    operation = _issue_operation(
        ledger_engine,
        principal,
        suffix="invalid-signature-audit",
        operation_type="REVOKE_CREDENTIAL",
        expected_state=str(first_outcome["resulting_state"]),
        predecessor_id=str(first_operation["operation_id"]),
        target=credential,
    )
    consumption = _consumption_values(
        operation,
        operation["initial_challenge"],
        suffix="invalid-signature-audit",
        terminal_result="INVALID_SIGNATURE",
        resulting_state=str(operation["expected_state"]),
        outcome_id="outcome-invalid-signature-audit",
    )
    auth = _operation_auth_values(
        operation,
        operation["initial_challenge"],
        consumption,
        credential,
        suffix="invalid-signature-audit",
        previous_sign_count=5,
        asserted_sign_count=5,
        authentication_result="REJECTED",
    )
    outcome = _outcome_values(
        operation,
        consumption,
        suffix="invalid-signature-audit",
        auth=auth,
    )
    with ledger_engine.begin() as connection:
        connection.execute(CONSUMPTION_INSERT, consumption)
        connection.execute(OPERATION_AUTH_INSERT, auth)
        connection.execute(OUTCOME_INSERT, outcome)
    with ledger_engine.connect() as connection:
        assert (
            connection.execute(
                text(
                    "SELECT authentication_result FROM "
                    "reviewer_credential_operation_authentication_events"
                )
            ).scalar_one()
            == "REJECTED"
        )
        assert (
            connection.execute(
                text(
                    "SELECT terminal_result FROM reviewer_credential_operation_outcomes "
                    "WHERE credential_operation_outcome_id=:outcome_id"
                ),
                outcome,
            ).scalar_one()
            == "REJECTED"
        )


def test_first_enrollment_retry_requires_linear_failed_predecessor(
    ledger_engine: Engine,
) -> None:
    principal = _seed_principal(ledger_engine)
    empty_state = _h("retry-empty")
    first = _issue_operation(
        ledger_engine,
        principal,
        suffix="retry-first",
        operation_type="FIRST_ENROLLMENT",
        expected_state=empty_state,
    )
    _consumption, failed_outcome = _terminalize_failure(
        ledger_engine,
        first,
        first["initial_challenge"],
        suffix="retry-first",
        terminal_result="INVALID_REGISTRATION",
    )
    retry = _issue_operation(
        ledger_engine,
        principal,
        suffix="retry-second",
        operation_type="FIRST_ENROLLMENT",
        expected_state=str(failed_outcome["resulting_state"]),
        predecessor_id=str(first["operation_id"]),
    )
    assert retry["predecessor_id"] == first["operation_id"]
    competing = _operation_values(
        principal,
        suffix="retry-competing",
        operation_type="FIRST_ENROLLMENT",
        expected_state=empty_state,
        predecessor_id=str(first["operation_id"]),
    )
    with pytest.raises(DBAPIError, match="already has successor"):
        with ledger_engine.begin() as connection:
            connection.execute(OPERATION_INSERT, competing)


def test_first_enrollment_never_restarts_after_historical_success(
    ledger_engine: Engine,
) -> None:
    principal, first_operation, _credential, first_outcome = _seed_first_credential(ledger_engine)
    attempted = _operation_values(
        principal,
        suffix="bootstrap-again",
        operation_type="FIRST_ENROLLMENT",
        expected_state=str(first_outcome["resulting_state"]),
        predecessor_id=str(first_operation["operation_id"]),
    )
    with pytest.raises(DBAPIError, match="permanently closed"):
        with ledger_engine.begin() as connection:
            connection.execute(OPERATION_INSERT, attempted)


def test_add_authorization_binds_consumption_verified_event_and_one_continuation(
    ledger_engine: Engine,
) -> None:
    principal, first_operation, credential, first_outcome = _seed_first_credential(ledger_engine)
    operation = _issue_operation(
        ledger_engine,
        principal,
        suffix="add-continuation",
        operation_type="ADD_CREDENTIAL",
        expected_state=str(first_outcome["resulting_state"]),
        predecessor_id=str(first_operation["operation_id"]),
    )
    auth, continuation, consumption = _authorize_management(
        ledger_engine,
        operation,
        credential,
        suffix="add-continuation",
        previous_sign_count=5,
        asserted_sign_count=6,
    )
    with ledger_engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT continuation_challenge_id, continuation_challenge_purpose "
                "FROM reviewer_credential_operation_challenge_consumptions "
                "WHERE challenge_consumption_id=:consumption_id"
            ),
            consumption,
        ).one()
        assert tuple(row) == (continuation["challenge_id"], "REGISTRATION_CREATE")
        assert (
            connection.execute(
                text(
                    "SELECT prerequisite_authentication_event_id FROM "
                    "reviewer_credential_operation_challenges "
                    "WHERE reviewer_credential_operation_challenge_id=:challenge_id"
                ),
                continuation,
            ).scalar_one()
            == auth["auth_id"]
        )
        assert (
            connection.execute(
                text(
                    "SELECT COUNT(*) FROM reviewer_credential_operation_challenges "
                    "WHERE reviewer_credential_operation_id=:operation_id "
                    "AND challenge_purpose='REGISTRATION_CREATE'"
                ),
                operation,
            ).scalar_one()
            == 1
        )


def test_second_add_or_replace_continuation_is_rejected(ledger_engine: Engine) -> None:
    principal, first_operation, credential, first_outcome = _seed_first_credential(ledger_engine)
    operation = _issue_operation(
        ledger_engine,
        principal,
        suffix="second-continuation",
        operation_type="ADD_CREDENTIAL",
        expected_state=str(first_outcome["resulting_state"]),
        predecessor_id=str(first_operation["operation_id"]),
    )
    auth, _continuation, _consumption = _authorize_management(
        ledger_engine,
        operation,
        credential,
        suffix="second-continuation",
        previous_sign_count=5,
        asserted_sign_count=6,
    )
    second = _challenge_values(
        operation,
        challenge_id="challenge-second-registration",
        purpose="REGISTRATION_CREATE",
        prerequisite=auth,
        issued_at="2026-08-28T00:03:00Z",
        expires_at="2026-08-28T00:08:00Z",
    )
    with pytest.raises(DBAPIError):
        with ledger_engine.begin() as connection:
            connection.execute(CHALLENGE_INSERT, second)


def test_continuation_cannot_commit_without_verified_operation_authentication(
    ledger_engine: Engine,
) -> None:
    principal, first_operation, credential, first_outcome = _seed_first_credential(ledger_engine)
    operation = _issue_operation(
        ledger_engine,
        principal,
        suffix="missing-verified-auth",
        operation_type="ADD_CREDENTIAL",
        expected_state=str(first_outcome["resulting_state"]),
        predecessor_id=str(first_operation["operation_id"]),
    )
    fake_auth = {
        "auth_id": "missing-auth-event",
        "auth_hash": _h("missing-auth-event"),
    }
    continuation = _challenge_values(
        operation,
        challenge_id="challenge-missing-auth-registration",
        purpose="REGISTRATION_CREATE",
        prerequisite=fake_auth,
        issued_at="2026-08-28T00:03:00Z",
        expires_at="2026-08-28T00:08:00Z",
    )
    with pytest.raises(DBAPIError, match="requires exact verified"):
        with ledger_engine.begin() as connection:
            connection.execute(CHALLENGE_INSERT, continuation)


def test_registration_failure_preserves_verified_counter_event_and_state(
    ledger_engine: Engine,
) -> None:
    principal, first_operation, credential, first_outcome = _seed_first_credential(ledger_engine)
    operation = _issue_operation(
        ledger_engine,
        principal,
        suffix="add-registration-fails",
        operation_type="ADD_CREDENTIAL",
        expected_state=str(first_outcome["resulting_state"]),
        predecessor_id=str(first_operation["operation_id"]),
    )
    auth, continuation, _assertion = _authorize_management(
        ledger_engine,
        operation,
        credential,
        suffix="add-registration-fails",
        previous_sign_count=5,
        asserted_sign_count=6,
    )
    _consumption, failed_outcome = _terminalize_failure(
        ledger_engine,
        operation,
        continuation,
        suffix="add-registration-fails",
        terminal_result="INVALID_REGISTRATION",
        auth=auth,
    )
    with ledger_engine.connect() as connection:
        assert connection.execute(
            text(
                "SELECT previous_sign_count, asserted_sign_count, authentication_result "
                "FROM reviewer_credential_operation_authentication_events"
            )
        ).one() == (5, 6, "VERIFIED")
        assert _active_credentials(connection, principal["principal_id"]) == (
            credential["credential_id"],
        )
        assert (
            connection.execute(
                text("SELECT COUNT(*) FROM reviewer_webauthn_credentials")
            ).scalar_one()
            == 1
        )
        assert failed_outcome["resulting_state"] == first_outcome["resulting_state"]


def test_successor_after_failed_registration_uses_resulting_state_after_restart(
    ledger_engine: Engine,
) -> None:
    principal, first_operation, credential, first_outcome = _seed_first_credential(ledger_engine)
    failed_operation = _issue_operation(
        ledger_engine,
        principal,
        suffix="restart-failed-add",
        operation_type="ADD_CREDENTIAL",
        expected_state=str(first_outcome["resulting_state"]),
        predecessor_id=str(first_operation["operation_id"]),
    )
    auth, continuation, _assertion = _authorize_management(
        ledger_engine,
        failed_operation,
        credential,
        suffix="restart-failed-add",
        previous_sign_count=5,
        asserted_sign_count=6,
    )
    _consumption, failed_outcome = _terminalize_failure(
        ledger_engine,
        failed_operation,
        continuation,
        suffix="restart-failed-add",
        terminal_result="INVALID_REGISTRATION",
        auth=auth,
    )
    ledger_engine.dispose()
    restarted = create_database_engine(str(ledger_engine.url))
    try:
        successor = _issue_operation(
            restarted,
            principal,
            suffix="restart-successor",
            operation_type="ADD_CREDENTIAL",
            expected_state=str(failed_outcome["resulting_state"]),
            predecessor_id=str(failed_operation["operation_id"]),
        )
        assert successor["expected_state"] == failed_outcome["resulting_state"]
    finally:
        restarted.dispose()


def test_successful_add_registers_one_new_active_credential(
    ledger_engine: Engine,
) -> None:
    principal, first_operation, first_credential, first_outcome = _seed_first_credential(
        ledger_engine
    )
    operation = _issue_operation(
        ledger_engine,
        principal,
        suffix="add-success",
        operation_type="ADD_CREDENTIAL",
        expected_state=str(first_outcome["resulting_state"]),
        predecessor_id=str(first_operation["operation_id"]),
    )
    auth, continuation, _assertion = _authorize_management(
        ledger_engine,
        operation,
        first_credential,
        suffix="add-success",
        previous_sign_count=5,
        asserted_sign_count=6,
    )
    added_credential, outcome = _complete_registration(
        ledger_engine,
        operation,
        continuation,
        principal,
        suffix="added",
        resulting_state=_h("two-active-credentials"),
        auth=auth,
    )
    with ledger_engine.connect() as connection:
        assert _active_credentials(connection, principal["principal_id"]) == tuple(
            sorted((first_credential["credential_id"], added_credential["credential_id"]))
        )
        assert (
            connection.execute(
                text(
                    "SELECT authorization_kind FROM "
                    "reviewer_webauthn_credential_event_authorizations "
                    "WHERE reviewer_credential_operation_id=:operation_id"
                ),
                operation,
            ).scalar_one()
            == "AUTHORIZED_REGISTRATION"
        )
        assert (
            connection.execute(
                text(
                    "SELECT terminal_result FROM reviewer_credential_operation_outcomes "
                    "WHERE credential_operation_outcome_id=:outcome_id"
                ),
                outcome,
            ).scalar_one()
            == "SUCCEEDED"
        )
        assert tuple(connection.exec_driver_sql("PRAGMA foreign_key_check")) == ()


def test_successful_replace_requires_registered_and_superseded_atomic_pattern(
    ledger_engine: Engine,
) -> None:
    principal, first_operation, old_credential, first_outcome = _seed_first_credential(
        ledger_engine
    )
    operation = _issue_operation(
        ledger_engine,
        principal,
        suffix="replace-success",
        operation_type="REPLACE_CREDENTIAL",
        expected_state=str(first_outcome["resulting_state"]),
        predecessor_id=str(first_operation["operation_id"]),
        target=old_credential,
    )
    auth, continuation, _assertion = _authorize_management(
        ledger_engine,
        operation,
        old_credential,
        suffix="replace-success",
        previous_sign_count=5,
        asserted_sign_count=6,
    )
    new_credential, outcome = _complete_registration(
        ledger_engine,
        operation,
        continuation,
        principal,
        suffix="replacement",
        resulting_state=_h("replacement-active-state"),
        auth=auth,
        replace_target=old_credential,
    )
    with ledger_engine.connect() as connection:
        assert _active_credentials(connection, principal["principal_id"]) == (
            new_credential["credential_id"],
        )
        rows = tuple(
            connection.execute(
                text(
                    "SELECT event_type, authorization_kind, webauthn_credential_id "
                    "FROM reviewer_webauthn_credential_event_authorizations "
                    "WHERE reviewer_credential_operation_id=:operation_id "
                    "ORDER BY event_type"
                ),
                operation,
            )
        )
        assert rows == (
            (
                "REGISTERED",
                "AUTHORIZED_REGISTRATION",
                new_credential["credential_id"],
            ),
            (
                "SUPERSEDED",
                "AUTHORIZED_SUPERSESSION",
                old_credential["credential_id"],
            ),
        )
        assert (
            connection.execute(
                text(
                    "SELECT terminal_result FROM reviewer_credential_operation_outcomes "
                    "WHERE credential_operation_outcome_id=:outcome_id"
                ),
                outcome,
            ).scalar_one()
            == "SUCCEEDED"
        )


def test_incomplete_replace_cannot_commit_new_registration(
    ledger_engine: Engine,
) -> None:
    principal, first_operation, old_credential, first_outcome = _seed_first_credential(
        ledger_engine
    )
    operation = _issue_operation(
        ledger_engine,
        principal,
        suffix="replace-incomplete",
        operation_type="REPLACE_CREDENTIAL",
        expected_state=str(first_outcome["resulting_state"]),
        predecessor_id=str(first_operation["operation_id"]),
        target=old_credential,
    )
    auth, continuation, _assertion = _authorize_management(
        ledger_engine,
        operation,
        old_credential,
        suffix="replace-incomplete",
        previous_sign_count=5,
        asserted_sign_count=6,
    )
    new_credential = _credential_values(principal, suffix="incomplete-replacement")
    event_id = "credential-event-incomplete-replacement-registered"
    event_hash = _h(event_id)
    new_credential["root_event_id"] = event_id
    new_credential["root_event_hash"] = event_hash
    outcome_id = "outcome-incomplete-replace"
    outcome_hash = _h(outcome_id)
    resulting_state = _h("incomplete-replace-state")
    consumption = _consumption_values(
        operation,
        continuation,
        suffix="incomplete-replace-registration",
        terminal_result="SUCCEEDED",
        resulting_state=resulting_state,
        outcome_id=outcome_id,
        credential=new_credential,
    )
    authorization = _authorization_values(
        operation,
        new_credential,
        event_id=event_id,
        event_hash=event_hash,
        event_type="REGISTERED",
        authorization_kind="AUTHORIZED_REGISTRATION",
        outcome_id=outcome_id,
        outcome_hash=outcome_hash,
        resulting_state=resulting_state,
        registration_consumption=consumption,
        auth=auth,
    )
    event = _event_values(
        new_credential,
        event_id=event_id,
        event_hash=event_hash,
        event_type="REGISTERED",
        predecessor_event_id=None,
    )
    outcome = _outcome_values(
        operation,
        consumption,
        suffix="incomplete-replace",
        outcome_hash=outcome_hash,
        auth=auth,
    )
    with pytest.raises(DBAPIError, match="registered plus superseded"):
        with ledger_engine.begin() as connection:
            connection.execute(CONSUMPTION_INSERT, consumption)
            connection.execute(AUTHORIZATION_INSERT, authorization)
            connection.execute(CREDENTIAL_INSERT, new_credential)
            connection.execute(EVENT_INSERT, event)
            connection.execute(OUTCOME_INSERT, outcome)
    with ledger_engine.connect() as connection:
        assert _active_credentials(connection, principal["principal_id"]) == (
            old_credential["credential_id"],
        )
        assert (
            connection.execute(
                text(
                    "SELECT COUNT(*) FROM reviewer_webauthn_credentials "
                    "WHERE webauthn_credential_id=:credential_id"
                ),
                new_credential,
            ).scalar_one()
            == 0
        )


def test_authenticated_final_revoke_produces_exact_relational_empty_state(
    ledger_engine: Engine,
) -> None:
    principal, first_operation, credential, first_outcome = _seed_first_credential(ledger_engine)
    operation = _issue_operation(
        ledger_engine,
        principal,
        suffix="final-revoke",
        operation_type="REVOKE_CREDENTIAL",
        expected_state=str(first_outcome["resulting_state"]),
        predecessor_id=str(first_operation["operation_id"]),
        target=credential,
    )
    empty_state = _h("principal-specific-final-empty-state")
    _auth, outcome = _complete_revoke(
        ledger_engine,
        operation,
        credential,
        suffix="final",
        resulting_state=empty_state,
        previous_sign_count=5,
        asserted_sign_count=6,
    )
    with ledger_engine.connect() as connection:
        assert _active_credentials(connection, principal["principal_id"]) == ()
        assert (
            connection.execute(
                text(
                    "SELECT event_type FROM reviewer_webauthn_credential_events "
                    "WHERE supersedes_credential_event_id=:root_event_id"
                ),
                credential,
            ).scalar_one()
            == "REVOKED"
        )
        assert (
            connection.execute(
                text(
                    "SELECT resulting_credential_state_hash FROM "
                    "reviewer_credential_operation_outcomes "
                    "WHERE credential_operation_outcome_id=:outcome_id"
                ),
                outcome,
            ).scalar_one()
            == empty_state
        )
        assert (
            connection.execute(
                text(
                    "SELECT authorization_kind FROM "
                    "reviewer_webauthn_credential_event_authorizations "
                    "WHERE reviewer_credential_operation_id=:operation_id"
                ),
                operation,
            ).scalar_one()
            == "AUTHORIZED_REVOCATION"
        )
        assert tuple(connection.exec_driver_sql("PRAGMA foreign_key_check")) == ()

    for suffix, operation_type, target in (
        ("post-final-add", "ADD_CREDENTIAL", None),
        ("post-final-replace", "REPLACE_CREDENTIAL", credential),
        ("post-final-revoke", "REVOKE_CREDENTIAL", credential),
        ("post-final-bootstrap", "FIRST_ENROLLMENT", None),
    ):
        blocked = _operation_values(
            principal,
            suffix=suffix,
            operation_type=operation_type,
            expected_state=empty_state,
            predecessor_id=str(operation["operation_id"]),
            target=target,
        )
        with pytest.raises(DBAPIError):
            with ledger_engine.begin() as connection:
                connection.execute(OPERATION_INSERT, blocked)


def test_operation_enum_has_no_recovery_reset_force_or_override_path(
    ledger_engine: Engine,
) -> None:
    principal = _seed_principal(ledger_engine)
    for forbidden in ("RECOVERY", "RESET", "FORCE", "OVERRIDE"):
        operation = _operation_values(
            principal,
            suffix=f"forbidden-{forbidden.lower()}",
            operation_type=forbidden,
            expected_state=_h("forbidden-empty"),
        )
        with pytest.raises(IntegrityError):
            with ledger_engine.begin() as connection:
                connection.execute(OPERATION_INSERT, operation)


def test_nonempty_0006_audit_ledger_refuses_destructive_downgrade(
    workspace_tmp_path: Path,
) -> None:
    url = f"sqlite:///{(workspace_tmp_path / 'nonempty-downgrade.sqlite3').as_posix()}"
    config = alembic_config(url)
    command.upgrade(config, REVISION_0006)
    engine = create_database_engine(url)
    try:
        principal = _seed_principal(engine)
        _issue_operation(
            engine,
            principal,
            suffix="nonempty-downgrade",
            operation_type="FIRST_ENROLLMENT",
            expected_state=_h("nonempty-downgrade-empty"),
        )
    finally:
        engine.dispose()
    with pytest.raises(RuntimeError, match="destructive downgrade refused"):
        command.downgrade(config, REVISION_0005)
    assert _revision(url) == REVISION_0006


def test_credential_operation_counter_union_accepts_exact_linear_chain(
    ledger_engine: Engine,
) -> None:
    principal, first_operation, credential, first_outcome = _seed_first_credential(ledger_engine)
    first_add = _issue_operation(
        ledger_engine,
        principal,
        suffix="counter-chain-one",
        operation_type="ADD_CREDENTIAL",
        expected_state=str(first_outcome["resulting_state"]),
        predecessor_id=str(first_operation["operation_id"]),
    )
    first_auth, first_continuation, _assertion = _authorize_management(
        ledger_engine,
        first_add,
        credential,
        suffix="counter-chain-one",
        previous_sign_count=5,
        asserted_sign_count=6,
    )
    _consumption, failed_outcome = _terminalize_failure(
        ledger_engine,
        first_add,
        first_continuation,
        suffix="counter-chain-one-registration",
        terminal_result="INVALID_REGISTRATION",
        auth=first_auth,
    )
    second_add = _issue_operation(
        ledger_engine,
        principal,
        suffix="counter-chain-two",
        operation_type="ADD_CREDENTIAL",
        expected_state=str(failed_outcome["resulting_state"]),
        predecessor_id=str(first_add["operation_id"]),
    )
    _second_auth, _continuation, _assertion = _authorize_management(
        ledger_engine,
        second_add,
        credential,
        suffix="counter-chain-two",
        previous_sign_count=6,
        asserted_sign_count=7,
    )
    with ledger_engine.connect() as connection:
        rows = tuple(
            connection.execute(
                text(
                    "SELECT previous_sign_count, asserted_sign_count FROM "
                    "reviewer_credential_operation_authentication_events "
                    "WHERE authentication_result='VERIFIED' ORDER BY asserted_sign_count"
                )
            )
        )
    assert rows == ((5, 6), (6, 7))


@pytest.mark.parametrize(
    ("previous_sign_count", "asserted_sign_count"),
    [(6, 6), (6, 5), (7, 8), (5, 7)],
    ids=("equality", "rollback", "gap", "fork"),
)
def test_supported_counter_union_rejects_equality_rollback_gap_and_fork(
    ledger_engine: Engine,
    previous_sign_count: int,
    asserted_sign_count: int,
) -> None:
    principal, first_operation, credential, first_outcome = _seed_first_credential(ledger_engine)
    first_add = _issue_operation(
        ledger_engine,
        principal,
        suffix="counter-invalid-base",
        operation_type="ADD_CREDENTIAL",
        expected_state=str(first_outcome["resulting_state"]),
        predecessor_id=str(first_operation["operation_id"]),
    )
    first_auth, first_continuation, _assertion = _authorize_management(
        ledger_engine,
        first_add,
        credential,
        suffix="counter-invalid-base",
        previous_sign_count=5,
        asserted_sign_count=6,
    )
    _consumption, failed_outcome = _terminalize_failure(
        ledger_engine,
        first_add,
        first_continuation,
        suffix="counter-invalid-base-registration",
        terminal_result="INVALID_REGISTRATION",
        auth=first_auth,
    )
    second_add = _issue_operation(
        ledger_engine,
        principal,
        suffix="counter-invalid-attempt",
        operation_type="ADD_CREDENTIAL",
        expected_state=str(failed_outcome["resulting_state"]),
        predecessor_id=str(first_add["operation_id"]),
    )
    with pytest.raises(DBAPIError):
        _authorize_management(
            ledger_engine,
            second_add,
            credential,
            suffix=f"counter-invalid-{previous_sign_count}-{asserted_sign_count}",
            previous_sign_count=previous_sign_count,
            asserted_sign_count=asserted_sign_count,
        )
    with ledger_engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT COUNT(*) FROM reviewer_credential_operation_authentication_events")
            ).scalar_one()
            == 1
        )


def test_no_usable_counter_remains_exact_null_null(
    ledger_engine: Engine,
) -> None:
    principal, first_operation, credential, first_outcome = _seed_first_credential(
        ledger_engine,
        suffix="no-counter",
        counter_capability="NO_USABLE_COUNTER",
        registration_sign_count=None,
    )
    operation = _issue_operation(
        ledger_engine,
        principal,
        suffix="no-counter-add",
        operation_type="ADD_CREDENTIAL",
        expected_state=str(first_outcome["resulting_state"]),
        predecessor_id=str(first_operation["operation_id"]),
    )
    _auth, _continuation, _assertion = _authorize_management(
        ledger_engine,
        operation,
        credential,
        suffix="no-counter-add",
        previous_sign_count=None,
        asserted_sign_count=None,
    )
    with ledger_engine.connect() as connection:
        assert connection.execute(
            text(
                "SELECT counter_capability, previous_sign_count, asserted_sign_count "
                "FROM reviewer_credential_operation_authentication_events"
            )
        ).one() == ("NO_USABLE_COUNTER", None, None)


@pytest.mark.parametrize("first_writer", ["issuer", "operation"])
def test_issuer_and_operation_counter_race_has_exactly_one_winner(
    ledger_engine: Engine,
    first_writer: str,
) -> None:
    (
        decision,
        bundle,
        issuer_principal,
        principal,
        credential,
        issuer_credential,
        first_outcome,
    ) = _seed_issuer_context_and_first_credential(ledger_engine)
    operation = _issue_operation(
        ledger_engine,
        principal,
        suffix=f"counter-race-{first_writer}",
        operation_type="ADD_CREDENTIAL",
        expected_state=str(first_outcome["resulting_state"]),
        predecessor_id="operation-issuer-context-first",
    )

    if first_writer == "issuer":
        _insert_counter_authentication_event(
            ledger_engine,
            decision,
            bundle,
            issuer_principal,
            issuer_credential,
            event_suffix="race_issuer_first",
            authenticated_at="2026-08-27T01:01:00Z",
            previous_sign_count=5,
            asserted_sign_count=6,
        )
        with pytest.raises(DBAPIError):
            _authorize_management(
                ledger_engine,
                operation,
                credential,
                suffix="race-operation-second",
                previous_sign_count=5,
                asserted_sign_count=7,
            )
    else:
        _authorize_management(
            ledger_engine,
            operation,
            credential,
            suffix="race-operation-first",
            previous_sign_count=5,
            asserted_sign_count=6,
        )
        with pytest.raises(DBAPIError):
            _insert_counter_authentication_event(
                ledger_engine,
                decision,
                bundle,
                issuer_principal,
                issuer_credential,
                event_suffix="race_issuer_second",
                authenticated_at="2026-08-27T01:01:00Z",
                previous_sign_count=5,
                asserted_sign_count=7,
            )

    with ledger_engine.connect() as connection:
        issuer_count = int(
            connection.execute(
                text("SELECT COUNT(*) FROM reviewer_authentication_events")
            ).scalar_one()
        )
        operation_count = int(
            connection.execute(
                text("SELECT COUNT(*) FROM reviewer_credential_operation_authentication_events")
            ).scalar_one()
        )
    assert issuer_count + operation_count == 1


def test_revoked_final_credential_cannot_authenticate_issuer_approval(
    ledger_engine: Engine,
) -> None:
    (
        decision,
        bundle,
        issuer_principal,
        principal,
        credential,
        issuer_credential,
        first_outcome,
    ) = _seed_issuer_context_and_first_credential(ledger_engine)
    operation = _issue_operation(
        ledger_engine,
        principal,
        suffix="issuer-after-final-revoke",
        operation_type="REVOKE_CREDENTIAL",
        expected_state=str(first_outcome["resulting_state"]),
        predecessor_id="operation-issuer-context-first",
        target=credential,
    )
    _complete_revoke(
        ledger_engine,
        operation,
        credential,
        suffix="issuer-after-final-revoke",
        resulting_state=_h("issuer-context-final-empty"),
        previous_sign_count=5,
        asserted_sign_count=6,
    )
    with pytest.raises(DBAPIError, match="currently active credential"):
        _insert_counter_authentication_event(
            ledger_engine,
            decision,
            bundle,
            issuer_principal,
            issuer_credential,
            event_suffix="revoked_issuer_attempt",
            authenticated_at="2026-08-27T01:01:00Z",
            previous_sign_count=6,
            asserted_sign_count=7,
        )


def test_superseded_credential_cannot_authenticate_issuer_approval(
    ledger_engine: Engine,
) -> None:
    (
        decision,
        bundle,
        issuer_principal,
        principal,
        old_credential,
        issuer_credential,
        first_outcome,
    ) = _seed_issuer_context_and_first_credential(ledger_engine)
    operation = _issue_operation(
        ledger_engine,
        principal,
        suffix="issuer-after-replace",
        operation_type="REPLACE_CREDENTIAL",
        expected_state=str(first_outcome["resulting_state"]),
        predecessor_id="operation-issuer-context-first",
        target=old_credential,
    )
    auth, continuation, _assertion = _authorize_management(
        ledger_engine,
        operation,
        old_credential,
        suffix="issuer-after-replace",
        previous_sign_count=5,
        asserted_sign_count=6,
    )
    _complete_registration(
        ledger_engine,
        operation,
        continuation,
        principal,
        suffix="issuer-replacement",
        resulting_state=_h("issuer-replacement-active"),
        auth=auth,
        replace_target=old_credential,
    )
    with pytest.raises(DBAPIError, match="currently active credential"):
        _insert_counter_authentication_event(
            ledger_engine,
            decision,
            bundle,
            issuer_principal,
            issuer_credential,
            event_suffix="superseded_issuer_attempt",
            authenticated_at="2026-08-27T01:01:00Z",
            previous_sign_count=6,
            asserted_sign_count=7,
        )


def test_issuer_and_credential_operation_assertion_relations_are_not_substitutable(
    ledger_engine: Engine,
) -> None:
    with ledger_engine.connect() as connection:
        authorization_fks = _foreign_key_groups(
            connection, "reviewer_webauthn_credential_event_authorizations"
        )
        issuer_event_fks = _foreign_key_groups(connection, "issuer_approval_events")
        operation_auth_fks = _foreign_key_groups(
            connection, "reviewer_credential_operation_authentication_events"
        )
    assert any(
        table == "reviewer_credential_operation_authentication_events"
        and "credential_operation_authentication_event_id" in child
        for table, child, _parent in authorization_fks
    )
    assert all(
        table != "reviewer_authentication_events" for table, _child, _parent in authorization_fks
    )
    assert any(
        table == "reviewer_authentication_events" and "authentication_event_id" in child
        for table, child, _parent in issuer_event_fks
    )
    assert all(
        table not in {"issuer_approval_challenges", "reviewer_authentication_events"}
        for table, _child, _parent in operation_auth_fks
    )


def test_0006_creates_no_canonical_security_or_verified_provider_mapping(
    ledger_engine: Engine,
) -> None:
    with ledger_engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM securities")).scalar_one() == 0
        assert (
            connection.execute(
                text(
                    "SELECT COUNT(*) FROM provider_identity_mappings "
                    "WHERE mapping_status='VERIFIED'"
                )
            ).scalar_one()
            == 0
        )


def test_append_only_guards_reject_actual_update_and_delete_operations(
    ledger_engine: Engine,
) -> None:
    principal, first_operation, credential, first_outcome = _seed_first_credential(ledger_engine)
    add_operation = _issue_operation(
        ledger_engine,
        principal,
        suffix="append-only-add",
        operation_type="ADD_CREDENTIAL",
        expected_state=str(first_outcome["resulting_state"]),
        predecessor_id=str(first_operation["operation_id"]),
    )
    _authorize_management(
        ledger_engine,
        add_operation,
        credential,
        suffix="append-only-add",
        previous_sign_count=5,
        asserted_sign_count=6,
    )
    with ledger_engine.connect() as connection:
        before = {
            table_name: int(
                connection.exec_driver_sql(f'SELECT COUNT(*) FROM "{table_name}"').scalar_one()
            )
            for table_name in NEW_TABLES
        }
    assert all(count > 0 for count in before.values())
    for table_name in sorted(NEW_TABLES):
        for statement in (
            f'UPDATE "{table_name}" SET payload_json=payload_json',
            f'DELETE FROM "{table_name}"',
        ):
            with pytest.raises(DBAPIError, match="append-only"):
                with ledger_engine.begin() as connection:
                    connection.exec_driver_sql(statement)
    with ledger_engine.connect() as connection:
        after = {
            table_name: int(
                connection.exec_driver_sql(f'SELECT COUNT(*) FROM "{table_name}"').scalar_one()
            )
            for table_name in NEW_TABLES
        }
    assert after == before


def test_one_active_local_steward_and_one_first_enrollment_root_are_unique(
    ledger_engine: Engine,
) -> None:
    principal = _seed_principal(ledger_engine)
    _issue_operation(
        ledger_engine,
        principal,
        suffix="unique-root-one",
        operation_type="FIRST_ENROLLMENT",
        expected_state=_h("unique-root-empty"),
    )
    second_root = _operation_values(
        principal,
        suffix="unique-root-two",
        operation_type="FIRST_ENROLLMENT",
        expected_state=_h("unique-root-empty"),
    )
    with pytest.raises(IntegrityError):
        with ledger_engine.begin() as connection:
            connection.execute(OPERATION_INSERT, second_root)
            connection.execute(CHALLENGE_INSERT, _challenge_values(second_root))
    with pytest.raises(IntegrityError):
        _seed_principal(ledger_engine, suffix="second-active-steward")


def test_every_unapproved_authorization_matrix_combination_is_rejected(
    ledger_engine: Engine,
) -> None:
    _seed_first_credential(ledger_engine)
    table_name = "reviewer_webauthn_credential_event_authorizations"
    with ledger_engine.connect() as connection:
        baseline = dict(connection.execute(text(f'SELECT * FROM "{table_name}"')).mappings().one())
    columns = tuple(baseline)
    placeholders = ", ".join(f":{column}" for column in columns)
    column_sql = ", ".join(f'"{column}"' for column in columns)
    insert = text(f'INSERT INTO "{table_name}" ({column_sql}) VALUES ({placeholders})')
    operations = (
        "FIRST_ENROLLMENT",
        "ADD_CREDENTIAL",
        "REPLACE_CREDENTIAL",
        "REVOKE_CREDENTIAL",
    )
    events = ("REGISTERED", "SUPERSEDED", "REVOKED")
    kinds = (
        "BOOTSTRAP_REGISTRATION",
        "AUTHORIZED_REGISTRATION",
        "AUTHORIZED_SUPERSESSION",
        "AUTHORIZED_REVOCATION",
    )
    allowed = {
        ("FIRST_ENROLLMENT", "REGISTERED", "BOOTSTRAP_REGISTRATION"),
        ("ADD_CREDENTIAL", "REGISTERED", "AUTHORIZED_REGISTRATION"),
        ("REPLACE_CREDENTIAL", "REGISTERED", "AUTHORIZED_REGISTRATION"),
        ("REPLACE_CREDENTIAL", "SUPERSEDED", "AUTHORIZED_SUPERSESSION"),
        ("REVOKE_CREDENTIAL", "REVOKED", "AUTHORIZED_REVOCATION"),
    }
    rejected = 0
    for operation_type in operations:
        for event_type in events:
            for authorization_kind in kinds:
                if (operation_type, event_type, authorization_kind) in allowed:
                    continue
                row = dict(baseline)
                suffix = f"{operation_type}-{event_type}-{authorization_kind}"
                row["credential_event_id"] = f"invalid-matrix-{rejected}"
                row["credential_event_content_hash"] = _h("event-" + suffix)
                row["authorization_content_hash"] = _h("authorization-" + suffix)
                row["operation_type"] = operation_type
                row["event_type"] = event_type
                row["authorization_kind"] = authorization_kind
                with pytest.raises(IntegrityError):
                    with ledger_engine.begin() as connection:
                        connection.execute(insert, row)
                rejected += 1
    assert rejected == 43

    row = dict(baseline)
    row["credential_event_id"] = "invalid-free-form-kind"
    row["credential_event_content_hash"] = _h("invalid-free-form-event")
    row["authorization_content_hash"] = _h("invalid-free-form-authorization")
    row["authorization_kind"] = "AUTHORIZED_LIFECYCLE"
    with pytest.raises(IntegrityError):
        with ledger_engine.begin() as connection:
            connection.execute(insert, row)


def test_successful_outcome_and_authorization_trust_tuple_mismatch_is_rejected(
    ledger_engine: Engine,
) -> None:
    principal, first_operation, credential, first_outcome = _seed_first_credential(ledger_engine)
    operation = _issue_operation(
        ledger_engine,
        principal,
        suffix="trust-mismatch-add",
        operation_type="ADD_CREDENTIAL",
        expected_state=str(first_outcome["resulting_state"]),
        predecessor_id=str(first_operation["operation_id"]),
    )
    auth, continuation, _assertion = _authorize_management(
        ledger_engine,
        operation,
        credential,
        suffix="trust-mismatch-add",
        previous_sign_count=5,
        asserted_sign_count=6,
    )
    new_credential = _credential_values(principal, suffix="trust-mismatch-added")
    event_id = "credential-event-trust-mismatch-registered"
    event_hash = _h(event_id)
    new_credential["root_event_id"] = event_id
    outcome_id = "outcome-trust-mismatch"
    outcome_hash = _h(outcome_id)
    resulting_state = _h("trust-mismatch-resulting")
    consumption = _consumption_values(
        operation,
        continuation,
        suffix="trust-mismatch-registration",
        terminal_result="SUCCEEDED",
        resulting_state=resulting_state,
        outcome_id=outcome_id,
        credential=new_credential,
    )
    authorization = _authorization_values(
        operation,
        new_credential,
        event_id=event_id,
        event_hash=event_hash,
        event_type="REGISTERED",
        authorization_kind="AUTHORIZED_REGISTRATION",
        outcome_id=outcome_id,
        outcome_hash=outcome_hash,
        resulting_state=resulting_state,
        registration_consumption=consumption,
        auth=auth,
    )
    event = _event_values(
        new_credential,
        event_id=event_id,
        event_hash=event_hash,
        event_type="REGISTERED",
        predecessor_event_id=None,
    )
    outcome = _outcome_values(
        operation,
        consumption,
        suffix="trust-mismatch",
        outcome_hash=outcome_hash,
        auth=auth,
    )
    outcome["sid_hash"] = _h("different-server-owned-sid")
    with pytest.raises(DBAPIError, match="trust tuple mismatch"):
        with ledger_engine.begin() as connection:
            connection.execute(CONSUMPTION_INSERT, consumption)
            connection.execute(AUTHORIZATION_INSERT, authorization)
            connection.execute(CREDENTIAL_INSERT, new_credential)
            connection.execute(EVENT_INSERT, event)
            connection.execute(OUTCOME_INSERT, outcome)


def test_cross_principal_lifecycle_graft_is_rejected(ledger_engine: Engine) -> None:
    principal, _operation, credential, _outcome = _seed_first_credential(ledger_engine)
    event = _event_values(
        credential,
        event_id="credential-event-cross-principal",
        event_hash=_h("credential-event-cross-principal"),
        event_type="REVOKED",
        predecessor_event_id=str(credential["root_event_id"]),
    )
    event["principal_id"] = "different-reviewer-principal"
    with pytest.raises(DBAPIError, match="same active root|authorization companion"):
        with ledger_engine.begin() as connection:
            connection.execute(EVENT_INSERT, event)
    assert principal["principal_id"] != event["principal_id"]


def test_cross_credential_lifecycle_predecessor_graft_is_rejected(
    ledger_engine: Engine,
) -> None:
    principal, first_operation, first_credential, first_outcome = _seed_first_credential(
        ledger_engine
    )
    add_operation = _issue_operation(
        ledger_engine,
        principal,
        suffix="cross-graft-add",
        operation_type="ADD_CREDENTIAL",
        expected_state=str(first_outcome["resulting_state"]),
        predecessor_id=str(first_operation["operation_id"]),
    )
    add_auth, continuation, _assertion = _authorize_management(
        ledger_engine,
        add_operation,
        first_credential,
        suffix="cross-graft-add",
        previous_sign_count=5,
        asserted_sign_count=6,
    )
    second_credential, add_outcome = _complete_registration(
        ledger_engine,
        add_operation,
        continuation,
        principal,
        suffix="cross-graft-second",
        resulting_state=_h("cross-graft-two-active"),
        auth=add_auth,
    )
    revoke_operation = _issue_operation(
        ledger_engine,
        principal,
        suffix="cross-graft-revoke",
        operation_type="REVOKE_CREDENTIAL",
        expected_state=str(add_outcome["resulting_state"]),
        predecessor_id=str(add_operation["operation_id"]),
        target=second_credential,
    )
    outcome_id = "outcome-cross-graft-revoke"
    outcome_hash = _h(outcome_id)
    consumption = _consumption_values(
        revoke_operation,
        revoke_operation["initial_challenge"],
        suffix="cross-graft-revoke",
        terminal_result="SUCCEEDED",
        resulting_state=_h("cross-graft-one-active"),
        outcome_id=outcome_id,
        consumed_at="2026-08-28T00:02:00Z",
    )
    auth = _operation_auth_values(
        revoke_operation,
        revoke_operation["initial_challenge"],
        consumption,
        second_credential,
        suffix="cross-graft-revoke",
        previous_sign_count=5,
        asserted_sign_count=6,
    )
    event_id = "credential-event-cross-graft-revoked"
    event_hash = _h(event_id)
    authorization = _authorization_values(
        revoke_operation,
        second_credential,
        event_id=event_id,
        event_hash=event_hash,
        event_type="REVOKED",
        authorization_kind="AUTHORIZED_REVOCATION",
        outcome_id=outcome_id,
        outcome_hash=outcome_hash,
        resulting_state=_h("cross-graft-one-active"),
        registration_consumption=None,
        auth=auth,
    )
    event = _event_values(
        second_credential,
        event_id=event_id,
        event_hash=event_hash,
        event_type="REVOKED",
        predecessor_event_id=str(first_credential["root_event_id"]),
    )
    with pytest.raises(DBAPIError, match="same active root"):
        with ledger_engine.begin() as connection:
            connection.execute(CONSUMPTION_INSERT, consumption)
            connection.execute(OPERATION_AUTH_INSERT, auth)
            connection.execute(AUTHORIZATION_INSERT, authorization)
            connection.execute(EVENT_INSERT, event)


def test_persisted_terminal_consumption_without_outcome_is_fail_closed_after_restart(
    ledger_engine: Engine,
) -> None:
    principal = _seed_principal(ledger_engine)
    operation = _issue_operation(
        ledger_engine,
        principal,
        suffix="corrupt-terminal",
        operation_type="FIRST_ENROLLMENT",
        expected_state=_h("corrupt-terminal-empty"),
    )
    consumption = _consumption_values(
        operation,
        operation["initial_challenge"],
        suffix="corrupt-terminal",
        terminal_result="INVALID_REGISTRATION",
        resulting_state=str(operation["expected_state"]),
        outcome_id="outcome-corrupt-missing",
    )
    database_url = str(ledger_engine.url)
    ledger_engine.dispose()
    corruption_engine = create_engine(database_url)
    try:
        with corruption_engine.begin() as connection:
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 0
            connection.execute(CONSUMPTION_INSERT, consumption)
    finally:
        corruption_engine.dispose()

    restarted = create_database_engine(database_url)
    try:
        with restarted.connect() as connection:
            violations = tuple(connection.exec_driver_sql("PRAGMA foreign_key_check"))
        assert any(
            str(row[0]) == "reviewer_credential_operation_challenge_consumptions"
            and str(row[2]) == "reviewer_credential_operation_outcomes"
            for row in violations
        )
        successor = _operation_values(
            principal,
            suffix="corrupt-terminal-successor",
            operation_type="FIRST_ENROLLMENT",
            expected_state=str(operation["expected_state"]),
            predecessor_id=str(operation["operation_id"]),
        )
        with pytest.raises(DBAPIError, match="terminal state leaf"):
            with restarted.begin() as connection:
                connection.execute(OPERATION_INSERT, successor)
    finally:
        restarted.dispose()
