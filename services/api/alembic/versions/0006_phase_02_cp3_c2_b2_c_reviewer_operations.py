# ruff: noqa: E501
"""Phase 2 CP3-C2-B2-C reviewer credential-operation ledger.

Revision 0006 is additive.  SQLite stores and checks the approved relational
bindings; aggregate ``reviewer-credential-state/0.1.0`` SHA-256 calculation is
deliberately left to trusted server code under ``BEGIN IMMEDIATE``.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import Connection

revision = "0006_phase_02_cp3_c2_b2_c_reviewer_operations"
down_revision = "0005_phase_02_cp3_c2_b_issuer_authority"
branch_labels = None
depends_on = None

_FROZEN_MIGRATION_BLOBS = {
    "0001_phase_01_foundation.py": "d00355c2456021e6ffb195e50833adc32c74a4ad",
    "0002_phase_02_cp3_foundation.py": "53f40664eca2ea2466cc6154b8579c5db506e0ba",
    "0003_phase_02_cp3_b_invariants.py": "47d5a69009949b155211cd68209640136a7cacd9",
    "0004_phase_02_cp3_c1_security_master.py": "91b4d96a445be23e7aa55e08b9310dc7334a026d",
    "0005_phase_02_cp3_c2_b_issuer_authority.py": "81976b8f70a1f6107526a13acadf23f369b196e3",
}

_NEW_TABLE_DDL: tuple[tuple[str, str], ...] = (
    (
        "reviewer_credential_operations",
        """CREATE TABLE reviewer_credential_operations (
    reviewer_credential_operation_id VARCHAR(128) NOT NULL,
    contract_version VARCHAR(64) NOT NULL,
    operation_content_hash VARCHAR(71) NOT NULL,
    reviewer_principal_id VARCHAR(128) NOT NULL,
    reviewer_role VARCHAR(32) NOT NULL,
    principal_content_hash VARCHAR(71) NOT NULL,
    os_owner_sid_hash VARCHAR(71) NOT NULL,
    operation_type VARCHAR(32) NOT NULL,
    target_webauthn_credential_id VARCHAR(512),
    target_credential_id_fingerprint VARCHAR(71),
    expected_credential_state_hash VARCHAR(71) NOT NULL,
    initial_challenge_id VARCHAR(128) NOT NULL,
    initial_challenge_purpose VARCHAR(32) NOT NULL,
    predecessor_operation_id VARCHAR(128),
    operation_policy_version VARCHAR(64) NOT NULL,
    created_at VARCHAR(35) NOT NULL,
    payload_json TEXT NOT NULL,
    PRIMARY KEY (reviewer_credential_operation_id),
    UNIQUE (operation_content_hash),
    CHECK (contract_version = 'reviewer-credential-operation/0.1.0'),
    CHECK (length(operation_content_hash) = 71 AND substr(operation_content_hash, 1, 7) = 'sha256:' AND substr(operation_content_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (reviewer_role = 'LOCAL_DATA_STEWARD'),
    CHECK (length(principal_content_hash) = 71 AND substr(principal_content_hash, 1, 7) = 'sha256:' AND substr(principal_content_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (length(os_owner_sid_hash) = 71 AND substr(os_owner_sid_hash, 1, 7) = 'sha256:' AND substr(os_owner_sid_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (operation_type IN ('FIRST_ENROLLMENT', 'ADD_CREDENTIAL', 'REPLACE_CREDENTIAL', 'REVOKE_CREDENTIAL')),
    CHECK ((target_webauthn_credential_id IS NULL AND target_credential_id_fingerprint IS NULL) OR (target_webauthn_credential_id IS NOT NULL AND target_credential_id_fingerprint IS NOT NULL)),
    CHECK ((operation_type IN ('FIRST_ENROLLMENT', 'ADD_CREDENTIAL') AND target_webauthn_credential_id IS NULL) OR (operation_type IN ('REPLACE_CREDENTIAL', 'REVOKE_CREDENTIAL') AND target_webauthn_credential_id IS NOT NULL)),
    CHECK (target_credential_id_fingerprint IS NULL OR (length(target_credential_id_fingerprint) = 71 AND substr(target_credential_id_fingerprint, 1, 7) = 'sha256:' AND substr(target_credential_id_fingerprint, 8) NOT GLOB '*[^0-9a-f]*')),
    CHECK (length(expected_credential_state_hash) = 71 AND substr(expected_credential_state_hash, 1, 7) = 'sha256:' AND substr(expected_credential_state_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK ((operation_type = 'FIRST_ENROLLMENT' AND initial_challenge_purpose = 'REGISTRATION_CREATE') OR (operation_type IN ('ADD_CREDENTIAL', 'REPLACE_CREDENTIAL', 'REVOKE_CREDENTIAL') AND initial_challenge_purpose = 'AUTHORIZATION_ASSERTION')),
    CHECK (predecessor_operation_id IS NOT NULL OR operation_type = 'FIRST_ENROLLMENT'),
    CHECK (julianday(created_at) IS NOT NULL AND substr(created_at, -1) = 'Z'),
    FOREIGN KEY (reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash)
        REFERENCES reviewer_principals (reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash),
    FOREIGN KEY (predecessor_operation_id, reviewer_principal_id)
        REFERENCES reviewer_credential_operations (reviewer_credential_operation_id, reviewer_principal_id)
        DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (target_webauthn_credential_id, reviewer_principal_id, target_credential_id_fingerprint)
        REFERENCES reviewer_webauthn_credentials (webauthn_credential_id, reviewer_principal_id, credential_id_fingerprint)
        DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (initial_challenge_id, reviewer_credential_operation_id, reviewer_principal_id, operation_type, initial_challenge_purpose)
        REFERENCES reviewer_credential_operation_challenges (reviewer_credential_operation_challenge_id, reviewer_credential_operation_id, reviewer_principal_id, operation_type, challenge_purpose)
        DEFERRABLE INITIALLY DEFERRED
)""",
    ),
    (
        "reviewer_credential_operation_challenges",
        """CREATE TABLE reviewer_credential_operation_challenges (
    reviewer_credential_operation_challenge_id VARCHAR(128) NOT NULL,
    contract_version VARCHAR(64) NOT NULL,
    challenge_digest VARCHAR(71) NOT NULL,
    challenge_binding_hash VARCHAR(71) NOT NULL,
    challenge_nonce_length INTEGER NOT NULL,
    reviewer_credential_operation_id VARCHAR(128) NOT NULL,
    operation_content_hash VARCHAR(71) NOT NULL,
    reviewer_principal_id VARCHAR(128) NOT NULL,
    reviewer_role VARCHAR(32) NOT NULL,
    principal_content_hash VARCHAR(71) NOT NULL,
    os_owner_sid_hash VARCHAR(71) NOT NULL,
    operation_type VARCHAR(32) NOT NULL,
    challenge_purpose VARCHAR(32) NOT NULL,
    expected_credential_state_hash VARCHAR(71) NOT NULL,
    target_webauthn_credential_id VARCHAR(512),
    target_credential_id_fingerprint VARCHAR(71),
    prerequisite_authentication_event_id VARCHAR(128),
    prerequisite_authentication_content_hash VARCHAR(71),
    prerequisite_authentication_result VARCHAR(16),
    rp_id VARCHAR(255) NOT NULL,
    allowed_origin VARCHAR(255) NOT NULL,
    client_data_type VARCHAR(32) NOT NULL,
    user_verification_required INTEGER NOT NULL,
    platform_attachment_required INTEGER,
    resident_key_required INTEGER,
    authentication_policy_version VARCHAR(64) NOT NULL,
    issued_at VARCHAR(35) NOT NULL,
    expires_at VARCHAR(35) NOT NULL,
    payload_json TEXT NOT NULL,
    PRIMARY KEY (reviewer_credential_operation_challenge_id),
    UNIQUE (challenge_digest),
    UNIQUE (challenge_binding_hash),
    CHECK (contract_version = 'reviewer-credential-operation-challenge/0.1.0'),
    CHECK (length(challenge_digest) = 71 AND substr(challenge_digest, 1, 7) = 'sha256:' AND substr(challenge_digest, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (length(challenge_binding_hash) = 71 AND substr(challenge_binding_hash, 1, 7) = 'sha256:' AND substr(challenge_binding_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (challenge_nonce_length = 32),
    CHECK (length(operation_content_hash) = 71 AND substr(operation_content_hash, 1, 7) = 'sha256:' AND substr(operation_content_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (reviewer_role = 'LOCAL_DATA_STEWARD'),
    CHECK (length(principal_content_hash) = 71 AND substr(principal_content_hash, 1, 7) = 'sha256:' AND substr(principal_content_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (length(os_owner_sid_hash) = 71 AND substr(os_owner_sid_hash, 1, 7) = 'sha256:' AND substr(os_owner_sid_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (operation_type IN ('FIRST_ENROLLMENT', 'ADD_CREDENTIAL', 'REPLACE_CREDENTIAL', 'REVOKE_CREDENTIAL')),
    CHECK (challenge_purpose IN ('REGISTRATION_CREATE', 'AUTHORIZATION_ASSERTION')),
    CHECK (length(expected_credential_state_hash) = 71 AND substr(expected_credential_state_hash, 1, 7) = 'sha256:' AND substr(expected_credential_state_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK ((target_webauthn_credential_id IS NULL AND target_credential_id_fingerprint IS NULL) OR (target_webauthn_credential_id IS NOT NULL AND target_credential_id_fingerprint IS NOT NULL)),
    CHECK (target_credential_id_fingerprint IS NULL OR (length(target_credential_id_fingerprint) = 71 AND substr(target_credential_id_fingerprint, 1, 7) = 'sha256:' AND substr(target_credential_id_fingerprint, 8) NOT GLOB '*[^0-9a-f]*')),
    CHECK ((prerequisite_authentication_event_id IS NULL AND prerequisite_authentication_content_hash IS NULL AND prerequisite_authentication_result IS NULL) OR (prerequisite_authentication_event_id IS NOT NULL AND prerequisite_authentication_content_hash IS NOT NULL AND prerequisite_authentication_result = 'VERIFIED')),
    CHECK (prerequisite_authentication_content_hash IS NULL OR (length(prerequisite_authentication_content_hash) = 71 AND substr(prerequisite_authentication_content_hash, 1, 7) = 'sha256:' AND substr(prerequisite_authentication_content_hash, 8) NOT GLOB '*[^0-9a-f]*')),
    CHECK (rp_id = 'localhost'),
    CHECK (allowed_origin = 'http://localhost:3000'),
    CHECK (user_verification_required = 1),
    CHECK ((challenge_purpose = 'REGISTRATION_CREATE' AND client_data_type = 'webauthn.create' AND platform_attachment_required = 1 AND resident_key_required = 1) OR (challenge_purpose = 'AUTHORIZATION_ASSERTION' AND client_data_type = 'webauthn.get' AND platform_attachment_required IS NULL AND resident_key_required IS NULL)),
    CHECK ((operation_type = 'FIRST_ENROLLMENT' AND challenge_purpose = 'REGISTRATION_CREATE' AND prerequisite_authentication_event_id IS NULL) OR (operation_type IN ('ADD_CREDENTIAL', 'REPLACE_CREDENTIAL') AND ((challenge_purpose = 'AUTHORIZATION_ASSERTION' AND prerequisite_authentication_event_id IS NULL) OR (challenge_purpose = 'REGISTRATION_CREATE' AND prerequisite_authentication_event_id IS NOT NULL))) OR (operation_type = 'REVOKE_CREDENTIAL' AND challenge_purpose = 'AUTHORIZATION_ASSERTION' AND prerequisite_authentication_event_id IS NULL)),
    CHECK (julianday(issued_at) IS NOT NULL AND julianday(expires_at) IS NOT NULL AND substr(issued_at, -1) = 'Z' AND substr(expires_at, -1) = 'Z'),
    CHECK (julianday(expires_at) > julianday(issued_at)),
    CHECK (julianday(expires_at) <= julianday(issued_at, '+5 minutes')),
    FOREIGN KEY (reviewer_credential_operation_id, operation_content_hash, reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash, operation_type, expected_credential_state_hash)
        REFERENCES reviewer_credential_operations (reviewer_credential_operation_id, operation_content_hash, reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash, operation_type, expected_credential_state_hash)
        DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (prerequisite_authentication_event_id, prerequisite_authentication_content_hash, reviewer_credential_operation_id, reviewer_principal_id, prerequisite_authentication_result)
        REFERENCES reviewer_credential_operation_authentication_events (credential_operation_authentication_event_id, authentication_content_hash, reviewer_credential_operation_id, reviewer_principal_id, authentication_result)
        DEFERRABLE INITIALLY DEFERRED
)""",
    ),
    (
        "reviewer_credential_operation_challenge_consumptions",
        """CREATE TABLE reviewer_credential_operation_challenge_consumptions (
    challenge_consumption_id VARCHAR(128) NOT NULL,
    contract_version VARCHAR(64) NOT NULL,
    reviewer_credential_operation_challenge_id VARCHAR(128) NOT NULL,
    reviewer_credential_operation_id VARCHAR(128) NOT NULL,
    reviewer_principal_id VARCHAR(128) NOT NULL,
    operation_type VARCHAR(32) NOT NULL,
    challenge_purpose VARCHAR(32) NOT NULL,
    challenge_binding_hash VARCHAR(71) NOT NULL,
    terminal_result VARCHAR(32) NOT NULL,
    safe_result_code VARCHAR(128) NOT NULL,
    client_data_type_verified INTEGER NOT NULL,
    challenge_verified INTEGER NOT NULL,
    origin_verified INTEGER NOT NULL,
    cross_origin_false_verified INTEGER NOT NULL,
    rp_id_hash_verified INTEGER NOT NULL,
    user_presence_verified INTEGER NOT NULL,
    user_verification_verified INTEGER NOT NULL,
    platform_authenticator_verified INTEGER,
    resident_key_verified INTEGER,
    public_key_material_verified INTEGER,
    registered_webauthn_credential_id VARCHAR(512),
    registered_credential_content_hash VARCHAR(71),
    registered_credential_id_fingerprint VARCHAR(71),
    registered_public_key_fingerprint VARCHAR(71),
    registered_rp_id VARCHAR(255),
    registered_counter_capability VARCHAR(32),
    registered_sign_count INTEGER,
    terminal_operation_outcome_id VARCHAR(128),
    terminal_operation_outcome_result VARCHAR(16),
    outcome_expected_credential_state_hash VARCHAR(71),
    outcome_resulting_credential_state_hash VARCHAR(71),
    continuation_challenge_id VARCHAR(128),
    continuation_challenge_purpose VARCHAR(32),
    consumption_content_hash VARCHAR(71) NOT NULL,
    consumed_at VARCHAR(35) NOT NULL,
    payload_json TEXT NOT NULL,
    PRIMARY KEY (challenge_consumption_id),
    UNIQUE (reviewer_credential_operation_challenge_id),
    UNIQUE (consumption_content_hash),
    CHECK (contract_version = 'reviewer-credential-operation-consumption/0.1.0'),
    CHECK (operation_type IN ('FIRST_ENROLLMENT', 'ADD_CREDENTIAL', 'REPLACE_CREDENTIAL', 'REVOKE_CREDENTIAL')),
    CHECK (challenge_purpose IN ('REGISTRATION_CREATE', 'AUTHORIZATION_ASSERTION')),
    CHECK (length(challenge_binding_hash) = 71 AND substr(challenge_binding_hash, 1, 7) = 'sha256:' AND substr(challenge_binding_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (terminal_result IN ('SUCCEEDED', 'EXPIRED', 'BINDING_MISMATCH', 'ORIGIN_RP_MISMATCH', 'USER_PRESENCE_ABSENT', 'USER_VERIFICATION_ABSENT', 'INVALID_REGISTRATION', 'INVALID_SIGNATURE', 'COUNTER_REJECTED', 'REPLAY_REJECTED', 'FAILED_CLOSED')),
    CHECK (client_data_type_verified IN (0, 1) AND challenge_verified IN (0, 1) AND origin_verified IN (0, 1) AND cross_origin_false_verified IN (0, 1) AND rp_id_hash_verified IN (0, 1) AND user_presence_verified IN (0, 1) AND user_verification_verified IN (0, 1)),
    CHECK (platform_authenticator_verified IS NULL OR platform_authenticator_verified IN (0, 1)),
    CHECK (resident_key_verified IS NULL OR resident_key_verified IN (0, 1)),
    CHECK (public_key_material_verified IS NULL OR public_key_material_verified IN (0, 1)),
    CHECK ((registered_webauthn_credential_id IS NULL AND registered_credential_content_hash IS NULL AND registered_credential_id_fingerprint IS NULL AND registered_public_key_fingerprint IS NULL AND registered_rp_id IS NULL AND registered_counter_capability IS NULL AND registered_sign_count IS NULL) OR (registered_webauthn_credential_id IS NOT NULL AND registered_credential_content_hash IS NOT NULL AND registered_credential_id_fingerprint IS NOT NULL AND registered_public_key_fingerprint IS NOT NULL AND registered_rp_id IS NOT NULL AND registered_counter_capability IS NOT NULL)),
    CHECK (registered_credential_content_hash IS NULL OR (length(registered_credential_content_hash) = 71 AND substr(registered_credential_content_hash, 1, 7) = 'sha256:' AND substr(registered_credential_content_hash, 8) NOT GLOB '*[^0-9a-f]*')),
    CHECK (registered_credential_id_fingerprint IS NULL OR (length(registered_credential_id_fingerprint) = 71 AND substr(registered_credential_id_fingerprint, 1, 7) = 'sha256:' AND substr(registered_credential_id_fingerprint, 8) NOT GLOB '*[^0-9a-f]*')),
    CHECK (registered_public_key_fingerprint IS NULL OR (length(registered_public_key_fingerprint) = 71 AND substr(registered_public_key_fingerprint, 1, 7) = 'sha256:' AND substr(registered_public_key_fingerprint, 8) NOT GLOB '*[^0-9a-f]*')),
    CHECK (registered_counter_capability IS NULL OR registered_counter_capability IN ('SIGN_COUNT_SUPPORTED', 'NO_USABLE_COUNTER')),
    CHECK ((registered_counter_capability IS NULL AND registered_sign_count IS NULL) OR (registered_counter_capability = 'SIGN_COUNT_SUPPORTED' AND registered_sign_count IS NOT NULL AND registered_sign_count >= 0) OR (registered_counter_capability = 'NO_USABLE_COUNTER' AND registered_sign_count IS NULL)),
    CHECK ((terminal_operation_outcome_id IS NULL AND terminal_operation_outcome_result IS NULL AND outcome_expected_credential_state_hash IS NULL AND outcome_resulting_credential_state_hash IS NULL) OR (terminal_operation_outcome_id IS NOT NULL AND terminal_operation_outcome_result IS NOT NULL AND outcome_expected_credential_state_hash IS NOT NULL AND outcome_resulting_credential_state_hash IS NOT NULL)),
    CHECK (outcome_expected_credential_state_hash IS NULL OR (length(outcome_expected_credential_state_hash) = 71 AND substr(outcome_expected_credential_state_hash, 1, 7) = 'sha256:' AND substr(outcome_expected_credential_state_hash, 8) NOT GLOB '*[^0-9a-f]*')),
    CHECK (outcome_resulting_credential_state_hash IS NULL OR (length(outcome_resulting_credential_state_hash) = 71 AND substr(outcome_resulting_credential_state_hash, 1, 7) = 'sha256:' AND substr(outcome_resulting_credential_state_hash, 8) NOT GLOB '*[^0-9a-f]*')),
    CHECK ((continuation_challenge_id IS NULL AND continuation_challenge_purpose IS NULL) OR (continuation_challenge_id IS NOT NULL AND continuation_challenge_purpose = 'REGISTRATION_CREATE')),
    CHECK ((terminal_operation_outcome_id IS NOT NULL AND continuation_challenge_id IS NULL) OR (terminal_operation_outcome_id IS NULL AND continuation_challenge_id IS NOT NULL)),
    CHECK ((terminal_operation_outcome_id IS NULL AND terminal_result = 'SUCCEEDED' AND challenge_purpose = 'AUTHORIZATION_ASSERTION' AND operation_type IN ('ADD_CREDENTIAL', 'REPLACE_CREDENTIAL')) OR terminal_operation_outcome_id IS NOT NULL),
    CHECK (terminal_operation_outcome_result IS NULL OR terminal_operation_outcome_result = CASE terminal_result WHEN 'SUCCEEDED' THEN 'SUCCEEDED' WHEN 'EXPIRED' THEN 'EXPIRED' WHEN 'INVALID_SIGNATURE' THEN 'REJECTED' WHEN 'USER_PRESENCE_ABSENT' THEN 'REJECTED' WHEN 'USER_VERIFICATION_ABSENT' THEN 'REJECTED' WHEN 'INVALID_REGISTRATION' THEN 'REJECTED' ELSE 'FAILED_CLOSED' END),
    CHECK (terminal_operation_outcome_result IS NULL OR terminal_operation_outcome_result = 'SUCCEEDED' OR outcome_resulting_credential_state_hash = outcome_expected_credential_state_hash),
    CHECK (terminal_result != 'SUCCEEDED' OR (client_data_type_verified = 1 AND challenge_verified = 1 AND origin_verified = 1 AND cross_origin_false_verified = 1 AND rp_id_hash_verified = 1 AND user_presence_verified = 1 AND user_verification_verified = 1)),
    CHECK (terminal_result != 'USER_PRESENCE_ABSENT' OR user_presence_verified = 0),
    CHECK (terminal_result != 'USER_VERIFICATION_ABSENT' OR user_verification_verified = 0),
    CHECK (terminal_result != 'INVALID_REGISTRATION' OR challenge_purpose = 'REGISTRATION_CREATE'),
    CHECK (terminal_result != 'INVALID_SIGNATURE' OR challenge_purpose = 'AUTHORIZATION_ASSERTION'),
    CHECK ((terminal_result = 'SUCCEEDED' AND challenge_purpose = 'REGISTRATION_CREATE' AND platform_authenticator_verified = 1 AND resident_key_verified = 1 AND public_key_material_verified = 1 AND registered_webauthn_credential_id IS NOT NULL) OR NOT (terminal_result = 'SUCCEEDED' AND challenge_purpose = 'REGISTRATION_CREATE')),
    CHECK ((terminal_result = 'SUCCEEDED' AND challenge_purpose = 'AUTHORIZATION_ASSERTION' AND registered_webauthn_credential_id IS NULL) OR challenge_purpose != 'AUTHORIZATION_ASSERTION' OR terminal_result != 'SUCCEEDED'),
    CHECK ((terminal_result = 'SUCCEEDED' AND challenge_purpose = 'REGISTRATION_CREATE') OR registered_webauthn_credential_id IS NULL),
    CHECK (length(consumption_content_hash) = 71 AND substr(consumption_content_hash, 1, 7) = 'sha256:' AND substr(consumption_content_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (julianday(consumed_at) IS NOT NULL AND substr(consumed_at, -1) = 'Z'),
    FOREIGN KEY (reviewer_credential_operation_challenge_id, reviewer_credential_operation_id, reviewer_principal_id, operation_type, challenge_purpose, challenge_binding_hash)
        REFERENCES reviewer_credential_operation_challenges (reviewer_credential_operation_challenge_id, reviewer_credential_operation_id, reviewer_principal_id, operation_type, challenge_purpose, challenge_binding_hash),
    FOREIGN KEY (registered_webauthn_credential_id, registered_credential_content_hash, reviewer_principal_id, registered_credential_id_fingerprint, registered_public_key_fingerprint, registered_rp_id, registered_counter_capability)
        REFERENCES reviewer_webauthn_credentials (webauthn_credential_id, credential_content_hash, reviewer_principal_id, credential_id_fingerprint, public_key_fingerprint, rp_id, counter_capability)
        DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (terminal_operation_outcome_id, reviewer_credential_operation_id, reviewer_principal_id, terminal_operation_outcome_result, challenge_consumption_id, outcome_expected_credential_state_hash, outcome_resulting_credential_state_hash)
        REFERENCES reviewer_credential_operation_outcomes (credential_operation_outcome_id, reviewer_credential_operation_id, reviewer_principal_id, terminal_result, terminal_consumption_id, expected_credential_state_hash, resulting_credential_state_hash)
        DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (continuation_challenge_id, reviewer_credential_operation_id, reviewer_principal_id, operation_type, continuation_challenge_purpose)
        REFERENCES reviewer_credential_operation_challenges (reviewer_credential_operation_challenge_id, reviewer_credential_operation_id, reviewer_principal_id, operation_type, challenge_purpose)
        DEFERRABLE INITIALLY DEFERRED
)""",
    ),
    (
        "reviewer_credential_operation_authentication_events",
        """CREATE TABLE reviewer_credential_operation_authentication_events (
    credential_operation_authentication_event_id VARCHAR(128) NOT NULL,
    contract_version VARCHAR(64) NOT NULL,
    reviewer_credential_operation_challenge_id VARCHAR(128) NOT NULL,
    challenge_binding_hash VARCHAR(71) NOT NULL,
    challenge_consumption_id VARCHAR(128) NOT NULL,
    challenge_consumption_content_hash VARCHAR(71) NOT NULL,
    challenge_purpose VARCHAR(32) NOT NULL,
    challenge_terminal_result VARCHAR(32) NOT NULL,
    reviewer_credential_operation_id VARCHAR(128) NOT NULL,
    operation_content_hash VARCHAR(71) NOT NULL,
    operation_type VARCHAR(32) NOT NULL,
    expected_credential_state_hash VARCHAR(71) NOT NULL,
    reviewer_principal_id VARCHAR(128) NOT NULL,
    reviewer_role VARCHAR(32) NOT NULL,
    principal_content_hash VARCHAR(71) NOT NULL,
    os_owner_sid_hash VARCHAR(71) NOT NULL,
    authorizing_webauthn_credential_id VARCHAR(512) NOT NULL,
    credential_id_fingerprint VARCHAR(71) NOT NULL,
    public_key_fingerprint VARCHAR(71) NOT NULL,
    authentication_result VARCHAR(16) NOT NULL,
    authentication_policy_version VARCHAR(64) NOT NULL,
    rp_id VARCHAR(255) NOT NULL,
    exact_origin VARCHAR(255) NOT NULL,
    user_presence_verified INTEGER NOT NULL,
    user_verification_verified INTEGER NOT NULL,
    origin_verified INTEGER NOT NULL,
    rp_id_hash_verified INTEGER NOT NULL,
    signature_verified INTEGER NOT NULL,
    counter_capability VARCHAR(32) NOT NULL,
    previous_sign_count INTEGER,
    asserted_sign_count INTEGER,
    counter_verified INTEGER NOT NULL,
    replay_rejected INTEGER NOT NULL,
    safe_result_code VARCHAR(128) NOT NULL,
    authentication_content_hash VARCHAR(71) NOT NULL,
    authenticated_at VARCHAR(35) NOT NULL,
    payload_json TEXT NOT NULL,
    PRIMARY KEY (credential_operation_authentication_event_id),
    UNIQUE (challenge_consumption_id),
    UNIQUE (authentication_content_hash),
    CHECK (contract_version = 'reviewer-credential-operation-authentication/0.1.0'),
    CHECK (length(challenge_binding_hash) = 71 AND substr(challenge_binding_hash, 1, 7) = 'sha256:' AND substr(challenge_binding_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (length(challenge_consumption_content_hash) = 71 AND substr(challenge_consumption_content_hash, 1, 7) = 'sha256:' AND substr(challenge_consumption_content_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (challenge_purpose = 'AUTHORIZATION_ASSERTION'),
    CHECK (challenge_terminal_result IN ('SUCCEEDED', 'EXPIRED', 'BINDING_MISMATCH', 'ORIGIN_RP_MISMATCH', 'USER_PRESENCE_ABSENT', 'USER_VERIFICATION_ABSENT', 'INVALID_SIGNATURE', 'COUNTER_REJECTED', 'REPLAY_REJECTED', 'FAILED_CLOSED')),
    CHECK (length(operation_content_hash) = 71 AND substr(operation_content_hash, 1, 7) = 'sha256:' AND substr(operation_content_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (operation_type IN ('ADD_CREDENTIAL', 'REPLACE_CREDENTIAL', 'REVOKE_CREDENTIAL')),
    CHECK (length(expected_credential_state_hash) = 71 AND substr(expected_credential_state_hash, 1, 7) = 'sha256:' AND substr(expected_credential_state_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (reviewer_role = 'LOCAL_DATA_STEWARD'),
    CHECK (length(principal_content_hash) = 71 AND substr(principal_content_hash, 1, 7) = 'sha256:' AND substr(principal_content_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (length(os_owner_sid_hash) = 71 AND substr(os_owner_sid_hash, 1, 7) = 'sha256:' AND substr(os_owner_sid_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (length(credential_id_fingerprint) = 71 AND substr(credential_id_fingerprint, 1, 7) = 'sha256:' AND substr(credential_id_fingerprint, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (length(public_key_fingerprint) = 71 AND substr(public_key_fingerprint, 1, 7) = 'sha256:' AND substr(public_key_fingerprint, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (authentication_result IN ('VERIFIED', 'REJECTED')),
    CHECK (rp_id = 'localhost'),
    CHECK (exact_origin = 'http://localhost:3000'),
    CHECK (user_presence_verified IN (0, 1) AND user_verification_verified IN (0, 1) AND origin_verified IN (0, 1) AND rp_id_hash_verified IN (0, 1) AND signature_verified IN (0, 1) AND counter_verified IN (0, 1) AND replay_rejected IN (0, 1)),
    CHECK (counter_capability IN ('SIGN_COUNT_SUPPORTED', 'NO_USABLE_COUNTER')),
    CHECK ((counter_capability = 'SIGN_COUNT_SUPPORTED' AND previous_sign_count IS NOT NULL AND asserted_sign_count IS NOT NULL AND previous_sign_count >= 0 AND asserted_sign_count >= 0) OR (counter_capability = 'NO_USABLE_COUNTER' AND previous_sign_count IS NULL AND asserted_sign_count IS NULL)),
    CHECK (authentication_result != 'VERIFIED' OR (challenge_terminal_result = 'SUCCEEDED' AND user_presence_verified = 1 AND user_verification_verified = 1 AND origin_verified = 1 AND rp_id_hash_verified = 1 AND signature_verified = 1 AND counter_verified = 1 AND replay_rejected = 1)),
    CHECK (authentication_result != 'VERIFIED' OR counter_capability = 'NO_USABLE_COUNTER' OR asserted_sign_count > previous_sign_count),
    CHECK (authentication_result != 'REJECTED' OR challenge_terminal_result != 'SUCCEEDED'),
    CHECK (length(authentication_content_hash) = 71 AND substr(authentication_content_hash, 1, 7) = 'sha256:' AND substr(authentication_content_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (julianday(authenticated_at) IS NOT NULL AND substr(authenticated_at, -1) = 'Z'),
    FOREIGN KEY (reviewer_credential_operation_challenge_id, reviewer_credential_operation_id, reviewer_principal_id, operation_type, challenge_purpose, challenge_binding_hash)
        REFERENCES reviewer_credential_operation_challenges (reviewer_credential_operation_challenge_id, reviewer_credential_operation_id, reviewer_principal_id, operation_type, challenge_purpose, challenge_binding_hash),
    FOREIGN KEY (challenge_consumption_id, reviewer_credential_operation_id, reviewer_principal_id, challenge_purpose, challenge_terminal_result, challenge_consumption_content_hash)
        REFERENCES reviewer_credential_operation_challenge_consumptions (challenge_consumption_id, reviewer_credential_operation_id, reviewer_principal_id, challenge_purpose, terminal_result, consumption_content_hash),
    FOREIGN KEY (reviewer_credential_operation_id, operation_content_hash, reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash, operation_type, expected_credential_state_hash)
        REFERENCES reviewer_credential_operations (reviewer_credential_operation_id, operation_content_hash, reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash, operation_type, expected_credential_state_hash),
    FOREIGN KEY (authorizing_webauthn_credential_id, reviewer_principal_id, credential_id_fingerprint, public_key_fingerprint, rp_id, counter_capability)
        REFERENCES reviewer_webauthn_credentials (webauthn_credential_id, reviewer_principal_id, credential_id_fingerprint, public_key_fingerprint, rp_id, counter_capability)
)""",
    ),
    (
        "reviewer_credential_operation_outcomes",
        """CREATE TABLE reviewer_credential_operation_outcomes (
    credential_operation_outcome_id VARCHAR(128) NOT NULL,
    contract_version VARCHAR(64) NOT NULL,
    outcome_content_hash VARCHAR(71) NOT NULL,
    reviewer_credential_operation_id VARCHAR(128) NOT NULL,
    operation_content_hash VARCHAR(71) NOT NULL,
    reviewer_principal_id VARCHAR(128) NOT NULL,
    reviewer_role VARCHAR(32) NOT NULL,
    principal_content_hash VARCHAR(71) NOT NULL,
    os_owner_sid_hash VARCHAR(71) NOT NULL,
    operation_type VARCHAR(32) NOT NULL,
    terminal_result VARCHAR(16) NOT NULL,
    terminal_consumption_id VARCHAR(128) NOT NULL,
    terminal_consumption_content_hash VARCHAR(71) NOT NULL,
    terminal_challenge_purpose VARCHAR(32) NOT NULL,
    terminal_challenge_result VARCHAR(32) NOT NULL,
    authorization_authentication_event_id VARCHAR(128),
    authorization_authentication_content_hash VARCHAR(71),
    authorization_authentication_result VARCHAR(16),
    registration_consumption_id VARCHAR(128),
    registration_consumption_content_hash VARCHAR(71),
    registration_challenge_purpose VARCHAR(32),
    registration_terminal_result VARCHAR(32),
    expected_credential_state_hash VARCHAR(71) NOT NULL,
    resulting_credential_state_hash VARCHAR(71) NOT NULL,
    safe_result_code VARCHAR(128) NOT NULL,
    completed_at VARCHAR(35) NOT NULL,
    payload_json TEXT NOT NULL,
    PRIMARY KEY (credential_operation_outcome_id),
    UNIQUE (outcome_content_hash),
    UNIQUE (reviewer_credential_operation_id),
    CHECK (contract_version = 'reviewer-credential-operation-outcome/0.1.0'),
    CHECK (length(outcome_content_hash) = 71 AND substr(outcome_content_hash, 1, 7) = 'sha256:' AND substr(outcome_content_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (length(operation_content_hash) = 71 AND substr(operation_content_hash, 1, 7) = 'sha256:' AND substr(operation_content_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (reviewer_role = 'LOCAL_DATA_STEWARD'),
    CHECK (length(principal_content_hash) = 71 AND substr(principal_content_hash, 1, 7) = 'sha256:' AND substr(principal_content_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (length(os_owner_sid_hash) = 71 AND substr(os_owner_sid_hash, 1, 7) = 'sha256:' AND substr(os_owner_sid_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (operation_type IN ('FIRST_ENROLLMENT', 'ADD_CREDENTIAL', 'REPLACE_CREDENTIAL', 'REVOKE_CREDENTIAL')),
    CHECK (terminal_result IN ('SUCCEEDED', 'REJECTED', 'EXPIRED', 'FAILED_CLOSED')),
    CHECK (length(terminal_consumption_content_hash) = 71 AND substr(terminal_consumption_content_hash, 1, 7) = 'sha256:' AND substr(terminal_consumption_content_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (terminal_challenge_purpose IN ('REGISTRATION_CREATE', 'AUTHORIZATION_ASSERTION')),
    CHECK (terminal_challenge_result IN ('SUCCEEDED', 'EXPIRED', 'BINDING_MISMATCH', 'ORIGIN_RP_MISMATCH', 'USER_PRESENCE_ABSENT', 'USER_VERIFICATION_ABSENT', 'INVALID_REGISTRATION', 'INVALID_SIGNATURE', 'COUNTER_REJECTED', 'REPLAY_REJECTED', 'FAILED_CLOSED')),
    CHECK ((authorization_authentication_event_id IS NULL AND authorization_authentication_content_hash IS NULL AND authorization_authentication_result IS NULL) OR (authorization_authentication_event_id IS NOT NULL AND authorization_authentication_content_hash IS NOT NULL AND authorization_authentication_result IN ('VERIFIED', 'REJECTED'))),
    CHECK (authorization_authentication_content_hash IS NULL OR (length(authorization_authentication_content_hash) = 71 AND substr(authorization_authentication_content_hash, 1, 7) = 'sha256:' AND substr(authorization_authentication_content_hash, 8) NOT GLOB '*[^0-9a-f]*')),
    CHECK ((registration_consumption_id IS NULL AND registration_consumption_content_hash IS NULL AND registration_challenge_purpose IS NULL AND registration_terminal_result IS NULL) OR (registration_consumption_id IS NOT NULL AND registration_consumption_content_hash IS NOT NULL AND registration_challenge_purpose = 'REGISTRATION_CREATE' AND registration_terminal_result IS NOT NULL)),
    CHECK (registration_consumption_content_hash IS NULL OR (length(registration_consumption_content_hash) = 71 AND substr(registration_consumption_content_hash, 1, 7) = 'sha256:' AND substr(registration_consumption_content_hash, 8) NOT GLOB '*[^0-9a-f]*')),
    CHECK (length(expected_credential_state_hash) = 71 AND substr(expected_credential_state_hash, 1, 7) = 'sha256:' AND substr(expected_credential_state_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (length(resulting_credential_state_hash) = 71 AND substr(resulting_credential_state_hash, 1, 7) = 'sha256:' AND substr(resulting_credential_state_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (terminal_result = CASE terminal_challenge_result WHEN 'SUCCEEDED' THEN 'SUCCEEDED' WHEN 'EXPIRED' THEN 'EXPIRED' WHEN 'INVALID_SIGNATURE' THEN 'REJECTED' WHEN 'USER_PRESENCE_ABSENT' THEN 'REJECTED' WHEN 'USER_VERIFICATION_ABSENT' THEN 'REJECTED' WHEN 'INVALID_REGISTRATION' THEN 'REJECTED' ELSE 'FAILED_CLOSED' END),
    CHECK (terminal_result = 'SUCCEEDED' OR resulting_credential_state_hash = expected_credential_state_hash),
    CHECK (terminal_result != 'SUCCEEDED' OR resulting_credential_state_hash != expected_credential_state_hash),
    CHECK ((terminal_challenge_purpose = 'REGISTRATION_CREATE' AND registration_consumption_id = terminal_consumption_id AND registration_consumption_content_hash = terminal_consumption_content_hash AND registration_terminal_result = terminal_challenge_result) OR (terminal_challenge_purpose = 'AUTHORIZATION_ASSERTION' AND registration_consumption_id IS NULL)),
    CHECK (operation_type != 'FIRST_ENROLLMENT' OR authorization_authentication_event_id IS NULL),
    CHECK (terminal_result != 'SUCCEEDED' OR operation_type = 'FIRST_ENROLLMENT' OR authorization_authentication_result = 'VERIFIED'),
    CHECK (terminal_challenge_purpose != 'REGISTRATION_CREATE' OR operation_type = 'FIRST_ENROLLMENT' OR authorization_authentication_result = 'VERIFIED'),
    CHECK (julianday(completed_at) IS NOT NULL AND substr(completed_at, -1) = 'Z'),
    FOREIGN KEY (reviewer_credential_operation_id, operation_content_hash, reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash, operation_type, expected_credential_state_hash)
        REFERENCES reviewer_credential_operations (reviewer_credential_operation_id, operation_content_hash, reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash, operation_type, expected_credential_state_hash)
        DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (terminal_consumption_id, reviewer_credential_operation_id, reviewer_principal_id, terminal_challenge_purpose, terminal_challenge_result, terminal_consumption_content_hash)
        REFERENCES reviewer_credential_operation_challenge_consumptions (challenge_consumption_id, reviewer_credential_operation_id, reviewer_principal_id, challenge_purpose, terminal_result, consumption_content_hash)
        DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (authorization_authentication_event_id, authorization_authentication_content_hash, reviewer_credential_operation_id, reviewer_principal_id, authorization_authentication_result)
        REFERENCES reviewer_credential_operation_authentication_events (credential_operation_authentication_event_id, authentication_content_hash, reviewer_credential_operation_id, reviewer_principal_id, authentication_result)
        DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (registration_consumption_id, reviewer_credential_operation_id, reviewer_principal_id, registration_challenge_purpose, registration_terminal_result, registration_consumption_content_hash)
        REFERENCES reviewer_credential_operation_challenge_consumptions (challenge_consumption_id, reviewer_credential_operation_id, reviewer_principal_id, challenge_purpose, terminal_result, consumption_content_hash)
        DEFERRABLE INITIALLY DEFERRED
)""",
    ),
    (
        "reviewer_webauthn_credential_event_authorizations",
        """CREATE TABLE reviewer_webauthn_credential_event_authorizations (
    credential_event_id VARCHAR(128) NOT NULL,
    contract_version VARCHAR(64) NOT NULL,
    credential_event_content_hash VARCHAR(71) NOT NULL,
    webauthn_credential_id VARCHAR(512) NOT NULL,
    webauthn_credential_content_hash VARCHAR(71) NOT NULL,
    reviewer_principal_id VARCHAR(128) NOT NULL,
    reviewer_role VARCHAR(32) NOT NULL,
    principal_content_hash VARCHAR(71) NOT NULL,
    os_owner_sid_hash VARCHAR(71) NOT NULL,
    event_type VARCHAR(16) NOT NULL,
    reviewer_credential_operation_id VARCHAR(128) NOT NULL,
    operation_content_hash VARCHAR(71) NOT NULL,
    operation_type VARCHAR(32) NOT NULL,
    authorization_kind VARCHAR(32) NOT NULL,
    registration_consumption_id VARCHAR(128),
    registration_consumption_content_hash VARCHAR(71),
    registration_challenge_purpose VARCHAR(32),
    registration_terminal_result VARCHAR(32),
    credential_operation_authentication_event_id VARCHAR(128),
    credential_operation_authentication_content_hash VARCHAR(71),
    credential_operation_authentication_result VARCHAR(16),
    credential_operation_outcome_id VARCHAR(128) NOT NULL,
    credential_operation_outcome_content_hash VARCHAR(71) NOT NULL,
    credential_operation_outcome_result VARCHAR(16) NOT NULL,
    expected_credential_state_hash VARCHAR(71) NOT NULL,
    resulting_credential_state_hash VARCHAR(71) NOT NULL,
    authorization_content_hash VARCHAR(71) NOT NULL,
    recorded_at VARCHAR(35) NOT NULL,
    payload_json TEXT NOT NULL,
    PRIMARY KEY (credential_event_id),
    UNIQUE (authorization_content_hash),
    CHECK (contract_version = 'reviewer-credential-event-authorization/0.1.0'),
    CHECK (length(credential_event_content_hash) = 71 AND substr(credential_event_content_hash, 1, 7) = 'sha256:' AND substr(credential_event_content_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (length(webauthn_credential_content_hash) = 71 AND substr(webauthn_credential_content_hash, 1, 7) = 'sha256:' AND substr(webauthn_credential_content_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (reviewer_role = 'LOCAL_DATA_STEWARD'),
    CHECK (length(principal_content_hash) = 71 AND substr(principal_content_hash, 1, 7) = 'sha256:' AND substr(principal_content_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (length(os_owner_sid_hash) = 71 AND substr(os_owner_sid_hash, 1, 7) = 'sha256:' AND substr(os_owner_sid_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (event_type IN ('REGISTERED', 'REVOKED', 'SUPERSEDED')),
    CHECK (length(operation_content_hash) = 71 AND substr(operation_content_hash, 1, 7) = 'sha256:' AND substr(operation_content_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (operation_type IN ('FIRST_ENROLLMENT', 'ADD_CREDENTIAL', 'REPLACE_CREDENTIAL', 'REVOKE_CREDENTIAL')),
    CHECK (authorization_kind IN ('BOOTSTRAP_REGISTRATION', 'AUTHORIZED_REGISTRATION', 'AUTHORIZED_SUPERSESSION', 'AUTHORIZED_REVOCATION')),
    CHECK ((operation_type = 'FIRST_ENROLLMENT' AND event_type = 'REGISTERED' AND authorization_kind = 'BOOTSTRAP_REGISTRATION') OR (operation_type = 'ADD_CREDENTIAL' AND event_type = 'REGISTERED' AND authorization_kind = 'AUTHORIZED_REGISTRATION') OR (operation_type = 'REPLACE_CREDENTIAL' AND event_type = 'REGISTERED' AND authorization_kind = 'AUTHORIZED_REGISTRATION') OR (operation_type = 'REPLACE_CREDENTIAL' AND event_type = 'SUPERSEDED' AND authorization_kind = 'AUTHORIZED_SUPERSESSION') OR (operation_type = 'REVOKE_CREDENTIAL' AND event_type = 'REVOKED' AND authorization_kind = 'AUTHORIZED_REVOCATION')),
    CHECK ((registration_consumption_id IS NULL AND registration_consumption_content_hash IS NULL AND registration_challenge_purpose IS NULL AND registration_terminal_result IS NULL) OR (registration_consumption_id IS NOT NULL AND registration_consumption_content_hash IS NOT NULL AND registration_challenge_purpose = 'REGISTRATION_CREATE' AND registration_terminal_result = 'SUCCEEDED')),
    CHECK (registration_consumption_content_hash IS NULL OR (length(registration_consumption_content_hash) = 71 AND substr(registration_consumption_content_hash, 1, 7) = 'sha256:' AND substr(registration_consumption_content_hash, 8) NOT GLOB '*[^0-9a-f]*')),
    CHECK ((credential_operation_authentication_event_id IS NULL AND credential_operation_authentication_content_hash IS NULL AND credential_operation_authentication_result IS NULL) OR (credential_operation_authentication_event_id IS NOT NULL AND credential_operation_authentication_content_hash IS NOT NULL AND credential_operation_authentication_result = 'VERIFIED')),
    CHECK (credential_operation_authentication_content_hash IS NULL OR (length(credential_operation_authentication_content_hash) = 71 AND substr(credential_operation_authentication_content_hash, 1, 7) = 'sha256:' AND substr(credential_operation_authentication_content_hash, 8) NOT GLOB '*[^0-9a-f]*')),
    CHECK ((authorization_kind = 'BOOTSTRAP_REGISTRATION' AND registration_consumption_id IS NOT NULL AND credential_operation_authentication_event_id IS NULL) OR (authorization_kind = 'AUTHORIZED_REGISTRATION' AND registration_consumption_id IS NOT NULL AND credential_operation_authentication_event_id IS NOT NULL) OR (authorization_kind IN ('AUTHORIZED_SUPERSESSION', 'AUTHORIZED_REVOCATION') AND registration_consumption_id IS NULL AND credential_operation_authentication_event_id IS NOT NULL)),
    CHECK (length(credential_operation_outcome_content_hash) = 71 AND substr(credential_operation_outcome_content_hash, 1, 7) = 'sha256:' AND substr(credential_operation_outcome_content_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (credential_operation_outcome_result = 'SUCCEEDED'),
    CHECK (length(expected_credential_state_hash) = 71 AND substr(expected_credential_state_hash, 1, 7) = 'sha256:' AND substr(expected_credential_state_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (length(resulting_credential_state_hash) = 71 AND substr(resulting_credential_state_hash, 1, 7) = 'sha256:' AND substr(resulting_credential_state_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (length(authorization_content_hash) = 71 AND substr(authorization_content_hash, 1, 7) = 'sha256:' AND substr(authorization_content_hash, 8) NOT GLOB '*[^0-9a-f]*'),
    CHECK (julianday(recorded_at) IS NOT NULL AND substr(recorded_at, -1) = 'Z'),
    FOREIGN KEY (credential_event_id, credential_event_content_hash, webauthn_credential_id, reviewer_principal_id, event_type)
        REFERENCES reviewer_webauthn_credential_events (credential_event_id, credential_event_content_hash, webauthn_credential_id, reviewer_principal_id, event_type)
        DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (webauthn_credential_id, webauthn_credential_content_hash)
        REFERENCES reviewer_webauthn_credentials (webauthn_credential_id, credential_content_hash)
        DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (reviewer_credential_operation_id, operation_content_hash, reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash, operation_type, expected_credential_state_hash)
        REFERENCES reviewer_credential_operations (reviewer_credential_operation_id, operation_content_hash, reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash, operation_type, expected_credential_state_hash)
        DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (registration_consumption_id, reviewer_credential_operation_id, reviewer_principal_id, registration_challenge_purpose, registration_terminal_result, webauthn_credential_id, webauthn_credential_content_hash, registration_consumption_content_hash)
        REFERENCES reviewer_credential_operation_challenge_consumptions (challenge_consumption_id, reviewer_credential_operation_id, reviewer_principal_id, challenge_purpose, terminal_result, registered_webauthn_credential_id, registered_credential_content_hash, consumption_content_hash)
        DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (credential_operation_authentication_event_id, credential_operation_authentication_content_hash, reviewer_credential_operation_id, reviewer_principal_id, credential_operation_authentication_result)
        REFERENCES reviewer_credential_operation_authentication_events (credential_operation_authentication_event_id, authentication_content_hash, reviewer_credential_operation_id, reviewer_principal_id, authentication_result)
        DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (credential_operation_outcome_id, credential_operation_outcome_content_hash, reviewer_credential_operation_id, operation_content_hash, reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash, credential_operation_outcome_result, expected_credential_state_hash, resulting_credential_state_hash)
        REFERENCES reviewer_credential_operation_outcomes (credential_operation_outcome_id, outcome_content_hash, reviewer_credential_operation_id, operation_content_hash, reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash, terminal_result, expected_credential_state_hash, resulting_credential_state_hash)
        DEFERRABLE INITIALLY DEFERRED
)""",
    ),
)

_OLD_TABLE_INDEX_DDL: tuple[tuple[str, str], ...] = (
    (
        "uq_reviewer_principals_active_local_steward",
        "CREATE UNIQUE INDEX uq_reviewer_principals_active_local_steward ON reviewer_principals (reviewer_role) WHERE principal_state = 'ACTIVE'",
    ),
    (
        "uq_reviewer_principals_exact_owner_binding",
        "CREATE UNIQUE INDEX uq_reviewer_principals_exact_owner_binding ON reviewer_principals (reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash)",
    ),
    (
        "uq_reviewer_credentials_exact_target",
        "CREATE UNIQUE INDEX uq_reviewer_credentials_exact_target ON reviewer_webauthn_credentials (webauthn_credential_id, reviewer_principal_id, credential_id_fingerprint)",
    ),
    (
        "uq_reviewer_credentials_exact_content",
        "CREATE UNIQUE INDEX uq_reviewer_credentials_exact_content ON reviewer_webauthn_credentials (webauthn_credential_id, credential_content_hash)",
    ),
    (
        "uq_reviewer_credentials_exact_registration",
        "CREATE UNIQUE INDEX uq_reviewer_credentials_exact_registration ON reviewer_webauthn_credentials (webauthn_credential_id, credential_content_hash, reviewer_principal_id, credential_id_fingerprint, public_key_fingerprint, rp_id, counter_capability)",
    ),
    (
        "uq_reviewer_credential_events_exact_authorization",
        "CREATE UNIQUE INDEX uq_reviewer_credential_events_exact_authorization ON reviewer_webauthn_credential_events (credential_event_id, credential_event_content_hash, webauthn_credential_id, reviewer_principal_id, event_type)",
    ),
    (
        "uq_reviewer_credential_events_root",
        "CREATE UNIQUE INDEX uq_reviewer_credential_events_root ON reviewer_webauthn_credential_events (webauthn_credential_id) WHERE supersedes_credential_event_id IS NULL",
    ),
    (
        "ix_reviewer_authentication_counter_chain",
        "CREATE INDEX ix_reviewer_authentication_counter_chain ON reviewer_authentication_events (webauthn_credential_id, authentication_result, previous_sign_count, asserted_sign_count)",
    ),
)

_NEW_TABLE_INDEX_DDL: tuple[tuple[str, str], ...] = (
    (
        "uq_reviewer_credential_operations_exact_binding",
        "CREATE UNIQUE INDEX uq_reviewer_credential_operations_exact_binding ON reviewer_credential_operations (reviewer_credential_operation_id, operation_content_hash, reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash, operation_type, expected_credential_state_hash)",
    ),
    (
        "uq_reviewer_credential_operations_exact_subject",
        "CREATE UNIQUE INDEX uq_reviewer_credential_operations_exact_subject ON reviewer_credential_operations (reviewer_credential_operation_id, reviewer_principal_id)",
    ),
    (
        "uq_reviewer_credential_operations_root",
        "CREATE UNIQUE INDEX uq_reviewer_credential_operations_root ON reviewer_credential_operations (reviewer_principal_id) WHERE predecessor_operation_id IS NULL",
    ),
    (
        "uq_reviewer_credential_operations_successor",
        "CREATE UNIQUE INDEX uq_reviewer_credential_operations_successor ON reviewer_credential_operations (predecessor_operation_id) WHERE predecessor_operation_id IS NOT NULL",
    ),
    (
        "uq_reviewer_credential_operation_challenges_exact_operation_step",
        "CREATE UNIQUE INDEX uq_reviewer_credential_operation_challenges_exact_operation_step ON reviewer_credential_operation_challenges (reviewer_credential_operation_challenge_id, reviewer_credential_operation_id, reviewer_principal_id, operation_type, challenge_purpose)",
    ),
    (
        "uq_reviewer_credential_operation_challenges_exact_binding",
        "CREATE UNIQUE INDEX uq_reviewer_credential_operation_challenges_exact_binding ON reviewer_credential_operation_challenges (reviewer_credential_operation_challenge_id, reviewer_credential_operation_id, reviewer_principal_id, operation_type, challenge_purpose, challenge_binding_hash)",
    ),
    (
        "uq_reviewer_credential_operation_challenge_step",
        "CREATE UNIQUE INDEX uq_reviewer_credential_operation_challenge_step ON reviewer_credential_operation_challenges (reviewer_credential_operation_id, challenge_purpose)",
    ),
    (
        "ix_reviewer_credential_operation_challenge_expiry",
        "CREATE INDEX ix_reviewer_credential_operation_challenge_expiry ON reviewer_credential_operation_challenges (reviewer_principal_id, expires_at)",
    ),
    (
        "uq_reviewer_credential_operation_consumptions_exact_terminal",
        "CREATE UNIQUE INDEX uq_reviewer_credential_operation_consumptions_exact_terminal ON reviewer_credential_operation_challenge_consumptions (challenge_consumption_id, reviewer_credential_operation_id, reviewer_principal_id, challenge_purpose, terminal_result, consumption_content_hash)",
    ),
    (
        "uq_reviewer_credential_operation_consumptions_exact_registration",
        "CREATE UNIQUE INDEX uq_reviewer_credential_operation_consumptions_exact_registration ON reviewer_credential_operation_challenge_consumptions (challenge_consumption_id, reviewer_credential_operation_id, reviewer_principal_id, challenge_purpose, terminal_result, registered_webauthn_credential_id, registered_credential_content_hash, consumption_content_hash)",
    ),
    (
        "uq_reviewer_credential_operation_authentication_exact_result",
        "CREATE UNIQUE INDEX uq_reviewer_credential_operation_authentication_exact_result ON reviewer_credential_operation_authentication_events (credential_operation_authentication_event_id, authentication_content_hash, reviewer_credential_operation_id, reviewer_principal_id, authentication_result)",
    ),
    (
        "uq_reviewer_credential_operation_outcomes_exact_terminal",
        "CREATE UNIQUE INDEX uq_reviewer_credential_operation_outcomes_exact_terminal ON reviewer_credential_operation_outcomes (credential_operation_outcome_id, reviewer_credential_operation_id, reviewer_principal_id, terminal_result, terminal_consumption_id, expected_credential_state_hash, resulting_credential_state_hash)",
    ),
    (
        "uq_reviewer_credential_operation_outcomes_exact_success",
        "CREATE UNIQUE INDEX uq_reviewer_credential_operation_outcomes_exact_success ON reviewer_credential_operation_outcomes (credential_operation_outcome_id, outcome_content_hash, reviewer_credential_operation_id, operation_content_hash, reviewer_principal_id, reviewer_role, principal_content_hash, os_owner_sid_hash, terminal_result, expected_credential_state_hash, resulting_credential_state_hash)",
    ),
    (
        "uq_reviewer_credential_event_authorization_step",
        "CREATE UNIQUE INDEX uq_reviewer_credential_event_authorization_step ON reviewer_webauthn_credential_event_authorizations (reviewer_credential_operation_id, event_type)",
    ),
    (
        "ix_reviewer_credential_operation_counter_chain",
        "CREATE INDEX ix_reviewer_credential_operation_counter_chain ON reviewer_credential_operation_authentication_events (authorizing_webauthn_credential_id, authentication_result, previous_sign_count, asserted_sign_count)",
    ),
)

_NEW_TABLE_NAMES = tuple(name for name, _ddl in _NEW_TABLE_DDL)
_INDEX_DDL = _OLD_TABLE_INDEX_DDL + _NEW_TABLE_INDEX_DDL
_INDEX_NAMES = tuple(name for name, _ddl in _INDEX_DDL)


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

_INSERT_GUARD_DDL: tuple[tuple[str, str], ...] = (
    (
        "trg_reviewer_credential_operations_insert_guard",
        """CREATE TRIGGER trg_reviewer_credential_operations_insert_guard
BEFORE INSERT ON reviewer_credential_operations
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1 FROM reviewer_principals p
        WHERE p.reviewer_principal_id = NEW.reviewer_principal_id
          AND p.reviewer_role = NEW.reviewer_role
          AND p.principal_content_hash = NEW.principal_content_hash
          AND p.os_owner_sid_hash = NEW.os_owner_sid_hash
          AND p.principal_state = 'ACTIVE'
    ) THEN RAISE(ABORT, 'credential operation requires exact active local steward') END;
    SELECT CASE WHEN NEW.predecessor_operation_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM reviewer_credential_operation_outcomes o
        WHERE o.reviewer_credential_operation_id = NEW.predecessor_operation_id
          AND o.reviewer_principal_id = NEW.reviewer_principal_id
          AND o.resulting_credential_state_hash = NEW.expected_credential_state_hash
    ) THEN RAISE(ABORT, 'credential operation predecessor must be exact terminal state leaf') END;
    SELECT CASE WHEN NEW.predecessor_operation_id IS NOT NULL AND EXISTS (
        SELECT 1 FROM reviewer_credential_operations child
        WHERE child.predecessor_operation_id = NEW.predecessor_operation_id
    ) THEN RAISE(ABORT, 'credential operation predecessor already has successor') END;
    SELECT CASE WHEN NEW.operation_type = 'FIRST_ENROLLMENT' AND EXISTS (
        SELECT 1 FROM reviewer_webauthn_credential_event_authorizations a
        WHERE a.reviewer_principal_id = NEW.reviewer_principal_id
          AND a.event_type = 'REGISTERED'
          AND a.credential_operation_outcome_result = 'SUCCEEDED'
    ) THEN RAISE(ABORT, 'first enrollment permanently closed after successful registration') END;
    SELECT CASE WHEN NEW.operation_type != 'FIRST_ENROLLMENT' AND NOT EXISTS (
        SELECT 1
        FROM reviewer_webauthn_credentials c
        JOIN reviewer_webauthn_credential_events root
          ON root.webauthn_credential_id = c.webauthn_credential_id
         AND root.reviewer_principal_id = c.reviewer_principal_id
         AND root.event_type = 'REGISTERED'
         AND root.supersedes_credential_event_id IS NULL
        JOIN reviewer_webauthn_credential_event_authorizations a
          ON a.credential_event_id = root.credential_event_id
        WHERE c.reviewer_principal_id = NEW.reviewer_principal_id
          AND NOT EXISTS (
              SELECT 1 FROM reviewer_webauthn_credential_events successor
              WHERE successor.supersedes_credential_event_id = root.credential_event_id
          )
    ) THEN RAISE(ABORT, 'credential operation requires a currently active credential') END;
    SELECT CASE WHEN NEW.operation_type IN ('REPLACE_CREDENTIAL', 'REVOKE_CREDENTIAL') AND NOT EXISTS (
        SELECT 1
        FROM reviewer_webauthn_credentials c
        JOIN reviewer_webauthn_credential_events root
          ON root.webauthn_credential_id = c.webauthn_credential_id
         AND root.reviewer_principal_id = c.reviewer_principal_id
         AND root.event_type = 'REGISTERED'
         AND root.supersedes_credential_event_id IS NULL
        JOIN reviewer_webauthn_credential_event_authorizations a
          ON a.credential_event_id = root.credential_event_id
        WHERE c.webauthn_credential_id = NEW.target_webauthn_credential_id
          AND c.reviewer_principal_id = NEW.reviewer_principal_id
          AND c.credential_id_fingerprint = NEW.target_credential_id_fingerprint
          AND NOT EXISTS (
              SELECT 1 FROM reviewer_webauthn_credential_events successor
              WHERE successor.supersedes_credential_event_id = root.credential_event_id
          )
    ) THEN RAISE(ABORT, 'replace or revoke target must be currently active') END;
END""",
    ),
    (
        "trg_reviewer_credential_operation_challenges_insert_guard",
        """CREATE TRIGGER trg_reviewer_credential_operation_challenges_insert_guard
BEFORE INSERT ON reviewer_credential_operation_challenges
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1 FROM reviewer_credential_operations o
        WHERE o.reviewer_credential_operation_id = NEW.reviewer_credential_operation_id
          AND o.operation_content_hash = NEW.operation_content_hash
          AND o.reviewer_principal_id = NEW.reviewer_principal_id
          AND o.reviewer_role = NEW.reviewer_role
          AND o.principal_content_hash = NEW.principal_content_hash
          AND o.os_owner_sid_hash = NEW.os_owner_sid_hash
          AND o.operation_type = NEW.operation_type
          AND o.expected_credential_state_hash = NEW.expected_credential_state_hash
          AND o.target_webauthn_credential_id IS NEW.target_webauthn_credential_id
          AND o.target_credential_id_fingerprint IS NEW.target_credential_id_fingerprint
    ) THEN RAISE(ABORT, 'operation challenge exact operation copy mismatch') END;
    SELECT CASE WHEN EXISTS (
        SELECT 1 FROM reviewer_credential_operation_outcomes outcome
        WHERE outcome.reviewer_credential_operation_id = NEW.reviewer_credential_operation_id
    ) THEN RAISE(ABORT, 'terminal operation cannot issue another challenge') END;
    SELECT CASE WHEN NEW.challenge_purpose = 'AUTHORIZATION_ASSERTION' AND NOT EXISTS (
        SELECT 1 FROM reviewer_credential_operations o
        WHERE o.reviewer_credential_operation_id = NEW.reviewer_credential_operation_id
          AND o.initial_challenge_id = NEW.reviewer_credential_operation_challenge_id
          AND o.initial_challenge_purpose = NEW.challenge_purpose
    ) THEN RAISE(ABORT, 'authorization assertion must be exact initial challenge') END;
    SELECT CASE WHEN NEW.operation_type = 'FIRST_ENROLLMENT' AND NOT EXISTS (
        SELECT 1 FROM reviewer_credential_operations o
        WHERE o.reviewer_credential_operation_id = NEW.reviewer_credential_operation_id
          AND o.initial_challenge_id = NEW.reviewer_credential_operation_challenge_id
          AND o.initial_challenge_purpose = NEW.challenge_purpose
    ) THEN RAISE(ABORT, 'first enrollment registration must be exact initial challenge') END;
    SELECT CASE WHEN NEW.challenge_purpose = 'REGISTRATION_CREATE'
          AND NEW.operation_type IN ('ADD_CREDENTIAL', 'REPLACE_CREDENTIAL')
          AND NOT EXISTS (
              SELECT 1
              FROM reviewer_credential_operation_authentication_events auth
              JOIN reviewer_credential_operation_challenge_consumptions consumption
                ON consumption.challenge_consumption_id = auth.challenge_consumption_id
              WHERE auth.credential_operation_authentication_event_id = NEW.prerequisite_authentication_event_id
                AND auth.authentication_content_hash = NEW.prerequisite_authentication_content_hash
                AND auth.authentication_result = 'VERIFIED'
                AND auth.reviewer_credential_operation_id = NEW.reviewer_credential_operation_id
                AND auth.reviewer_principal_id = NEW.reviewer_principal_id
                AND consumption.continuation_challenge_id = NEW.reviewer_credential_operation_challenge_id
                AND consumption.continuation_challenge_purpose = NEW.challenge_purpose
          ) THEN RAISE(ABORT, 'registration continuation requires exact verified operation authentication') END;
END""",
    ),
    (
        "trg_reviewer_credential_operation_consumptions_insert_guard",
        """CREATE TRIGGER trg_reviewer_credential_operation_consumptions_insert_guard
BEFORE INSERT ON reviewer_credential_operation_challenge_consumptions
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1 FROM reviewer_credential_operation_challenges c
        WHERE c.reviewer_credential_operation_challenge_id = NEW.reviewer_credential_operation_challenge_id
          AND c.reviewer_credential_operation_id = NEW.reviewer_credential_operation_id
          AND c.reviewer_principal_id = NEW.reviewer_principal_id
          AND c.operation_type = NEW.operation_type
          AND c.challenge_purpose = NEW.challenge_purpose
          AND c.challenge_binding_hash = NEW.challenge_binding_hash
    ) THEN RAISE(ABORT, 'challenge consumption exact challenge mismatch') END;
    SELECT CASE WHEN EXISTS (
        SELECT 1 FROM reviewer_credential_operation_challenge_consumptions old
        WHERE old.reviewer_credential_operation_challenge_id = NEW.reviewer_credential_operation_challenge_id
    ) THEN RAISE(ABORT, 'operation challenge already consumed') END;
    SELECT CASE WHEN EXISTS (
        SELECT 1 FROM reviewer_credential_operation_challenges c
        WHERE c.reviewer_credential_operation_challenge_id = NEW.reviewer_credential_operation_challenge_id
          AND ((julianday(NEW.consumed_at) >= julianday(c.expires_at) AND NEW.terminal_result != 'EXPIRED')
            OR (julianday(NEW.consumed_at) < julianday(c.expires_at) AND NEW.terminal_result = 'EXPIRED'))
    ) THEN RAISE(ABORT, 'challenge expiry instant/result mismatch') END;
    SELECT CASE WHEN NEW.terminal_operation_outcome_id IS NULL
          AND NOT (NEW.terminal_result = 'SUCCEEDED' AND NEW.challenge_purpose = 'AUTHORIZATION_ASSERTION' AND NEW.operation_type IN ('ADD_CREDENTIAL', 'REPLACE_CREDENTIAL'))
        THEN RAISE(ABORT, 'only successful add or replace assertion may continue') END;
    SELECT CASE WHEN NEW.terminal_operation_outcome_id IS NOT NULL
          AND NEW.terminal_operation_outcome_result != CASE NEW.terminal_result
              WHEN 'SUCCEEDED' THEN 'SUCCEEDED'
              WHEN 'EXPIRED' THEN 'EXPIRED'
              WHEN 'INVALID_SIGNATURE' THEN 'REJECTED'
              WHEN 'USER_PRESENCE_ABSENT' THEN 'REJECTED'
              WHEN 'USER_VERIFICATION_ABSENT' THEN 'REJECTED'
              WHEN 'INVALID_REGISTRATION' THEN 'REJECTED'
              ELSE 'FAILED_CLOSED' END
        THEN RAISE(ABORT, 'challenge result has invalid operation outcome mapping') END;
END""",
    ),
    (
        "trg_reviewer_webauthn_credentials_requires_registration_proof",
        """CREATE TRIGGER trg_reviewer_webauthn_credentials_requires_registration_proof
BEFORE INSERT ON reviewer_webauthn_credentials
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1
        FROM reviewer_credential_operation_challenge_consumptions consumption
        JOIN reviewer_webauthn_credential_event_authorizations authorization
          ON authorization.registration_consumption_id = consumption.challenge_consumption_id
         AND authorization.registration_consumption_content_hash = consumption.consumption_content_hash
         AND authorization.reviewer_credential_operation_id = consumption.reviewer_credential_operation_id
         AND authorization.reviewer_principal_id = consumption.reviewer_principal_id
        JOIN reviewer_principals principal
          ON principal.reviewer_principal_id = NEW.reviewer_principal_id
         AND principal.reviewer_role = NEW.reviewer_role
         AND principal.principal_content_hash = NEW.principal_content_hash
        WHERE consumption.terminal_result = 'SUCCEEDED'
          AND consumption.challenge_purpose = 'REGISTRATION_CREATE'
          AND consumption.registered_webauthn_credential_id = NEW.webauthn_credential_id
          AND consumption.registered_credential_content_hash = NEW.credential_content_hash
          AND consumption.reviewer_principal_id = NEW.reviewer_principal_id
          AND consumption.registered_credential_id_fingerprint = NEW.credential_id_fingerprint
          AND consumption.registered_public_key_fingerprint = NEW.public_key_fingerprint
          AND consumption.registered_rp_id = NEW.rp_id
          AND consumption.registered_counter_capability = NEW.counter_capability
          AND consumption.registered_sign_count IS NEW.registration_sign_count
          AND authorization.webauthn_credential_id = NEW.webauthn_credential_id
          AND authorization.webauthn_credential_content_hash = NEW.credential_content_hash
          AND authorization.event_type = 'REGISTERED'
          AND authorization.authorization_kind IN ('BOOTSTRAP_REGISTRATION', 'AUTHORIZED_REGISTRATION')
          AND authorization.reviewer_role = NEW.reviewer_role
          AND authorization.principal_content_hash = NEW.principal_content_hash
          AND authorization.os_owner_sid_hash = principal.os_owner_sid_hash
    ) THEN RAISE(ABORT, 'public credential requires exact successful registration proof') END;
END""",
    ),
    (
        "trg_reviewer_webauthn_credential_events_requires_authorization",
        """CREATE TRIGGER trg_reviewer_webauthn_credential_events_requires_authorization
BEFORE INSERT ON reviewer_webauthn_credential_events
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1
        FROM reviewer_webauthn_credential_event_authorizations authorization
        JOIN reviewer_webauthn_credentials credential
          ON credential.webauthn_credential_id = authorization.webauthn_credential_id
         AND credential.credential_content_hash = authorization.webauthn_credential_content_hash
        WHERE authorization.credential_event_id = NEW.credential_event_id
          AND authorization.credential_event_content_hash = NEW.credential_event_content_hash
          AND authorization.webauthn_credential_id = NEW.webauthn_credential_id
          AND authorization.reviewer_principal_id = NEW.reviewer_principal_id
          AND authorization.event_type = NEW.event_type
          AND credential.reviewer_principal_id = NEW.reviewer_principal_id
    ) THEN RAISE(ABORT, 'credential lifecycle event requires exact authorization companion') END;
END""",
    ),
    (
        "trg_reviewer_webauthn_credential_events_chain_guard",
        """CREATE TRIGGER trg_reviewer_webauthn_credential_events_chain_guard
BEFORE INSERT ON reviewer_webauthn_credential_events
BEGIN
    SELECT CASE WHEN NEW.event_type = 'REGISTERED' AND NEW.supersedes_credential_event_id IS NOT NULL
        THEN RAISE(ABORT, 'registered lifecycle event must be root') END;
    SELECT CASE WHEN NEW.event_type IN ('REVOKED', 'SUPERSEDED') AND NEW.supersedes_credential_event_id IS NULL
        THEN RAISE(ABORT, 'terminal lifecycle event requires predecessor') END;
    SELECT CASE WHEN NEW.event_type IN ('REVOKED', 'SUPERSEDED') AND NOT EXISTS (
        SELECT 1 FROM reviewer_webauthn_credential_events predecessor
        WHERE predecessor.credential_event_id = NEW.supersedes_credential_event_id
          AND predecessor.webauthn_credential_id = NEW.webauthn_credential_id
          AND predecessor.reviewer_principal_id = NEW.reviewer_principal_id
          AND predecessor.event_type = 'REGISTERED'
          AND predecessor.supersedes_credential_event_id IS NULL
          AND NOT EXISTS (
              SELECT 1 FROM reviewer_webauthn_credential_events child
              WHERE child.supersedes_credential_event_id = predecessor.credential_event_id
          )
    ) THEN RAISE(ABORT, 'credential lifecycle successor must extend same active root') END;
END""",
    ),
    (
        "trg_reviewer_credential_operation_authentication_active_guard",
        """CREATE TRIGGER trg_reviewer_credential_operation_authentication_active_guard
BEFORE INSERT ON reviewer_credential_operation_authentication_events
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1
        FROM reviewer_webauthn_credentials credential
        JOIN reviewer_webauthn_credential_events root
          ON root.webauthn_credential_id = credential.webauthn_credential_id
         AND root.reviewer_principal_id = credential.reviewer_principal_id
         AND root.event_type = 'REGISTERED'
         AND root.supersedes_credential_event_id IS NULL
        JOIN reviewer_webauthn_credential_event_authorizations authorization
          ON authorization.credential_event_id = root.credential_event_id
        WHERE credential.webauthn_credential_id = NEW.authorizing_webauthn_credential_id
          AND credential.reviewer_principal_id = NEW.reviewer_principal_id
          AND credential.credential_id_fingerprint = NEW.credential_id_fingerprint
          AND credential.public_key_fingerprint = NEW.public_key_fingerprint
          AND NOT EXISTS (
              SELECT 1 FROM reviewer_webauthn_credential_events successor
              WHERE successor.supersedes_credential_event_id = root.credential_event_id
          )
    ) THEN RAISE(ABORT, 'credential operation authentication requires currently active credential') END;
    SELECT CASE WHEN NEW.authentication_result = 'VERIFIED'
          AND NEW.operation_type IN ('ADD_CREDENTIAL', 'REPLACE_CREDENTIAL')
          AND NOT EXISTS (
              SELECT 1 FROM reviewer_credential_operation_challenge_consumptions consumption
              WHERE consumption.challenge_consumption_id = NEW.challenge_consumption_id
                AND consumption.continuation_challenge_id IS NOT NULL
                AND consumption.continuation_challenge_purpose = 'REGISTRATION_CREATE'
          ) THEN RAISE(ABORT, 'verified add or replace assertion requires exact continuation') END;
    SELECT CASE WHEN (NEW.authentication_result = 'REJECTED' OR NEW.operation_type = 'REVOKE_CREDENTIAL')
          AND NOT EXISTS (
              SELECT 1 FROM reviewer_credential_operation_challenge_consumptions consumption
              WHERE consumption.challenge_consumption_id = NEW.challenge_consumption_id
                AND consumption.terminal_operation_outcome_id IS NOT NULL
          ) THEN RAISE(ABORT, 'terminal assertion authentication requires exact outcome companion') END;
END""",
    ),
)

_OUTCOME_AND_ISSUER_GUARD_DDL: tuple[tuple[str, str], ...] = (
    (
        "trg_reviewer_credential_operation_outcomes_insert_guard",
        """CREATE TRIGGER trg_reviewer_credential_operation_outcomes_insert_guard
BEFORE INSERT ON reviewer_credential_operation_outcomes
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1 FROM reviewer_credential_operation_challenge_consumptions consumption
        WHERE consumption.challenge_consumption_id = NEW.terminal_consumption_id
          AND consumption.consumption_content_hash = NEW.terminal_consumption_content_hash
          AND consumption.reviewer_credential_operation_id = NEW.reviewer_credential_operation_id
          AND consumption.reviewer_principal_id = NEW.reviewer_principal_id
          AND consumption.challenge_purpose = NEW.terminal_challenge_purpose
          AND consumption.terminal_result = NEW.terminal_challenge_result
          AND consumption.terminal_operation_outcome_id = NEW.credential_operation_outcome_id
          AND consumption.terminal_operation_outcome_result = NEW.terminal_result
          AND consumption.outcome_expected_credential_state_hash = NEW.expected_credential_state_hash
          AND consumption.outcome_resulting_credential_state_hash = NEW.resulting_credential_state_hash
    ) THEN RAISE(ABORT, 'operation outcome requires reverse-bound terminal consumption') END;
    SELECT CASE WHEN NEW.terminal_result != 'SUCCEEDED' AND EXISTS (
        SELECT 1 FROM reviewer_webauthn_credential_event_authorizations authorization
        WHERE authorization.reviewer_credential_operation_id = NEW.reviewer_credential_operation_id
    ) THEN RAISE(ABORT, 'failed operation cannot authorize credential lifecycle') END;
    SELECT CASE WHEN NEW.terminal_result = 'SUCCEEDED' AND NEW.operation_type = 'FIRST_ENROLLMENT' AND (
        SELECT COUNT(*) FROM reviewer_webauthn_credential_event_authorizations authorization
        WHERE authorization.reviewer_credential_operation_id = NEW.reviewer_credential_operation_id
          AND authorization.credential_operation_outcome_id = NEW.credential_operation_outcome_id
          AND authorization.credential_operation_outcome_content_hash = NEW.outcome_content_hash
          AND authorization.event_type = 'REGISTERED'
          AND authorization.authorization_kind = 'BOOTSTRAP_REGISTRATION'
    ) != 1 THEN RAISE(ABORT, 'first enrollment success requires exact registered authorization') END;
    SELECT CASE WHEN NEW.terminal_result = 'SUCCEEDED' AND NEW.operation_type = 'ADD_CREDENTIAL' AND (
        SELECT COUNT(*) FROM reviewer_webauthn_credential_event_authorizations authorization
        WHERE authorization.reviewer_credential_operation_id = NEW.reviewer_credential_operation_id
          AND authorization.credential_operation_outcome_id = NEW.credential_operation_outcome_id
          AND authorization.credential_operation_outcome_content_hash = NEW.outcome_content_hash
          AND authorization.event_type = 'REGISTERED'
          AND authorization.authorization_kind = 'AUTHORIZED_REGISTRATION'
    ) != 1 THEN RAISE(ABORT, 'add success requires exact registered authorization') END;
    SELECT CASE WHEN NEW.terminal_result = 'SUCCEEDED' AND NEW.operation_type = 'REPLACE_CREDENTIAL' AND (
        (SELECT COUNT(*) FROM reviewer_webauthn_credential_event_authorizations authorization
         WHERE authorization.reviewer_credential_operation_id = NEW.reviewer_credential_operation_id
           AND authorization.credential_operation_outcome_id = NEW.credential_operation_outcome_id
           AND authorization.credential_operation_outcome_content_hash = NEW.outcome_content_hash) != 2
        OR (SELECT COUNT(*) FROM reviewer_webauthn_credential_event_authorizations authorization
            WHERE authorization.reviewer_credential_operation_id = NEW.reviewer_credential_operation_id
              AND authorization.credential_operation_outcome_id = NEW.credential_operation_outcome_id
              AND authorization.event_type = 'REGISTERED'
              AND authorization.authorization_kind = 'AUTHORIZED_REGISTRATION') != 1
        OR (SELECT COUNT(*) FROM reviewer_webauthn_credential_event_authorizations authorization
            JOIN reviewer_credential_operations operation
              ON operation.reviewer_credential_operation_id = NEW.reviewer_credential_operation_id
            WHERE authorization.reviewer_credential_operation_id = NEW.reviewer_credential_operation_id
              AND authorization.credential_operation_outcome_id = NEW.credential_operation_outcome_id
              AND authorization.event_type = 'SUPERSEDED'
              AND authorization.authorization_kind = 'AUTHORIZED_SUPERSESSION'
              AND authorization.webauthn_credential_id = operation.target_webauthn_credential_id) != 1
        OR EXISTS (
            SELECT 1 FROM reviewer_webauthn_credential_event_authorizations registered
            JOIN reviewer_credential_operations operation
              ON operation.reviewer_credential_operation_id = NEW.reviewer_credential_operation_id
            WHERE registered.reviewer_credential_operation_id = NEW.reviewer_credential_operation_id
              AND registered.event_type = 'REGISTERED'
              AND registered.webauthn_credential_id = operation.target_webauthn_credential_id)
    ) THEN RAISE(ABORT, 'replace success requires atomic registered plus superseded pattern') END;
    SELECT CASE WHEN NEW.terminal_result = 'SUCCEEDED' AND NEW.operation_type = 'REVOKE_CREDENTIAL' AND (
        SELECT COUNT(*)
        FROM reviewer_webauthn_credential_event_authorizations authorization
        JOIN reviewer_credential_operations operation
          ON operation.reviewer_credential_operation_id = NEW.reviewer_credential_operation_id
        WHERE authorization.reviewer_credential_operation_id = NEW.reviewer_credential_operation_id
          AND authorization.credential_operation_outcome_id = NEW.credential_operation_outcome_id
          AND authorization.credential_operation_outcome_content_hash = NEW.outcome_content_hash
          AND authorization.event_type = 'REVOKED'
          AND authorization.authorization_kind = 'AUTHORIZED_REVOCATION'
          AND authorization.webauthn_credential_id = operation.target_webauthn_credential_id
    ) != 1 THEN RAISE(ABORT, 'revoke success requires exact authorized revocation') END;
    SELECT CASE WHEN NEW.terminal_result = 'SUCCEEDED' AND EXISTS (
        SELECT 1 FROM reviewer_webauthn_credential_event_authorizations authorization
        WHERE authorization.reviewer_credential_operation_id = NEW.reviewer_credential_operation_id
          AND (authorization.credential_operation_outcome_id != NEW.credential_operation_outcome_id
            OR authorization.credential_operation_outcome_content_hash != NEW.outcome_content_hash
            OR authorization.reviewer_principal_id != NEW.reviewer_principal_id
            OR authorization.reviewer_role != NEW.reviewer_role
            OR authorization.principal_content_hash != NEW.principal_content_hash
            OR authorization.os_owner_sid_hash != NEW.os_owner_sid_hash
            OR authorization.expected_credential_state_hash != NEW.expected_credential_state_hash
            OR authorization.resulting_credential_state_hash != NEW.resulting_credential_state_hash)
    ) THEN RAISE(ABORT, 'successful authorization trust tuple mismatch') END;
END""",
    ),
    (
        "trg_reviewer_authentication_events_credential_active_guard",
        """CREATE TRIGGER trg_reviewer_authentication_events_credential_active_guard
BEFORE INSERT ON reviewer_authentication_events
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1
        FROM reviewer_webauthn_credentials credential
        JOIN reviewer_webauthn_credential_events root
          ON root.webauthn_credential_id = credential.webauthn_credential_id
         AND root.reviewer_principal_id = credential.reviewer_principal_id
         AND root.event_type = 'REGISTERED'
         AND root.supersedes_credential_event_id IS NULL
        JOIN reviewer_webauthn_credential_event_authorizations authorization
          ON authorization.credential_event_id = root.credential_event_id
        WHERE credential.webauthn_credential_id = NEW.webauthn_credential_id
          AND credential.reviewer_principal_id = NEW.reviewer_principal_id
          AND credential.credential_id_fingerprint = NEW.credential_id_fingerprint
          AND credential.public_key_fingerprint = NEW.public_key_fingerprint
          AND NOT EXISTS (
              SELECT 1 FROM reviewer_webauthn_credential_events successor
              WHERE successor.supersedes_credential_event_id = root.credential_event_id
          )
    ) THEN RAISE(ABORT, 'issuer authentication requires currently active credential') END;
END""",
    ),
)


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


_COUNTER_GUARD_DDL: tuple[tuple[str, str], ...] = (
    (
        "trg_reviewer_authentication_events_counter_union_guard",
        _counter_union_trigger_sql(
            trigger_name="trg_reviewer_authentication_events_counter_union_guard",
            table_name="reviewer_authentication_events",
            credential_column="webauthn_credential_id",
        ),
    ),
    (
        "trg_reviewer_credential_operation_authentication_counter_union_guard",
        _counter_union_trigger_sql(
            trigger_name="trg_reviewer_credential_operation_authentication_counter_union_guard",
            table_name="reviewer_credential_operation_authentication_events",
            credential_column="authorizing_webauthn_credential_id",
        ),
    ),
)

_INSERT_GUARD_DDL = _INSERT_GUARD_DDL + _OUTCOME_AND_ISSUER_GUARD_DDL + _COUNTER_GUARD_DDL
_INSERT_GUARD_NAMES = tuple(name for name, _ddl in _INSERT_GUARD_DDL)

_TARGET_TRIGGER_NAMES = _APPEND_ONLY_TRIGGER_NAMES + _INSERT_GUARD_NAMES
_PREEXISTING_REVIEWER_LINEAGE_TABLES = (
    "reviewer_principals",
    "reviewer_webauthn_credentials",
    "reviewer_webauthn_credential_events",
    "issuer_approval_challenges",
    "issuer_approval_challenge_consumptions",
    "reviewer_authentication_events",
    "issuer_approval_events",
    "issuer_approval_evidence_observations",
    "issuer_authority_links",
    "issuer_authority_link_heads",
)
_PREDECESSOR_REQUIRED_COLUMNS = {
    "reviewer_principals": {
        "reviewer_principal_id",
        "reviewer_role",
        "principal_state",
        "principal_content_hash",
        "os_owner_sid_hash",
    },
    "reviewer_webauthn_credentials": {
        "webauthn_credential_id",
        "reviewer_principal_id",
        "reviewer_role",
        "principal_content_hash",
        "credential_id_fingerprint",
        "public_key_fingerprint",
        "counter_capability",
        "registration_sign_count",
        "rp_id",
        "credential_content_hash",
    },
    "reviewer_webauthn_credential_events": {
        "credential_event_id",
        "webauthn_credential_id",
        "reviewer_principal_id",
        "event_type",
        "supersedes_credential_event_id",
        "credential_event_content_hash",
    },
    "reviewer_authentication_events": {
        "authentication_event_id",
        "webauthn_credential_id",
        "reviewer_principal_id",
        "authentication_result",
        "counter_capability",
        "previous_sign_count",
        "asserted_sign_count",
    },
}


def _git_blob_id(path: Path) -> str:
    payload = path.read_bytes()
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload, usedforsecurity=False).hexdigest()


def _verify_frozen_migrations() -> None:
    versions = Path(__file__).resolve().parent
    actual = {
        name: _git_blob_id(versions / name) for name in _FROZEN_MIGRATION_BLOBS
    }
    if actual != _FROZEN_MIGRATION_BLOBS:
        mismatches = ", ".join(
            f"{name}:{actual.get(name)}!={expected}"
            for name, expected in _FROZEN_MIGRATION_BLOBS.items()
            if actual.get(name) != expected
        )
        raise RuntimeError("0006 frozen predecessor migration mismatch: " + mismatches)


def _sqlite_objects(connection: Connection) -> set[tuple[str, str]]:
    rows = connection.execute(
        sa.text(
            "SELECT type, name FROM sqlite_master "
            "WHERE type IN ('table', 'index', 'trigger')"
        )
    ).mappings()
    return {(str(row["type"]), str(row["name"])) for row in rows}


def _target_objects() -> set[tuple[str, str]]:
    return (
        {("table", name) for name in _NEW_TABLE_NAMES}
        | {("index", name) for name in _INDEX_NAMES}
        | {("trigger", name) for name in _TARGET_TRIGGER_NAMES}
    )


def _table_columns(connection: Connection, table_name: str) -> set[str]:
    rows = connection.exec_driver_sql(f'PRAGMA table_info("{table_name}")').mappings()
    return {str(row["name"]) for row in rows}


def _verify_predecessor_schema(connection: Connection) -> None:
    current_revision = connection.execute(
        sa.text("SELECT version_num FROM alembic_version")
    ).scalar_one()
    if str(current_revision) != down_revision:
        raise RuntimeError(
            f"0006 requires exact predecessor revision {down_revision}; got {current_revision}"
        )
    objects = _sqlite_objects(connection)
    for table_name, required_columns in _PREDECESSOR_REQUIRED_COLUMNS.items():
        if ("table", table_name) not in objects:
            raise RuntimeError(f"0006 predecessor table missing: {table_name}")
        actual_columns = _table_columns(connection, table_name)
        if not required_columns.issubset(actual_columns):
            missing = sorted(required_columns - actual_columns)
            raise RuntimeError(
                f"0006 predecessor schema mismatch for {table_name}: missing {missing}"
            )
    for table_name in _PREEXISTING_REVIEWER_LINEAGE_TABLES:
        if ("table", table_name) not in objects:
            raise RuntimeError(f"0006 predecessor lineage table missing: {table_name}")
        has_rows = connection.exec_driver_sql(
            f'SELECT EXISTS(SELECT 1 FROM "{table_name}" LIMIT 1)'
        ).scalar_one()
        if bool(has_rows):
            raise RuntimeError(
                "0006 refuses unexpected pre-existing reviewer/approval lineage "
                f"without synthetic backfill: {table_name}"
            )


def _drop_objects(connection: Connection, statements: Iterable[str]) -> None:
    for statement in statements:
        connection.exec_driver_sql(statement)


def _cleanup_failed_upgrade(connection: Connection) -> None:
    _drop_objects(
        connection,
        (
            *(f"DROP TRIGGER IF EXISTS {name}" for name in reversed(_TARGET_TRIGGER_NAMES)),
            *(f"DROP INDEX IF EXISTS {name}" for name in reversed(_INDEX_NAMES)),
            *(f"DROP TABLE IF EXISTS {name}" for name in reversed(_NEW_TABLE_NAMES)),
        ),
    )


def _verify_created_schema(connection: Connection) -> None:
    missing = sorted(_target_objects() - _sqlite_objects(connection))
    if missing:
        rendered = ", ".join(f"{kind}:{name}" for kind, name in missing)
        raise RuntimeError("0006 schema inventory incomplete: " + rendered)
    violations = tuple(connection.exec_driver_sql("PRAGMA foreign_key_check"))
    if violations:
        raise RuntimeError(f"0006 foreign_key_check failed: {violations!r}")


def upgrade() -> None:
    connection = op.get_bind()
    _verify_frozen_migrations()
    collisions = sorted(_sqlite_objects(connection) & _target_objects())
    if collisions:
        rendered = ", ".join(f"{kind}:{name}" for kind, name in collisions)
        raise RuntimeError("0006 refuses to replace pre-existing reviewer objects: " + rendered)
    _verify_predecessor_schema(connection)
    try:
        for _name, statement in _OLD_TABLE_INDEX_DDL:
            op.execute(sa.text(statement))
        for _name, statement in _NEW_TABLE_DDL:
            op.execute(sa.text(statement))
        for _name, statement in _NEW_TABLE_INDEX_DDL:
            op.execute(sa.text(statement))
        for table_name in _NEW_TABLE_NAMES:
            for operation in ("UPDATE", "DELETE"):
                op.execute(sa.text(_append_only_trigger_sql(table_name, operation)))
        for _name, statement in _INSERT_GUARD_DDL:
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
                "0006 destructive downgrade refused: reviewer operation audit ledger is non-empty"
            )
    _cleanup_failed_upgrade(connection)
