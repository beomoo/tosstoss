# ruff: noqa: E501
"""Phase 2 CP3-C2-B2-C counter-capability bootstrap ledger.

Revision 0007 is additive. It admits a registration ``signCount`` of zero only
after one exact pending-credential assertion classifies the credential as
``SIGN_COUNT_SUPPORTED`` or ``NO_USABLE_COUNTER``. Runtime ceremony behavior is
deliberately outside this migration.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import Connection

revision = "0007_phase_02_cp3_c2_b2_c_counter_capability_bootstrap"
down_revision = "0006_phase_02_cp3_c2_b2_c_reviewer_operations"
branch_labels = None
depends_on = None

_FROZEN_MIGRATION_BLOBS = {
    "0001_phase_01_foundation.py": "d00355c2456021e6ffb195e50833adc32c74a4ad",
    "0002_phase_02_cp3_foundation.py": "53f40664eca2ea2466cc6154b8579c5db506e0ba",
    "0003_phase_02_cp3_b_invariants.py": "47d5a69009949b155211cd68209640136a7cacd9",
    "0004_phase_02_cp3_c1_security_master.py": "91b4d96a445be23e7aa55e08b9310dc7334a026d",
    "0005_phase_02_cp3_c2_b_issuer_authority.py": "81976b8f70a1f6107526a13acadf23f369b196e3",
    "0006_phase_02_cp3_c2_b2_c_reviewer_operations.py": "f10e7f5bc21e232fc68b38144f5b8fb124f31698",
}

_REGISTRATIONS = "reviewer_webauthn_counter_capability_registrations"
_CHALLENGES = "reviewer_webauthn_counter_capability_challenges"
_ASSERTIONS = "reviewer_webauthn_counter_capability_assertions"
_NEW_TABLE_NAMES = (_REGISTRATIONS, _CHALLENGES, _ASSERTIONS)

_NEW_TABLE_DDL: tuple[tuple[str, str], ...] = (
    (
        _REGISTRATIONS,
        """CREATE TABLE reviewer_webauthn_counter_capability_registrations (
    counter_capability_registration_id VARCHAR(128) NOT NULL,
    contract_version VARCHAR(64) NOT NULL,
    counter_capability_registration_content_hash VARCHAR(71) NOT NULL,
    reviewer_credential_operation_id VARCHAR(128) NOT NULL,
    operation_content_hash VARCHAR(71) NOT NULL,
    operation_type VARCHAR(32) NOT NULL,
    reviewer_principal_id VARCHAR(128) NOT NULL,
    reviewer_role VARCHAR(32) NOT NULL,
    principal_content_hash VARCHAR(71) NOT NULL,
    os_owner_sid_hash VARCHAR(71) NOT NULL,
    expected_credential_state_hash VARCHAR(71) NOT NULL,
    registration_challenge_id VARCHAR(128) NOT NULL,
    registration_challenge_purpose VARCHAR(32) NOT NULL,
    registration_challenge_binding_hash VARCHAR(71) NOT NULL,
    prerequisite_authentication_event_id VARCHAR(128),
    prerequisite_authentication_content_hash VARCHAR(71),
    prerequisite_authentication_result VARCHAR(16),
    webauthn_credential_id VARCHAR(512) NOT NULL,
    credential_id_fingerprint VARCHAR(71) NOT NULL,
    cose_public_key_canonical TEXT NOT NULL,
    public_key_fingerprint VARCHAR(71) NOT NULL,
    public_key_algorithm VARCHAR(32) NOT NULL,
    authenticator_aaguid VARCHAR(64),
    authenticator_attachment VARCHAR(16) NOT NULL,
    authenticator_transports_json TEXT NOT NULL,
    rp_id VARCHAR(255) NOT NULL,
    exact_origin VARCHAR(255) NOT NULL,
    resident_key_required INTEGER NOT NULL,
    require_resident_key INTEGER NOT NULL,
    user_verification_required INTEGER NOT NULL,
    attestation_conveyance VARCHAR(16) NOT NULL,
    cred_props_requested INTEGER NOT NULL,
    cred_props_rk INTEGER,
    registration_policy_version VARCHAR(64) NOT NULL,
    observed_registration_sign_count INTEGER NOT NULL,
    client_data_type_verified INTEGER NOT NULL,
    challenge_verified INTEGER NOT NULL,
    origin_verified INTEGER NOT NULL,
    cross_origin_false_verified INTEGER NOT NULL,
    rp_id_hash_verified INTEGER NOT NULL,
    user_presence_verified INTEGER NOT NULL,
    user_verification_verified INTEGER NOT NULL,
    platform_authenticator_verified INTEGER NOT NULL,
    resident_key_verified INTEGER NOT NULL,
    public_key_material_verified INTEGER NOT NULL,
    safe_result_code VARCHAR(128) NOT NULL,
    continuation_challenge_id VARCHAR(128) NOT NULL,
    verified_at VARCHAR(35) NOT NULL,
    payload_json TEXT NOT NULL,
    PRIMARY KEY (counter_capability_registration_id),
    CHECK (contract_version = 'reviewer-counter-capability-registration/0.1.0'),
    CHECK (length(counter_capability_registration_content_hash) = 71 AND substr(counter_capability_registration_content_hash, 1, 7) = 'sha256:' AND substr(counter_capability_registration_content_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (length(operation_content_hash) = 71 AND substr(operation_content_hash, 1, 7) = 'sha256:' AND substr(operation_content_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (operation_type IN ('FIRST_ENROLLMENT', 'ADD_CREDENTIAL', 'REPLACE_CREDENTIAL')),
    CHECK (reviewer_role = 'LOCAL_DATA_STEWARD'),
    CHECK (length(principal_content_hash) = 71 AND substr(principal_content_hash, 1, 7) = 'sha256:' AND substr(principal_content_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (length(os_owner_sid_hash) = 71 AND substr(os_owner_sid_hash, 1, 7) = 'sha256:' AND substr(os_owner_sid_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (length(expected_credential_state_hash) = 71 AND substr(expected_credential_state_hash, 1, 7) = 'sha256:' AND substr(expected_credential_state_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (registration_challenge_purpose = 'REGISTRATION_CREATE'),
    CHECK (length(registration_challenge_binding_hash) = 71 AND substr(registration_challenge_binding_hash, 1, 7) = 'sha256:' AND substr(registration_challenge_binding_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK ((prerequisite_authentication_event_id IS NULL AND prerequisite_authentication_content_hash IS NULL AND prerequisite_authentication_result IS NULL) OR (prerequisite_authentication_event_id IS NOT NULL AND prerequisite_authentication_content_hash IS NOT NULL AND prerequisite_authentication_result = 'VERIFIED')),
    CHECK ((operation_type = 'FIRST_ENROLLMENT' AND prerequisite_authentication_event_id IS NULL) OR (operation_type IN ('ADD_CREDENTIAL', 'REPLACE_CREDENTIAL') AND prerequisite_authentication_result = 'VERIFIED')),
    CHECK (prerequisite_authentication_content_hash IS NULL OR (length(prerequisite_authentication_content_hash) = 71 AND substr(prerequisite_authentication_content_hash, 1, 7) = 'sha256:' AND substr(prerequisite_authentication_content_hash, 8) NOT GLOB '*[^0-9a-f]*')),
    CHECK (length(webauthn_credential_id) > 0 AND webauthn_credential_id NOT GLOB '*[^A-Za-z0-9_-]*' AND instr(webauthn_credential_id, '=') = 0),
    CHECK (length(credential_id_fingerprint) = 71 AND substr(credential_id_fingerprint, 1, 7) = 'sha256:' AND substr(credential_id_fingerprint, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (length(cose_public_key_canonical) > 0 AND cose_public_key_canonical NOT GLOB '*[^A-Za-z0-9_-]*' AND instr(cose_public_key_canonical, '=') = 0),
    CHECK (length(public_key_fingerprint) = 71 AND substr(public_key_fingerprint, 1, 7) = 'sha256:' AND substr(public_key_fingerprint, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (public_key_algorithm IN ('ES256', 'RS256')),
    CHECK (authenticator_aaguid IS NULL OR (length(authenticator_aaguid) = 36 AND authenticator_aaguid = lower(authenticator_aaguid) AND substr(authenticator_aaguid, 9, 1) = '-' AND substr(authenticator_aaguid, 14, 1) = '-' AND substr(authenticator_aaguid, 19, 1) = '-' AND substr(authenticator_aaguid, 24, 1) = '-' AND replace(authenticator_aaguid, '-', '') NOT GLOB '*[^0-9a-f]*')),
    CHECK (authenticator_attachment = 'platform'),
    CHECK (json_valid(authenticator_transports_json) AND json_type(authenticator_transports_json) = 'array' AND instr(authenticator_transports_json, ' ') = 0 AND instr(authenticator_transports_json, char(9)) = 0 AND instr(authenticator_transports_json, char(10)) = 0 AND instr(authenticator_transports_json, char(13)) = 0),
    CHECK (rp_id = 'localhost'),
    CHECK (exact_origin = 'http://localhost:3000'),
    CHECK (resident_key_required = 1 AND require_resident_key = 1 AND user_verification_required = 1),
    CHECK (attestation_conveyance = 'none'),
    CHECK (cred_props_requested = 1 AND (cred_props_rk IS NULL OR cred_props_rk = 1)),
    CHECK (registration_policy_version = 'issuer-steward-webauthn/0.1.0'),
    CHECK (observed_registration_sign_count = 0),
    CHECK (client_data_type_verified = 1 AND challenge_verified = 1 AND origin_verified = 1 AND cross_origin_false_verified = 1 AND rp_id_hash_verified = 1 AND user_presence_verified = 1 AND user_verification_verified = 1 AND platform_authenticator_verified = 1 AND resident_key_verified = 1 AND public_key_material_verified = 1),
    CHECK (safe_result_code = 'COUNTER_CAPABILITY_CONTINUATION_REQUIRED'),
    CHECK (julianday(verified_at) IS NOT NULL AND substr(verified_at, -1) = 'Z'),
    CHECK (json_valid(payload_json) AND json_type(payload_json) = 'object'),
    FOREIGN KEY (reviewer_credential_operation_id, operation_content_hash, reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash, operation_type, expected_credential_state_hash)
        REFERENCES reviewer_credential_operations (reviewer_credential_operation_id, operation_content_hash, reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash, operation_type, expected_credential_state_hash)
        DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (registration_challenge_id, reviewer_credential_operation_id, reviewer_principal_id, operation_type, registration_challenge_purpose, registration_challenge_binding_hash)
        REFERENCES reviewer_credential_operation_challenges (reviewer_credential_operation_challenge_id, reviewer_credential_operation_id, reviewer_principal_id, operation_type, challenge_purpose, challenge_binding_hash)
        DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (prerequisite_authentication_event_id, prerequisite_authentication_content_hash, reviewer_credential_operation_id, reviewer_principal_id, prerequisite_authentication_result)
        REFERENCES reviewer_credential_operation_authentication_events (credential_operation_authentication_event_id, authentication_content_hash, reviewer_credential_operation_id, reviewer_principal_id, authentication_result)
        DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (continuation_challenge_id, counter_capability_registration_id)
        REFERENCES reviewer_webauthn_counter_capability_challenges (counter_capability_challenge_id, counter_capability_registration_id)
        DEFERRABLE INITIALLY DEFERRED
)""",
    ),
    (
        _CHALLENGES,
        """CREATE TABLE reviewer_webauthn_counter_capability_challenges (
    counter_capability_challenge_id VARCHAR(128) NOT NULL,
    contract_version VARCHAR(64) NOT NULL,
    challenge_digest VARCHAR(71) NOT NULL,
    challenge_binding_hash VARCHAR(71) NOT NULL,
    challenge_nonce_length INTEGER NOT NULL,
    challenge_purpose VARCHAR(32) NOT NULL,
    counter_capability_registration_id VARCHAR(128) NOT NULL,
    counter_capability_registration_content_hash VARCHAR(71) NOT NULL,
    reviewer_credential_operation_id VARCHAR(128) NOT NULL,
    operation_content_hash VARCHAR(71) NOT NULL,
    operation_type VARCHAR(32) NOT NULL,
    reviewer_principal_id VARCHAR(128) NOT NULL,
    reviewer_role VARCHAR(32) NOT NULL,
    principal_content_hash VARCHAR(71) NOT NULL,
    os_owner_sid_hash VARCHAR(71) NOT NULL,
    expected_credential_state_hash VARCHAR(71) NOT NULL,
    parent_registration_challenge_id VARCHAR(128) NOT NULL,
    parent_registration_challenge_binding_hash VARCHAR(71) NOT NULL,
    webauthn_credential_id VARCHAR(512) NOT NULL,
    credential_id_fingerprint VARCHAR(71) NOT NULL,
    public_key_fingerprint VARCHAR(71) NOT NULL,
    rp_id VARCHAR(255) NOT NULL,
    allowed_origin VARCHAR(255) NOT NULL,
    client_data_type VARCHAR(32) NOT NULL,
    user_verification_required INTEGER NOT NULL,
    allow_credentials_count INTEGER NOT NULL,
    allowed_webauthn_credential_id VARCHAR(512) NOT NULL,
    user_handle_contract_version VARCHAR(64) NOT NULL,
    authentication_policy_version VARCHAR(64) NOT NULL,
    issued_at VARCHAR(35) NOT NULL,
    expires_at VARCHAR(35) NOT NULL,
    payload_json TEXT NOT NULL,
    PRIMARY KEY (counter_capability_challenge_id),
    CHECK (contract_version = 'reviewer-counter-capability-challenge/0.1.0'),
    CHECK (length(challenge_digest) = 71 AND substr(challenge_digest, 1, 7) = 'sha256:' AND substr(challenge_digest, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (length(challenge_binding_hash) = 71 AND substr(challenge_binding_hash, 1, 7) = 'sha256:' AND substr(challenge_binding_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (challenge_nonce_length = 32),
    CHECK (challenge_purpose = 'COUNTER_CAPABILITY_ASSERTION'),
    CHECK (length(counter_capability_registration_content_hash) = 71 AND substr(counter_capability_registration_content_hash, 1, 7) = 'sha256:' AND substr(counter_capability_registration_content_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (length(operation_content_hash) = 71 AND substr(operation_content_hash, 1, 7) = 'sha256:' AND substr(operation_content_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (operation_type IN ('FIRST_ENROLLMENT', 'ADD_CREDENTIAL', 'REPLACE_CREDENTIAL')),
    CHECK (reviewer_role = 'LOCAL_DATA_STEWARD'),
    CHECK (length(principal_content_hash) = 71 AND substr(principal_content_hash, 1, 7) = 'sha256:' AND substr(principal_content_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (length(os_owner_sid_hash) = 71 AND substr(os_owner_sid_hash, 1, 7) = 'sha256:' AND substr(os_owner_sid_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (length(expected_credential_state_hash) = 71 AND substr(expected_credential_state_hash, 1, 7) = 'sha256:' AND substr(expected_credential_state_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (length(parent_registration_challenge_binding_hash) = 71 AND substr(parent_registration_challenge_binding_hash, 1, 7) = 'sha256:' AND substr(parent_registration_challenge_binding_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (length(webauthn_credential_id) > 0 AND webauthn_credential_id NOT GLOB '*[^A-Za-z0-9_-]*' AND instr(webauthn_credential_id, '=') = 0),
    CHECK (length(credential_id_fingerprint) = 71 AND substr(credential_id_fingerprint, 1, 7) = 'sha256:' AND substr(credential_id_fingerprint, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (length(public_key_fingerprint) = 71 AND substr(public_key_fingerprint, 1, 7) = 'sha256:' AND substr(public_key_fingerprint, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (rp_id = 'localhost' AND allowed_origin = 'http://localhost:3000' AND client_data_type = 'webauthn.get'),
    CHECK (user_verification_required = 1 AND allow_credentials_count = 1),
    CHECK (allowed_webauthn_credential_id = webauthn_credential_id),
    CHECK (user_handle_contract_version = 'issuer-steward-webauthn-user-handle/0.1.0'),
    CHECK (authentication_policy_version = 'issuer-steward-webauthn/0.1.0'),
    CHECK (julianday(issued_at) IS NOT NULL AND julianday(expires_at) IS NOT NULL AND substr(issued_at, -1) = 'Z' AND substr(expires_at, -1) = 'Z'),
    CHECK (julianday(expires_at) > julianday(issued_at) AND julianday(expires_at) <= julianday(issued_at, '+5 minutes')),
    CHECK (json_valid(payload_json) AND json_type(payload_json) = 'object'),
    FOREIGN KEY (counter_capability_registration_id, counter_capability_registration_content_hash, reviewer_credential_operation_id, operation_content_hash, operation_type, reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash, expected_credential_state_hash, parent_registration_challenge_id, parent_registration_challenge_binding_hash, webauthn_credential_id, credential_id_fingerprint, public_key_fingerprint, counter_capability_challenge_id)
        REFERENCES reviewer_webauthn_counter_capability_registrations (counter_capability_registration_id, counter_capability_registration_content_hash, reviewer_credential_operation_id, operation_content_hash, operation_type, reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash, expected_credential_state_hash, registration_challenge_id, registration_challenge_binding_hash, webauthn_credential_id, credential_id_fingerprint, public_key_fingerprint, continuation_challenge_id)
        DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (reviewer_credential_operation_id, operation_content_hash, reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash, operation_type, expected_credential_state_hash)
        REFERENCES reviewer_credential_operations (reviewer_credential_operation_id, operation_content_hash, reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash, operation_type, expected_credential_state_hash)
        DEFERRABLE INITIALLY DEFERRED
)""",
    ),
)

_NEW_TABLE_DDL = (
    *_NEW_TABLE_DDL,
    (
        _ASSERTIONS,
        """CREATE TABLE reviewer_webauthn_counter_capability_assertions (
    counter_capability_assertion_id VARCHAR(128) NOT NULL,
    contract_version VARCHAR(64) NOT NULL,
    assertion_content_hash VARCHAR(71) NOT NULL,
    counter_capability_challenge_id VARCHAR(128) NOT NULL,
    challenge_binding_hash VARCHAR(71) NOT NULL,
    counter_capability_registration_id VARCHAR(128) NOT NULL,
    counter_capability_registration_content_hash VARCHAR(71) NOT NULL,
    reviewer_credential_operation_id VARCHAR(128) NOT NULL,
    operation_content_hash VARCHAR(71) NOT NULL,
    operation_type VARCHAR(32) NOT NULL,
    reviewer_principal_id VARCHAR(128) NOT NULL,
    reviewer_role VARCHAR(32) NOT NULL,
    principal_content_hash VARCHAR(71) NOT NULL,
    os_owner_sid_hash VARCHAR(71) NOT NULL,
    expected_credential_state_hash VARCHAR(71) NOT NULL,
    webauthn_credential_id VARCHAR(512) NOT NULL,
    credential_id_fingerprint VARCHAR(71) NOT NULL,
    public_key_fingerprint VARCHAR(71) NOT NULL,
    challenge_terminal_result VARCHAR(32) NOT NULL,
    safe_result_code VARCHAR(128) NOT NULL,
    client_data_type_verified INTEGER NOT NULL,
    challenge_verified INTEGER NOT NULL,
    origin_verified INTEGER NOT NULL,
    cross_origin_false_verified INTEGER NOT NULL,
    rp_id_hash_verified INTEGER NOT NULL,
    user_presence_verified INTEGER NOT NULL,
    user_verification_verified INTEGER NOT NULL,
    credential_id_verified INTEGER NOT NULL,
    signature_verified INTEGER NOT NULL,
    replay_rejected INTEGER NOT NULL,
    user_handle_status VARCHAR(24) NOT NULL,
    observed_registration_sign_count INTEGER NOT NULL,
    previous_sign_count INTEGER,
    asserted_sign_count INTEGER,
    selected_counter_capability VARCHAR(32),
    selected_registration_sign_count INTEGER,
    classification_verified INTEGER NOT NULL,
    projected_registration_consumption_id VARCHAR(128) NOT NULL,
    projected_registration_consumption_content_hash VARCHAR(71) NOT NULL,
    projected_registration_challenge_purpose VARCHAR(32) NOT NULL,
    projected_registration_terminal_result VARCHAR(32) NOT NULL,
    projected_registration_safe_result_code VARCHAR(128) NOT NULL,
    projected_operation_outcome_id VARCHAR(128) NOT NULL,
    projected_operation_outcome_content_hash VARCHAR(71) NOT NULL,
    projected_operation_terminal_result VARCHAR(16) NOT NULL,
    projected_resulting_credential_state_hash VARCHAR(71) NOT NULL,
    projected_credential_content_hash VARCHAR(71),
    projected_registered_event_id VARCHAR(128),
    projected_registered_event_content_hash VARCHAR(71),
    projected_registered_authorization_content_hash VARCHAR(71),
    projected_superseded_event_id VARCHAR(128),
    projected_superseded_event_content_hash VARCHAR(71),
    projected_superseded_authorization_content_hash VARCHAR(71),
    consumed_at VARCHAR(35) NOT NULL,
    payload_json TEXT NOT NULL,
    PRIMARY KEY (counter_capability_assertion_id),
    CHECK (contract_version = 'reviewer-counter-capability-assertion/0.1.0'),
    CHECK (length(assertion_content_hash) = 71 AND substr(assertion_content_hash, 1, 7) = 'sha256:' AND substr(assertion_content_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (length(challenge_binding_hash) = 71 AND substr(challenge_binding_hash, 1, 7) = 'sha256:' AND substr(challenge_binding_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (length(counter_capability_registration_content_hash) = 71 AND substr(counter_capability_registration_content_hash, 1, 7) = 'sha256:' AND substr(counter_capability_registration_content_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (length(operation_content_hash) = 71 AND substr(operation_content_hash, 1, 7) = 'sha256:' AND substr(operation_content_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (operation_type IN ('FIRST_ENROLLMENT', 'ADD_CREDENTIAL', 'REPLACE_CREDENTIAL')),
    CHECK (reviewer_role = 'LOCAL_DATA_STEWARD'),
    CHECK (length(principal_content_hash) = 71 AND substr(principal_content_hash, 1, 7) = 'sha256:' AND substr(principal_content_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (length(os_owner_sid_hash) = 71 AND substr(os_owner_sid_hash, 1, 7) = 'sha256:' AND substr(os_owner_sid_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (length(expected_credential_state_hash) = 71 AND substr(expected_credential_state_hash, 1, 7) = 'sha256:' AND substr(expected_credential_state_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (length(webauthn_credential_id) > 0 AND webauthn_credential_id NOT GLOB '*[^A-Za-z0-9_-]*' AND instr(webauthn_credential_id, '=') = 0),
    CHECK (length(credential_id_fingerprint) = 71 AND substr(credential_id_fingerprint, 1, 7) = 'sha256:' AND substr(credential_id_fingerprint, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (length(public_key_fingerprint) = 71 AND substr(public_key_fingerprint, 1, 7) = 'sha256:' AND substr(public_key_fingerprint, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (challenge_terminal_result IN ('SUCCEEDED', 'EXPIRED', 'BINDING_MISMATCH', 'ORIGIN_RP_MISMATCH', 'USER_PRESENCE_ABSENT', 'USER_VERIFICATION_ABSENT', 'INVALID_REGISTRATION', 'INVALID_SIGNATURE', 'COUNTER_REJECTED', 'REPLAY_REJECTED', 'FAILED_CLOSED')),
    CHECK (length(safe_result_code) > 0 AND length(safe_result_code) <= 128),
    CHECK (client_data_type_verified IN (0, 1) AND challenge_verified IN (0, 1) AND origin_verified IN (0, 1) AND cross_origin_false_verified IN (0, 1) AND rp_id_hash_verified IN (0, 1) AND user_presence_verified IN (0, 1) AND user_verification_verified IN (0, 1) AND credential_id_verified IN (0, 1) AND signature_verified IN (0, 1) AND replay_rejected IN (0, 1) AND classification_verified IN (0, 1)),
    CHECK (user_handle_status IN ('MATCHED', 'ABSENT_ALLOWED', 'MISMATCHED', 'NOT_EVALUATED')),
    CHECK (observed_registration_sign_count = 0),
    CHECK ((previous_sign_count IS NULL AND asserted_sign_count IS NULL) OR (previous_sign_count = 0 AND asserted_sign_count IS NOT NULL AND asserted_sign_count >= 0 AND signature_verified = 1)),
    CHECK (selected_counter_capability IS NULL OR selected_counter_capability IN ('SIGN_COUNT_SUPPORTED', 'NO_USABLE_COUNTER')),
    CHECK (selected_registration_sign_count IS NULL OR selected_registration_sign_count = 0),
    CHECK (projected_registration_challenge_purpose = 'REGISTRATION_CREATE'),
    CHECK (length(projected_registration_consumption_content_hash) = 71 AND substr(projected_registration_consumption_content_hash, 1, 7) = 'sha256:' AND substr(projected_registration_consumption_content_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (projected_registration_terminal_result IN ('SUCCEEDED', 'FAILED_CLOSED', 'EXPIRED')),
    CHECK (length(projected_registration_safe_result_code) > 0 AND length(projected_registration_safe_result_code) <= 128),
    CHECK (length(projected_operation_outcome_content_hash) = 71 AND substr(projected_operation_outcome_content_hash, 1, 7) = 'sha256:' AND substr(projected_operation_outcome_content_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (projected_operation_terminal_result IN ('SUCCEEDED', 'FAILED_CLOSED', 'EXPIRED')),
    CHECK (length(projected_resulting_credential_state_hash) = 71 AND substr(projected_resulting_credential_state_hash, 1, 7) = 'sha256:' AND substr(projected_resulting_credential_state_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (projected_credential_content_hash IS NULL OR (length(projected_credential_content_hash) = 71 AND substr(projected_credential_content_hash, 1, 7) = 'sha256:' AND substr(projected_credential_content_hash, 8) NOT GLOB '*[^0-9a-f]*')),
    CHECK (projected_registered_event_content_hash IS NULL OR (length(projected_registered_event_content_hash) = 71 AND substr(projected_registered_event_content_hash, 1, 7) = 'sha256:' AND substr(projected_registered_event_content_hash, 8) NOT GLOB '*[^0-9a-f]*')),
    CHECK (projected_registered_authorization_content_hash IS NULL OR (length(projected_registered_authorization_content_hash) = 71 AND substr(projected_registered_authorization_content_hash, 1, 7) = 'sha256:' AND substr(projected_registered_authorization_content_hash, 8) NOT GLOB '*[^0-9a-f]*')),
    CHECK (projected_superseded_event_content_hash IS NULL OR (length(projected_superseded_event_content_hash) = 71 AND substr(projected_superseded_event_content_hash, 1, 7) = 'sha256:' AND substr(projected_superseded_event_content_hash, 8) NOT GLOB '*[^0-9a-f]*')),
    CHECK (projected_superseded_authorization_content_hash IS NULL OR (length(projected_superseded_authorization_content_hash) = 71 AND substr(projected_superseded_authorization_content_hash, 1, 7) = 'sha256:' AND substr(projected_superseded_authorization_content_hash, 8) NOT GLOB '*[^0-9a-f]*')),
    CHECK (challenge_terminal_result != 'SUCCEEDED' OR (client_data_type_verified = 1 AND challenge_verified = 1 AND origin_verified = 1 AND cross_origin_false_verified = 1 AND rp_id_hash_verified = 1 AND user_presence_verified = 1 AND user_verification_verified = 1 AND credential_id_verified = 1 AND signature_verified = 1 AND replay_rejected = 1 AND user_handle_status IN ('MATCHED', 'ABSENT_ALLOWED') AND previous_sign_count = 0 AND asserted_sign_count IS NOT NULL AND classification_verified = 1)),
    CHECK (challenge_terminal_result != 'BINDING_MISMATCH' OR client_data_type_verified = 0 OR challenge_verified = 0 OR credential_id_verified = 0 OR user_handle_status = 'MISMATCHED'),
    CHECK (challenge_terminal_result != 'ORIGIN_RP_MISMATCH' OR origin_verified = 0 OR cross_origin_false_verified = 0 OR rp_id_hash_verified = 0),
    CHECK (challenge_terminal_result != 'USER_PRESENCE_ABSENT' OR user_presence_verified = 0),
    CHECK (challenge_terminal_result != 'USER_VERIFICATION_ABSENT' OR user_verification_verified = 0),
    CHECK (challenge_terminal_result != 'INVALID_SIGNATURE' OR signature_verified = 0),
    CHECK (challenge_terminal_result != 'REPLAY_REJECTED' OR replay_rejected = 0),
    CHECK ((challenge_terminal_result = 'SUCCEEDED' AND asserted_sign_count > 0 AND selected_counter_capability = 'SIGN_COUNT_SUPPORTED' AND selected_registration_sign_count = 0) OR (challenge_terminal_result = 'SUCCEEDED' AND asserted_sign_count = 0 AND selected_counter_capability = 'NO_USABLE_COUNTER' AND selected_registration_sign_count IS NULL) OR challenge_terminal_result != 'SUCCEEDED'),
    CHECK (challenge_terminal_result = 'SUCCEEDED' OR (classification_verified = 0 AND selected_counter_capability IS NULL AND selected_registration_sign_count IS NULL)),
    CHECK ((challenge_terminal_result = 'SUCCEEDED' AND projected_registration_terminal_result = 'SUCCEEDED' AND projected_operation_terminal_result = 'SUCCEEDED' AND projected_resulting_credential_state_hash != expected_credential_state_hash) OR (challenge_terminal_result != 'SUCCEEDED' AND projected_registration_terminal_result IN ('FAILED_CLOSED', 'EXPIRED') AND projected_operation_terminal_result = projected_registration_terminal_result AND projected_resulting_credential_state_hash = expected_credential_state_hash)),
    CHECK ((projected_credential_content_hash IS NULL AND projected_registered_event_id IS NULL AND projected_registered_event_content_hash IS NULL AND projected_registered_authorization_content_hash IS NULL) OR (projected_credential_content_hash IS NOT NULL AND projected_registered_event_id IS NOT NULL AND projected_registered_event_content_hash IS NOT NULL AND projected_registered_authorization_content_hash IS NOT NULL)),
    CHECK ((challenge_terminal_result = 'SUCCEEDED' AND projected_credential_content_hash IS NOT NULL) OR (challenge_terminal_result != 'SUCCEEDED' AND projected_credential_content_hash IS NULL)),
    CHECK ((projected_superseded_event_id IS NULL AND projected_superseded_event_content_hash IS NULL AND projected_superseded_authorization_content_hash IS NULL) OR (projected_superseded_event_id IS NOT NULL AND projected_superseded_event_content_hash IS NOT NULL AND projected_superseded_authorization_content_hash IS NOT NULL)),
    CHECK ((challenge_terminal_result = 'SUCCEEDED' AND operation_type = 'REPLACE_CREDENTIAL' AND projected_superseded_event_id IS NOT NULL) OR (NOT (challenge_terminal_result = 'SUCCEEDED' AND operation_type = 'REPLACE_CREDENTIAL') AND projected_superseded_event_id IS NULL)),
    CHECK (projected_registered_event_id IS NULL OR projected_registered_event_id IS NOT projected_superseded_event_id),
    CHECK (julianday(consumed_at) IS NOT NULL AND substr(consumed_at, -1) = 'Z'),
    CHECK (json_valid(payload_json) AND json_type(payload_json) = 'object'),
    FOREIGN KEY (counter_capability_challenge_id, challenge_binding_hash, counter_capability_registration_id, counter_capability_registration_content_hash, reviewer_credential_operation_id, operation_content_hash, operation_type, reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash, expected_credential_state_hash, webauthn_credential_id, credential_id_fingerprint, public_key_fingerprint)
        REFERENCES reviewer_webauthn_counter_capability_challenges (counter_capability_challenge_id, challenge_binding_hash, counter_capability_registration_id, counter_capability_registration_content_hash, reviewer_credential_operation_id, operation_content_hash, operation_type, reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash, expected_credential_state_hash, webauthn_credential_id, credential_id_fingerprint, public_key_fingerprint)
        DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (counter_capability_registration_id, counter_capability_registration_content_hash, reviewer_credential_operation_id, operation_content_hash, operation_type, reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash, expected_credential_state_hash, webauthn_credential_id, credential_id_fingerprint, public_key_fingerprint)
        REFERENCES reviewer_webauthn_counter_capability_registrations (counter_capability_registration_id, counter_capability_registration_content_hash, reviewer_credential_operation_id, operation_content_hash, operation_type, reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash, expected_credential_state_hash, webauthn_credential_id, credential_id_fingerprint, public_key_fingerprint)
        DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (reviewer_credential_operation_id, operation_content_hash, reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash, operation_type, expected_credential_state_hash)
        REFERENCES reviewer_credential_operations (reviewer_credential_operation_id, operation_content_hash, reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash, operation_type, expected_credential_state_hash)
        DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (projected_registration_consumption_id, reviewer_credential_operation_id, reviewer_principal_id, projected_registration_challenge_purpose, projected_registration_terminal_result, projected_registration_consumption_content_hash)
        REFERENCES reviewer_credential_operation_challenge_consumptions (challenge_consumption_id, reviewer_credential_operation_id, reviewer_principal_id, challenge_purpose, terminal_result, consumption_content_hash)
        DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (projected_operation_outcome_id, projected_operation_outcome_content_hash, reviewer_credential_operation_id, operation_content_hash, reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash, operation_type, projected_operation_terminal_result, projected_registration_consumption_id, projected_registration_consumption_content_hash, expected_credential_state_hash, projected_resulting_credential_state_hash)
        REFERENCES reviewer_credential_operation_outcomes (credential_operation_outcome_id, outcome_content_hash, reviewer_credential_operation_id, operation_content_hash, reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash, operation_type, terminal_result, terminal_consumption_id, terminal_consumption_content_hash, expected_credential_state_hash, resulting_credential_state_hash)
        DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (webauthn_credential_id, projected_credential_content_hash)
        REFERENCES reviewer_webauthn_credentials (webauthn_credential_id, credential_content_hash)
        DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (projected_registered_event_id)
        REFERENCES reviewer_webauthn_credential_events (credential_event_id)
        DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (projected_superseded_event_id)
        REFERENCES reviewer_webauthn_credential_events (credential_event_id)
        DEFERRABLE INITIALLY DEFERRED
)""",
    ),
)

_FROZEN_INDEX_DDL: tuple[tuple[str, str], ...] = (
    (
        "uq_0007_reviewer_credential_operation_outcomes_bootstrap_projection",
        "CREATE UNIQUE INDEX uq_0007_reviewer_credential_operation_outcomes_bootstrap_projection ON reviewer_credential_operation_outcomes (credential_operation_outcome_id, outcome_content_hash, reviewer_credential_operation_id, operation_content_hash, reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash, operation_type, terminal_result, terminal_consumption_id, terminal_consumption_content_hash, expected_credential_state_hash, resulting_credential_state_hash)",
    ),
    (
        "uq_0007_credential_event_authorization_projection",
        "CREATE UNIQUE INDEX uq_0007_credential_event_authorization_projection ON reviewer_webauthn_credential_event_authorizations (credential_event_id, credential_event_content_hash, authorization_content_hash, webauthn_credential_id, reviewer_credential_operation_id, credential_operation_outcome_id, credential_operation_outcome_content_hash, event_type, authorization_kind)",
    ),
)

_NEW_INDEX_DDL: tuple[tuple[str, str], ...] = (
    (
        "uq_0007_cc_registration_content",
        "CREATE UNIQUE INDEX uq_0007_cc_registration_content ON reviewer_webauthn_counter_capability_registrations (counter_capability_registration_content_hash)",
    ),
    (
        "uq_0007_cc_registration_parent",
        "CREATE UNIQUE INDEX uq_0007_cc_registration_parent ON reviewer_webauthn_counter_capability_registrations (registration_challenge_id)",
    ),
    (
        "uq_0007_cc_registration_child",
        "CREATE UNIQUE INDEX uq_0007_cc_registration_child ON reviewer_webauthn_counter_capability_registrations (continuation_challenge_id)",
    ),
    (
        "uq_0007_cc_registration_credential",
        "CREATE UNIQUE INDEX uq_0007_cc_registration_credential ON reviewer_webauthn_counter_capability_registrations (webauthn_credential_id)",
    ),
    (
        "uq_0007_cc_registration_credential_fingerprint",
        "CREATE UNIQUE INDEX uq_0007_cc_registration_credential_fingerprint ON reviewer_webauthn_counter_capability_registrations (credential_id_fingerprint)",
    ),
    (
        "uq_0007_cc_registration_public_key_fingerprint",
        "CREATE UNIQUE INDEX uq_0007_cc_registration_public_key_fingerprint ON reviewer_webauthn_counter_capability_registrations (public_key_fingerprint)",
    ),
    (
        "uq_0007_cc_registration_exact_copy",
        "CREATE UNIQUE INDEX uq_0007_cc_registration_exact_copy ON reviewer_webauthn_counter_capability_registrations (counter_capability_registration_id, counter_capability_registration_content_hash, reviewer_credential_operation_id, operation_content_hash, operation_type, reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash, expected_credential_state_hash, registration_challenge_id, registration_challenge_binding_hash, webauthn_credential_id, credential_id_fingerprint, public_key_fingerprint, continuation_challenge_id)",
    ),
    (
        "uq_0007_cc_registration_assertion_copy",
        "CREATE UNIQUE INDEX uq_0007_cc_registration_assertion_copy ON reviewer_webauthn_counter_capability_registrations (counter_capability_registration_id, counter_capability_registration_content_hash, reviewer_credential_operation_id, operation_content_hash, operation_type, reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash, expected_credential_state_hash, webauthn_credential_id, credential_id_fingerprint, public_key_fingerprint)",
    ),
    (
        "ix_counter_capability_registrations_operation",
        "CREATE INDEX ix_counter_capability_registrations_operation ON reviewer_webauthn_counter_capability_registrations (reviewer_credential_operation_id, reviewer_principal_id)",
    ),
    (
        "uq_0007_cc_challenge_digest",
        "CREATE UNIQUE INDEX uq_0007_cc_challenge_digest ON reviewer_webauthn_counter_capability_challenges (challenge_digest)",
    ),
    (
        "uq_0007_cc_challenge_binding",
        "CREATE UNIQUE INDEX uq_0007_cc_challenge_binding ON reviewer_webauthn_counter_capability_challenges (challenge_binding_hash)",
    ),
    (
        "uq_0007_cc_challenge_registration",
        "CREATE UNIQUE INDEX uq_0007_cc_challenge_registration ON reviewer_webauthn_counter_capability_challenges (counter_capability_registration_id)",
    ),
    (
        "uq_0007_cc_challenge_exact_child",
        "CREATE UNIQUE INDEX uq_0007_cc_challenge_exact_child ON reviewer_webauthn_counter_capability_challenges (counter_capability_challenge_id, counter_capability_registration_id)",
    ),
    (
        "uq_0007_cc_challenge_exact_copy",
        "CREATE UNIQUE INDEX uq_0007_cc_challenge_exact_copy ON reviewer_webauthn_counter_capability_challenges (counter_capability_challenge_id, challenge_binding_hash, counter_capability_registration_id, counter_capability_registration_content_hash, reviewer_credential_operation_id, operation_content_hash, operation_type, reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash, expected_credential_state_hash, webauthn_credential_id, credential_id_fingerprint, public_key_fingerprint)",
    ),
    (
        "ix_counter_capability_challenges_expiry",
        "CREATE INDEX ix_counter_capability_challenges_expiry ON reviewer_webauthn_counter_capability_challenges (reviewer_principal_id, expires_at)",
    ),
    (
        "uq_0007_cc_assertion_content",
        "CREATE UNIQUE INDEX uq_0007_cc_assertion_content ON reviewer_webauthn_counter_capability_assertions (assertion_content_hash)",
    ),
    (
        "uq_0007_cc_assertion_challenge",
        "CREATE UNIQUE INDEX uq_0007_cc_assertion_challenge ON reviewer_webauthn_counter_capability_assertions (counter_capability_challenge_id)",
    ),
    (
        "uq_0007_cc_assertion_registration",
        "CREATE UNIQUE INDEX uq_0007_cc_assertion_registration ON reviewer_webauthn_counter_capability_assertions (counter_capability_registration_id)",
    ),
    (
        "uq_0007_cc_assertion_consumption_projection",
        "CREATE UNIQUE INDEX uq_0007_cc_assertion_consumption_projection ON reviewer_webauthn_counter_capability_assertions (projected_registration_consumption_id)",
    ),
    (
        "uq_0007_cc_assertion_outcome_projection",
        "CREATE UNIQUE INDEX uq_0007_cc_assertion_outcome_projection ON reviewer_webauthn_counter_capability_assertions (projected_operation_outcome_id)",
    ),
    (
        "ix_counter_capability_assertions_operation",
        "CREATE INDEX ix_counter_capability_assertions_operation ON reviewer_webauthn_counter_capability_assertions (reviewer_credential_operation_id, projected_operation_terminal_result)",
    ),
)


def _append_only_trigger_sql(table_name: str, operation: str) -> str:
    trigger_name = f"trg_{table_name}_append_only_{operation.lower()}"
    message = f"{table_name} is append-only: {operation} forbidden"
    return (
        f"CREATE TRIGGER {trigger_name} BEFORE {operation} ON {table_name} "
        f"BEGIN SELECT RAISE(ABORT, '{message}'); END"
    )


_APPEND_ONLY_TRIGGER_NAMES = tuple(
    f"trg_{table_name}_append_only_{operation.lower()}"
    for table_name in _NEW_TABLE_NAMES
    for operation in ("UPDATE", "DELETE")
)

_NEW_INSERT_GUARD_DDL: tuple[tuple[str, str], ...] = (
    (
        "trg_0007_counter_capability_registrations_insert_guard",
        """CREATE TRIGGER trg_0007_counter_capability_registrations_insert_guard
BEFORE INSERT ON reviewer_webauthn_counter_capability_registrations
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1
        FROM reviewer_credential_operation_challenges challenge
        JOIN reviewer_credential_operations operation
          ON operation.reviewer_credential_operation_id = challenge.reviewer_credential_operation_id
         AND operation.operation_content_hash = challenge.operation_content_hash
         AND operation.reviewer_principal_id = challenge.reviewer_principal_id
         AND operation.reviewer_role = challenge.reviewer_role
         AND operation.principal_content_hash = challenge.principal_content_hash
         AND operation.os_owner_sid_hash = challenge.os_owner_sid_hash
         AND operation.operation_type = challenge.operation_type
         AND operation.expected_credential_state_hash = challenge.expected_credential_state_hash
        WHERE challenge.reviewer_credential_operation_challenge_id = NEW.registration_challenge_id
          AND challenge.challenge_binding_hash = NEW.registration_challenge_binding_hash
          AND challenge.reviewer_credential_operation_id = NEW.reviewer_credential_operation_id
          AND challenge.operation_content_hash = NEW.operation_content_hash
          AND challenge.operation_type = NEW.operation_type
          AND challenge.reviewer_principal_id = NEW.reviewer_principal_id
          AND challenge.reviewer_role = NEW.reviewer_role
          AND challenge.principal_content_hash = NEW.principal_content_hash
          AND challenge.os_owner_sid_hash = NEW.os_owner_sid_hash
          AND challenge.expected_credential_state_hash = NEW.expected_credential_state_hash
          AND challenge.challenge_purpose = 'REGISTRATION_CREATE'
          AND challenge.rp_id = NEW.rp_id
          AND challenge.allowed_origin = NEW.exact_origin
          AND challenge.client_data_type = 'webauthn.create'
          AND challenge.user_verification_required = 1
          AND challenge.platform_attachment_required = 1
          AND challenge.resident_key_required = 1
          AND challenge.authentication_policy_version = NEW.registration_policy_version
          AND challenge.prerequisite_authentication_event_id IS NEW.prerequisite_authentication_event_id
          AND challenge.prerequisite_authentication_content_hash IS NEW.prerequisite_authentication_content_hash
          AND challenge.prerequisite_authentication_result IS NEW.prerequisite_authentication_result
          AND ((NEW.operation_type = 'FIRST_ENROLLMENT'
                AND challenge.prerequisite_authentication_event_id IS NULL)
            OR (NEW.operation_type IN ('ADD_CREDENTIAL', 'REPLACE_CREDENTIAL')
                AND challenge.prerequisite_authentication_result = 'VERIFIED'))
          AND julianday(NEW.verified_at) < julianday(challenge.expires_at)
    ) THEN RAISE(ABORT, 'counter capability registration exact live parent mismatch') END;
    SELECT CASE WHEN EXISTS (
        SELECT 1 FROM reviewer_credential_operation_challenge_consumptions consumption
        WHERE consumption.reviewer_credential_operation_challenge_id = NEW.registration_challenge_id
    ) THEN RAISE(ABORT, 'counter capability registration parent already consumed') END;
    SELECT CASE WHEN EXISTS (
        SELECT 1 FROM reviewer_credential_operation_outcomes outcome
        WHERE outcome.reviewer_credential_operation_id = NEW.reviewer_credential_operation_id
    ) THEN RAISE(ABORT, 'counter capability registration operation already terminal') END;
    SELECT CASE WHEN EXISTS (
        SELECT 1 FROM reviewer_webauthn_counter_capability_registrations pending
        WHERE pending.registration_challenge_id = NEW.registration_challenge_id
           OR pending.webauthn_credential_id = NEW.webauthn_credential_id
           OR pending.credential_id_fingerprint = NEW.credential_id_fingerprint
           OR pending.public_key_fingerprint = NEW.public_key_fingerprint
    ) THEN RAISE(ABORT, 'counter capability registration replay or pending credential collision') END;
    SELECT CASE WHEN EXISTS (
        SELECT 1 FROM reviewer_webauthn_credentials credential
        WHERE credential.webauthn_credential_id = NEW.webauthn_credential_id
           OR credential.credential_id_fingerprint = NEW.credential_id_fingerprint
           OR credential.public_key_fingerprint = NEW.public_key_fingerprint
    ) THEN RAISE(ABORT, 'counter capability pending credential already public or key-colliding') END;
    SELECT CASE WHEN EXISTS (
        SELECT 1 FROM reviewer_credential_operation_challenges challenge
        WHERE challenge.reviewer_credential_operation_challenge_id = NEW.continuation_challenge_id
    ) THEN RAISE(ABORT, 'counter capability child id collides with frozen challenge') END;
END""",
    ),
    (
        "trg_0007_counter_capability_challenges_insert_guard",
        """CREATE TRIGGER trg_0007_counter_capability_challenges_insert_guard
BEFORE INSERT ON reviewer_webauthn_counter_capability_challenges
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1
        FROM reviewer_webauthn_counter_capability_registrations registration
        JOIN reviewer_credential_operation_challenges parent
          ON parent.reviewer_credential_operation_challenge_id = registration.registration_challenge_id
         AND parent.challenge_binding_hash = registration.registration_challenge_binding_hash
         AND parent.reviewer_credential_operation_id = registration.reviewer_credential_operation_id
         AND parent.reviewer_principal_id = registration.reviewer_principal_id
         AND parent.operation_type = registration.operation_type
         AND parent.challenge_purpose = registration.registration_challenge_purpose
        WHERE registration.counter_capability_registration_id = NEW.counter_capability_registration_id
          AND registration.counter_capability_registration_content_hash = NEW.counter_capability_registration_content_hash
          AND registration.continuation_challenge_id = NEW.counter_capability_challenge_id
          AND registration.reviewer_credential_operation_id = NEW.reviewer_credential_operation_id
          AND registration.operation_content_hash = NEW.operation_content_hash
          AND registration.operation_type = NEW.operation_type
          AND registration.reviewer_principal_id = NEW.reviewer_principal_id
          AND registration.reviewer_role = NEW.reviewer_role
          AND registration.principal_content_hash = NEW.principal_content_hash
          AND registration.os_owner_sid_hash = NEW.os_owner_sid_hash
          AND registration.expected_credential_state_hash = NEW.expected_credential_state_hash
          AND registration.registration_challenge_id = NEW.parent_registration_challenge_id
          AND registration.registration_challenge_binding_hash = NEW.parent_registration_challenge_binding_hash
          AND registration.webauthn_credential_id = NEW.webauthn_credential_id
          AND registration.credential_id_fingerprint = NEW.credential_id_fingerprint
          AND registration.public_key_fingerprint = NEW.public_key_fingerprint
          AND registration.rp_id = NEW.rp_id
          AND registration.exact_origin = NEW.allowed_origin
          AND registration.user_verification_required = NEW.user_verification_required
          AND registration.registration_policy_version = NEW.authentication_policy_version
          AND julianday(NEW.issued_at) >= julianday(registration.verified_at)
          AND julianday(NEW.expires_at) <= julianday(parent.expires_at)
    ) THEN RAISE(ABORT, 'counter capability challenge exact pending copy or parent expiry mismatch') END;
    SELECT CASE WHEN EXISTS (
        SELECT 1 FROM reviewer_webauthn_counter_capability_assertions assertion
        WHERE assertion.counter_capability_challenge_id = NEW.counter_capability_challenge_id
           OR assertion.counter_capability_registration_id = NEW.counter_capability_registration_id
    ) THEN RAISE(ABORT, 'terminalized counter capability registration cannot issue challenge') END;
END""",
    ),
    (
        "trg_0007_counter_capability_assertions_insert_guard",
        """CREATE TRIGGER trg_0007_counter_capability_assertions_insert_guard
BEFORE INSERT ON reviewer_webauthn_counter_capability_assertions
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1
        FROM reviewer_webauthn_counter_capability_challenges challenge
        JOIN reviewer_webauthn_counter_capability_registrations registration
          ON registration.counter_capability_registration_id = challenge.counter_capability_registration_id
         AND registration.counter_capability_registration_content_hash = challenge.counter_capability_registration_content_hash
         AND registration.continuation_challenge_id = challenge.counter_capability_challenge_id
        WHERE challenge.counter_capability_challenge_id = NEW.counter_capability_challenge_id
          AND challenge.challenge_binding_hash = NEW.challenge_binding_hash
          AND challenge.counter_capability_registration_id = NEW.counter_capability_registration_id
          AND challenge.counter_capability_registration_content_hash = NEW.counter_capability_registration_content_hash
          AND challenge.reviewer_credential_operation_id = NEW.reviewer_credential_operation_id
          AND challenge.operation_content_hash = NEW.operation_content_hash
          AND challenge.operation_type = NEW.operation_type
          AND challenge.reviewer_principal_id = NEW.reviewer_principal_id
          AND challenge.reviewer_role = NEW.reviewer_role
          AND challenge.principal_content_hash = NEW.principal_content_hash
          AND challenge.os_owner_sid_hash = NEW.os_owner_sid_hash
          AND challenge.expected_credential_state_hash = NEW.expected_credential_state_hash
          AND challenge.webauthn_credential_id = NEW.webauthn_credential_id
          AND challenge.credential_id_fingerprint = NEW.credential_id_fingerprint
          AND challenge.public_key_fingerprint = NEW.public_key_fingerprint
          AND challenge.allowed_webauthn_credential_id = NEW.webauthn_credential_id
          AND julianday(NEW.consumed_at) >= julianday(challenge.issued_at)
    ) THEN RAISE(ABORT, 'counter capability assertion exact one-time challenge mismatch') END;
    SELECT CASE WHEN EXISTS (
        SELECT 1 FROM reviewer_webauthn_counter_capability_assertions old
        WHERE old.counter_capability_challenge_id = NEW.counter_capability_challenge_id
           OR old.counter_capability_registration_id = NEW.counter_capability_registration_id
    ) THEN RAISE(ABORT, 'counter capability assertion replay rejected') END;
    SELECT CASE WHEN EXISTS (
        SELECT 1 FROM reviewer_webauthn_counter_capability_challenges challenge
        JOIN reviewer_webauthn_counter_capability_registrations registration
          ON registration.counter_capability_registration_id = challenge.counter_capability_registration_id
        JOIN reviewer_credential_operation_challenges parent
          ON parent.reviewer_credential_operation_challenge_id = registration.registration_challenge_id
        WHERE challenge.counter_capability_challenge_id = NEW.counter_capability_challenge_id
          AND (
              (NEW.challenge_terminal_result = 'SUCCEEDED'
               AND (julianday(NEW.consumed_at) >= julianday(challenge.expires_at)
                    OR julianday(NEW.consumed_at) >= julianday(parent.expires_at)))
           OR (NEW.challenge_terminal_result != 'SUCCEEDED'
               AND julianday(NEW.consumed_at) >= julianday(parent.expires_at)
               AND (NEW.projected_registration_terminal_result != 'EXPIRED'
                    OR NEW.projected_operation_terminal_result != 'EXPIRED'))
           OR (NEW.challenge_terminal_result != 'SUCCEEDED'
               AND julianday(NEW.consumed_at) < julianday(parent.expires_at)
               AND (NEW.projected_registration_terminal_result != 'FAILED_CLOSED'
                    OR NEW.projected_operation_terminal_result != 'FAILED_CLOSED'))
           OR (NEW.challenge_terminal_result = 'EXPIRED'
               AND julianday(NEW.consumed_at) < julianday(challenge.expires_at))
           OR (NEW.challenge_terminal_result != 'EXPIRED'
               AND NEW.challenge_terminal_result != 'SUCCEEDED'
               AND julianday(NEW.consumed_at) >= julianday(challenge.expires_at))
          )
    ) THEN RAISE(ABORT, 'counter capability assertion time and result mismatch') END;
    SELECT CASE WHEN EXISTS (
        SELECT 1 FROM reviewer_credential_operation_challenge_consumptions consumption
        JOIN reviewer_webauthn_counter_capability_registrations registration
          ON registration.registration_challenge_id = consumption.reviewer_credential_operation_challenge_id
        WHERE registration.counter_capability_registration_id = NEW.counter_capability_registration_id
    ) THEN RAISE(ABORT, 'counter capability assertion parent already consumed') END;
    SELECT CASE WHEN EXISTS (
        SELECT 1 FROM reviewer_credential_operation_outcomes outcome
        WHERE outcome.reviewer_credential_operation_id = NEW.reviewer_credential_operation_id
    ) THEN RAISE(ABORT, 'counter capability assertion operation already terminal') END;
    SELECT CASE WHEN NEW.challenge_terminal_result = 'SUCCEEDED' AND EXISTS (
        SELECT 1 FROM reviewer_webauthn_credentials credential
        WHERE credential.webauthn_credential_id = NEW.webauthn_credential_id
           OR credential.credential_id_fingerprint = NEW.credential_id_fingerprint
           OR credential.public_key_fingerprint = NEW.public_key_fingerprint
    ) THEN RAISE(ABORT, 'counter capability assertion credential projection already exists') END;
    SELECT CASE WHEN NEW.challenge_terminal_result != 'SUCCEEDED' AND EXISTS (
        SELECT 1 FROM reviewer_webauthn_credential_event_authorizations authorization
        WHERE authorization.reviewer_credential_operation_id = NEW.reviewer_credential_operation_id
    ) THEN RAISE(ABORT, 'failed counter capability assertion cannot retain lifecycle authorization') END;
    SELECT CASE WHEN NEW.operation_type IN ('FIRST_ENROLLMENT', 'ADD_CREDENTIAL')
          AND NEW.projected_superseded_event_id IS NOT NULL
        THEN RAISE(ABORT, 'first or add bootstrap cannot project supersession') END;
    SELECT CASE WHEN NEW.challenge_terminal_result = 'SUCCEEDED'
          AND NEW.operation_type = 'REPLACE_CREDENTIAL'
          AND NOT EXISTS (
              SELECT 1 FROM reviewer_credential_operations operation
              WHERE operation.reviewer_credential_operation_id = NEW.reviewer_credential_operation_id
                AND operation.target_webauthn_credential_id IS NOT NULL
                AND operation.target_webauthn_credential_id != NEW.webauthn_credential_id
          ) THEN RAISE(ABORT, 'replace bootstrap requires distinct exact target credential') END;
END""",
    ),
)

_NEW_INSERT_GUARD_NAMES = tuple(name for name, _statement in _NEW_INSERT_GUARD_DDL)

_FROZEN_PROJECTION_GUARD_DDL: tuple[tuple[str, str], ...] = (
    (
        "trg_0007_operation_consumptions_bootstrap_projection_guard",
        """CREATE TRIGGER trg_0007_operation_consumptions_bootstrap_projection_guard
BEFORE INSERT ON reviewer_credential_operation_challenge_consumptions
BEGIN
    SELECT CASE WHEN EXISTS (
        SELECT 1 FROM reviewer_webauthn_counter_capability_registrations registration
        WHERE registration.registration_challenge_id = NEW.reviewer_credential_operation_challenge_id
    ) AND NOT EXISTS (
        SELECT 1
        FROM reviewer_webauthn_counter_capability_registrations registration
        JOIN reviewer_webauthn_counter_capability_assertions assertion
          ON assertion.counter_capability_registration_id = registration.counter_capability_registration_id
         AND assertion.counter_capability_registration_content_hash = registration.counter_capability_registration_content_hash
        WHERE registration.registration_challenge_id = NEW.reviewer_credential_operation_challenge_id
          AND registration.registration_challenge_binding_hash = NEW.challenge_binding_hash
          AND registration.reviewer_credential_operation_id = NEW.reviewer_credential_operation_id
          AND registration.operation_type = NEW.operation_type
          AND registration.reviewer_principal_id = NEW.reviewer_principal_id
          AND NEW.challenge_purpose = 'REGISTRATION_CREATE'
          AND assertion.projected_registration_consumption_id = NEW.challenge_consumption_id
          AND assertion.projected_registration_consumption_content_hash = NEW.consumption_content_hash
          AND assertion.projected_registration_challenge_purpose = NEW.challenge_purpose
          AND assertion.projected_registration_terminal_result = NEW.terminal_result
          AND assertion.projected_registration_safe_result_code = NEW.safe_result_code
          AND assertion.projected_operation_outcome_id = NEW.terminal_operation_outcome_id
          AND assertion.projected_operation_terminal_result = NEW.terminal_operation_outcome_result
          AND assertion.expected_credential_state_hash = NEW.outcome_expected_credential_state_hash
          AND assertion.projected_resulting_credential_state_hash = NEW.outcome_resulting_credential_state_hash
          AND assertion.consumed_at = NEW.consumed_at
          AND NEW.client_data_type_verified = registration.client_data_type_verified
          AND NEW.challenge_verified = registration.challenge_verified
          AND NEW.origin_verified = registration.origin_verified
          AND NEW.cross_origin_false_verified = registration.cross_origin_false_verified
          AND NEW.rp_id_hash_verified = registration.rp_id_hash_verified
          AND NEW.user_presence_verified = registration.user_presence_verified
          AND NEW.user_verification_verified = registration.user_verification_verified
          AND NEW.platform_authenticator_verified = registration.platform_authenticator_verified
          AND NEW.resident_key_verified = registration.resident_key_verified
          AND NEW.public_key_material_verified = registration.public_key_material_verified
          AND NEW.continuation_challenge_id IS NULL
          AND NEW.continuation_challenge_purpose IS NULL
          AND (
              (assertion.challenge_terminal_result = 'SUCCEEDED'
               AND NEW.terminal_result = 'SUCCEEDED'
               AND NEW.registered_webauthn_credential_id = registration.webauthn_credential_id
               AND NEW.registered_credential_content_hash = assertion.projected_credential_content_hash
               AND NEW.registered_credential_id_fingerprint = registration.credential_id_fingerprint
               AND NEW.registered_public_key_fingerprint = registration.public_key_fingerprint
               AND NEW.registered_rp_id = registration.rp_id
               AND NEW.registered_counter_capability = assertion.selected_counter_capability
               AND ((assertion.selected_counter_capability = 'SIGN_COUNT_SUPPORTED'
                     AND NEW.registered_sign_count = 0)
                 OR (assertion.selected_counter_capability = 'NO_USABLE_COUNTER'
                     AND NEW.registered_sign_count IS NULL)))
           OR (assertion.challenge_terminal_result != 'SUCCEEDED'
               AND NEW.registered_webauthn_credential_id IS NULL
               AND NEW.registered_credential_content_hash IS NULL
               AND NEW.registered_credential_id_fingerprint IS NULL
               AND NEW.registered_public_key_fingerprint IS NULL
               AND NEW.registered_rp_id IS NULL
               AND NEW.registered_counter_capability IS NULL
               AND NEW.registered_sign_count IS NULL)
          )
    ) THEN RAISE(ABORT, 'pending counter capability parent requires exact assertion projection before consumption') END;
END""",
    ),
    (
        "trg_0007_operation_outcomes_bootstrap_projection_guard",
        """CREATE TRIGGER trg_0007_operation_outcomes_bootstrap_projection_guard
BEFORE INSERT ON reviewer_credential_operation_outcomes
BEGIN
    SELECT CASE WHEN EXISTS (
        SELECT 1
        FROM reviewer_credential_operation_challenge_consumptions consumption
        JOIN reviewer_webauthn_counter_capability_registrations registration
          ON registration.registration_challenge_id = consumption.reviewer_credential_operation_challenge_id
        WHERE consumption.challenge_consumption_id = NEW.terminal_consumption_id
    ) AND NOT EXISTS (
        SELECT 1
        FROM reviewer_webauthn_counter_capability_assertions assertion
        JOIN reviewer_webauthn_counter_capability_registrations registration
          ON registration.counter_capability_registration_id = assertion.counter_capability_registration_id
        JOIN reviewer_credential_operation_challenge_consumptions consumption
          ON consumption.challenge_consumption_id = assertion.projected_registration_consumption_id
        WHERE assertion.projected_operation_outcome_id = NEW.credential_operation_outcome_id
          AND assertion.projected_operation_outcome_content_hash = NEW.outcome_content_hash
          AND assertion.reviewer_credential_operation_id = NEW.reviewer_credential_operation_id
          AND assertion.operation_content_hash = NEW.operation_content_hash
          AND assertion.operation_type = NEW.operation_type
          AND assertion.reviewer_principal_id = NEW.reviewer_principal_id
          AND assertion.reviewer_role = NEW.reviewer_role
          AND assertion.principal_content_hash = NEW.principal_content_hash
          AND assertion.os_owner_sid_hash = NEW.os_owner_sid_hash
          AND assertion.projected_operation_terminal_result = NEW.terminal_result
          AND assertion.projected_registration_consumption_id = NEW.terminal_consumption_id
          AND assertion.projected_registration_consumption_content_hash = NEW.terminal_consumption_content_hash
          AND assertion.projected_registration_challenge_purpose = NEW.terminal_challenge_purpose
          AND assertion.projected_registration_terminal_result = NEW.terminal_challenge_result
          AND assertion.expected_credential_state_hash = NEW.expected_credential_state_hash
          AND assertion.projected_resulting_credential_state_hash = NEW.resulting_credential_state_hash
          AND assertion.projected_registration_safe_result_code = NEW.safe_result_code
          AND consumption.safe_result_code = NEW.safe_result_code
          AND NEW.registration_consumption_id = assertion.projected_registration_consumption_id
          AND NEW.registration_consumption_content_hash = assertion.projected_registration_consumption_content_hash
          AND NEW.registration_challenge_purpose = assertion.projected_registration_challenge_purpose
          AND NEW.registration_terminal_result = assertion.projected_registration_terminal_result
          AND NEW.completed_at = assertion.consumed_at
          AND ((NEW.operation_type = 'FIRST_ENROLLMENT'
                AND NEW.authorization_authentication_event_id IS NULL
                AND NEW.authorization_authentication_content_hash IS NULL
                AND NEW.authorization_authentication_result IS NULL)
            OR (NEW.operation_type IN ('ADD_CREDENTIAL', 'REPLACE_CREDENTIAL')
                AND NEW.authorization_authentication_event_id = registration.prerequisite_authentication_event_id
                AND NEW.authorization_authentication_content_hash = registration.prerequisite_authentication_content_hash
                AND NEW.authorization_authentication_result = registration.prerequisite_authentication_result))
          AND ((assertion.challenge_terminal_result = 'SUCCEEDED'
                AND NEW.terminal_result = 'SUCCEEDED'
                AND NEW.resulting_credential_state_hash != NEW.expected_credential_state_hash)
            OR (assertion.challenge_terminal_result != 'SUCCEEDED'
                AND NEW.terminal_result IN ('FAILED_CLOSED', 'EXPIRED')
                AND NEW.resulting_credential_state_hash = NEW.expected_credential_state_hash))
    ) THEN RAISE(ABORT, 'counter capability outcome requires exact assertion projection') END;
END""",
    ),
    (
        "trg_0007_credentials_counter_bootstrap_guard",
        """CREATE TRIGGER trg_0007_credentials_counter_bootstrap_guard
BEFORE INSERT ON reviewer_webauthn_credentials
WHEN NEW.registration_sign_count = 0 OR NEW.counter_capability = 'NO_USABLE_COUNTER'
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1
        FROM reviewer_webauthn_counter_capability_assertions assertion
        JOIN reviewer_webauthn_counter_capability_registrations registration
          ON registration.counter_capability_registration_id = assertion.counter_capability_registration_id
         AND registration.counter_capability_registration_content_hash = assertion.counter_capability_registration_content_hash
        WHERE assertion.challenge_terminal_result = 'SUCCEEDED'
          AND assertion.classification_verified = 1
          AND assertion.webauthn_credential_id = NEW.webauthn_credential_id
          AND assertion.projected_credential_content_hash = NEW.credential_content_hash
          AND assertion.reviewer_principal_id = NEW.reviewer_principal_id
          AND assertion.reviewer_role = NEW.reviewer_role
          AND assertion.principal_content_hash = NEW.principal_content_hash
          AND assertion.credential_id_fingerprint = NEW.credential_id_fingerprint
          AND assertion.public_key_fingerprint = NEW.public_key_fingerprint
          AND assertion.selected_counter_capability = NEW.counter_capability
          AND assertion.selected_registration_sign_count IS NEW.registration_sign_count
          AND registration.cose_public_key_canonical = NEW.cose_public_key_canonical
          AND registration.public_key_algorithm = NEW.public_key_algorithm
          AND registration.authenticator_aaguid IS NEW.authenticator_aaguid
          AND registration.authenticator_attachment = NEW.authenticator_attachment
          AND registration.authenticator_transports_json = NEW.authenticator_transports_json
          AND registration.rp_id = NEW.rp_id
          AND registration.resident_key_required = NEW.resident_key_required
          AND registration.user_verification_required = NEW.user_verification_required
          AND registration.registration_policy_version = NEW.registration_policy_version
    ) THEN RAISE(ABORT, 'zero or no-usable-counter public credential requires successful bootstrap assertion') END;
END""",
    ),
    (
        "trg_0007_credential_event_authorizations_counter_bootstrap_guard",
        """CREATE TRIGGER trg_0007_credential_event_authorizations_counter_bootstrap_guard
BEFORE INSERT ON reviewer_webauthn_credential_event_authorizations
BEGIN
    SELECT CASE WHEN EXISTS (
        SELECT 1 FROM reviewer_webauthn_counter_capability_assertions assertion
        WHERE assertion.reviewer_credential_operation_id = NEW.reviewer_credential_operation_id
          AND assertion.challenge_terminal_result != 'SUCCEEDED'
    ) THEN RAISE(ABORT, 'failed counter capability assertion cannot authorize lifecycle') END;
    SELECT CASE WHEN EXISTS (
        SELECT 1 FROM reviewer_webauthn_counter_capability_assertions assertion
        WHERE assertion.reviewer_credential_operation_id = NEW.reviewer_credential_operation_id
          AND assertion.challenge_terminal_result = 'SUCCEEDED'
    ) AND NOT EXISTS (
        SELECT 1
        FROM reviewer_webauthn_counter_capability_assertions assertion
        JOIN reviewer_webauthn_counter_capability_registrations registration
          ON registration.counter_capability_registration_id = assertion.counter_capability_registration_id
        JOIN reviewer_credential_operations operation
          ON operation.reviewer_credential_operation_id = assertion.reviewer_credential_operation_id
        WHERE assertion.reviewer_credential_operation_id = NEW.reviewer_credential_operation_id
          AND assertion.challenge_terminal_result = 'SUCCEEDED'
          AND assertion.projected_operation_outcome_id = NEW.credential_operation_outcome_id
          AND assertion.projected_operation_outcome_content_hash = NEW.credential_operation_outcome_content_hash
          AND assertion.operation_content_hash = NEW.operation_content_hash
          AND assertion.operation_type = NEW.operation_type
          AND assertion.reviewer_principal_id = NEW.reviewer_principal_id
          AND assertion.reviewer_role = NEW.reviewer_role
          AND assertion.principal_content_hash = NEW.principal_content_hash
          AND assertion.os_owner_sid_hash = NEW.os_owner_sid_hash
          AND assertion.expected_credential_state_hash = NEW.expected_credential_state_hash
          AND assertion.projected_resulting_credential_state_hash = NEW.resulting_credential_state_hash
          AND NEW.credential_operation_outcome_result = 'SUCCEEDED'
          AND (
              (NEW.event_type = 'REGISTERED'
               AND NEW.authorization_kind = CASE assertion.operation_type WHEN 'FIRST_ENROLLMENT' THEN 'BOOTSTRAP_REGISTRATION' ELSE 'AUTHORIZED_REGISTRATION' END
               AND NEW.credential_event_id = assertion.projected_registered_event_id
               AND NEW.credential_event_content_hash = assertion.projected_registered_event_content_hash
               AND NEW.authorization_content_hash = assertion.projected_registered_authorization_content_hash
               AND NEW.webauthn_credential_id = assertion.webauthn_credential_id
               AND NEW.webauthn_credential_content_hash = assertion.projected_credential_content_hash
               AND NEW.registration_consumption_id = assertion.projected_registration_consumption_id
               AND NEW.registration_consumption_content_hash = assertion.projected_registration_consumption_content_hash
               AND NEW.registration_challenge_purpose = assertion.projected_registration_challenge_purpose
               AND NEW.registration_terminal_result = assertion.projected_registration_terminal_result
               AND ((assertion.operation_type = 'FIRST_ENROLLMENT'
                     AND NEW.credential_operation_authentication_event_id IS NULL
                     AND NEW.credential_operation_authentication_content_hash IS NULL
                     AND NEW.credential_operation_authentication_result IS NULL)
                 OR (assertion.operation_type IN ('ADD_CREDENTIAL', 'REPLACE_CREDENTIAL')
                     AND NEW.credential_operation_authentication_event_id = registration.prerequisite_authentication_event_id
                     AND NEW.credential_operation_authentication_content_hash = registration.prerequisite_authentication_content_hash
                     AND NEW.credential_operation_authentication_result = registration.prerequisite_authentication_result)))
           OR (assertion.operation_type = 'REPLACE_CREDENTIAL'
               AND NEW.event_type = 'SUPERSEDED'
               AND NEW.authorization_kind = 'AUTHORIZED_SUPERSESSION'
               AND NEW.credential_event_id = assertion.projected_superseded_event_id
               AND NEW.credential_event_content_hash = assertion.projected_superseded_event_content_hash
               AND NEW.authorization_content_hash = assertion.projected_superseded_authorization_content_hash
               AND NEW.webauthn_credential_id = operation.target_webauthn_credential_id
               AND NEW.registration_consumption_id IS NULL
               AND NEW.registration_consumption_content_hash IS NULL
               AND NEW.registration_challenge_purpose IS NULL
               AND NEW.registration_terminal_result IS NULL
               AND NEW.credential_operation_authentication_event_id = registration.prerequisite_authentication_event_id
               AND NEW.credential_operation_authentication_content_hash = registration.prerequisite_authentication_content_hash
               AND NEW.credential_operation_authentication_result = registration.prerequisite_authentication_result)
          )
    ) THEN RAISE(ABORT, 'counter capability lifecycle authorization projection mismatch') END;
END""",
    ),
    (
        "trg_0007_credential_events_counter_bootstrap_guard",
        """CREATE TRIGGER trg_0007_credential_events_counter_bootstrap_guard
BEFORE INSERT ON reviewer_webauthn_credential_events
BEGIN
    SELECT CASE WHEN EXISTS (
        SELECT 1
        FROM reviewer_webauthn_credential_event_authorizations authorization
        JOIN reviewer_webauthn_counter_capability_assertions assertion
          ON assertion.reviewer_credential_operation_id = authorization.reviewer_credential_operation_id
        WHERE authorization.credential_event_id = NEW.credential_event_id
    ) AND NOT EXISTS (
        SELECT 1
        FROM reviewer_webauthn_credential_event_authorizations authorization
        JOIN reviewer_webauthn_counter_capability_assertions assertion
          ON assertion.reviewer_credential_operation_id = authorization.reviewer_credential_operation_id
        JOIN reviewer_credential_operations operation
          ON operation.reviewer_credential_operation_id = assertion.reviewer_credential_operation_id
        WHERE authorization.credential_event_id = NEW.credential_event_id
          AND assertion.challenge_terminal_result = 'SUCCEEDED'
          AND authorization.credential_event_content_hash = NEW.credential_event_content_hash
          AND authorization.webauthn_credential_id = NEW.webauthn_credential_id
          AND authorization.reviewer_principal_id = NEW.reviewer_principal_id
          AND authorization.event_type = NEW.event_type
          AND (
              (NEW.event_type = 'REGISTERED'
               AND NEW.credential_event_id = assertion.projected_registered_event_id
               AND NEW.credential_event_content_hash = assertion.projected_registered_event_content_hash
               AND NEW.webauthn_credential_id = assertion.webauthn_credential_id
               AND NEW.supersedes_credential_event_id IS NULL
               AND authorization.authorization_content_hash = assertion.projected_registered_authorization_content_hash)
           OR (NEW.event_type = 'SUPERSEDED'
               AND assertion.operation_type = 'REPLACE_CREDENTIAL'
               AND NEW.credential_event_id = assertion.projected_superseded_event_id
               AND NEW.credential_event_content_hash = assertion.projected_superseded_event_content_hash
               AND NEW.webauthn_credential_id = operation.target_webauthn_credential_id
               AND NEW.supersedes_credential_event_id IS NOT NULL
               AND authorization.authorization_content_hash = assertion.projected_superseded_authorization_content_hash)
          )
    ) THEN RAISE(ABORT, 'counter capability lifecycle event projection mismatch') END;
END""",
    ),
)

_FROZEN_PROJECTION_GUARD_NAMES = tuple(name for name, _statement in _FROZEN_PROJECTION_GUARD_DDL)

_ASSERTION_COUNTER_GUARD_DDL = (
    "trg_0007_counter_capability_assertions_counter_union_guard",
    """CREATE TRIGGER trg_0007_counter_capability_assertions_counter_union_guard
BEFORE INSERT ON reviewer_webauthn_counter_capability_assertions
WHEN NEW.challenge_terminal_result = 'SUCCEEDED'
 AND NEW.classification_verified = 1
 AND NEW.selected_counter_capability = 'SIGN_COUNT_SUPPORTED'
BEGIN
    SELECT CASE WHEN NEW.previous_sign_count != 0 OR NEW.asserted_sign_count <= 0
        THEN RAISE(ABORT, 'supported bootstrap counter must be exact zero to positive edge') END;
    SELECT CASE WHEN EXISTS (
        SELECT 1 FROM reviewer_authentication_events issuer_event
         WHERE issuer_event.webauthn_credential_id = NEW.webauthn_credential_id
           AND issuer_event.authentication_result = 'VERIFIED'
           AND issuer_event.counter_capability = 'SIGN_COUNT_SUPPORTED'
        UNION ALL
        SELECT 1 FROM reviewer_credential_operation_authentication_events operation_event
         WHERE operation_event.authorizing_webauthn_credential_id = NEW.webauthn_credential_id
           AND operation_event.authentication_result = 'VERIFIED'
           AND operation_event.counter_capability = 'SIGN_COUNT_SUPPORTED'
        UNION ALL
        SELECT 1 FROM reviewer_webauthn_counter_capability_assertions bootstrap_event
         WHERE bootstrap_event.webauthn_credential_id = NEW.webauthn_credential_id
           AND bootstrap_event.challenge_terminal_result = 'SUCCEEDED'
           AND bootstrap_event.classification_verified = 1
           AND bootstrap_event.selected_counter_capability = 'SIGN_COUNT_SUPPORTED'
    ) THEN RAISE(ABORT, 'supported bootstrap counter must be unique first union edge') END;
END""",
)


def _legacy_counter_union_trigger_sql(
    *, trigger_name: str, table_name: str, credential_column: str
) -> str:
    """Return the byte-equivalent 0006 trigger definition for recovery."""

    return f"""CREATE TRIGGER {trigger_name}
BEFORE INSERT ON {table_name}
WHEN NEW.authentication_result = 'VERIFIED' AND NEW.counter_capability = 'SIGN_COUNT_SUPPORTED'
BEGIN
    SELECT CASE WHEN (
        SELECT COUNT(*) FROM (
            SELECT asserted_sign_count FROM reviewer_authentication_events
             WHERE webauthn_credential_id = NEW.{credential_column} AND authentication_result = 'VERIFIED' AND counter_capability = 'SIGN_COUNT_SUPPORTED'
            UNION ALL
            SELECT asserted_sign_count FROM reviewer_credential_operation_authentication_events
             WHERE authorizing_webauthn_credential_id = NEW.{credential_column} AND authentication_result = 'VERIFIED' AND counter_capability = 'SIGN_COUNT_SUPPORTED'
        )
    ) = 0 AND NEW.previous_sign_count != (
        SELECT registration_sign_count FROM reviewer_webauthn_credentials
        WHERE webauthn_credential_id = NEW.{credential_column}
    ) THEN RAISE(ABORT, 'supported counter must start at registration count') END;
    SELECT CASE WHEN (
        SELECT COUNT(*) FROM (
            SELECT asserted_sign_count FROM reviewer_authentication_events
             WHERE webauthn_credential_id = NEW.{credential_column} AND authentication_result = 'VERIFIED' AND counter_capability = 'SIGN_COUNT_SUPPORTED'
            UNION ALL
            SELECT asserted_sign_count FROM reviewer_credential_operation_authentication_events
             WHERE authorizing_webauthn_credential_id = NEW.{credential_column} AND authentication_result = 'VERIFIED' AND counter_capability = 'SIGN_COUNT_SUPPORTED'
        )
    ) > 0 AND (
        SELECT COUNT(*) FROM (
            SELECT asserted_sign_count AS leaf_value FROM reviewer_authentication_events issuer_leaf
             WHERE issuer_leaf.webauthn_credential_id = NEW.{credential_column}
               AND issuer_leaf.authentication_result = 'VERIFIED'
               AND issuer_leaf.counter_capability = 'SIGN_COUNT_SUPPORTED'
            UNION ALL
            SELECT asserted_sign_count AS leaf_value FROM reviewer_credential_operation_authentication_events operation_leaf
             WHERE operation_leaf.authorizing_webauthn_credential_id = NEW.{credential_column}
               AND operation_leaf.authentication_result = 'VERIFIED'
               AND operation_leaf.counter_capability = 'SIGN_COUNT_SUPPORTED'
        ) leaves
        WHERE NOT EXISTS (
            SELECT 1 FROM (
                SELECT previous_sign_count AS prior_value FROM reviewer_authentication_events issuer_prior
                 WHERE issuer_prior.webauthn_credential_id = NEW.{credential_column}
                   AND issuer_prior.authentication_result = 'VERIFIED'
                   AND issuer_prior.counter_capability = 'SIGN_COUNT_SUPPORTED'
                UNION ALL
                SELECT previous_sign_count AS prior_value FROM reviewer_credential_operation_authentication_events operation_prior
                 WHERE operation_prior.authorizing_webauthn_credential_id = NEW.{credential_column}
                   AND operation_prior.authentication_result = 'VERIFIED'
                   AND operation_prior.counter_capability = 'SIGN_COUNT_SUPPORTED'
            ) priors WHERE priors.prior_value = leaves.leaf_value
        ) AND leaves.leaf_value = NEW.previous_sign_count
    ) != 1 THEN RAISE(ABORT, 'supported counter previous value must equal unique union leaf') END;
    SELECT CASE WHEN EXISTS (
        SELECT 1 FROM reviewer_authentication_events issuer_event
         WHERE issuer_event.webauthn_credential_id = NEW.{credential_column}
           AND issuer_event.authentication_result = 'VERIFIED'
           AND (issuer_event.previous_sign_count = NEW.previous_sign_count OR issuer_event.asserted_sign_count = NEW.asserted_sign_count)
        UNION ALL
        SELECT 1 FROM reviewer_credential_operation_authentication_events operation_event
         WHERE operation_event.authorizing_webauthn_credential_id = NEW.{credential_column}
           AND operation_event.authentication_result = 'VERIFIED'
           AND (operation_event.previous_sign_count = NEW.previous_sign_count OR operation_event.asserted_sign_count = NEW.asserted_sign_count)
    ) THEN RAISE(ABORT, 'supported counter union fork or duplicate rejected') END;
END"""


def _counter_union_trigger_sql(
    *, trigger_name: str, table_name: str, credential_column: str
) -> str:
    return f"""CREATE TRIGGER {trigger_name}
BEFORE INSERT ON {table_name}
WHEN NEW.authentication_result = 'VERIFIED' AND NEW.counter_capability = 'SIGN_COUNT_SUPPORTED'
BEGIN
    SELECT CASE WHEN (
        SELECT COUNT(*) FROM (
            SELECT asserted_sign_count FROM reviewer_authentication_events
             WHERE webauthn_credential_id = NEW.{credential_column} AND authentication_result = 'VERIFIED' AND counter_capability = 'SIGN_COUNT_SUPPORTED'
            UNION ALL
            SELECT asserted_sign_count FROM reviewer_credential_operation_authentication_events
             WHERE authorizing_webauthn_credential_id = NEW.{credential_column} AND authentication_result = 'VERIFIED' AND counter_capability = 'SIGN_COUNT_SUPPORTED'
            UNION ALL
            SELECT asserted_sign_count FROM reviewer_webauthn_counter_capability_assertions
             WHERE webauthn_credential_id = NEW.{credential_column} AND challenge_terminal_result = 'SUCCEEDED' AND classification_verified = 1 AND selected_counter_capability = 'SIGN_COUNT_SUPPORTED'
        )
    ) = 0 AND NEW.previous_sign_count != (
        SELECT registration_sign_count FROM reviewer_webauthn_credentials
        WHERE webauthn_credential_id = NEW.{credential_column}
    ) THEN RAISE(ABORT, 'supported counter must start at registration count') END;
    SELECT CASE WHEN (
        SELECT COUNT(*) FROM (
            SELECT asserted_sign_count FROM reviewer_authentication_events
             WHERE webauthn_credential_id = NEW.{credential_column} AND authentication_result = 'VERIFIED' AND counter_capability = 'SIGN_COUNT_SUPPORTED'
            UNION ALL
            SELECT asserted_sign_count FROM reviewer_credential_operation_authentication_events
             WHERE authorizing_webauthn_credential_id = NEW.{credential_column} AND authentication_result = 'VERIFIED' AND counter_capability = 'SIGN_COUNT_SUPPORTED'
            UNION ALL
            SELECT asserted_sign_count FROM reviewer_webauthn_counter_capability_assertions
             WHERE webauthn_credential_id = NEW.{credential_column} AND challenge_terminal_result = 'SUCCEEDED' AND classification_verified = 1 AND selected_counter_capability = 'SIGN_COUNT_SUPPORTED'
        )
    ) > 0 AND (
        SELECT COUNT(*) FROM (
            SELECT asserted_sign_count AS leaf_value FROM reviewer_authentication_events issuer_leaf
             WHERE issuer_leaf.webauthn_credential_id = NEW.{credential_column}
               AND issuer_leaf.authentication_result = 'VERIFIED'
               AND issuer_leaf.counter_capability = 'SIGN_COUNT_SUPPORTED'
            UNION ALL
            SELECT asserted_sign_count AS leaf_value FROM reviewer_credential_operation_authentication_events operation_leaf
             WHERE operation_leaf.authorizing_webauthn_credential_id = NEW.{credential_column}
               AND operation_leaf.authentication_result = 'VERIFIED'
               AND operation_leaf.counter_capability = 'SIGN_COUNT_SUPPORTED'
            UNION ALL
            SELECT asserted_sign_count AS leaf_value FROM reviewer_webauthn_counter_capability_assertions bootstrap_leaf
             WHERE bootstrap_leaf.webauthn_credential_id = NEW.{credential_column}
               AND bootstrap_leaf.challenge_terminal_result = 'SUCCEEDED'
               AND bootstrap_leaf.classification_verified = 1
               AND bootstrap_leaf.selected_counter_capability = 'SIGN_COUNT_SUPPORTED'
        ) leaves
        WHERE NOT EXISTS (
            SELECT 1 FROM (
                SELECT previous_sign_count AS prior_value FROM reviewer_authentication_events issuer_prior
                 WHERE issuer_prior.webauthn_credential_id = NEW.{credential_column}
                   AND issuer_prior.authentication_result = 'VERIFIED'
                   AND issuer_prior.counter_capability = 'SIGN_COUNT_SUPPORTED'
                UNION ALL
                SELECT previous_sign_count AS prior_value FROM reviewer_credential_operation_authentication_events operation_prior
                 WHERE operation_prior.authorizing_webauthn_credential_id = NEW.{credential_column}
                   AND operation_prior.authentication_result = 'VERIFIED'
                   AND operation_prior.counter_capability = 'SIGN_COUNT_SUPPORTED'
                UNION ALL
                SELECT previous_sign_count AS prior_value FROM reviewer_webauthn_counter_capability_assertions bootstrap_prior
                 WHERE bootstrap_prior.webauthn_credential_id = NEW.{credential_column}
                   AND bootstrap_prior.challenge_terminal_result = 'SUCCEEDED'
                   AND bootstrap_prior.classification_verified = 1
                   AND bootstrap_prior.selected_counter_capability = 'SIGN_COUNT_SUPPORTED'
            ) priors WHERE priors.prior_value = leaves.leaf_value
        ) AND leaves.leaf_value = NEW.previous_sign_count
    ) != 1 THEN RAISE(ABORT, 'supported counter previous value must equal unique union leaf') END;
    SELECT CASE WHEN EXISTS (
        SELECT 1 FROM reviewer_authentication_events issuer_event
         WHERE issuer_event.webauthn_credential_id = NEW.{credential_column}
           AND issuer_event.authentication_result = 'VERIFIED'
           AND (issuer_event.previous_sign_count = NEW.previous_sign_count OR issuer_event.asserted_sign_count = NEW.asserted_sign_count)
        UNION ALL
        SELECT 1 FROM reviewer_credential_operation_authentication_events operation_event
         WHERE operation_event.authorizing_webauthn_credential_id = NEW.{credential_column}
           AND operation_event.authentication_result = 'VERIFIED'
           AND (operation_event.previous_sign_count = NEW.previous_sign_count OR operation_event.asserted_sign_count = NEW.asserted_sign_count)
        UNION ALL
        SELECT 1 FROM reviewer_webauthn_counter_capability_assertions bootstrap_event
         WHERE bootstrap_event.webauthn_credential_id = NEW.{credential_column}
           AND bootstrap_event.challenge_terminal_result = 'SUCCEEDED'
           AND bootstrap_event.classification_verified = 1
           AND bootstrap_event.selected_counter_capability = 'SIGN_COUNT_SUPPORTED'
           AND (bootstrap_event.previous_sign_count = NEW.previous_sign_count OR bootstrap_event.asserted_sign_count = NEW.asserted_sign_count)
    ) THEN RAISE(ABORT, 'supported counter union fork or duplicate rejected') END;
END"""


_COUNTER_TRIGGER_SPECS = (
    (
        "trg_reviewer_authentication_events_counter_union_guard",
        "reviewer_authentication_events",
        "webauthn_credential_id",
    ),
    (
        "trg_reviewer_credential_operation_authentication_counter_union_guard",
        "reviewer_credential_operation_authentication_events",
        "authorizing_webauthn_credential_id",
    ),
)

_LEGACY_COUNTER_GUARD_DDL = tuple(
    (
        trigger_name,
        _legacy_counter_union_trigger_sql(
            trigger_name=trigger_name,
            table_name=table_name,
            credential_column=credential_column,
        ),
    )
    for trigger_name, table_name, credential_column in _COUNTER_TRIGGER_SPECS
)

_COUNTER_GUARD_DDL = tuple(
    (
        trigger_name,
        _counter_union_trigger_sql(
            trigger_name=trigger_name,
            table_name=table_name,
            credential_column=credential_column,
        ),
    )
    for trigger_name, table_name, credential_column in _COUNTER_TRIGGER_SPECS
)

_COUNTER_GUARD_NAMES = tuple(name for name, _statement in _COUNTER_GUARD_DDL)

_NEW_TRIGGER_NAMES = (
    _APPEND_ONLY_TRIGGER_NAMES
    + _NEW_INSERT_GUARD_NAMES
    + _FROZEN_PROJECTION_GUARD_NAMES
    + (_ASSERTION_COUNTER_GUARD_DDL[0],)
)
_INDEX_DDL = _FROZEN_INDEX_DDL + _NEW_INDEX_DDL
_INDEX_NAMES = tuple(name for name, _statement in _INDEX_DDL)

_EXPECTED_TABLE_COLUMNS = {
    _REGISTRATIONS: {
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
    },
    _CHALLENGES: {
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
    },
    _ASSERTIONS: {
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
    },
}

_REQUIRED_PARENT_INDEX_COLUMNS = {
    "uq_reviewer_credential_operations_exact_binding": (
        "reviewer_credential_operation_id",
        "operation_content_hash",
        "reviewer_principal_id",
        "reviewer_role",
        "principal_content_hash",
        "os_owner_sid_hash",
        "operation_type",
        "expected_credential_state_hash",
    ),
    "uq_reviewer_credential_operation_challenges_exact_binding": (
        "reviewer_credential_operation_challenge_id",
        "reviewer_credential_operation_id",
        "reviewer_principal_id",
        "operation_type",
        "challenge_purpose",
        "challenge_binding_hash",
    ),
    "uq_reviewer_credential_operation_consumptions_exact_terminal": (
        "challenge_consumption_id",
        "reviewer_credential_operation_id",
        "reviewer_principal_id",
        "challenge_purpose",
        "terminal_result",
        "consumption_content_hash",
    ),
    "uq_reviewer_credential_operation_authentication_exact_result": (
        "credential_operation_authentication_event_id",
        "authentication_content_hash",
        "reviewer_credential_operation_id",
        "reviewer_principal_id",
        "authentication_result",
    ),
    "uq_reviewer_credentials_exact_content": (
        "webauthn_credential_id",
        "credential_content_hash",
    ),
    "uq_reviewer_credential_events_exact_authorization": (
        "credential_event_id",
        "credential_event_content_hash",
        "webauthn_credential_id",
        "reviewer_principal_id",
        "event_type",
    ),
}


def _git_blob_id(path: Path) -> str:
    payload = path.read_bytes()
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload, usedforsecurity=False).hexdigest()


def _verify_frozen_migrations() -> None:
    versions = Path(__file__).resolve().parent
    actual = {name: _git_blob_id(versions / name) for name in _FROZEN_MIGRATION_BLOBS}
    if actual != _FROZEN_MIGRATION_BLOBS:
        mismatches = ", ".join(
            f"{name}:{actual.get(name)}!={expected}"
            for name, expected in _FROZEN_MIGRATION_BLOBS.items()
            if actual.get(name) != expected
        )
        raise RuntimeError("0007 frozen predecessor migration mismatch: " + mismatches)


def _sqlite_objects(connection: Connection) -> set[tuple[str, str]]:
    rows = connection.execute(
        sa.text("SELECT type, name FROM sqlite_master WHERE type IN ('table', 'index', 'trigger')")
    ).mappings()
    return {(str(row["type"]), str(row["name"])) for row in rows}


def _table_columns(connection: Connection, table_name: str) -> set[str]:
    rows = connection.exec_driver_sql(f'PRAGMA table_info("{table_name}")').mappings()
    return {str(row["name"]) for row in rows}


def _index_columns(connection: Connection, index_name: str) -> tuple[str, ...]:
    rows = connection.exec_driver_sql(f'PRAGMA index_info("{index_name}")').mappings()
    return tuple(str(row["name"]) for row in rows)


def _trigger_sql(connection: Connection, trigger_name: str) -> str | None:
    value = connection.execute(
        sa.text("SELECT sql FROM sqlite_master WHERE type='trigger' AND name=:name"),
        {"name": trigger_name},
    ).scalar_one_or_none()
    return None if value is None else str(value)


def _target_new_objects() -> set[tuple[str, str]]:
    return (
        {("table", name) for name in _NEW_TABLE_NAMES}
        | {("index", name) for name in _INDEX_NAMES}
        | {("trigger", name) for name in _NEW_TRIGGER_NAMES}
    )


def _verify_predecessor_schema(connection: Connection) -> None:
    current_revision = connection.execute(
        sa.text("SELECT version_num FROM alembic_version")
    ).scalar_one()
    if str(current_revision) != down_revision:
        raise RuntimeError(
            f"0007 requires exact predecessor revision {down_revision}; got {current_revision}"
        )
    objects = _sqlite_objects(connection)
    required_tables = {
        "reviewer_credential_operations",
        "reviewer_credential_operation_challenges",
        "reviewer_credential_operation_challenge_consumptions",
        "reviewer_credential_operation_authentication_events",
        "reviewer_credential_operation_outcomes",
        "reviewer_principals",
        "reviewer_webauthn_credentials",
        "reviewer_webauthn_credential_events",
        "reviewer_webauthn_credential_event_authorizations",
        "reviewer_authentication_events",
    }
    missing_tables = sorted(table for table in required_tables if ("table", table) not in objects)
    if missing_tables:
        raise RuntimeError(f"0007 predecessor tables missing: {missing_tables}")
    for index_name, expected_columns in _REQUIRED_PARENT_INDEX_COLUMNS.items():
        if ("index", index_name) not in objects:
            raise RuntimeError(f"0007 predecessor parent index missing: {index_name}")
        actual_columns = _index_columns(connection, index_name)
        if actual_columns != expected_columns:
            raise RuntimeError(
                f"0007 predecessor parent index mismatch for {index_name}: "
                f"{actual_columns!r} != {expected_columns!r}"
            )
    for trigger_name, expected_sql in _LEGACY_COUNTER_GUARD_DDL:
        actual_sql = _trigger_sql(connection, trigger_name)
        if actual_sql != expected_sql:
            raise RuntimeError(f"0007 frozen counter trigger mismatch for {trigger_name}")


def _execute_all(connection: Connection, statements: Iterable[str]) -> None:
    for statement in statements:
        connection.exec_driver_sql(statement)


def _restore_legacy_counter_guards(connection: Connection) -> None:
    _execute_all(
        connection,
        (f"DROP TRIGGER IF EXISTS {name}" for name in _COUNTER_GUARD_NAMES),
    )
    for _name, statement in _LEGACY_COUNTER_GUARD_DDL:
        connection.exec_driver_sql(statement)


def _drop_new_objects(connection: Connection) -> None:
    _execute_all(
        connection,
        (f"DROP TRIGGER IF EXISTS {name}" for name in reversed(_NEW_TRIGGER_NAMES)),
    )
    _execute_all(
        connection,
        (f"DROP INDEX IF EXISTS {name}" for name in reversed(_INDEX_NAMES)),
    )
    _execute_all(
        connection,
        (f"DROP TABLE IF EXISTS {name}" for name in reversed(_NEW_TABLE_NAMES)),
    )


def _cleanup_failed_upgrade(connection: Connection) -> None:
    _restore_legacy_counter_guards(connection)
    _drop_new_objects(connection)


def _verify_created_schema(connection: Connection) -> None:
    objects = _sqlite_objects(connection)
    missing = sorted(_target_new_objects() - objects)
    if missing:
        rendered = ", ".join(f"{kind}:{name}" for kind, name in missing)
        raise RuntimeError("0007 schema inventory incomplete: " + rendered)
    for table_name, expected_columns in _EXPECTED_TABLE_COLUMNS.items():
        actual_columns = _table_columns(connection, table_name)
        if actual_columns != expected_columns:
            missing_columns = sorted(expected_columns - actual_columns)
            extra_columns = sorted(actual_columns - expected_columns)
            raise RuntimeError(
                f"0007 table surface mismatch for {table_name}: "
                f"missing={missing_columns}, extra={extra_columns}"
            )
    for trigger_name, expected_sql in _COUNTER_GUARD_DDL:
        if _trigger_sql(connection, trigger_name) != expected_sql:
            raise RuntimeError(f"0007 counter trigger replacement failed: {trigger_name}")
    violations = tuple(connection.exec_driver_sql("PRAGMA foreign_key_check"))
    if violations:
        raise RuntimeError(f"0007 foreign_key_check failed: {violations!r}")


def upgrade() -> None:
    connection = op.get_bind()
    _verify_frozen_migrations()
    collisions = sorted(_sqlite_objects(connection) & _target_new_objects())
    if collisions:
        rendered = ", ".join(f"{kind}:{name}" for kind, name in collisions)
        raise RuntimeError("0007 refuses to replace pre-existing objects: " + rendered)
    _verify_predecessor_schema(connection)
    try:
        for _name, statement in _FROZEN_INDEX_DDL:
            op.execute(sa.text(statement))
        for _name, statement in _NEW_TABLE_DDL:
            op.execute(sa.text(statement))
        for _name, statement in _NEW_INDEX_DDL:
            op.execute(sa.text(statement))
        for table_name in _NEW_TABLE_NAMES:
            for operation in ("UPDATE", "DELETE"):
                op.execute(sa.text(_append_only_trigger_sql(table_name, operation)))
        for _name, statement in _NEW_INSERT_GUARD_DDL:
            op.execute(sa.text(statement))
        for _name, statement in _FROZEN_PROJECTION_GUARD_DDL:
            op.execute(sa.text(statement))
        op.execute(sa.text(_ASSERTION_COUNTER_GUARD_DDL[1]))
        for trigger_name in _COUNTER_GUARD_NAMES:
            op.execute(sa.text(f"DROP TRIGGER {trigger_name}"))
        for _name, statement in _COUNTER_GUARD_DDL:
            op.execute(sa.text(statement))
        _verify_created_schema(connection)
    except Exception:
        _cleanup_failed_upgrade(connection)
        raise


def downgrade() -> None:
    connection = op.get_bind()
    objects = _sqlite_objects(connection)
    for table_name in _NEW_TABLE_NAMES:
        if ("table", table_name) not in objects:
            continue
        has_rows = connection.exec_driver_sql(
            f'SELECT EXISTS(SELECT 1 FROM "{table_name}" LIMIT 1)'
        ).scalar_one()
        if bool(has_rows):
            raise RuntimeError(
                "0007 destructive downgrade refused: counter capability audit ledger is non-empty"
            )
    _restore_legacy_counter_guards(connection)
    _drop_new_objects(connection)
    for trigger_name, expected_sql in _LEGACY_COUNTER_GUARD_DDL:
        if _trigger_sql(connection, trigger_name) != expected_sql:
            raise RuntimeError(f"0007 downgrade failed to restore {trigger_name}")
    violations = tuple(connection.exec_driver_sql("PRAGMA foreign_key_check"))
    if violations:
        raise RuntimeError(f"0007 downgrade foreign_key_check failed: {violations!r}")
