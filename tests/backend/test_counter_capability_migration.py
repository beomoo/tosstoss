from __future__ import annotations

import copy
import hashlib
import importlib.util
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.exc import DBAPIError
from tests.backend.conftest import alembic_config
from tests.backend.test_reviewer_operation_migration import (
    AUTHORIZATION_INSERT,
    CONSUMPTION_INSERT,
    EVENT_INSERT,
    OPERATION_AUTH_INSERT,
    OPERATION_INSERT,
    OUTCOME_INSERT,
    _active_credentials,
    _authorization_values,
    _challenge_values,
    _consumption_values,
    _credential_values,
    _event_values,
    _h,
    _operation_auth_values,
    _operation_values,
    _outcome_values,
    _seed_first_credential,
    _seed_principal,
)

from toss_dashboard_api.storage.database import create_database_engine

REVISION_0006 = "0006_phase_02_cp3_c2_b2_c_reviewer_operations"
REVISION_0007 = "0007_phase_02_cp3_c2_b2_c_counter_capability_bootstrap"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
REVISION_0007_PATH = (
    PROJECT_ROOT
    / "services"
    / "api"
    / "alembic"
    / "versions"
    / "0007_phase_02_cp3_c2_b2_c_counter_capability_bootstrap.py"
)
FROZEN_MIGRATION_BLOBS = {
    "0001_phase_01_foundation.py": "d00355c2456021e6ffb195e50833adc32c74a4ad",
    "0002_phase_02_cp3_foundation.py": "53f40664eca2ea2466cc6154b8579c5db506e0ba",
    "0003_phase_02_cp3_b_invariants.py": "47d5a69009949b155211cd68209640136a7cacd9",
    "0004_phase_02_cp3_c1_security_master.py": "91b4d96a445be23e7aa55e08b9310dc7334a026d",
    "0005_phase_02_cp3_c2_b_issuer_authority.py": "81976b8f70a1f6107526a13acadf23f369b196e3",
    "0006_phase_02_cp3_c2_b2_c_reviewer_operations.py": "f10e7f5bc21e232fc68b38144f5b8fb124f31698",
}
COUNTER_TABLES = {
    "reviewer_webauthn_counter_capability_registrations",
    "reviewer_webauthn_counter_capability_challenges",
    "reviewer_webauthn_counter_capability_assertions",
}
COUNTER_INDEXES = {
    "uq_0007_cc_registration_content",
    "uq_0007_cc_registration_parent",
    "uq_0007_cc_registration_child",
    "uq_0007_cc_registration_credential",
    "uq_0007_cc_registration_credential_fingerprint",
    "uq_0007_cc_registration_public_key_fingerprint",
    "uq_0007_cc_registration_exact_copy",
    "uq_0007_cc_registration_assertion_copy",
    "ix_counter_capability_registrations_operation",
    "uq_0007_cc_challenge_digest",
    "uq_0007_cc_challenge_binding",
    "uq_0007_cc_challenge_registration",
    "uq_0007_cc_challenge_exact_child",
    "uq_0007_cc_challenge_exact_copy",
    "ix_counter_capability_challenges_expiry",
    "uq_0007_cc_assertion_content",
    "uq_0007_cc_assertion_challenge",
    "uq_0007_cc_assertion_registration",
    "uq_0007_cc_assertion_consumption_projection",
    "uq_0007_cc_assertion_outcome_projection",
    "ix_counter_capability_assertions_operation",
    "uq_0007_reviewer_credential_operation_outcomes_bootstrap_projection",
    "uq_0007_credential_event_authorization_projection",
}
COUNTER_GUARDS = {
    "trg_0007_counter_capability_registrations_insert_guard",
    "trg_0007_counter_capability_challenges_insert_guard",
    "trg_0007_counter_capability_assertions_insert_guard",
    "trg_0007_operation_consumptions_bootstrap_projection_guard",
    "trg_0007_operation_outcomes_bootstrap_projection_guard",
    "trg_0007_credentials_counter_bootstrap_guard",
    "trg_0007_credential_event_authorizations_counter_bootstrap_guard",
    "trg_0007_credential_events_counter_bootstrap_guard",
    "trg_0007_counter_capability_assertions_counter_union_guard",
}
REPLACED_COUNTER_GUARDS = {
    "trg_reviewer_authentication_events_counter_union_guard",
    "trg_reviewer_credential_operation_authentication_counter_union_guard",
}

NORMATIVE_CHALLENGE_INSERT = text(
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
    ":platform_required, :resident_required, 'issuer-steward-webauthn/0.1.0', "
    ":issued_at, :expires_at, '{}'"
    ")"
)
REGISTRATION_INSERT = text(
    "INSERT INTO reviewer_webauthn_counter_capability_registrations ("
    "counter_capability_registration_id, contract_version, "
    "counter_capability_registration_content_hash, reviewer_credential_operation_id, "
    "operation_content_hash, operation_type, reviewer_principal_id, reviewer_role, "
    "principal_content_hash, os_owner_sid_hash, expected_credential_state_hash, "
    "registration_challenge_id, registration_challenge_purpose, "
    "registration_challenge_binding_hash, prerequisite_authentication_event_id, "
    "prerequisite_authentication_content_hash, prerequisite_authentication_result, "
    "webauthn_credential_id, credential_id_fingerprint, cose_public_key_canonical, "
    "public_key_fingerprint, public_key_algorithm, authenticator_aaguid, "
    "authenticator_attachment, authenticator_transports_json, rp_id, exact_origin, "
    "resident_key_required, require_resident_key, user_verification_required, "
    "attestation_conveyance, cred_props_requested, cred_props_rk, "
    "registration_policy_version, observed_registration_sign_count, "
    "client_data_type_verified, challenge_verified, origin_verified, "
    "cross_origin_false_verified, rp_id_hash_verified, user_presence_verified, "
    "user_verification_verified, platform_authenticator_verified, resident_key_verified, "
    "public_key_material_verified, safe_result_code, continuation_challenge_id, "
    "verified_at, payload_json"
    ") VALUES ("
    ":registration_id, 'reviewer-counter-capability-registration/0.1.0', "
    ":registration_hash, :operation_id, :operation_hash, :operation_type, :principal_id, "
    "'LOCAL_DATA_STEWARD', :principal_hash, :sid_hash, :expected_state, :parent_id, "
    "'REGISTRATION_CREATE', :parent_binding_hash, :prerequisite_auth_id, "
    ":prerequisite_auth_hash, :prerequisite_auth_result, :credential_id, "
    ":credential_fingerprint, :cose_key, :public_key_fingerprint, :public_key_algorithm, "
    ":aaguid, 'platform', :transports_json, 'localhost', 'http://localhost:3000', "
    "1, 1, 1, 'none', 1, :cred_props_rk, 'issuer-steward-webauthn/0.1.0', "
    "0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, "
    "'COUNTER_CAPABILITY_CONTINUATION_REQUIRED', :child_id, :verified_at, '{}'"
    ")"
)
CHILD_INSERT = text(
    "INSERT INTO reviewer_webauthn_counter_capability_challenges ("
    "counter_capability_challenge_id, contract_version, challenge_digest, "
    "challenge_binding_hash, challenge_nonce_length, challenge_purpose, "
    "counter_capability_registration_id, counter_capability_registration_content_hash, "
    "reviewer_credential_operation_id, operation_content_hash, operation_type, "
    "reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash, "
    "expected_credential_state_hash, parent_registration_challenge_id, "
    "parent_registration_challenge_binding_hash, webauthn_credential_id, "
    "credential_id_fingerprint, public_key_fingerprint, rp_id, allowed_origin, "
    "client_data_type, user_verification_required, allow_credentials_count, "
    "allowed_webauthn_credential_id, user_handle_contract_version, "
    "authentication_policy_version, issued_at, expires_at, payload_json"
    ") VALUES ("
    ":child_id, 'reviewer-counter-capability-challenge/0.1.0', :child_digest, "
    ":child_binding_hash, 32, 'COUNTER_CAPABILITY_ASSERTION', :registration_id, "
    ":registration_hash, :operation_id, :operation_hash, :operation_type, :principal_id, "
    "'LOCAL_DATA_STEWARD', :principal_hash, :sid_hash, :expected_state, :parent_id, "
    ":parent_binding_hash, :credential_id, :credential_fingerprint, "
    ":public_key_fingerprint, 'localhost', 'http://localhost:3000', 'webauthn.get', "
    "1, 1, :credential_id, 'issuer-steward-webauthn-user-handle/0.1.0', "
    "'issuer-steward-webauthn/0.1.0', :child_issued_at, :child_expires_at, '{}'"
    ")"
)
ASSERTION_INSERT = text(
    "INSERT INTO reviewer_webauthn_counter_capability_assertions ("
    "counter_capability_assertion_id, contract_version, assertion_content_hash, "
    "counter_capability_challenge_id, challenge_binding_hash, "
    "counter_capability_registration_id, counter_capability_registration_content_hash, "
    "reviewer_credential_operation_id, operation_content_hash, operation_type, "
    "reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash, "
    "expected_credential_state_hash, webauthn_credential_id, credential_id_fingerprint, "
    "public_key_fingerprint, challenge_terminal_result, safe_result_code, "
    "client_data_type_verified, challenge_verified, origin_verified, "
    "cross_origin_false_verified, rp_id_hash_verified, user_presence_verified, "
    "user_verification_verified, credential_id_verified, signature_verified, "
    "replay_rejected, user_handle_status, observed_registration_sign_count, "
    "previous_sign_count, asserted_sign_count, selected_counter_capability, "
    "selected_registration_sign_count, classification_verified, "
    "projected_registration_consumption_id, "
    "projected_registration_consumption_content_hash, "
    "projected_registration_challenge_purpose, projected_registration_terminal_result, "
    "projected_registration_safe_result_code, projected_operation_outcome_id, "
    "projected_operation_outcome_content_hash, projected_operation_terminal_result, "
    "projected_resulting_credential_state_hash, projected_credential_content_hash, "
    "projected_registered_event_id, projected_registered_event_content_hash, "
    "projected_registered_authorization_content_hash, projected_superseded_event_id, "
    "projected_superseded_event_content_hash, "
    "projected_superseded_authorization_content_hash, consumed_at, payload_json"
    ") VALUES ("
    ":assertion_id, 'reviewer-counter-capability-assertion/0.1.0', :assertion_hash, "
    ":child_id, :child_binding_hash, :registration_id, :registration_hash, :operation_id, "
    ":operation_hash, :operation_type, :principal_id, 'LOCAL_DATA_STEWARD', "
    ":principal_hash, :sid_hash, :expected_state, :credential_id, "
    ":credential_fingerprint, :public_key_fingerprint, :child_result, :safe_result_code, "
    ":client_type_ok, :challenge_ok, :origin_ok, :cross_origin_ok, :rp_ok, :up_ok, "
    ":uv_ok, :credential_id_ok, :signature_ok, :replay_ok, :user_handle_status, 0, "
    ":previous_sign_count, :asserted_sign_count, :selected_capability, "
    ":selected_registration_sign_count, :classification_ok, :consumption_id, "
    ":consumption_hash, :projected_purpose, :registration_result, "
    ":registration_safe_result_code, :outcome_id, :outcome_hash, :outcome_result, "
    ":resulting_state, :credential_hash, :registered_event_id, :registered_event_hash, "
    ":registered_authorization_hash, :superseded_event_id, :superseded_event_hash, "
    ":superseded_authorization_hash, :consumed_at, '{}'"
    ")"
)
BOOTSTRAP_CREDENTIAL_INSERT = text(
    "INSERT INTO reviewer_webauthn_credentials ("
    "webauthn_credential_id, contract_version, reviewer_principal_id, reviewer_role, "
    "principal_content_hash, credential_id_fingerprint, cose_public_key_canonical, "
    "public_key_fingerprint, public_key_algorithm, authenticator_aaguid, "
    "authenticator_attachment, authenticator_transports_json, counter_capability, "
    "registration_sign_count, rp_id, resident_key_required, user_verification_required, "
    "registration_policy_version, credential_content_hash, registered_at, payload_json"
    ") VALUES ("
    ":credential_id, 'issuer-steward-webauthn/0.1.0', :principal_id, "
    "'LOCAL_DATA_STEWARD', :principal_hash, :credential_fingerprint, :cose_key, "
    ":public_key_fingerprint, :public_key_algorithm, :aaguid, 'platform', "
    ":transports_json, :counter_capability, :registration_sign_count, 'localhost', "
    "1, 1, 'issuer-steward-webauthn/0.1.0', :credential_hash, :registered_at, '{}'"
    ")"
)


@pytest.fixture
def bootstrap_engine(workspace_tmp_path: Path) -> Iterator[Engine]:
    url = f"sqlite:///{(workspace_tmp_path / 'counter-bootstrap.sqlite3').as_posix()}"
    command.upgrade(alembic_config(url), REVISION_0007)
    engine = create_database_engine(url)
    try:
        yield engine
    finally:
        engine.dispose()


def _git_blob_id(path: Path) -> str:
    payload = path.read_bytes()
    return hashlib.sha1(
        f"blob {len(payload)}\0".encode("ascii") + payload,
        usedforsecurity=False,
    ).hexdigest()


def _fk_check(engine: Engine) -> tuple[Any, ...]:
    with engine.connect() as connection:
        return tuple(connection.execute(text("PRAGMA foreign_key_check")))


def _active_credential_ids(engine: Engine, principal_id: str) -> tuple[str, ...]:
    with engine.connect() as connection:
        return _active_credentials(connection, principal_id)


def _revision(url: str) -> str:
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            return str(
                connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            )
    finally:
        engine.dispose()


def _issue_normative_operation(
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
    challenge = _challenge_values(
        operation,
        issued_at="2026-08-28T00:01:00Z",
        expires_at="2026-08-28T00:06:00Z",
    )
    with engine.begin() as connection:
        connection.execute(OPERATION_INSERT, operation)
        connection.execute(NORMATIVE_CHALLENGE_INSERT, challenge)
    return {**operation, "initial_challenge": challenge}


def _authorize_normative_management(
    engine: Engine,
    operation: dict[str, Any],
    credential: dict[str, Any],
    *,
    suffix: str,
    previous_sign_count: int | None = None,
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
    previous_count = (
        int(credential["registration_sign_count"])
        if previous_sign_count is None
        else previous_sign_count
    )
    authentication = _operation_auth_values(
        operation,
        initial,
        consumption,
        credential,
        suffix=suffix,
        previous_sign_count=previous_count,
        asserted_sign_count=previous_count + 1,
    )
    continuation = _challenge_values(
        operation,
        challenge_id=continuation_id,
        purpose="REGISTRATION_CREATE",
        prerequisite=authentication,
        issued_at="2026-08-28T00:03:00Z",
        expires_at="2026-08-28T00:08:00Z",
    )
    with engine.begin() as connection:
        connection.execute(CONSUMPTION_INSERT, consumption)
        connection.execute(OPERATION_AUTH_INSERT, authentication)
        connection.execute(NORMATIVE_CHALLENGE_INSERT, continuation)
    return authentication, continuation, consumption


def _prepare_operation(
    engine: Engine,
    operation_type: str,
    *,
    suffix: str,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any] | None,
    dict[str, Any] | None,
]:
    if operation_type == "FIRST_ENROLLMENT":
        principal = _seed_principal(engine, suffix=suffix)
        operation = _issue_normative_operation(
            engine,
            principal,
            suffix=suffix,
            operation_type=operation_type,
            expected_state=_h(f"empty-state-{suffix}"),
        )
        return principal, operation, operation["initial_challenge"], None, None

    principal, predecessor, old_credential, predecessor_outcome = _seed_first_credential(
        engine,
        suffix=f"{suffix}-authorizer",
        registration_sign_count=5,
    )
    target = old_credential if operation_type == "REPLACE_CREDENTIAL" else None
    operation = _issue_normative_operation(
        engine,
        principal,
        suffix=suffix,
        operation_type=operation_type,
        expected_state=str(predecessor_outcome["resulting_state"]),
        predecessor_id=str(predecessor["operation_id"]),
        target=target,
    )
    authentication, registration_challenge, _authorization_consumption = (
        _authorize_normative_management(
            engine,
            operation,
            old_credential,
            suffix=suffix,
        )
    )
    return principal, operation, registration_challenge, authentication, target


def _pending_values(
    operation: dict[str, Any],
    parent: dict[str, Any],
    principal: dict[str, Any],
    *,
    suffix: str,
    authentication: dict[str, Any] | None,
    child_expires_at: str = "2026-08-28T00:06:00Z",
) -> tuple[dict[str, Any], dict[str, Any]]:
    credential = _credential_values(
        principal,
        suffix=f"{suffix}-pending",
        registration_sign_count=0,
    )
    credential.update(
        {
            "cose_key": "c3ludGhldGljLWNvc2Uta2V5",
            "public_key_algorithm": "ES256",
            "aaguid": None,
            "transports_json": '["internal"]',
            "registered_at": "2026-08-28T00:05:00Z",
        }
    )
    registration = {
        **operation,
        **principal,
        **credential,
        "registration_id": f"counter-registration-{suffix}",
        "registration_hash": _h(f"counter-registration-{suffix}"),
        "parent_id": parent["challenge_id"],
        "parent_binding_hash": parent["challenge_binding_hash"],
        "prerequisite_auth_id": None if authentication is None else authentication["auth_id"],
        "prerequisite_auth_hash": None if authentication is None else authentication["auth_hash"],
        "prerequisite_auth_result": None if authentication is None else "VERIFIED",
        "child_id": f"counter-challenge-{suffix}",
        "verified_at": "2026-08-28T00:04:00Z",
        "cred_props_rk": None,
    }
    challenge = {
        **registration,
        "child_digest": _h(f"counter-challenge-{suffix}-digest"),
        "child_binding_hash": _h(f"counter-challenge-{suffix}-binding"),
        "child_issued_at": "2026-08-28T00:04:00Z",
        "child_expires_at": child_expires_at,
    }
    return registration, challenge


def _insert_pending(
    engine: Engine,
    registration: dict[str, Any],
    challenge: dict[str, Any],
) -> None:
    with engine.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        try:
            connection.execute(REGISTRATION_INSERT, registration)
            connection.execute(CHILD_INSERT, challenge)
            connection.commit()
        except Exception:
            connection.rollback()
            raise


def _terminal_values(
    operation: dict[str, Any],
    parent: dict[str, Any],
    registration: dict[str, Any],
    challenge: dict[str, Any],
    *,
    suffix: str,
    branch: str,
    authentication: dict[str, Any] | None,
    replace_target: dict[str, Any] | None,
) -> dict[str, Any]:
    success = branch in {"supported", "no_usable"}
    expired = branch == "expired"
    child_result = "SUCCEEDED" if success else ("EXPIRED" if expired else "INVALID_SIGNATURE")
    registration_result = "SUCCEEDED" if success else ("EXPIRED" if expired else "FAILED_CLOSED")
    outcome_result = registration_result
    consumed_at = "2026-08-28T00:10:00Z" if expired else "2026-08-28T00:05:00Z"
    safe_result_code = {
        "supported": "COUNTER_CAPABILITY_SUPPORTED",
        "no_usable": "COUNTER_CAPABILITY_NO_USABLE_COUNTER",
        "failure": "COUNTER_CAPABILITY_ASSERTION_FAILED",
        "expired": "COUNTER_CAPABILITY_PARENT_EXPIRED",
    }[branch]
    resulting_state = (
        _h(f"resulting-state-{suffix}") if success else str(operation["expected_state"])
    )
    selected_capability = (
        "SIGN_COUNT_SUPPORTED"
        if branch == "supported"
        else ("NO_USABLE_COUNTER" if branch == "no_usable" else None)
    )
    credential = {
        **registration,
        "counter_capability": selected_capability,
        "registration_sign_count": 0 if branch == "supported" else None,
        "credential_hash": _h(f"credential-{suffix}-bootstrap"),
        "registered_at": consumed_at,
    }
    outcome_id = f"outcome-{suffix}-bootstrap"
    outcome_hash = _h(outcome_id)
    frozen_consumption = _consumption_values(
        operation,
        parent,
        suffix=f"{suffix}-bootstrap-terminal",
        terminal_result=registration_result,
        resulting_state=resulting_state,
        outcome_id=outcome_id,
        credential=credential if success else None,
        consumed_at=consumed_at,
    )
    frozen_consumption.update(
        {
            "safe_result_code": safe_result_code,
            "client_type_ok": 1,
            "challenge_ok": 1,
            "origin_ok": 1,
            "cross_origin_ok": 1,
            "rp_ok": 1,
            "up_ok": 1,
            "uv_ok": 1,
            "platform_ok": 1,
            "resident_ok": 1,
            "key_ok": 1,
        }
    )
    outcome = _outcome_values(
        operation,
        frozen_consumption,
        suffix=f"{suffix}-bootstrap-terminal",
        outcome_hash=outcome_hash,
        auth=authentication,
    )
    registered_authorization: dict[str, Any] | None = None
    registered_event: dict[str, Any] | None = None
    superseded_authorization: dict[str, Any] | None = None
    superseded_event: dict[str, Any] | None = None
    if success:
        registered_event_id = f"credential-event-{suffix}-registered"
        registered_event_hash = _h(registered_event_id)
        registered_authorization = _authorization_values(
            operation,
            credential,
            event_id=registered_event_id,
            event_hash=registered_event_hash,
            event_type="REGISTERED",
            authorization_kind=(
                "BOOTSTRAP_REGISTRATION"
                if operation["operation_type"] == "FIRST_ENROLLMENT"
                else "AUTHORIZED_REGISTRATION"
            ),
            outcome_id=outcome_id,
            outcome_hash=outcome_hash,
            resulting_state=resulting_state,
            registration_consumption=frozen_consumption,
            auth=authentication,
        )
        registered_event = _event_values(
            credential,
            event_id=registered_event_id,
            event_hash=registered_event_hash,
            event_type="REGISTERED",
            predecessor_event_id=None,
        )
        if operation["operation_type"] == "REPLACE_CREDENTIAL":
            assert replace_target is not None
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
                auth=authentication,
            )
            superseded_event = _event_values(
                replace_target,
                event_id=superseded_event_id,
                event_hash=superseded_event_hash,
                event_type="SUPERSEDED",
                predecessor_event_id=str(replace_target["root_event_id"]),
            )

    assertion = {
        **operation,
        **registration,
        **challenge,
        "assertion_id": f"counter-assertion-{suffix}",
        "assertion_hash": _h(f"counter-assertion-{suffix}"),
        "child_result": child_result,
        "safe_result_code": safe_result_code,
        "client_type_ok": 1 if success or branch == "failure" else 0,
        "challenge_ok": 1 if success or branch == "failure" else 0,
        "origin_ok": 1 if success or branch == "failure" else 0,
        "cross_origin_ok": 1 if success or branch == "failure" else 0,
        "rp_ok": 1 if success or branch == "failure" else 0,
        "up_ok": 1 if success or branch == "failure" else 0,
        "uv_ok": 1 if success or branch == "failure" else 0,
        "credential_id_ok": 1 if success or branch == "failure" else 0,
        "signature_ok": 1 if success else 0,
        "replay_ok": 1 if success or branch == "failure" else 0,
        "user_handle_status": "MATCHED" if success else "NOT_EVALUATED",
        "previous_sign_count": 0 if success else None,
        "asserted_sign_count": (
            1 if branch == "supported" else (0 if branch == "no_usable" else None)
        ),
        "selected_capability": selected_capability,
        "selected_registration_sign_count": 0 if branch == "supported" else None,
        "classification_ok": 1 if success else 0,
        "consumption_id": frozen_consumption["consumption_id"],
        "consumption_hash": frozen_consumption["consumption_hash"],
        "projected_purpose": "REGISTRATION_CREATE",
        "registration_result": registration_result,
        "registration_safe_result_code": safe_result_code,
        "outcome_id": outcome_id,
        "outcome_hash": outcome_hash,
        "outcome_result": outcome_result,
        "resulting_state": resulting_state,
        "credential_hash": credential["credential_hash"] if success else None,
        "registered_event_id": (None if registered_event is None else registered_event["event_id"]),
        "registered_event_hash": (
            None if registered_event is None else registered_event["event_hash"]
        ),
        "registered_authorization_hash": (
            None
            if registered_authorization is None
            else registered_authorization["authorization_hash"]
        ),
        "superseded_event_id": (None if superseded_event is None else superseded_event["event_id"]),
        "superseded_event_hash": (
            None if superseded_event is None else superseded_event["event_hash"]
        ),
        "superseded_authorization_hash": (
            None
            if superseded_authorization is None
            else superseded_authorization["authorization_hash"]
        ),
        "consumed_at": consumed_at,
    }
    return {
        "assertion": assertion,
        "consumption": frozen_consumption,
        "registered_authorization": registered_authorization,
        "superseded_authorization": superseded_authorization,
        "credential": credential if success else None,
        "registered_event": registered_event,
        "superseded_event": superseded_event,
        "outcome": outcome,
    }


def _execute_terminal(
    engine: Engine,
    rows: dict[str, Any],
    *,
    order: tuple[str, ...] | None = None,
) -> None:
    statements: dict[str, tuple[Any, dict[str, Any] | None]] = {
        "assertion": (ASSERTION_INSERT, rows["assertion"]),
        "consumption": (CONSUMPTION_INSERT, rows["consumption"]),
        "registered_authorization": (AUTHORIZATION_INSERT, rows["registered_authorization"]),
        "superseded_authorization": (AUTHORIZATION_INSERT, rows["superseded_authorization"]),
        "credential": (BOOTSTRAP_CREDENTIAL_INSERT, rows["credential"]),
        "registered_event": (EVENT_INSERT, rows["registered_event"]),
        "superseded_event": (EVENT_INSERT, rows["superseded_event"]),
        "outcome": (OUTCOME_INSERT, rows["outcome"]),
    }
    selected_order = order or tuple(
        name
        for name in (
            "assertion",
            "consumption",
            "registered_authorization",
            "superseded_authorization",
            "credential",
            "registered_event",
            "superseded_event",
            "outcome",
        )
        if rows[name] is not None
    )
    with engine.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        try:
            for name in selected_order:
                statement, values = statements[name]
                assert values is not None
                connection.execute(statement, values)
            connection.commit()
        except Exception:
            connection.rollback()
            raise


APPEND_ONLY_GUARDS = {
    f"trg_{table}_append_only_{operation}"
    for table in COUNTER_TABLES
    for operation in ("update", "delete")
}

EXPECTED_COLUMNS = {
    "reviewer_webauthn_counter_capability_registrations": (
        "counter_capability_registration_id",
        "contract_version",
        "counter_capability_registration_content_hash",
        "reviewer_credential_operation_id",
        "operation_content_hash",
        "operation_type",
        "reviewer_principal_id",
        "reviewer_role",
        "principal_content_hash",
        "os_owner_sid_hash",
        "expected_credential_state_hash",
        "registration_challenge_id",
        "registration_challenge_purpose",
        "registration_challenge_binding_hash",
        "prerequisite_authentication_event_id",
        "prerequisite_authentication_content_hash",
        "prerequisite_authentication_result",
        "webauthn_credential_id",
        "credential_id_fingerprint",
        "cose_public_key_canonical",
        "public_key_fingerprint",
        "public_key_algorithm",
        "authenticator_aaguid",
        "authenticator_attachment",
        "authenticator_transports_json",
        "rp_id",
        "exact_origin",
        "resident_key_required",
        "require_resident_key",
        "user_verification_required",
        "attestation_conveyance",
        "cred_props_requested",
        "cred_props_rk",
        "registration_policy_version",
        "observed_registration_sign_count",
        "client_data_type_verified",
        "challenge_verified",
        "origin_verified",
        "cross_origin_false_verified",
        "rp_id_hash_verified",
        "user_presence_verified",
        "user_verification_verified",
        "platform_authenticator_verified",
        "resident_key_verified",
        "public_key_material_verified",
        "safe_result_code",
        "continuation_challenge_id",
        "verified_at",
        "payload_json",
    ),
    "reviewer_webauthn_counter_capability_challenges": (
        "counter_capability_challenge_id",
        "contract_version",
        "challenge_digest",
        "challenge_binding_hash",
        "challenge_nonce_length",
        "challenge_purpose",
        "counter_capability_registration_id",
        "counter_capability_registration_content_hash",
        "reviewer_credential_operation_id",
        "operation_content_hash",
        "operation_type",
        "reviewer_principal_id",
        "reviewer_role",
        "principal_content_hash",
        "os_owner_sid_hash",
        "expected_credential_state_hash",
        "parent_registration_challenge_id",
        "parent_registration_challenge_binding_hash",
        "webauthn_credential_id",
        "credential_id_fingerprint",
        "public_key_fingerprint",
        "rp_id",
        "allowed_origin",
        "client_data_type",
        "user_verification_required",
        "allow_credentials_count",
        "allowed_webauthn_credential_id",
        "user_handle_contract_version",
        "authentication_policy_version",
        "issued_at",
        "expires_at",
        "payload_json",
    ),
    "reviewer_webauthn_counter_capability_assertions": (
        "counter_capability_assertion_id",
        "contract_version",
        "assertion_content_hash",
        "counter_capability_challenge_id",
        "challenge_binding_hash",
        "counter_capability_registration_id",
        "counter_capability_registration_content_hash",
        "reviewer_credential_operation_id",
        "operation_content_hash",
        "operation_type",
        "reviewer_principal_id",
        "reviewer_role",
        "principal_content_hash",
        "os_owner_sid_hash",
        "expected_credential_state_hash",
        "webauthn_credential_id",
        "credential_id_fingerprint",
        "public_key_fingerprint",
        "challenge_terminal_result",
        "safe_result_code",
        "client_data_type_verified",
        "challenge_verified",
        "origin_verified",
        "cross_origin_false_verified",
        "rp_id_hash_verified",
        "user_presence_verified",
        "user_verification_verified",
        "credential_id_verified",
        "signature_verified",
        "replay_rejected",
        "user_handle_status",
        "observed_registration_sign_count",
        "previous_sign_count",
        "asserted_sign_count",
        "selected_counter_capability",
        "selected_registration_sign_count",
        "classification_verified",
        "projected_registration_consumption_id",
        "projected_registration_consumption_content_hash",
        "projected_registration_challenge_purpose",
        "projected_registration_terminal_result",
        "projected_registration_safe_result_code",
        "projected_operation_outcome_id",
        "projected_operation_outcome_content_hash",
        "projected_operation_terminal_result",
        "projected_resulting_credential_state_hash",
        "projected_credential_content_hash",
        "projected_registered_event_id",
        "projected_registered_event_content_hash",
        "projected_registered_authorization_content_hash",
        "projected_superseded_event_id",
        "projected_superseded_event_content_hash",
        "projected_superseded_authorization_content_hash",
        "consumed_at",
        "payload_json",
    ),
}


def _ordered_columns(value: str) -> tuple[str, ...]:
    return tuple(value.split())


EXPECTED_INDEX_COLUMNS = {
    "uq_0007_cc_registration_content": _ordered_columns(
        "counter_capability_registration_content_hash"
    ),
    "uq_0007_cc_registration_parent": _ordered_columns("registration_challenge_id"),
    "uq_0007_cc_registration_child": _ordered_columns("continuation_challenge_id"),
    "uq_0007_cc_registration_credential": _ordered_columns("webauthn_credential_id"),
    "uq_0007_cc_registration_credential_fingerprint": _ordered_columns("credential_id_fingerprint"),
    "uq_0007_cc_registration_public_key_fingerprint": _ordered_columns("public_key_fingerprint"),
    "uq_0007_cc_registration_exact_copy": _ordered_columns(
        "counter_capability_registration_id counter_capability_registration_content_hash "
        "reviewer_credential_operation_id operation_content_hash operation_type "
        "reviewer_principal_id reviewer_role principal_content_hash os_owner_sid_hash "
        "expected_credential_state_hash registration_challenge_id "
        "registration_challenge_binding_hash webauthn_credential_id "
        "credential_id_fingerprint public_key_fingerprint continuation_challenge_id"
    ),
    "uq_0007_cc_registration_assertion_copy": _ordered_columns(
        "counter_capability_registration_id counter_capability_registration_content_hash "
        "reviewer_credential_operation_id operation_content_hash operation_type "
        "reviewer_principal_id reviewer_role principal_content_hash os_owner_sid_hash "
        "expected_credential_state_hash webauthn_credential_id credential_id_fingerprint "
        "public_key_fingerprint"
    ),
    "ix_counter_capability_registrations_operation": _ordered_columns(
        "reviewer_credential_operation_id reviewer_principal_id"
    ),
    "uq_0007_cc_challenge_digest": _ordered_columns("challenge_digest"),
    "uq_0007_cc_challenge_binding": _ordered_columns("challenge_binding_hash"),
    "uq_0007_cc_challenge_registration": _ordered_columns("counter_capability_registration_id"),
    "uq_0007_cc_challenge_exact_child": _ordered_columns(
        "counter_capability_challenge_id counter_capability_registration_id"
    ),
    "uq_0007_cc_challenge_exact_copy": _ordered_columns(
        "counter_capability_challenge_id challenge_binding_hash "
        "counter_capability_registration_id counter_capability_registration_content_hash "
        "reviewer_credential_operation_id operation_content_hash operation_type "
        "reviewer_principal_id reviewer_role principal_content_hash os_owner_sid_hash "
        "expected_credential_state_hash webauthn_credential_id credential_id_fingerprint "
        "public_key_fingerprint"
    ),
    "ix_counter_capability_challenges_expiry": _ordered_columns("reviewer_principal_id expires_at"),
    "uq_0007_cc_assertion_content": _ordered_columns("assertion_content_hash"),
    "uq_0007_cc_assertion_challenge": _ordered_columns("counter_capability_challenge_id"),
    "uq_0007_cc_assertion_registration": _ordered_columns("counter_capability_registration_id"),
    "uq_0007_cc_assertion_consumption_projection": _ordered_columns(
        "projected_registration_consumption_id"
    ),
    "uq_0007_cc_assertion_outcome_projection": _ordered_columns("projected_operation_outcome_id"),
    "ix_counter_capability_assertions_operation": _ordered_columns(
        "reviewer_credential_operation_id projected_operation_terminal_result"
    ),
    "uq_0007_reviewer_credential_operation_outcomes_bootstrap_projection": _ordered_columns(
        "credential_operation_outcome_id outcome_content_hash "
        "reviewer_credential_operation_id operation_content_hash reviewer_principal_id "
        "reviewer_role principal_content_hash os_owner_sid_hash operation_type "
        "terminal_result terminal_consumption_id terminal_consumption_content_hash "
        "expected_credential_state_hash resulting_credential_state_hash"
    ),
    "uq_0007_credential_event_authorization_projection": _ordered_columns(
        "credential_event_id credential_event_content_hash authorization_content_hash "
        "webauthn_credential_id reviewer_credential_operation_id "
        "credential_operation_outcome_id credential_operation_outcome_content_hash "
        "event_type authorization_kind"
    ),
}

EXPECTED_FOREIGN_KEYS = {
    "reviewer_webauthn_counter_capability_registrations": {
        (
            _ordered_columns(
                "reviewer_credential_operation_id operation_content_hash "
                "reviewer_principal_id reviewer_role principal_content_hash "
                "os_owner_sid_hash operation_type expected_credential_state_hash"
            ),
            "reviewer_credential_operations",
            _ordered_columns(
                "reviewer_credential_operation_id operation_content_hash "
                "reviewer_principal_id reviewer_role principal_content_hash "
                "os_owner_sid_hash operation_type expected_credential_state_hash"
            ),
        ),
        (
            _ordered_columns(
                "registration_challenge_id reviewer_credential_operation_id "
                "reviewer_principal_id operation_type registration_challenge_purpose "
                "registration_challenge_binding_hash"
            ),
            "reviewer_credential_operation_challenges",
            _ordered_columns(
                "reviewer_credential_operation_challenge_id "
                "reviewer_credential_operation_id reviewer_principal_id operation_type "
                "challenge_purpose challenge_binding_hash"
            ),
        ),
        (
            _ordered_columns(
                "prerequisite_authentication_event_id "
                "prerequisite_authentication_content_hash reviewer_credential_operation_id "
                "reviewer_principal_id prerequisite_authentication_result"
            ),
            "reviewer_credential_operation_authentication_events",
            _ordered_columns(
                "credential_operation_authentication_event_id authentication_content_hash "
                "reviewer_credential_operation_id reviewer_principal_id authentication_result"
            ),
        ),
        (
            _ordered_columns("continuation_challenge_id counter_capability_registration_id"),
            "reviewer_webauthn_counter_capability_challenges",
            _ordered_columns("counter_capability_challenge_id counter_capability_registration_id"),
        ),
    },
    "reviewer_webauthn_counter_capability_challenges": {
        (
            _ordered_columns(
                "counter_capability_registration_id "
                "counter_capability_registration_content_hash "
                "reviewer_credential_operation_id operation_content_hash operation_type "
                "reviewer_principal_id reviewer_role principal_content_hash os_owner_sid_hash "
                "expected_credential_state_hash parent_registration_challenge_id "
                "parent_registration_challenge_binding_hash webauthn_credential_id "
                "credential_id_fingerprint public_key_fingerprint "
                "counter_capability_challenge_id"
            ),
            "reviewer_webauthn_counter_capability_registrations",
            _ordered_columns(
                "counter_capability_registration_id "
                "counter_capability_registration_content_hash "
                "reviewer_credential_operation_id operation_content_hash operation_type "
                "reviewer_principal_id reviewer_role principal_content_hash os_owner_sid_hash "
                "expected_credential_state_hash registration_challenge_id "
                "registration_challenge_binding_hash webauthn_credential_id "
                "credential_id_fingerprint public_key_fingerprint continuation_challenge_id"
            ),
        ),
        (
            _ordered_columns(
                "reviewer_credential_operation_id operation_content_hash "
                "reviewer_principal_id reviewer_role principal_content_hash "
                "os_owner_sid_hash operation_type expected_credential_state_hash"
            ),
            "reviewer_credential_operations",
            _ordered_columns(
                "reviewer_credential_operation_id operation_content_hash "
                "reviewer_principal_id reviewer_role principal_content_hash "
                "os_owner_sid_hash operation_type expected_credential_state_hash"
            ),
        ),
    },
    "reviewer_webauthn_counter_capability_assertions": {
        (
            _ordered_columns(
                "counter_capability_challenge_id challenge_binding_hash "
                "counter_capability_registration_id "
                "counter_capability_registration_content_hash "
                "reviewer_credential_operation_id operation_content_hash operation_type "
                "reviewer_principal_id reviewer_role principal_content_hash os_owner_sid_hash "
                "expected_credential_state_hash webauthn_credential_id "
                "credential_id_fingerprint public_key_fingerprint"
            ),
            "reviewer_webauthn_counter_capability_challenges",
            _ordered_columns(
                "counter_capability_challenge_id challenge_binding_hash "
                "counter_capability_registration_id "
                "counter_capability_registration_content_hash "
                "reviewer_credential_operation_id operation_content_hash operation_type "
                "reviewer_principal_id reviewer_role principal_content_hash os_owner_sid_hash "
                "expected_credential_state_hash webauthn_credential_id "
                "credential_id_fingerprint public_key_fingerprint"
            ),
        ),
        (
            _ordered_columns(
                "counter_capability_registration_id "
                "counter_capability_registration_content_hash "
                "reviewer_credential_operation_id operation_content_hash operation_type "
                "reviewer_principal_id reviewer_role principal_content_hash os_owner_sid_hash "
                "expected_credential_state_hash webauthn_credential_id "
                "credential_id_fingerprint public_key_fingerprint"
            ),
            "reviewer_webauthn_counter_capability_registrations",
            _ordered_columns(
                "counter_capability_registration_id "
                "counter_capability_registration_content_hash "
                "reviewer_credential_operation_id operation_content_hash operation_type "
                "reviewer_principal_id reviewer_role principal_content_hash os_owner_sid_hash "
                "expected_credential_state_hash webauthn_credential_id "
                "credential_id_fingerprint public_key_fingerprint"
            ),
        ),
        (
            _ordered_columns(
                "reviewer_credential_operation_id operation_content_hash "
                "reviewer_principal_id reviewer_role principal_content_hash "
                "os_owner_sid_hash operation_type expected_credential_state_hash"
            ),
            "reviewer_credential_operations",
            _ordered_columns(
                "reviewer_credential_operation_id operation_content_hash "
                "reviewer_principal_id reviewer_role principal_content_hash "
                "os_owner_sid_hash operation_type expected_credential_state_hash"
            ),
        ),
        (
            _ordered_columns(
                "projected_registration_consumption_id reviewer_credential_operation_id "
                "reviewer_principal_id projected_registration_challenge_purpose "
                "projected_registration_terminal_result "
                "projected_registration_consumption_content_hash"
            ),
            "reviewer_credential_operation_challenge_consumptions",
            _ordered_columns(
                "challenge_consumption_id reviewer_credential_operation_id "
                "reviewer_principal_id challenge_purpose terminal_result "
                "consumption_content_hash"
            ),
        ),
        (
            _ordered_columns(
                "projected_operation_outcome_id projected_operation_outcome_content_hash "
                "reviewer_credential_operation_id operation_content_hash "
                "reviewer_principal_id reviewer_role principal_content_hash os_owner_sid_hash "
                "operation_type projected_operation_terminal_result "
                "projected_registration_consumption_id "
                "projected_registration_consumption_content_hash "
                "expected_credential_state_hash projected_resulting_credential_state_hash"
            ),
            "reviewer_credential_operation_outcomes",
            _ordered_columns(
                "credential_operation_outcome_id outcome_content_hash "
                "reviewer_credential_operation_id operation_content_hash "
                "reviewer_principal_id reviewer_role principal_content_hash os_owner_sid_hash "
                "operation_type terminal_result terminal_consumption_id "
                "terminal_consumption_content_hash expected_credential_state_hash "
                "resulting_credential_state_hash"
            ),
        ),
        (
            _ordered_columns("webauthn_credential_id projected_credential_content_hash"),
            "reviewer_webauthn_credentials",
            _ordered_columns("webauthn_credential_id credential_content_hash"),
        ),
        (
            _ordered_columns("projected_registered_event_id"),
            "reviewer_webauthn_credential_events",
            _ordered_columns("credential_event_id"),
        ),
        (
            _ordered_columns("projected_superseded_event_id"),
            "reviewer_webauthn_credential_events",
            _ordered_columns("credential_event_id"),
        ),
    },
}


def _objects(engine: Engine, object_type: str) -> set[str]:
    with engine.connect() as connection:
        return {
            str(row[0])
            for row in connection.execute(
                text(
                    "SELECT name FROM sqlite_master "
                    "WHERE type=:object_type AND name NOT LIKE 'sqlite_%'"
                ),
                {"object_type": object_type},
            )
        }


def _trigger_sql(engine: Engine, name: str) -> str:
    with engine.connect() as connection:
        return str(
            connection.execute(
                text("SELECT sql FROM sqlite_master WHERE type='trigger' AND name=:name"),
                {"name": name},
            ).scalar_one()
        )


def _foreign_key_shapes(
    engine: Engine, table_name: str
) -> set[tuple[tuple[str, ...], str, tuple[str, ...]]]:
    with engine.connect() as connection:
        rows = tuple(
            connection.exec_driver_sql(f'PRAGMA foreign_key_list("{table_name}")').mappings()
        )
    grouped: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(int(row["id"]), []).append(dict(row))
    return {
        (
            tuple(str(row["from"]) for row in sorted(group, key=lambda item: item["seq"])),
            str(group[0]["table"]),
            tuple(str(row["to"]) for row in sorted(group, key=lambda item: item["seq"])),
        )
        for group in grouped.values()
    }


def _index_columns(engine: Engine, index_name: str) -> tuple[str, ...]:
    with engine.connect() as connection:
        rows = connection.exec_driver_sql(f'PRAGMA index_info("{index_name}")').mappings()
        return tuple(str(row["name"]) for row in rows)


def test_0007_identity_and_frozen_predecessor_blobs_are_exact() -> None:
    spec = importlib.util.spec_from_file_location("counter_capability_0007", REVISION_0007_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.revision == REVISION_0007
    assert module.down_revision == REVISION_0006
    versions = REVISION_0007_PATH.parent
    assert {
        name: _git_blob_id(versions / name) for name in FROZEN_MIGRATION_BLOBS
    } == FROZEN_MIGRATION_BLOBS


def test_clean_upgrade_downgrade_and_reupgrade_are_exact_and_fk_clean(
    workspace_tmp_path: Path,
) -> None:
    url = f"sqlite:///{(workspace_tmp_path / 'counter-roundtrip.sqlite3').as_posix()}"
    config = alembic_config(url)
    command.upgrade(config, REVISION_0006)
    engine = create_database_engine(url)
    old_tables = _objects(engine, "table")
    old_indexes = _objects(engine, "index")
    old_triggers = _objects(engine, "trigger")
    old_counter_sql = {name: _trigger_sql(engine, name) for name in REPLACED_COUNTER_GUARDS}
    engine.dispose()

    command.upgrade(config, REVISION_0007)
    assert _revision(url) == REVISION_0007
    engine = create_database_engine(url)
    try:
        assert _objects(engine, "table") == old_tables | COUNTER_TABLES
        assert _objects(engine, "index") == old_indexes | COUNTER_INDEXES
        assert _objects(engine, "trigger") == (old_triggers | COUNTER_GUARDS | APPEND_ONLY_GUARDS)
        assert _fk_check(engine) == ()
        reflected = inspect(engine)
        assert {
            table: tuple(column["name"] for column in reflected.get_columns(table))
            for table in COUNTER_TABLES
        } == EXPECTED_COLUMNS
        assert {
            name: _index_columns(engine, name) for name in COUNTER_INDEXES
        } == EXPECTED_INDEX_COLUMNS
        assert {
            table: _foreign_key_shapes(engine, table) for table in COUNTER_TABLES
        } == EXPECTED_FOREIGN_KEYS
        for name in REPLACED_COUNTER_GUARDS:
            expanded = _trigger_sql(engine, name)
            assert expanded != old_counter_sql[name]
            assert "reviewer_webauthn_counter_capability_assertions" in expanded
    finally:
        engine.dispose()

    command.downgrade(config, REVISION_0006)
    assert _revision(url) == REVISION_0006
    engine = create_database_engine(url)
    try:
        assert _objects(engine, "table") == old_tables
        assert _objects(engine, "index") == old_indexes
        assert _objects(engine, "trigger") == old_triggers
        assert {
            name: _trigger_sql(engine, name) for name in REPLACED_COUNTER_GUARDS
        } == old_counter_sql
        assert _fk_check(engine) == ()
    finally:
        engine.dispose()

    command.upgrade(config, REVISION_0007)
    assert _revision(url) == REVISION_0007
    engine = create_database_engine(url)
    try:
        assert _objects(engine, "table") == old_tables | COUNTER_TABLES
        assert _objects(engine, "index") == old_indexes | COUNTER_INDEXES
        assert _fk_check(engine) == ()
    finally:
        engine.dispose()


def test_late_upgrade_failure_restores_exact_0006_without_new_objects(
    workspace_tmp_path: Path,
) -> None:
    url = f"sqlite:///{(workspace_tmp_path / 'counter-upgrade-failure.sqlite3').as_posix()}"
    config = alembic_config(url)
    command.upgrade(config, REVISION_0006)
    engine = create_database_engine(url)
    old_tables = _objects(engine, "table")
    old_indexes = _objects(engine, "index")
    old_triggers = _objects(engine, "trigger")
    old_counter_sql = {name: _trigger_sql(engine, name) for name in REPLACED_COUNTER_GUARDS}

    spec = importlib.util.spec_from_file_location(
        "counter_capability_0007_fault", REVISION_0007_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        connection.commit()

        class FaultingOperations:
            def get_bind(self) -> Any:
                return connection

            def execute(self, statement: Any) -> Any:
                sql = str(statement)
                if sql.startswith(
                    "CREATE TRIGGER "
                    "trg_reviewer_credential_operation_authentication_counter_union_guard"
                ):
                    raise RuntimeError("injected late 0007 upgrade failure")
                return connection.execute(statement)

        module.op = FaultingOperations()
        with pytest.raises(RuntimeError, match="injected late 0007 upgrade failure"):
            module.upgrade()
        connection.commit()

    try:
        assert _revision(url) == REVISION_0006
        assert _objects(engine, "table") == old_tables
        assert _objects(engine, "index") == old_indexes
        assert _objects(engine, "trigger") == old_triggers
        assert {
            name: _trigger_sql(engine, name) for name in REPLACED_COUNTER_GUARDS
        } == old_counter_sql
        assert _fk_check(engine) == ()
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "operation_type", ("FIRST_ENROLLMENT", "ADD_CREDENTIAL", "REPLACE_CREDENTIAL")
)
def test_zero_registration_creates_one_pending_pair_without_public_side_effects(
    bootstrap_engine: Engine,
    operation_type: str,
) -> None:
    suffix = f"pending-{operation_type.lower()}"
    principal, operation, parent, authentication, target = _prepare_operation(
        bootstrap_engine, operation_type, suffix=suffix
    )
    registration, child = _pending_values(
        operation,
        parent,
        principal,
        suffix=suffix,
        authentication=authentication,
    )
    public_before = _active_credential_ids(bootstrap_engine, principal["principal_id"])
    with bootstrap_engine.connect() as connection:
        lifecycle_event_count_before = connection.exec_driver_sql(
            "SELECT COUNT(*) FROM reviewer_webauthn_credential_events"
        ).scalar_one()
    _insert_pending(bootstrap_engine, registration, child)
    with bootstrap_engine.connect() as connection:
        assert (
            connection.execute(
                text(
                    "SELECT COUNT(*) FROM reviewer_webauthn_counter_capability_registrations "
                    "WHERE reviewer_credential_operation_id=:operation_id"
                ),
                {"operation_id": operation["operation_id"]},
            ).scalar_one()
            == 1
        )
        assert (
            connection.execute(
                text(
                    "SELECT COUNT(*) FROM reviewer_webauthn_counter_capability_challenges "
                    "WHERE reviewer_credential_operation_id=:operation_id"
                ),
                {"operation_id": operation["operation_id"]},
            ).scalar_one()
            == 1
        )
        assert (
            connection.execute(
                text(
                    "SELECT COUNT(*) FROM reviewer_credential_operation_challenge_consumptions "
                    "WHERE reviewer_credential_operation_id=:operation_id "
                    "AND challenge_purpose='REGISTRATION_CREATE'"
                ),
                {"operation_id": operation["operation_id"]},
            ).scalar_one()
            == 0
        )
        for table in (
            "reviewer_credential_operation_outcomes",
            "reviewer_webauthn_credential_event_authorizations",
        ):
            assert (
                connection.execute(
                    text(
                        f"SELECT COUNT(*) FROM {table} "
                        "WHERE reviewer_credential_operation_id=:operation_id"
                    ),
                    {"operation_id": operation["operation_id"]},
                ).scalar_one()
                == 0
            )
        assert (
            connection.exec_driver_sql(
                "SELECT COUNT(*) FROM reviewer_webauthn_credential_events"
            ).scalar_one()
            == lifecycle_event_count_before
        )
    assert _active_credential_ids(bootstrap_engine, principal["principal_id"]) == public_before
    assert target is None or target["credential_id"] in public_before
    with pytest.raises(DBAPIError):
        _insert_pending(bootstrap_engine, registration, child)
    assert _fk_check(bootstrap_engine) == ()


@pytest.mark.parametrize(
    ("operation_type", "branch"),
    [
        (operation_type, branch)
        for operation_type in ("FIRST_ENROLLMENT", "ADD_CREDENTIAL", "REPLACE_CREDENTIAL")
        for branch in ("supported", "no_usable", "failure")
    ],
)
def test_nine_representative_terminal_transactions_are_atomic_and_fk_clean(
    bootstrap_engine: Engine,
    operation_type: str,
    branch: str,
) -> None:
    suffix = f"terminal-{operation_type.lower()}-{branch}"
    principal, operation, parent, authentication, target = _prepare_operation(
        bootstrap_engine, operation_type, suffix=suffix
    )
    authorizer_before: dict[str, Any] | None = None
    if authentication is not None:
        with bootstrap_engine.connect() as connection:
            authorizer_before = dict(
                connection.execute(
                    text(
                        "SELECT * FROM reviewer_credential_operation_authentication_events "
                        "WHERE credential_operation_authentication_event_id=:auth_id"
                    ),
                    {"auth_id": authentication["auth_id"]},
                )
                .mappings()
                .one()
            )
    public_before = _active_credential_ids(bootstrap_engine, principal["principal_id"])
    registration, child = _pending_values(
        operation,
        parent,
        principal,
        suffix=suffix,
        authentication=authentication,
    )
    _insert_pending(bootstrap_engine, registration, child)
    rows = _terminal_values(
        operation,
        parent,
        registration,
        child,
        suffix=suffix,
        branch=branch,
        authentication=authentication,
        replace_target=target,
    )
    _execute_terminal(bootstrap_engine, rows)
    assert _fk_check(bootstrap_engine) == ()

    with bootstrap_engine.connect() as connection:
        assert (
            connection.execute(
                text(
                    "SELECT COUNT(*) FROM reviewer_webauthn_counter_capability_assertions "
                    "WHERE reviewer_credential_operation_id=:operation_id"
                ),
                {"operation_id": operation["operation_id"]},
            ).scalar_one()
            == 1
        )
        assert (
            connection.execute(
                text(
                    "SELECT COUNT(*) FROM reviewer_credential_operation_challenge_consumptions "
                    "WHERE reviewer_credential_operation_id=:operation_id "
                    "AND challenge_purpose='REGISTRATION_CREATE'"
                ),
                {"operation_id": operation["operation_id"]},
            ).scalar_one()
            == 1
        )
        outcome = (
            connection.execute(
                text(
                    "SELECT terminal_result, expected_credential_state_hash, "
                    "resulting_credential_state_hash FROM reviewer_credential_operation_outcomes "
                    "WHERE reviewer_credential_operation_id=:operation_id"
                ),
                {"operation_id": operation["operation_id"]},
            )
            .mappings()
            .one()
        )
        authorization_rows = connection.execute(
            text(
                "SELECT authorization_kind, event_type "
                "FROM reviewer_webauthn_credential_event_authorizations "
                "WHERE reviewer_credential_operation_id=:operation_id "
                "ORDER BY authorization_kind"
            ),
            {"operation_id": operation["operation_id"]},
        ).all()
        event_rows = connection.execute(
            text(
                "SELECT event_type FROM reviewer_webauthn_credential_events "
                "WHERE credential_event_id IN ("
                "SELECT credential_event_id FROM reviewer_webauthn_credential_event_authorizations "
                "WHERE reviewer_credential_operation_id=:operation_id) ORDER BY event_type"
            ),
            {"operation_id": operation["operation_id"]},
        ).all()

    public_after = _active_credential_ids(bootstrap_engine, principal["principal_id"])
    if branch == "failure":
        assert outcome["terminal_result"] == "FAILED_CLOSED"
        assert (
            outcome["resulting_credential_state_hash"] == outcome["expected_credential_state_hash"]
        )
        assert authorization_rows == []
        assert event_rows == []
        assert public_after == public_before
    else:
        assert outcome["terminal_result"] == "SUCCEEDED"
        assert (
            outcome["resulting_credential_state_hash"] != outcome["expected_credential_state_hash"]
        )
        expected_auth = (
            [("AUTHORIZED_REGISTRATION", "REGISTERED"), ("AUTHORIZED_SUPERSESSION", "SUPERSEDED")]
            if operation_type == "REPLACE_CREDENTIAL"
            else [
                (
                    "BOOTSTRAP_REGISTRATION"
                    if operation_type == "FIRST_ENROLLMENT"
                    else "AUTHORIZED_REGISTRATION",
                    "REGISTERED",
                )
            ]
        )
        assert authorization_rows == expected_auth
        assert event_rows == (
            [("REGISTERED",), ("SUPERSEDED",)]
            if operation_type == "REPLACE_CREDENTIAL"
            else [("REGISTERED",)]
        )
        assert registration["credential_id"] in public_after
        with bootstrap_engine.connect() as connection:
            new_credential = (
                connection.execute(
                    text(
                        "SELECT counter_capability, registration_sign_count "
                        "FROM reviewer_webauthn_credentials "
                        "WHERE webauthn_credential_id=:credential_id"
                    ),
                    {"credential_id": registration["credential_id"]},
                )
                .mappings()
                .one()
            )
        assert new_credential["counter_capability"] == (
            "SIGN_COUNT_SUPPORTED" if branch == "supported" else "NO_USABLE_COUNTER"
        )
        assert new_credential["registration_sign_count"] == (0 if branch == "supported" else None)
        if operation_type == "REPLACE_CREDENTIAL":
            assert target is not None
            assert target["credential_id"] not in public_after
    if authentication is not None:
        with bootstrap_engine.connect() as connection:
            authorizer_after = dict(
                connection.execute(
                    text(
                        "SELECT * FROM reviewer_credential_operation_authentication_events "
                        "WHERE credential_operation_authentication_event_id=:auth_id"
                    ),
                    {"auth_id": authentication["auth_id"]},
                )
                .mappings()
                .one()
            )
        assert authorizer_after == authorizer_before


def test_replace_preserves_an_unrelated_active_credential_exactly(
    bootstrap_engine: Engine,
) -> None:
    principal, first_operation, target, first_outcome = _seed_first_credential(
        bootstrap_engine,
        suffix="unrelated-preservation-first",
        registration_sign_count=5,
    )
    add_operation = _issue_normative_operation(
        bootstrap_engine,
        principal,
        suffix="unrelated-preservation-add",
        operation_type="ADD_CREDENTIAL",
        expected_state=str(first_outcome["resulting_state"]),
        predecessor_id=str(first_operation["operation_id"]),
    )
    add_authentication, add_parent, _add_consumption = _authorize_normative_management(
        bootstrap_engine,
        add_operation,
        target,
        suffix="unrelated-preservation-add",
    )
    add_registration, add_child = _pending_values(
        add_operation,
        add_parent,
        principal,
        suffix="unrelated-preservation-add",
        authentication=add_authentication,
    )
    _insert_pending(bootstrap_engine, add_registration, add_child)
    add_rows = _terminal_values(
        add_operation,
        add_parent,
        add_registration,
        add_child,
        suffix="unrelated-preservation-add",
        branch="supported",
        authentication=add_authentication,
        replace_target=None,
    )
    _execute_terminal(bootstrap_engine, add_rows)
    sentinel = add_rows["credential"]
    assert sentinel is not None

    with bootstrap_engine.connect() as connection:
        sentinel_credential_before = dict(
            connection.execute(
                text(
                    "SELECT * FROM reviewer_webauthn_credentials "
                    "WHERE webauthn_credential_id=:credential_id"
                ),
                {"credential_id": sentinel["credential_id"]},
            )
            .mappings()
            .one()
        )
        sentinel_events_before = tuple(
            dict(row)
            for row in connection.execute(
                text(
                    "SELECT * FROM reviewer_webauthn_credential_events "
                    "WHERE webauthn_credential_id=:credential_id ORDER BY credential_event_id"
                ),
                {"credential_id": sentinel["credential_id"]},
            ).mappings()
        )

    replace_operation = _issue_normative_operation(
        bootstrap_engine,
        principal,
        suffix="unrelated-preservation-replace",
        operation_type="REPLACE_CREDENTIAL",
        expected_state=str(add_rows["outcome"]["resulting_state"]),
        predecessor_id=str(add_operation["operation_id"]),
        target=target,
    )
    replace_authentication, replace_parent, _replace_consumption = _authorize_normative_management(
        bootstrap_engine,
        replace_operation,
        target,
        suffix="unrelated-preservation-replace",
        previous_sign_count=6,
    )
    replace_registration, replace_child = _pending_values(
        replace_operation,
        replace_parent,
        principal,
        suffix="unrelated-preservation-replace",
        authentication=replace_authentication,
    )
    _insert_pending(bootstrap_engine, replace_registration, replace_child)
    replace_rows = _terminal_values(
        replace_operation,
        replace_parent,
        replace_registration,
        replace_child,
        suffix="unrelated-preservation-replace",
        branch="supported",
        authentication=replace_authentication,
        replace_target=target,
    )
    active_before = _active_credential_ids(bootstrap_engine, principal["principal_id"])
    _execute_terminal(bootstrap_engine, replace_rows)

    replacement = replace_rows["credential"]
    assert replacement is not None
    assert set(_active_credential_ids(bootstrap_engine, principal["principal_id"])) == (
        set(active_before) - {target["credential_id"]}
    ) | {replacement["credential_id"]}
    with bootstrap_engine.connect() as connection:
        assert (
            dict(
                connection.execute(
                    text(
                        "SELECT * FROM reviewer_webauthn_credentials "
                        "WHERE webauthn_credential_id=:credential_id"
                    ),
                    {"credential_id": sentinel["credential_id"]},
                )
                .mappings()
                .one()
            )
            == sentinel_credential_before
        )
        assert (
            tuple(
                dict(row)
                for row in connection.execute(
                    text(
                        "SELECT * FROM reviewer_webauthn_credential_events "
                        "WHERE webauthn_credential_id=:credential_id ORDER BY credential_event_id"
                    ),
                    {"credential_id": sentinel["credential_id"]},
                ).mappings()
            )
            == sentinel_events_before
        )
    assert _fk_check(bootstrap_engine) == ()


@pytest.mark.parametrize(
    "operation_type", ("FIRST_ENROLLMENT", "ADD_CREDENTIAL", "REPLACE_CREDENTIAL")
)
def test_expiry_terminalizes_fail_closed_without_lifecycle_writes(
    bootstrap_engine: Engine,
    operation_type: str,
) -> None:
    suffix = f"expiry-{operation_type.lower()}"
    principal, operation, parent, authentication, target = _prepare_operation(
        bootstrap_engine, operation_type, suffix=suffix
    )
    public_before = _active_credential_ids(bootstrap_engine, principal["principal_id"])
    registration, child = _pending_values(
        operation,
        parent,
        principal,
        suffix=suffix,
        authentication=authentication,
    )
    _insert_pending(bootstrap_engine, registration, child)
    rows = _terminal_values(
        operation,
        parent,
        registration,
        child,
        suffix=suffix,
        branch="expired",
        authentication=authentication,
        replace_target=target,
    )
    _execute_terminal(bootstrap_engine, rows)
    with bootstrap_engine.connect() as connection:
        assertion_result = connection.execute(
            text(
                "SELECT challenge_terminal_result, projected_operation_terminal_result, "
                "expected_credential_state_hash, projected_resulting_credential_state_hash "
                "FROM reviewer_webauthn_counter_capability_assertions "
                "WHERE counter_capability_assertion_id=:assertion_id"
            ),
            {"assertion_id": rows["assertion"]["assertion_id"]},
        ).one()
        assert assertion_result == (
            "EXPIRED",
            "EXPIRED",
            operation["expected_state"],
            operation["expected_state"],
        )
        for table in (
            "reviewer_webauthn_credential_event_authorizations",
            "reviewer_webauthn_credential_events",
        ):
            query = f"SELECT COUNT(*) FROM {table} WHERE " + (
                "reviewer_credential_operation_id=:operation_id"
                if table.endswith("authorizations")
                else "credential_event_id IN ("
                "SELECT credential_event_id FROM reviewer_webauthn_credential_event_authorizations "
                "WHERE reviewer_credential_operation_id=:operation_id)"
            )
            assert (
                connection.execute(
                    text(query), {"operation_id": operation["operation_id"]}
                ).scalar_one()
                == 0
            )
    assert _active_credential_ids(bootstrap_engine, principal["principal_id"]) == public_before
    assert _fk_check(bootstrap_engine) == ()


@pytest.mark.parametrize(
    ("operation_type", "parent_state"),
    [
        (operation_type, parent_state)
        for operation_type in ("FIRST_ENROLLMENT", "ADD_CREDENTIAL", "REPLACE_CREDENTIAL")
        for parent_state in ("expired", "consumed", "terminal")
    ],
)
def test_pending_rejects_expired_consumed_and_terminal_parents(
    bootstrap_engine: Engine,
    operation_type: str,
    parent_state: str,
) -> None:
    suffix = f"parent-{operation_type.lower()}-{parent_state}"
    principal, operation, parent, authentication, _target = _prepare_operation(
        bootstrap_engine, operation_type, suffix=suffix
    )
    registration, child = _pending_values(
        operation,
        parent,
        principal,
        suffix=suffix,
        authentication=authentication,
    )
    if parent_state == "expired":
        registration["verified_at"] = "2026-08-28T00:09:00Z"
        with pytest.raises(DBAPIError, match="live parent mismatch"):
            _insert_pending(bootstrap_engine, registration, child)
    else:
        outcome_id = f"outcome-{suffix}-existing"
        consumption = _consumption_values(
            operation,
            parent,
            suffix=f"{suffix}-existing",
            terminal_result="INVALID_REGISTRATION",
            resulting_state=str(operation["expected_state"]),
            outcome_id=outcome_id,
            consumed_at="2026-08-28T00:05:00Z",
        )
        if parent_state == "consumed":
            with bootstrap_engine.connect() as connection:
                connection.exec_driver_sql("BEGIN IMMEDIATE")
                try:
                    connection.execute(CONSUMPTION_INSERT, consumption)
                    with pytest.raises(DBAPIError, match="already consumed"):
                        connection.execute(REGISTRATION_INSERT, registration)
                finally:
                    connection.rollback()
        else:
            outcome = _outcome_values(
                operation,
                consumption,
                suffix=f"{suffix}-existing",
                auth=authentication,
            )
            with bootstrap_engine.begin() as connection:
                connection.execute(CONSUMPTION_INSERT, consumption)
                connection.execute(OUTCOME_INSERT, outcome)
            with pytest.raises(DBAPIError, match="already consumed|already terminal"):
                _insert_pending(bootstrap_engine, registration, child)
    assert _fk_check(bootstrap_engine) == ()


@pytest.mark.parametrize(
    "operation_type", ("FIRST_ENROLLMENT", "ADD_CREDENTIAL", "REPLACE_CREDENTIAL")
)
def test_pending_child_expiry_later_than_parent_rolls_back_the_pair(
    bootstrap_engine: Engine,
    operation_type: str,
) -> None:
    suffix = f"child-expiry-{operation_type.lower()}"
    principal, operation, parent, authentication, _target = _prepare_operation(
        bootstrap_engine, operation_type, suffix=suffix
    )
    registration, child = _pending_values(
        operation,
        parent,
        principal,
        suffix=suffix,
        authentication=authentication,
        child_expires_at="2026-08-28T00:09:00Z",
    )
    with pytest.raises(DBAPIError, match="parent expiry mismatch"):
        _insert_pending(bootstrap_engine, registration, child)
    with bootstrap_engine.connect() as connection:
        assert (
            connection.execute(
                text(
                    "SELECT COUNT(*) FROM reviewer_webauthn_counter_capability_registrations "
                    "WHERE counter_capability_registration_id=:registration_id"
                ),
                {"registration_id": registration["registration_id"]},
            ).scalar_one()
            == 0
        )
    assert _fk_check(bootstrap_engine) == ()


def test_all_new_ledgers_reject_update_and_delete(bootstrap_engine: Engine) -> None:
    principal, operation, parent, authentication, target = _prepare_operation(
        bootstrap_engine, "FIRST_ENROLLMENT", suffix="append-only"
    )
    registration, child = _pending_values(
        operation,
        parent,
        principal,
        suffix="append-only",
        authentication=authentication,
    )
    _insert_pending(bootstrap_engine, registration, child)
    rows = _terminal_values(
        operation,
        parent,
        registration,
        child,
        suffix="append-only",
        branch="supported",
        authentication=authentication,
        replace_target=target,
    )
    _execute_terminal(bootstrap_engine, rows)
    primary_keys = {
        "reviewer_webauthn_counter_capability_registrations": (
            "counter_capability_registration_id",
            registration["registration_id"],
        ),
        "reviewer_webauthn_counter_capability_challenges": (
            "counter_capability_challenge_id",
            child["child_id"],
        ),
        "reviewer_webauthn_counter_capability_assertions": (
            "counter_capability_assertion_id",
            rows["assertion"]["assertion_id"],
        ),
    }
    for table, (column, value) in primary_keys.items():
        with pytest.raises(DBAPIError, match="append-only"):
            with bootstrap_engine.begin() as connection:
                connection.execute(
                    text(f"UPDATE {table} SET payload_json=payload_json WHERE {column}=:value"),
                    {"value": value},
                )
        with pytest.raises(DBAPIError, match="append-only"):
            with bootstrap_engine.begin() as connection:
                connection.execute(
                    text(f"DELETE FROM {table} WHERE {column}=:value"),
                    {"value": value},
                )
    assert _fk_check(bootstrap_engine) == ()


def test_nonempty_0007_ledger_refuses_destructive_downgrade(
    workspace_tmp_path: Path,
) -> None:
    url = f"sqlite:///{(workspace_tmp_path / 'counter-nonempty.sqlite3').as_posix()}"
    config = alembic_config(url)
    command.upgrade(config, REVISION_0007)
    engine = create_database_engine(url)
    try:
        principal, operation, parent, authentication, _target = _prepare_operation(
            engine, "FIRST_ENROLLMENT", suffix="nonempty-downgrade"
        )
        registration, child = _pending_values(
            operation,
            parent,
            principal,
            suffix="nonempty-downgrade",
            authentication=authentication,
        )
        _insert_pending(engine, registration, child)
        before_tables = _objects(engine, "table")
        before_indexes = _objects(engine, "index")
        before_triggers = _objects(engine, "trigger")
        before_counter_sql = {name: _trigger_sql(engine, name) for name in REPLACED_COUNTER_GUARDS}
        with engine.connect() as connection:
            before_rows = {
                table: connection.exec_driver_sql(f'SELECT COUNT(*) FROM "{table}"').scalar_one()
                for table in COUNTER_TABLES
            }
        assert before_rows == {
            "reviewer_webauthn_counter_capability_registrations": 1,
            "reviewer_webauthn_counter_capability_challenges": 1,
            "reviewer_webauthn_counter_capability_assertions": 0,
        }
        assert _fk_check(engine) == ()
    finally:
        engine.dispose()
    with pytest.raises(RuntimeError, match="destructive downgrade refused"):
        command.downgrade(config, REVISION_0006)
    assert _revision(url) == REVISION_0007
    engine = create_database_engine(url)
    try:
        assert _objects(engine, "table") == before_tables
        assert _objects(engine, "index") == before_indexes
        assert _objects(engine, "trigger") == before_triggers
        assert {
            name: _trigger_sql(engine, name) for name in REPLACED_COUNTER_GUARDS
        } == before_counter_sql
        with engine.connect() as connection:
            assert {
                table: connection.exec_driver_sql(f'SELECT COUNT(*) FROM "{table}"').scalar_one()
                for table in COUNTER_TABLES
            } == before_rows
        assert _fk_check(engine) == ()
    finally:
        engine.dispose()


def _prepare_pending_case(
    engine: Engine,
    *,
    suffix: str,
    operation_type: str = "FIRST_ENROLLMENT",
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any] | None,
    dict[str, Any] | None,
]:
    principal, operation, parent, authentication, target = _prepare_operation(
        engine, operation_type, suffix=suffix
    )
    registration, child = _pending_values(
        operation,
        parent,
        principal,
        suffix=suffix,
        authentication=authentication,
    )
    _insert_pending(engine, registration, child)
    return principal, operation, parent, registration, child, authentication, target


def test_exact_success_order_succeeds_and_selected_reorderings_fail_immediately(
    bootstrap_engine: Engine,
) -> None:
    (
        _principal,
        operation,
        parent,
        registration,
        child,
        authentication,
        target,
    ) = _prepare_pending_case(bootstrap_engine, suffix="order")
    rows = _terminal_values(
        operation,
        parent,
        registration,
        child,
        suffix="order",
        branch="supported",
        authentication=authentication,
        replace_target=target,
    )
    with pytest.raises(DBAPIError, match="assertion projection"):
        _execute_terminal(bootstrap_engine, rows, order=("consumption",))
    with pytest.raises(DBAPIError, match="authorization|credential|event|projection"):
        _execute_terminal(
            bootstrap_engine,
            rows,
            order=("assertion", "consumption", "outcome"),
        )
    _execute_terminal(bootstrap_engine, rows)
    assert _fk_check(bootstrap_engine) == ()


@pytest.mark.parametrize(
    ("field", "bad_value"),
    (
        ("principal_id", "reviewer-principal-wrong"),
        ("operation_hash", _h("wrong-operation-hash")),
        ("sid_hash", _h("wrong-sid-hash")),
        ("credential_id", "d3JvbmctY3JlZGVudGlhbA"),
        ("credential_fingerprint", _h("wrong-credential-fingerprint")),
        ("public_key_fingerprint", _h("wrong-public-key-fingerprint")),
        ("child_id", "counter-challenge-wrong"),
        ("projected_purpose", "AUTHORIZATION_ASSERTION"),
        ("projected_purpose", None),
        ("outcome_id", "outcome-wrong"),
        ("outcome_hash", _h("wrong-outcome-hash")),
        ("resulting_state", _h("wrong-resulting-state")),
    ),
)
def test_mismatched_assertion_projections_are_rejected(
    bootstrap_engine: Engine,
    field: str,
    bad_value: Any,
) -> None:
    suffix = f"projection-{field}-{str(bad_value)[-8:]}"
    (
        _principal,
        operation,
        parent,
        registration,
        child,
        authentication,
        target,
    ) = _prepare_pending_case(bootstrap_engine, suffix=suffix)
    rows = _terminal_values(
        operation,
        parent,
        registration,
        child,
        suffix=suffix,
        branch="supported",
        authentication=authentication,
        replace_target=target,
    )
    rows["assertion"] = {**rows["assertion"], field: bad_value}
    with pytest.raises(DBAPIError):
        _execute_terminal(bootstrap_engine, rows)
    with bootstrap_engine.connect() as connection:
        assert (
            connection.execute(
                text(
                    "SELECT COUNT(*) FROM reviewer_webauthn_counter_capability_assertions "
                    "WHERE counter_capability_assertion_id=:assertion_id"
                ),
                {"assertion_id": rows["assertion"]["assertion_id"]},
            ).scalar_one()
            == 0
        )
    assert _fk_check(bootstrap_engine) == ()


@pytest.mark.parametrize(
    "child_result",
    (
        "BINDING_MISMATCH",
        "ORIGIN_RP_MISMATCH",
        "USER_PRESENCE_ABSENT",
        "USER_VERIFICATION_ABSENT",
        "INVALID_SIGNATURE",
        "REPLAY_REJECTED",
    ),
)
def test_failure_result_requires_a_matching_failed_verification_fact(
    bootstrap_engine: Engine,
    child_result: str,
) -> None:
    suffix = f"failure-matrix-{child_result.lower()}"
    (
        _principal,
        operation,
        parent,
        registration,
        child,
        authentication,
        target,
    ) = _prepare_pending_case(bootstrap_engine, suffix=suffix)
    rows = _terminal_values(
        operation,
        parent,
        registration,
        child,
        suffix=suffix,
        branch="failure",
        authentication=authentication,
        replace_target=target,
    )
    rows["assertion"].update(
        {
            "child_result": child_result,
            "client_type_ok": 1,
            "challenge_ok": 1,
            "origin_ok": 1,
            "cross_origin_ok": 1,
            "rp_ok": 1,
            "up_ok": 1,
            "uv_ok": 1,
            "credential_id_ok": 1,
            "signature_ok": 1,
            "replay_ok": 1,
            "user_handle_status": "MATCHED",
        }
    )
    with pytest.raises(DBAPIError):
        _execute_terminal(bootstrap_engine, rows)
    assert _fk_check(bootstrap_engine) == ()


def test_assertion_consumption_cannot_predate_child_challenge_issuance(
    bootstrap_engine: Engine,
) -> None:
    (
        _principal,
        operation,
        parent,
        registration,
        child,
        authentication,
        target,
    ) = _prepare_pending_case(bootstrap_engine, suffix="before-child-issued")
    rows = _terminal_values(
        operation,
        parent,
        registration,
        child,
        suffix="before-child-issued",
        branch="failure",
        authentication=authentication,
        replace_target=target,
    )
    before_issuance = "2026-08-28T00:03:59Z"
    rows["assertion"]["consumed_at"] = before_issuance
    rows["consumption"]["consumed_at"] = before_issuance
    rows["outcome"]["completed_at"] = before_issuance
    with pytest.raises(DBAPIError):
        _execute_terminal(bootstrap_engine, rows)
    assert _fk_check(bootstrap_engine) == ()


def test_child_and_overall_safe_codes_project_to_their_exact_frozen_roles(
    bootstrap_engine: Engine,
) -> None:
    (
        _principal,
        operation,
        parent,
        registration,
        child,
        authentication,
        target,
    ) = _prepare_pending_case(bootstrap_engine, suffix="distinct-safe-codes")
    rows = _terminal_values(
        operation,
        parent,
        registration,
        child,
        suffix="distinct-safe-codes",
        branch="failure",
        authentication=authentication,
        replace_target=target,
    )
    child_code = "COUNTER_CAPABILITY_CHILD_INVALID_SIGNATURE"
    overall_code = "COUNTER_CAPABILITY_ASSERTION_FAILED"
    rows["assertion"]["safe_result_code"] = child_code
    rows["assertion"]["registration_safe_result_code"] = overall_code
    rows["consumption"]["safe_result_code"] = overall_code
    rows["outcome"]["safe_result_code"] = child_code

    with pytest.raises(DBAPIError):
        _execute_terminal(bootstrap_engine, rows)

    rows["outcome"]["safe_result_code"] = overall_code

    _execute_terminal(bootstrap_engine, rows)
    with bootstrap_engine.connect() as connection:
        assert connection.execute(
            text(
                "SELECT safe_result_code, projected_registration_safe_result_code "
                "FROM reviewer_webauthn_counter_capability_assertions "
                "WHERE counter_capability_assertion_id=:assertion_id"
            ),
            {"assertion_id": rows["assertion"]["assertion_id"]},
        ).one() == (child_code, overall_code)
        assert (
            connection.execute(
                text(
                    "SELECT safe_result_code "
                    "FROM reviewer_credential_operation_challenge_consumptions "
                    "WHERE challenge_consumption_id=:consumption_id"
                ),
                {"consumption_id": rows["consumption"]["consumption_id"]},
            ).scalar_one()
            == overall_code
        )
        assert (
            connection.execute(
                text(
                    "SELECT safe_result_code FROM reviewer_credential_operation_outcomes "
                    "WHERE credential_operation_outcome_id=:outcome_id"
                ),
                {"outcome_id": rows["outcome"]["outcome_id"]},
            ).scalar_one()
            == overall_code
        )
    assert _fk_check(bootstrap_engine) == ()


def test_wrong_parent_registration_challenge_is_rejected(
    bootstrap_engine: Engine,
) -> None:
    principal, operation, parent, authentication, _target = _prepare_operation(
        bootstrap_engine, "FIRST_ENROLLMENT", suffix="wrong-parent"
    )
    registration, child = _pending_values(
        operation,
        parent,
        principal,
        suffix="wrong-parent",
        authentication=authentication,
    )
    registration["parent_id"] = "challenge-wrong-parent"
    with pytest.raises(DBAPIError, match="live parent mismatch"):
        _insert_pending(bootstrap_engine, registration, child)
    assert _fk_check(bootstrap_engine) == ()


@pytest.mark.parametrize("operation_type", ("FIRST_ENROLLMENT", "ADD_CREDENTIAL"))
def test_first_and_add_cannot_project_supersession(
    bootstrap_engine: Engine,
    operation_type: str,
) -> None:
    suffix = f"unexpected-supersession-{operation_type.lower()}"
    (
        _principal,
        operation,
        parent,
        registration,
        child,
        authentication,
        target,
    ) = _prepare_pending_case(bootstrap_engine, suffix=suffix, operation_type=operation_type)
    rows = _terminal_values(
        operation,
        parent,
        registration,
        child,
        suffix=suffix,
        branch="supported",
        authentication=authentication,
        replace_target=target,
    )
    rows["assertion"] = {
        **rows["assertion"],
        "superseded_event_id": "credential-event-invented-superseded",
        "superseded_event_hash": _h("credential-event-invented-superseded"),
        "superseded_authorization_hash": _h("authorization-invented-superseded"),
    }
    with pytest.raises(DBAPIError):
        _execute_terminal(bootstrap_engine, rows)
    assert _fk_check(bootstrap_engine) == ()


def test_replace_success_requires_exact_supersession_projection(
    bootstrap_engine: Engine,
) -> None:
    (
        _principal,
        operation,
        parent,
        registration,
        child,
        authentication,
        target,
    ) = _prepare_pending_case(
        bootstrap_engine,
        suffix="missing-supersession",
        operation_type="REPLACE_CREDENTIAL",
    )
    rows = _terminal_values(
        operation,
        parent,
        registration,
        child,
        suffix="missing-supersession",
        branch="supported",
        authentication=authentication,
        replace_target=target,
    )
    rows["assertion"] = {
        **rows["assertion"],
        "superseded_event_id": None,
        "superseded_event_hash": None,
        "superseded_authorization_hash": None,
    }
    with pytest.raises(DBAPIError):
        _execute_terminal(bootstrap_engine, rows)
    assert _fk_check(bootstrap_engine) == ()


def test_fake_success_without_lifecycle_authorization_is_rejected(
    bootstrap_engine: Engine,
) -> None:
    (
        _principal,
        operation,
        parent,
        registration,
        child,
        authentication,
        target,
    ) = _prepare_pending_case(bootstrap_engine, suffix="fake-success")
    rows = _terminal_values(
        operation,
        parent,
        registration,
        child,
        suffix="fake-success",
        branch="supported",
        authentication=authentication,
        replace_target=target,
    )
    with pytest.raises(DBAPIError):
        _execute_terminal(
            bootstrap_engine,
            rows,
            order=("assertion", "consumption", "credential", "registered_event", "outcome"),
        )
    assert _fk_check(bootstrap_engine) == ()


def test_public_credential_without_bootstrap_assertion_is_rejected(
    bootstrap_engine: Engine,
) -> None:
    (
        _principal,
        operation,
        parent,
        registration,
        child,
        authentication,
        target,
    ) = _prepare_pending_case(bootstrap_engine, suffix="fake-credential")
    rows = _terminal_values(
        operation,
        parent,
        registration,
        child,
        suffix="fake-credential",
        branch="supported",
        authentication=authentication,
        replace_target=target,
    )
    with pytest.raises(DBAPIError, match="bootstrap assertion"):
        with bootstrap_engine.begin() as connection:
            connection.execute(BOOTSTRAP_CREDENTIAL_INSERT, rows["credential"])
    assert _fk_check(bootstrap_engine) == ()


@pytest.mark.parametrize("write_kind", ("credential", "event"))
def test_failed_assertion_cannot_write_credential_or_event(
    bootstrap_engine: Engine,
    write_kind: str,
) -> None:
    (
        _principal,
        operation,
        parent,
        registration,
        child,
        authentication,
        target,
    ) = _prepare_pending_case(bootstrap_engine, suffix=f"failed-write-{write_kind}")
    failed = _terminal_values(
        operation,
        parent,
        registration,
        child,
        suffix=f"failed-write-{write_kind}",
        branch="failure",
        authentication=authentication,
        replace_target=target,
    )
    successful = _terminal_values(
        operation,
        parent,
        registration,
        child,
        suffix=f"failed-write-{write_kind}-invented",
        branch="supported",
        authentication=authentication,
        replace_target=target,
    )
    statement, values = (
        (BOOTSTRAP_CREDENTIAL_INSERT, successful["credential"])
        if write_kind == "credential"
        else (EVENT_INSERT, successful["registered_event"])
    )
    assert values is not None
    with bootstrap_engine.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        try:
            connection.execute(ASSERTION_INSERT, failed["assertion"])
            connection.execute(CONSUMPTION_INSERT, failed["consumption"])
            with pytest.raises(DBAPIError):
                connection.execute(statement, values)
        finally:
            connection.rollback()
    assert _fk_check(bootstrap_engine) == ()


def test_duplicate_consumption_and_outcome_are_rejected(
    bootstrap_engine: Engine,
) -> None:
    (
        _principal,
        operation,
        parent,
        registration,
        child,
        authentication,
        target,
    ) = _prepare_pending_case(bootstrap_engine, suffix="duplicate-terminal")
    rows = _terminal_values(
        operation,
        parent,
        registration,
        child,
        suffix="duplicate-terminal",
        branch="supported",
        authentication=authentication,
        replace_target=target,
    )
    _execute_terminal(bootstrap_engine, rows)
    with pytest.raises(DBAPIError):
        with bootstrap_engine.begin() as connection:
            connection.execute(CONSUMPTION_INSERT, rows["consumption"])
    with pytest.raises(DBAPIError):
        with bootstrap_engine.begin() as connection:
            connection.execute(OUTCOME_INSERT, rows["outcome"])
    assert _fk_check(bootstrap_engine) == ()


def test_supported_bootstrap_extends_counter_union_and_rejects_duplicate_edge(
    bootstrap_engine: Engine,
) -> None:
    (
        principal,
        operation,
        parent,
        registration,
        child,
        authentication,
        target,
    ) = _prepare_pending_case(bootstrap_engine, suffix="counter-union")
    rows = _terminal_values(
        operation,
        parent,
        registration,
        child,
        suffix="counter-union",
        branch="supported",
        authentication=authentication,
        replace_target=target,
    )
    _execute_terminal(bootstrap_engine, rows)
    credential = rows["credential"]
    assert credential is not None
    authorizer = {
        key: credential[key]
        for key in (
            "credential_id",
            "credential_fingerprint",
            "public_key_fingerprint",
            "counter_capability",
            "registration_sign_count",
        )
    }
    next_operation = _issue_normative_operation(
        bootstrap_engine,
        principal,
        suffix="counter-union-next",
        operation_type="ADD_CREDENTIAL",
        expected_state=rows["outcome"]["resulting_state"],
        predecessor_id=operation["operation_id"],
    )
    next_authentication, _continuation, _consumption = _authorize_normative_management(
        bootstrap_engine,
        next_operation,
        authorizer,
        suffix="counter-union-next",
        previous_sign_count=1,
    )
    assert next_authentication["previous_sign_count"] == 1
    assert next_authentication["asserted_sign_count"] == 2
    duplicate = copy.deepcopy(next_authentication)
    duplicate["auth_id"] = "operation-auth-counter-union-duplicate"
    duplicate["auth_hash"] = _h("operation-auth-counter-union-duplicate")
    with pytest.raises(DBAPIError, match="unique union leaf|fork or duplicate"):
        with bootstrap_engine.begin() as connection:
            connection.execute(OPERATION_AUTH_INSERT, duplicate)
    fork = copy.deepcopy(next_authentication)
    fork["auth_id"] = "operation-auth-counter-union-fork"
    fork["auth_hash"] = _h("operation-auth-counter-union-fork")
    fork["asserted_sign_count"] = 3
    with pytest.raises(DBAPIError, match="unique union leaf|fork or duplicate"):
        with bootstrap_engine.begin() as connection:
            connection.execute(OPERATION_AUTH_INSERT, fork)
    assert _fk_check(bootstrap_engine) == ()


def test_no_usable_counter_preserves_both_observed_zeros_without_fabrication(
    bootstrap_engine: Engine,
) -> None:
    (
        _principal,
        operation,
        parent,
        registration,
        child,
        authentication,
        target,
    ) = _prepare_pending_case(bootstrap_engine, suffix="no-counter-evidence")
    rows = _terminal_values(
        operation,
        parent,
        registration,
        child,
        suffix="no-counter-evidence",
        branch="no_usable",
        authentication=authentication,
        replace_target=target,
    )
    _execute_terminal(bootstrap_engine, rows)
    with bootstrap_engine.connect() as connection:
        evidence = connection.execute(
            text(
                "SELECT observed_registration_sign_count, previous_sign_count, "
                "asserted_sign_count, selected_registration_sign_count "
                "FROM reviewer_webauthn_counter_capability_assertions "
                "WHERE counter_capability_assertion_id=:assertion_id"
            ),
            {"assertion_id": rows["assertion"]["assertion_id"]},
        ).one()
        public_count = connection.execute(
            text(
                "SELECT registration_sign_count FROM reviewer_webauthn_credentials "
                "WHERE webauthn_credential_id=:credential_id"
            ),
            {"credential_id": registration["credential_id"]},
        ).scalar_one()
    assert evidence == (0, 0, 0, None)
    assert public_count is None
    assert _fk_check(bootstrap_engine) == ()


def test_positive_registration_count_direct_path_remains_unaffected(
    bootstrap_engine: Engine,
) -> None:
    principal, _operation, credential, _outcome = _seed_first_credential(
        bootstrap_engine,
        suffix="positive-direct",
        registration_sign_count=7,
    )
    assert credential["credential_id"] in _active_credential_ids(
        bootstrap_engine, principal["principal_id"]
    )
    with bootstrap_engine.connect() as connection:
        assert (
            sum(
                int(connection.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one())
                for table in COUNTER_TABLES
            )
            == 0
        )
    assert _fk_check(bootstrap_engine) == ()
