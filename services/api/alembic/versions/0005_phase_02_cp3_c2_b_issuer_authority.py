# ruff: noqa: E501
"""Phase 2 CP3-C2-B issuer-authority ledger foundation.

Revision 0005 is additive. It creates only the approved issuer-authority tables,
indexes, and new-table append-only triggers; revisions 0001-0004 and all
pre-existing data remain untouched.
"""

from __future__ import annotations

from collections.abc import Iterable

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import Connection

revision = "0005_phase_02_cp3_c2_b_issuer_authority"
down_revision = "0004_phase_02_cp3_c1_security_master"
branch_labels = None
depends_on = None

_TABLE_DDL: tuple[tuple[str, str], ...] = (
    (
        "authority_source_policies",
        """CREATE TABLE authority_source_policies (
	authority_source_policy_id VARCHAR(128) NOT NULL,
	contract_version VARCHAR(64) NOT NULL,
	policy_content_hash VARCHAR(71) NOT NULL,
	source_namespace VARCHAR(128) NOT NULL,
	field_owner VARCHAR(256) NOT NULL,
	authority_classification VARCHAR(64) NOT NULL,
	allowed_document_kinds_json TEXT NOT NULL,
	credential_free_locator_roots_json TEXT NOT NULL,
	allowed_authority_scopes_json TEXT NOT NULL,
	allowed_subject_roles_json TEXT NOT NULL,
	scope_role_weights_json TEXT NOT NULL,
	maximum_issuer_authority_weight VARCHAR(16) NOT NULL,
	ingestion_mode VARCHAR(64) NOT NULL,
	admitted_adapter_contract_versions_json TEXT NOT NULL,
	admitted_parser_contract_versions_json TEXT NOT NULL,
	production_authority_eligible INTEGER NOT NULL,
	required_access_disposition VARCHAR(32) NOT NULL,
	required_license_disposition VARCHAR(32) NOT NULL,
	allowed_origin_data_modes_json TEXT NOT NULL,
	permanent_fixture_test_taint INTEGER NOT NULL,
	predecessor_policy_id VARCHAR(128),
	policy_effective_at VARCHAR(35),
	registered_at VARCHAR(35) NOT NULL,
	payload_json TEXT NOT NULL,
	PRIMARY KEY (authority_source_policy_id),
	UNIQUE (authority_source_policy_id, policy_content_hash),
	CHECK (maximum_issuer_authority_weight IN ('ZERO', 'SUPPORTING', 'DECISIVE')),
	CHECK (ingestion_mode IN ('AUTOMATED_OFFICIAL_PUBLIC', 'HUMAN_ASSISTED_VERIFIED_DOCUMENT', 'PROVENANCE_ONLY', 'TEST_ISOLATED_ONLY')),
	CHECK (production_authority_eligible IN (0, 1)),
	CHECK (permanent_fixture_test_taint IN (0, 1)),
	CHECK (NOT (production_authority_eligible = 1 AND permanent_fixture_test_taint = 1)),
	CHECK (permanent_fixture_test_taint = 0 OR maximum_issuer_authority_weight = 'ZERO'),
	CHECK (production_authority_eligible = 0 OR (instr(source_namespace, '*') = 0 AND instr(source_namespace, '?') = 0)),
	FOREIGN KEY(predecessor_policy_id) REFERENCES authority_source_policies (authority_source_policy_id)
)""",
    ),
    (
        "reviewer_principals",
        """CREATE TABLE reviewer_principals (
	reviewer_principal_id VARCHAR(128) NOT NULL,
	contract_version VARCHAR(64) NOT NULL,
	reviewer_role VARCHAR(32) NOT NULL,
	principal_state VARCHAR(16) NOT NULL,
	os_owner_sid_hash VARCHAR(71) NOT NULL,
	enrollment_policy_version VARCHAR(64) NOT NULL,
	principal_content_hash VARCHAR(71) NOT NULL,
	registered_at VARCHAR(35) NOT NULL,
	payload_json TEXT NOT NULL,
	PRIMARY KEY (reviewer_principal_id),
	CHECK (reviewer_role = 'LOCAL_DATA_STEWARD'),
	CHECK (principal_state IN ('ACTIVE', 'REVOKED')),
	UNIQUE (reviewer_principal_id, reviewer_role, principal_content_hash)
)""",
    ),
    (
        "reviewer_webauthn_credentials",
        """CREATE TABLE reviewer_webauthn_credentials (
	webauthn_credential_id VARCHAR(512) NOT NULL,
	contract_version VARCHAR(64) NOT NULL,
	reviewer_principal_id VARCHAR(128) NOT NULL,
	reviewer_role VARCHAR(32) NOT NULL,
	principal_content_hash VARCHAR(71) NOT NULL,
	credential_id_fingerprint VARCHAR(71) NOT NULL,
	cose_public_key_canonical TEXT NOT NULL,
	public_key_fingerprint VARCHAR(71) NOT NULL,
	public_key_algorithm VARCHAR(32) NOT NULL,
	authenticator_aaguid VARCHAR(64),
	authenticator_attachment VARCHAR(16) NOT NULL,
	authenticator_transports_json TEXT NOT NULL,
	counter_capability VARCHAR(32) NOT NULL,
	registration_sign_count INTEGER,
	rp_id VARCHAR(255) NOT NULL,
	resident_key_required INTEGER NOT NULL,
	user_verification_required INTEGER NOT NULL,
	registration_policy_version VARCHAR(64) NOT NULL,
	credential_content_hash VARCHAR(71) NOT NULL,
	registered_at VARCHAR(35) NOT NULL,
	payload_json TEXT NOT NULL,
	PRIMARY KEY (webauthn_credential_id),
	FOREIGN KEY(reviewer_principal_id, reviewer_role, principal_content_hash) REFERENCES reviewer_principals (reviewer_principal_id, reviewer_role, principal_content_hash),
	UNIQUE (webauthn_credential_id, reviewer_principal_id, credential_id_fingerprint, public_key_fingerprint, rp_id, counter_capability),
	UNIQUE (credential_id_fingerprint),
	CHECK (authenticator_attachment = 'platform'),
	CHECK (resident_key_required = 1),
	CHECK (user_verification_required = 1),
	CHECK (counter_capability IN ('SIGN_COUNT_SUPPORTED', 'NO_USABLE_COUNTER')),
	CHECK (registration_sign_count IS NULL OR registration_sign_count >= 0),
	CHECK ((counter_capability = 'SIGN_COUNT_SUPPORTED' AND registration_sign_count IS NOT NULL) OR (counter_capability = 'NO_USABLE_COUNTER' AND registration_sign_count IS NULL))
)""",
    ),
    (
        "reviewer_webauthn_credential_events",
        """CREATE TABLE reviewer_webauthn_credential_events (
	credential_event_id VARCHAR(128) NOT NULL,
	contract_version VARCHAR(64) NOT NULL,
	webauthn_credential_id VARCHAR(512) NOT NULL,
	reviewer_principal_id VARCHAR(128) NOT NULL,
	event_type VARCHAR(16) NOT NULL,
	structured_reason_code VARCHAR(128) NOT NULL,
	supersedes_credential_event_id VARCHAR(128),
	credential_event_content_hash VARCHAR(71) NOT NULL,
	occurred_at VARCHAR(35) NOT NULL,
	payload_json TEXT NOT NULL,
	PRIMARY KEY (credential_event_id),
	CHECK (event_type IN ('REGISTERED', 'REVOKED', 'SUPERSEDED')),
	FOREIGN KEY(webauthn_credential_id) REFERENCES reviewer_webauthn_credentials (webauthn_credential_id),
	FOREIGN KEY(reviewer_principal_id) REFERENCES reviewer_principals (reviewer_principal_id),
	FOREIGN KEY(supersedes_credential_event_id) REFERENCES reviewer_webauthn_credential_events (credential_event_id)
)""",
    ),
    (
        "authority_evidence",
        """CREATE TABLE authority_evidence (
	evidence_id VARCHAR(128) NOT NULL,
	contract_version VARCHAR(64) NOT NULL,
	evidence_content_hash VARCHAR(71) NOT NULL,
	evidence_provenance_hash VARCHAR(71) NOT NULL,
	authority_source_policy_id VARCHAR(128) NOT NULL,
	authority_source_identifier VARCHAR(128) NOT NULL,
	authority_classification VARCHAR(64) NOT NULL,
	authority_source_locator TEXT NOT NULL,
	authority_document_reference VARCHAR(512) NOT NULL,
	source_document_kind VARCHAR(128) NOT NULL,
	authority_external_key VARCHAR(512) NOT NULL,
	authority_source_document_id VARCHAR(128) NOT NULL,
	raw_content_hash VARCHAR(71) NOT NULL,
	parser_contract_version VARCHAR(128) NOT NULL,
	evidence_kind VARCHAR(32) NOT NULL,
	authority_scope VARCHAR(64) NOT NULL,
	subject_role VARCHAR(64) NOT NULL,
	policy_maximum_issuer_authority_weight VARCHAR(16) NOT NULL,
	claim_field VARCHAR(256) NOT NULL,
	raw_claim_value_json TEXT NOT NULL,
	normalized_claim_value_json TEXT NOT NULL,
	authority_published_at VARCHAR(35),
	authority_accepted_at VARCHAR(35),
	authority_as_of_date DATE,
	authority_effective_at VARCHAR(35),
	authority_effective_date DATE,
	authority_time_missing_reasons_json TEXT NOT NULL,
	access_disposition VARCHAR(32) NOT NULL,
	license_disposition VARCHAR(32) NOT NULL,
	origin_data_mode VARCHAR(32) NOT NULL,
	origin_adapter_class VARCHAR(128) NOT NULL,
	origin_source_system VARCHAR(128),
	lineage_tainted INTEGER NOT NULL,
	lineage_ancestor_tainted INTEGER NOT NULL,
	lineage_ancestor_hashes_json TEXT NOT NULL,
	payload_json TEXT NOT NULL,
	PRIMARY KEY (evidence_id),
	UNIQUE (evidence_id, evidence_content_hash, authority_source_policy_id, authority_scope, policy_maximum_issuer_authority_weight),
	UNIQUE (evidence_content_hash),
	UNIQUE (evidence_provenance_hash),
	CHECK (policy_maximum_issuer_authority_weight IN ('ZERO', 'SUPPORTING', 'DECISIVE')),
	CHECK (origin_data_mode IN ('PRODUCTION_AUTHORITY', 'TEST_ONLY')),
	CHECK (lineage_tainted IN (0, 1)),
	CHECK (lineage_ancestor_tainted IN (0, 1)),
	CHECK (lineage_tainted = 0 OR policy_maximum_issuer_authority_weight = 'ZERO'),
	CHECK (subject_role NOT IN ('SEC_LOGIN_CIK', 'SEC_FILING_AGENT') OR (authority_scope = 'SUBMISSION_PROVENANCE' AND evidence_kind = 'PROVENANCE_ONLY' AND policy_maximum_issuer_authority_weight = 'ZERO')),
	CHECK (authority_effective_at IS NULL OR authority_effective_date IS NULL),
	FOREIGN KEY(authority_source_policy_id) REFERENCES authority_source_policies (authority_source_policy_id)
)""",
    ),
    (
        "authority_evidence_observations",
        """CREATE TABLE authority_evidence_observations (
	authority_evidence_observation_id VARCHAR(128) NOT NULL,
	contract_version VARCHAR(64) NOT NULL,
	observation_content_hash VARCHAR(71) NOT NULL,
	evidence_id VARCHAR(128) NOT NULL,
	fetched_at VARCHAR(35) NOT NULL,
	raw_content_hash VARCHAR(71) NOT NULL,
	authority_source_locator TEXT NOT NULL,
	authority_document_reference VARCHAR(512) NOT NULL,
	raw_storage_reference VARCHAR(128) NOT NULL,
	retrieval_status VARCHAR(32) NOT NULL,
	secret_free_retrieval_fingerprint VARCHAR(71) NOT NULL,
	safe_status_code VARCHAR(128) NOT NULL,
	payload_json TEXT NOT NULL,
	PRIMARY KEY (authority_evidence_observation_id),
	UNIQUE (observation_content_hash),
	UNIQUE (authority_evidence_observation_id, observation_content_hash),
	FOREIGN KEY(evidence_id) REFERENCES authority_evidence (evidence_id)
)""",
    ),
    (
        "authority_evidence_relations",
        """CREATE TABLE authority_evidence_relations (
	authority_evidence_relation_id VARCHAR(128) NOT NULL,
	contract_version VARCHAR(64) NOT NULL,
	relation_content_hash VARCHAR(71) NOT NULL,
	predecessor_evidence_id VARCHAR(128) NOT NULL,
	successor_evidence_id VARCHAR(128) NOT NULL,
	relation_type VARCHAR(32) NOT NULL,
	authority_effective_at VARCHAR(35),
	authority_effective_date DATE,
	authority_effective_missing_reason VARCHAR(64),
	recorded_at VARCHAR(35) NOT NULL,
	payload_json TEXT NOT NULL,
	PRIMARY KEY (authority_evidence_relation_id),
	CHECK (predecessor_evidence_id != successor_evidence_id),
	CHECK (relation_type IN ('CORRECTS', 'REVOKES', 'SUPERSEDES')),
	CHECK (authority_effective_at IS NULL OR authority_effective_date IS NULL),
	FOREIGN KEY(predecessor_evidence_id) REFERENCES authority_evidence (evidence_id),
	FOREIGN KEY(successor_evidence_id) REFERENCES authority_evidence (evidence_id)
)""",
    ),
    (
        "authority_evidence_applications",
        """CREATE TABLE authority_evidence_applications (
	evidence_application_id VARCHAR(128) NOT NULL,
	contract_version VARCHAR(64) NOT NULL,
	application_content_hash VARCHAR(71) NOT NULL,
	evidence_id VARCHAR(128) NOT NULL,
	evidence_content_hash VARCHAR(71) NOT NULL,
	provider_security_identity_id VARCHAR(128) NOT NULL,
	provider_observation_ids_json TEXT NOT NULL,
	proposed_issuer_id VARCHAR(128) NOT NULL,
	candidate_fingerprint VARCHAR(71) NOT NULL,
	authority_scope VARCHAR(64) NOT NULL,
	claim_target_field VARCHAR(256) NOT NULL,
	authority_source_policy_id VARCHAR(128) NOT NULL,
	authority_source_policy_content_hash VARCHAR(71) NOT NULL,
	policy_maximum_issuer_authority_weight VARCHAR(16) NOT NULL,
	application_status VARCHAR(64) NOT NULL,
	effective_issuer_authority_weight VARCHAR(16) NOT NULL,
	reason_codes_json TEXT NOT NULL,
	authority_relation_head_hash VARCHAR(71) NOT NULL,
	application_rule_version VARCHAR(64) NOT NULL,
	production_authority_admitted INTEGER NOT NULL,
	lineage_tainted INTEGER NOT NULL,
	evaluated_at VARCHAR(35) NOT NULL,
	payload_json TEXT NOT NULL,
	PRIMARY KEY (evidence_application_id),
	FOREIGN KEY(evidence_id, evidence_content_hash, authority_source_policy_id, authority_scope, policy_maximum_issuer_authority_weight) REFERENCES authority_evidence (evidence_id, evidence_content_hash, authority_source_policy_id, authority_scope, policy_maximum_issuer_authority_weight),
	FOREIGN KEY(authority_source_policy_id, authority_source_policy_content_hash) REFERENCES authority_source_policies (authority_source_policy_id, policy_content_hash),
	UNIQUE (evidence_application_id, application_content_hash, evidence_id, evidence_content_hash, authority_source_policy_id, authority_source_policy_content_hash, provider_security_identity_id, proposed_issuer_id, candidate_fingerprint, authority_scope, application_status, effective_issuer_authority_weight),
	UNIQUE (evidence_application_id, application_content_hash, evidence_id, evidence_content_hash, authority_source_policy_id, authority_source_policy_content_hash, provider_security_identity_id, proposed_issuer_id, candidate_fingerprint, authority_scope),
	UNIQUE (application_content_hash),
	CHECK (effective_issuer_authority_weight IN ('ZERO', 'SUPPORTING', 'DECISIVE')),
	CHECK (policy_maximum_issuer_authority_weight IN ('ZERO', 'SUPPORTING', 'DECISIVE')),
	CHECK (production_authority_admitted IN (0, 1)),
	CHECK (lineage_tainted IN (0, 1)),
	CHECK (lineage_tainted = 0 OR (production_authority_admitted = 0 AND effective_issuer_authority_weight = 'ZERO')),
	CHECK (production_authority_admitted = 1 OR effective_issuer_authority_weight = 'ZERO'),
	CHECK ((application_status = 'APPLIED_DECISIVE' AND effective_issuer_authority_weight = 'DECISIVE') OR (application_status = 'APPLIED_SUPPORTING' AND effective_issuer_authority_weight = 'SUPPORTING') OR (application_status NOT IN ('APPLIED_DECISIVE', 'APPLIED_SUPPORTING') AND effective_issuer_authority_weight = 'ZERO')),
	FOREIGN KEY(provider_security_identity_id) REFERENCES provider_security_identities (provider_security_identity_id)
)""",
    ),
    (
        "authority_bundles",
        """CREATE TABLE authority_bundles (
	authority_bundle_id VARCHAR(128) NOT NULL,
	contract_version VARCHAR(64) NOT NULL,
	bundle_content_hash VARCHAR(71) NOT NULL,
	bundle_origin_data_mode VARCHAR(32) NOT NULL,
	provider_security_identity_id VARCHAR(128) NOT NULL,
	candidate_jurisdiction VARCHAR(8) NOT NULL,
	candidate_identifier_kind VARCHAR(32) NOT NULL,
	candidate_identifier_value VARCHAR(10) NOT NULL,
	proposed_issuer_anchor VARCHAR(256) NOT NULL,
	proposed_issuer_id VARCHAR(128) NOT NULL,
	candidate_fingerprint VARCHAR(71) NOT NULL,
	legal_jurisdiction_result VARCHAR(32) NOT NULL,
	collision_scan_result VARCHAR(16) NOT NULL,
	collision_claim_candidate_fingerprints_json TEXT NOT NULL,
	decision_rule_version VARCHAR(64) NOT NULL,
	evidence_application_set_hash VARCHAR(71) NOT NULL,
	source_policy_set_hash VARCHAR(71) NOT NULL,
	provider_lineage_set_hash VARCHAR(71) NOT NULL,
	collision_scan_hash VARCHAR(71) NOT NULL,
	built_at VARCHAR(35) NOT NULL,
	payload_json TEXT NOT NULL,
	PRIMARY KEY (authority_bundle_id),
	UNIQUE (authority_bundle_id, bundle_content_hash, provider_security_identity_id, proposed_issuer_id, candidate_fingerprint),
	UNIQUE (authority_bundle_id, bundle_content_hash, provider_security_identity_id, proposed_issuer_id),
	UNIQUE (bundle_content_hash),
	CHECK (bundle_origin_data_mode IN ('PRODUCTION_AUTHORITY', 'TEST_ONLY')),
	CHECK ((candidate_jurisdiction = 'KR' AND candidate_identifier_kind = 'DART_CORP_CODE' AND length(candidate_identifier_value) = 8 AND candidate_identifier_value NOT GLOB '*[^0-9]*') OR (candidate_jurisdiction = 'US' AND candidate_identifier_kind = 'SEC_REGISTRANT_CIK' AND length(candidate_identifier_value) = 10 AND candidate_identifier_value NOT GLOB '*[^0-9]*')),
	CHECK (legal_jurisdiction_result IN ('ESTABLISHED', 'UNRESOLVED', 'UNSUPPORTED_BY_CONTRACT')),
	CHECK (collision_scan_result IN ('CLEAR', 'CONFLICT')),
	FOREIGN KEY(provider_security_identity_id) REFERENCES provider_security_identities (provider_security_identity_id)
)""",
    ),
    (
        "authority_bundle_evidence_applications",
        """CREATE TABLE authority_bundle_evidence_applications (
	authority_bundle_id VARCHAR(128) NOT NULL,
	evidence_application_id VARCHAR(128) NOT NULL,
	member_ordinal INTEGER NOT NULL,
	bundle_content_hash VARCHAR(71) NOT NULL,
	application_content_hash VARCHAR(71) NOT NULL,
	evidence_id VARCHAR(128) NOT NULL,
	evidence_content_hash VARCHAR(71) NOT NULL,
	authority_source_policy_id VARCHAR(128) NOT NULL,
	authority_source_policy_content_hash VARCHAR(71) NOT NULL,
	provider_security_identity_id VARCHAR(128) NOT NULL,
	proposed_issuer_id VARCHAR(128) NOT NULL,
	candidate_fingerprint VARCHAR(71) NOT NULL,
	authority_scope VARCHAR(64) NOT NULL,
	application_status VARCHAR(64) NOT NULL,
	effective_issuer_authority_weight VARCHAR(16) NOT NULL,
	membership_content_hash VARCHAR(71) NOT NULL,
	payload_json TEXT NOT NULL,
	PRIMARY KEY (authority_bundle_id, evidence_application_id),
	FOREIGN KEY(authority_bundle_id, bundle_content_hash, provider_security_identity_id, proposed_issuer_id, candidate_fingerprint) REFERENCES authority_bundles (authority_bundle_id, bundle_content_hash, provider_security_identity_id, proposed_issuer_id, candidate_fingerprint),
	FOREIGN KEY(evidence_application_id, application_content_hash, evidence_id, evidence_content_hash, authority_source_policy_id, authority_source_policy_content_hash, provider_security_identity_id, proposed_issuer_id, candidate_fingerprint, authority_scope, application_status, effective_issuer_authority_weight) REFERENCES authority_evidence_applications (evidence_application_id, application_content_hash, evidence_id, evidence_content_hash, authority_source_policy_id, authority_source_policy_content_hash, provider_security_identity_id, proposed_issuer_id, candidate_fingerprint, authority_scope, application_status, effective_issuer_authority_weight),
	UNIQUE (authority_bundle_id, member_ordinal),
	CHECK (member_ordinal >= 0)
)""",
    ),
    (
        "authority_bundle_scope_results",
        """CREATE TABLE authority_bundle_scope_results (
	authority_bundle_id VARCHAR(128) NOT NULL,
	authority_scope VARCHAR(64) NOT NULL,
	bundle_content_hash VARCHAR(71) NOT NULL,
	provider_security_identity_id VARCHAR(128) NOT NULL,
	proposed_issuer_id VARCHAR(128) NOT NULL,
	candidate_fingerprint VARCHAR(71) NOT NULL,
	scope_status VARCHAR(32) NOT NULL,
	reason_codes_json TEXT NOT NULL,
	scope_result_content_hash VARCHAR(71) NOT NULL,
	payload_json TEXT NOT NULL,
	PRIMARY KEY (authority_bundle_id, authority_scope),
	FOREIGN KEY(authority_bundle_id, bundle_content_hash, provider_security_identity_id, proposed_issuer_id, candidate_fingerprint) REFERENCES authority_bundles (authority_bundle_id, bundle_content_hash, provider_security_identity_id, proposed_issuer_id, candidate_fingerprint),
	CHECK (scope_status IN ('SATISFIED', 'MISSING', 'CONFLICT', 'STALE', 'UNSUPPORTED', 'UNUSABLE'))
)""",
    ),
    (
        "authority_bundle_provider_observations",
        """CREATE TABLE authority_bundle_provider_observations (
	authority_bundle_id VARCHAR(128) NOT NULL,
	provider_observation_id VARCHAR(128) NOT NULL,
	member_ordinal INTEGER NOT NULL,
	bundle_content_hash VARCHAR(71) NOT NULL,
	provider_security_identity_id VARCHAR(128) NOT NULL,
	proposed_issuer_id VARCHAR(128) NOT NULL,
	candidate_fingerprint VARCHAR(71) NOT NULL,
	membership_content_hash VARCHAR(71) NOT NULL,
	payload_json TEXT NOT NULL,
	PRIMARY KEY (authority_bundle_id, provider_observation_id),
	FOREIGN KEY(authority_bundle_id, bundle_content_hash, provider_security_identity_id, proposed_issuer_id, candidate_fingerprint) REFERENCES authority_bundles (authority_bundle_id, bundle_content_hash, provider_security_identity_id, proposed_issuer_id, candidate_fingerprint),
	UNIQUE (authority_bundle_id, member_ordinal),
	CHECK (member_ordinal >= 0),
	FOREIGN KEY(provider_observation_id) REFERENCES provider_security_master_observations (observation_id)
)""",
    ),
    (
        "authority_identifier_claims",
        """CREATE TABLE authority_identifier_claims (
	authority_identifier_claim_id VARCHAR(128) NOT NULL,
	contract_version VARCHAR(64) NOT NULL,
	claim_content_hash VARCHAR(71) NOT NULL,
	identifier_kind VARCHAR(32) NOT NULL,
	normalized_identifier_value VARCHAR(10) NOT NULL,
	candidate_jurisdiction VARCHAR(8) NOT NULL,
	proposed_issuer_id VARCHAR(128) NOT NULL,
	candidate_fingerprint VARCHAR(71) NOT NULL,
	provider_security_identity_id VARCHAR(128) NOT NULL,
	evidence_application_id VARCHAR(128) NOT NULL,
	application_content_hash VARCHAR(71) NOT NULL,
	evidence_id VARCHAR(128) NOT NULL,
	evidence_content_hash VARCHAR(71) NOT NULL,
	authority_source_policy_id VARCHAR(128) NOT NULL,
	authority_source_policy_content_hash VARCHAR(71) NOT NULL,
	claim_role VARCHAR(64) NOT NULL,
	claim_scope VARCHAR(64) NOT NULL,
	recorded_at VARCHAR(35) NOT NULL,
	payload_json TEXT NOT NULL,
	PRIMARY KEY (authority_identifier_claim_id),
	FOREIGN KEY(evidence_application_id, application_content_hash, evidence_id, evidence_content_hash, authority_source_policy_id, authority_source_policy_content_hash, provider_security_identity_id, proposed_issuer_id, candidate_fingerprint, claim_scope) REFERENCES authority_evidence_applications (evidence_application_id, application_content_hash, evidence_id, evidence_content_hash, authority_source_policy_id, authority_source_policy_content_hash, provider_security_identity_id, proposed_issuer_id, candidate_fingerprint, authority_scope),
	CHECK ((candidate_jurisdiction = 'KR' AND identifier_kind = 'DART_CORP_CODE' AND length(normalized_identifier_value) = 8 AND normalized_identifier_value NOT GLOB '*[^0-9]*') OR (candidate_jurisdiction = 'US' AND identifier_kind = 'SEC_REGISTRANT_CIK' AND length(normalized_identifier_value) = 10 AND normalized_identifier_value NOT GLOB '*[^0-9]*')),
	FOREIGN KEY(provider_security_identity_id) REFERENCES provider_security_identities (provider_security_identity_id)
)""",
    ),
    (
        "issuer_decisions",
        """CREATE TABLE issuer_decisions (
	issuer_decision_id VARCHAR(128) NOT NULL,
	contract_version VARCHAR(64) NOT NULL,
	decision_content_hash VARCHAR(71) NOT NULL,
	decision_audit_hash VARCHAR(71) NOT NULL,
	decision_rule_version VARCHAR(64) NOT NULL,
	authority_bundle_id VARCHAR(128) NOT NULL,
	authority_bundle_content_hash VARCHAR(71) NOT NULL,
	provider_security_identity_id VARCHAR(128) NOT NULL,
	proposed_issuer_id VARCHAR(128) NOT NULL,
	decision_state VARCHAR(32) NOT NULL,
	reason_codes_json TEXT NOT NULL,
	latest_revision_check_hash VARCHAR(71) NOT NULL,
	freshness_policy_version VARCHAR(128) NOT NULL,
	freshness_result VARCHAR(32) NOT NULL,
	collision_scan_hash VARCHAR(71) NOT NULL,
	supersedes_decision_id VARCHAR(128),
	evaluated_at VARCHAR(35) NOT NULL,
	payload_json TEXT NOT NULL,
	PRIMARY KEY (issuer_decision_id),
	FOREIGN KEY(authority_bundle_id, authority_bundle_content_hash, provider_security_identity_id, proposed_issuer_id) REFERENCES authority_bundles (authority_bundle_id, bundle_content_hash, provider_security_identity_id, proposed_issuer_id),
	UNIQUE (issuer_decision_id, authority_bundle_id, decision_content_hash, authority_bundle_content_hash, provider_security_identity_id, proposed_issuer_id),
	CHECK (decision_state IN ('UNRESOLVED', 'READY_FOR_MANUAL_REVIEW', 'STALE', 'REVIEW_REQUIRED')),
	FOREIGN KEY(supersedes_decision_id) REFERENCES issuer_decisions (issuer_decision_id)
)""",
    ),
    (
        "issuer_approval_challenges",
        """CREATE TABLE issuer_approval_challenges (
	issuer_approval_challenge_id VARCHAR(128) NOT NULL,
	contract_version VARCHAR(64) NOT NULL,
	challenge_digest VARCHAR(71) NOT NULL,
	challenge_binding_hash VARCHAR(71) NOT NULL,
	reviewer_principal_id VARCHAR(128) NOT NULL,
	reviewer_role VARCHAR(32) NOT NULL,
	principal_content_hash VARCHAR(71) NOT NULL,
	issuer_decision_id VARCHAR(128) NOT NULL,
	authority_bundle_id VARCHAR(128) NOT NULL,
	expected_decision_content_hash VARCHAR(71) NOT NULL,
	expected_bundle_content_hash VARCHAR(71) NOT NULL,
	provider_security_identity_id VARCHAR(128) NOT NULL,
	proposed_issuer_id VARCHAR(128) NOT NULL,
	requested_disposition VARCHAR(16) NOT NULL,
	predecessor_approval_event_id VARCHAR(128),
	predecessor_link_id VARCHAR(128),
	successor_decision_id VARCHAR(128),
	rp_id VARCHAR(255) NOT NULL,
	allowed_origin VARCHAR(255) NOT NULL,
	user_verification_required INTEGER NOT NULL,
	authentication_policy_version VARCHAR(64) NOT NULL,
	issued_at VARCHAR(35) NOT NULL,
	expires_at VARCHAR(35) NOT NULL,
	payload_json TEXT NOT NULL,
	PRIMARY KEY (issuer_approval_challenge_id),
	FOREIGN KEY(issuer_decision_id, authority_bundle_id, expected_decision_content_hash, expected_bundle_content_hash, provider_security_identity_id, proposed_issuer_id) REFERENCES issuer_decisions (issuer_decision_id, authority_bundle_id, decision_content_hash, authority_bundle_content_hash, provider_security_identity_id, proposed_issuer_id),
	FOREIGN KEY(reviewer_principal_id, reviewer_role, principal_content_hash) REFERENCES reviewer_principals (reviewer_principal_id, reviewer_role, principal_content_hash),
	UNIQUE (challenge_digest),
	UNIQUE (challenge_binding_hash),
	UNIQUE (issuer_approval_challenge_id, reviewer_principal_id, reviewer_role, issuer_decision_id, authority_bundle_id, expected_decision_content_hash, expected_bundle_content_hash, requested_disposition),
	CHECK (requested_disposition IN ('APPROVED', 'REJECTED', 'REVOKED', 'SUPERSEDED')),
	CHECK (rp_id = 'localhost'),
	CHECK (allowed_origin = 'http://localhost:3000'),
	CHECK (user_verification_required = 1),
	CHECK (expires_at > issued_at),
	CHECK (julianday(expires_at) <= julianday(issued_at, '+5 minutes')),
	FOREIGN KEY(predecessor_approval_event_id) REFERENCES issuer_approval_events (issuer_approval_event_id),
	FOREIGN KEY(predecessor_link_id) REFERENCES issuer_authority_links (issuer_authority_link_id),
	FOREIGN KEY(successor_decision_id) REFERENCES issuer_decisions (issuer_decision_id)
)""",
    ),
    (
        "issuer_approval_challenge_consumptions",
        """CREATE TABLE issuer_approval_challenge_consumptions (
	challenge_consumption_id VARCHAR(128) NOT NULL,
	contract_version VARCHAR(64) NOT NULL,
	issuer_approval_challenge_id VARCHAR(128) NOT NULL,
	terminal_result VARCHAR(32) NOT NULL,
	safe_result_code VARCHAR(128) NOT NULL,
	consumption_content_hash VARCHAR(71) NOT NULL,
	consumed_at VARCHAR(35) NOT NULL,
	payload_json TEXT NOT NULL,
	PRIMARY KEY (challenge_consumption_id),
	CHECK (terminal_result IN ('SUCCEEDED', 'EXPIRED', 'INVALID_SIGNATURE', 'USER_VERIFICATION_ABSENT', 'ORIGIN_RP_MISMATCH', 'BINDING_MISMATCH', 'REPLAY_REJECTED', 'FAILED_CLOSED')),
	UNIQUE (issuer_approval_challenge_id),
	FOREIGN KEY(issuer_approval_challenge_id) REFERENCES issuer_approval_challenges (issuer_approval_challenge_id)
)""",
    ),
    (
        "reviewer_authentication_events",
        """CREATE TABLE reviewer_authentication_events (
	authentication_event_id VARCHAR(128) NOT NULL,
	contract_version VARCHAR(64) NOT NULL,
	issuer_approval_challenge_id VARCHAR(128) NOT NULL,
	challenge_consumption_id VARCHAR(128) NOT NULL,
	reviewer_principal_id VARCHAR(128) NOT NULL,
	reviewer_role VARCHAR(32) NOT NULL,
	webauthn_credential_id VARCHAR(512) NOT NULL,
	credential_id_fingerprint VARCHAR(71) NOT NULL,
	public_key_fingerprint VARCHAR(71) NOT NULL,
	issuer_decision_id VARCHAR(128) NOT NULL,
	authority_bundle_id VARCHAR(128) NOT NULL,
	expected_decision_content_hash VARCHAR(71) NOT NULL,
	expected_bundle_content_hash VARCHAR(71) NOT NULL,
	requested_disposition VARCHAR(16) NOT NULL,
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
	PRIMARY KEY (authentication_event_id),
	FOREIGN KEY(issuer_approval_challenge_id, reviewer_principal_id, reviewer_role, issuer_decision_id, authority_bundle_id, expected_decision_content_hash, expected_bundle_content_hash, requested_disposition) REFERENCES issuer_approval_challenges (issuer_approval_challenge_id, reviewer_principal_id, reviewer_role, issuer_decision_id, authority_bundle_id, expected_decision_content_hash, expected_bundle_content_hash, requested_disposition),
	FOREIGN KEY(webauthn_credential_id, reviewer_principal_id, credential_id_fingerprint, public_key_fingerprint, rp_id, counter_capability) REFERENCES reviewer_webauthn_credentials (webauthn_credential_id, reviewer_principal_id, credential_id_fingerprint, public_key_fingerprint, rp_id, counter_capability),
	CHECK (authentication_result IN ('VERIFIED', 'REJECTED')),
	CHECK (rp_id = 'localhost'),
	CHECK (exact_origin = 'http://localhost:3000'),
	CHECK (user_presence_verified IN (0, 1)),
	CHECK (user_verification_verified IN (0, 1)),
	CHECK (origin_verified IN (0, 1)),
	CHECK (rp_id_hash_verified IN (0, 1)),
	CHECK (signature_verified IN (0, 1)),
	CHECK (counter_capability IN ('SIGN_COUNT_SUPPORTED', 'NO_USABLE_COUNTER')),
	CHECK (previous_sign_count IS NULL OR previous_sign_count >= 0),
	CHECK (asserted_sign_count IS NULL OR asserted_sign_count >= 0),
	CHECK ((counter_capability = 'SIGN_COUNT_SUPPORTED' AND previous_sign_count IS NOT NULL AND asserted_sign_count IS NOT NULL) OR (counter_capability = 'NO_USABLE_COUNTER' AND previous_sign_count IS NULL AND asserted_sign_count IS NULL)),
	CHECK (counter_verified IN (0, 1)),
	CHECK (counter_verified = 0 OR (counter_capability = 'NO_USABLE_COUNTER' OR (counter_capability = 'SIGN_COUNT_SUPPORTED' AND asserted_sign_count > previous_sign_count))),
	CHECK (replay_rejected IN (0, 1)),
	CHECK (authentication_result != 'VERIFIED' OR (user_presence_verified = 1 AND user_verification_verified = 1 AND origin_verified = 1 AND rp_id_hash_verified = 1 AND signature_verified = 1 AND counter_verified = 1 AND replay_rejected = 1)),
	UNIQUE (authentication_event_id, issuer_approval_challenge_id, reviewer_principal_id, reviewer_role, issuer_decision_id, authority_bundle_id, expected_decision_content_hash, expected_bundle_content_hash, requested_disposition, authentication_result, public_key_fingerprint),
	UNIQUE (challenge_consumption_id),
	FOREIGN KEY(challenge_consumption_id) REFERENCES issuer_approval_challenge_consumptions (challenge_consumption_id)
)""",
    ),
    (
        "issuer_approval_events",
        """CREATE TABLE issuer_approval_events (
	issuer_approval_event_id VARCHAR(128) NOT NULL,
	contract_version VARCHAR(64) NOT NULL,
	approval_event_content_hash VARCHAR(71) NOT NULL,
	approval_event_audit_hash VARCHAR(71) NOT NULL,
	issuer_decision_id VARCHAR(128) NOT NULL,
	decision_content_hash VARCHAR(71) NOT NULL,
	authority_bundle_id VARCHAR(128) NOT NULL,
	bundle_content_hash VARCHAR(71) NOT NULL,
	provider_security_identity_id VARCHAR(128) NOT NULL,
	proposed_issuer_id VARCHAR(128) NOT NULL,
	event_state VARCHAR(16) NOT NULL,
	reviewer_principal_id VARCHAR(128) NOT NULL,
	reviewer_role VARCHAR(32) NOT NULL,
	authentication_event_id VARCHAR(128) NOT NULL,
	issuer_approval_challenge_id VARCHAR(128) NOT NULL,
	authentication_result VARCHAR(16) NOT NULL,
	authentication_policy_version VARCHAR(64) NOT NULL,
	credential_public_key_fingerprint VARCHAR(71) NOT NULL,
	structured_reason_code VARCHAR(128) NOT NULL,
	review_note_digest VARCHAR(71) NOT NULL,
	predecessor_approval_event_id VARCHAR(128),
	successor_decision_id VARCHAR(128),
	authenticated_at VARCHAR(35) NOT NULL,
	recorded_at VARCHAR(35) NOT NULL,
	payload_json TEXT NOT NULL,
	PRIMARY KEY (issuer_approval_event_id),
	FOREIGN KEY(issuer_decision_id, authority_bundle_id, decision_content_hash, bundle_content_hash, provider_security_identity_id, proposed_issuer_id) REFERENCES issuer_decisions (issuer_decision_id, authority_bundle_id, decision_content_hash, authority_bundle_content_hash, provider_security_identity_id, proposed_issuer_id),
	FOREIGN KEY(authentication_event_id, issuer_approval_challenge_id, reviewer_principal_id, reviewer_role, issuer_decision_id, authority_bundle_id, decision_content_hash, bundle_content_hash, event_state, authentication_result, credential_public_key_fingerprint) REFERENCES reviewer_authentication_events (authentication_event_id, issuer_approval_challenge_id, reviewer_principal_id, reviewer_role, issuer_decision_id, authority_bundle_id, expected_decision_content_hash, expected_bundle_content_hash, requested_disposition, authentication_result, public_key_fingerprint),
	UNIQUE (authentication_event_id),
	UNIQUE (issuer_approval_event_id, issuer_decision_id, authority_bundle_id, decision_content_hash, bundle_content_hash, provider_security_identity_id, proposed_issuer_id),
	CHECK (event_state IN ('APPROVED', 'REJECTED', 'REVOKED', 'SUPERSEDED')),
	CHECK (reviewer_role = 'LOCAL_DATA_STEWARD'),
	CHECK (authentication_result = 'VERIFIED'),
	FOREIGN KEY(predecessor_approval_event_id) REFERENCES issuer_approval_events (issuer_approval_event_id),
	FOREIGN KEY(successor_decision_id) REFERENCES issuer_decisions (issuer_decision_id)
)""",
    ),
    (
        "issuer_approval_evidence_observations",
        """CREATE TABLE issuer_approval_evidence_observations (
	issuer_approval_event_id VARCHAR(128) NOT NULL,
	authority_evidence_observation_id VARCHAR(128) NOT NULL,
	member_ordinal INTEGER NOT NULL,
	observation_content_hash VARCHAR(71) NOT NULL,
	membership_content_hash VARCHAR(71) NOT NULL,
	payload_json TEXT NOT NULL,
	PRIMARY KEY (issuer_approval_event_id, authority_evidence_observation_id),
	FOREIGN KEY(authority_evidence_observation_id, observation_content_hash) REFERENCES authority_evidence_observations (authority_evidence_observation_id, observation_content_hash),
	CHECK (member_ordinal >= 0),
	FOREIGN KEY(issuer_approval_event_id) REFERENCES issuer_approval_events (issuer_approval_event_id),
	FOREIGN KEY(authority_evidence_observation_id) REFERENCES authority_evidence_observations (authority_evidence_observation_id)
)""",
    ),
    (
        "issuer_authority_links",
        """CREATE TABLE issuer_authority_links (
	issuer_authority_link_id VARCHAR(128) NOT NULL,
	contract_version VARCHAR(64) NOT NULL,
	link_content_hash VARCHAR(71) NOT NULL,
	link_audit_hash VARCHAR(71) NOT NULL,
	provider_security_identity_id VARCHAR(128) NOT NULL,
	issuer_id VARCHAR(128) NOT NULL,
	authority_bundle_id VARCHAR(128) NOT NULL,
	bundle_content_hash VARCHAR(71) NOT NULL,
	issuer_decision_id VARCHAR(128) NOT NULL,
	decision_content_hash VARCHAR(71) NOT NULL,
	approval_event_id VARCHAR(128),
	machine_trigger_decision_id VARCHAR(128),
	link_state VARCHAR(32) NOT NULL,
	security_resolution_state VARCHAR(16) NOT NULL,
	supersedes_link_id VARCHAR(128),
	authority_valid_from DATE,
	authority_valid_to DATE,
	recorded_at VARCHAR(35) NOT NULL,
	payload_json TEXT NOT NULL,
	PRIMARY KEY (issuer_authority_link_id),
	FOREIGN KEY(issuer_decision_id, authority_bundle_id, decision_content_hash, bundle_content_hash, provider_security_identity_id, issuer_id) REFERENCES issuer_decisions (issuer_decision_id, authority_bundle_id, decision_content_hash, authority_bundle_content_hash, provider_security_identity_id, proposed_issuer_id),
	FOREIGN KEY(approval_event_id, issuer_decision_id, authority_bundle_id, decision_content_hash, bundle_content_hash, provider_security_identity_id, issuer_id) REFERENCES issuer_approval_events (issuer_approval_event_id, issuer_decision_id, authority_bundle_id, decision_content_hash, bundle_content_hash, provider_security_identity_id, proposed_issuer_id),
	CHECK (link_state IN ('APPROVED', 'REVIEW_REQUIRED', 'REVOKED', 'SUPERSEDED')),
	CHECK (security_resolution_state = 'UNRESOLVED'),
	CHECK ((link_state = 'REVIEW_REQUIRED' AND approval_event_id IS NULL AND machine_trigger_decision_id IS NOT NULL) OR (link_state IN ('APPROVED', 'REVOKED', 'SUPERSEDED') AND approval_event_id IS NOT NULL AND machine_trigger_decision_id IS NULL)),
	CHECK (authority_valid_to IS NULL OR authority_valid_from IS NULL OR authority_valid_from <= authority_valid_to),
	FOREIGN KEY(provider_security_identity_id) REFERENCES provider_security_identities (provider_security_identity_id),
	FOREIGN KEY(issuer_id) REFERENCES issuers (issuer_id),
	FOREIGN KEY(machine_trigger_decision_id) REFERENCES issuer_decisions (issuer_decision_id),
	FOREIGN KEY(supersedes_link_id) REFERENCES issuer_authority_links (issuer_authority_link_id)
)""",
    ),
    (
        "issuer_authority_link_heads",
        """CREATE TABLE issuer_authority_link_heads (
	provider_security_identity_id VARCHAR(128) NOT NULL,
	issuer_authority_link_id VARCHAR(128) NOT NULL,
	link_state VARCHAR(32) NOT NULL,
	security_resolution_state VARCHAR(16) NOT NULL,
	state_hash VARCHAR(71) NOT NULL,
	previous_state_hash VARCHAR(71),
	projected_at VARCHAR(35) NOT NULL,
	payload_json TEXT NOT NULL,
	PRIMARY KEY (provider_security_identity_id),
	CHECK (link_state IN ('APPROVED', 'REVIEW_REQUIRED', 'REVOKED', 'SUPERSEDED')),
	CHECK (security_resolution_state = 'UNRESOLVED'),
	FOREIGN KEY(provider_security_identity_id) REFERENCES provider_security_identities (provider_security_identity_id),
	UNIQUE (issuer_authority_link_id),
	FOREIGN KEY(issuer_authority_link_id) REFERENCES issuer_authority_links (issuer_authority_link_id)
)""",
    ),
)

_INDEX_DDL: tuple[tuple[str, str], ...] = (
    (
        "ix_authority_bundles_candidate",
        """CREATE INDEX ix_authority_bundles_candidate ON authority_bundles (candidate_identifier_kind, candidate_identifier_value)""",
    ),
    (
        "ix_authority_evidence_applications_candidate_scope",
        """CREATE INDEX ix_authority_evidence_applications_candidate_scope ON authority_evidence_applications (provider_security_identity_id, proposed_issuer_id, authority_scope)""",
    ),
    (
        "ix_authority_evidence_observations_evidence_fetched",
        """CREATE INDEX ix_authority_evidence_observations_evidence_fetched ON authority_evidence_observations (evidence_id, fetched_at)""",
    ),
    (
        "ix_authority_evidence_relations_predecessor",
        """CREATE INDEX ix_authority_evidence_relations_predecessor ON authority_evidence_relations (predecessor_evidence_id)""",
    ),
    (
        "ix_authority_evidence_relations_successor",
        """CREATE INDEX ix_authority_evidence_relations_successor ON authority_evidence_relations (successor_evidence_id)""",
    ),
    (
        "ix_authority_identifier_claims_identifier",
        """CREATE INDEX ix_authority_identifier_claims_identifier ON authority_identifier_claims (identifier_kind, normalized_identifier_value)""",
    ),
    (
        "ix_authority_identifier_claims_provider",
        """CREATE INDEX ix_authority_identifier_claims_provider ON authority_identifier_claims (provider_security_identity_id)""",
    ),
    (
        "uq_issuer_approval_events_initial_disposition",
        """CREATE UNIQUE INDEX uq_issuer_approval_events_initial_disposition ON issuer_approval_events (issuer_decision_id) WHERE predecessor_approval_event_id IS NULL AND event_state IN ('APPROVED', 'REJECTED')""",
    ),
    (
        "uq_issuer_approval_events_supersedes",
        """CREATE UNIQUE INDEX uq_issuer_approval_events_supersedes ON issuer_approval_events (predecessor_approval_event_id) WHERE predecessor_approval_event_id IS NOT NULL""",
    ),
    (
        "uq_issuer_authority_links_provider_root",
        """CREATE UNIQUE INDEX uq_issuer_authority_links_provider_root ON issuer_authority_links (provider_security_identity_id) WHERE supersedes_link_id IS NULL""",
    ),
    (
        "uq_issuer_authority_links_supersedes",
        """CREATE UNIQUE INDEX uq_issuer_authority_links_supersedes ON issuer_authority_links (supersedes_link_id) WHERE supersedes_link_id IS NOT NULL""",
    ),
    (
        "uq_issuer_decisions_bundle_root",
        """CREATE UNIQUE INDEX uq_issuer_decisions_bundle_root ON issuer_decisions (authority_bundle_id) WHERE supersedes_decision_id IS NULL""",
    ),
    (
        "uq_issuer_decisions_supersedes",
        """CREATE UNIQUE INDEX uq_issuer_decisions_supersedes ON issuer_decisions (supersedes_decision_id) WHERE supersedes_decision_id IS NOT NULL""",
    ),
    (
        "uq_reviewer_webauthn_credential_events_supersedes",
        """CREATE UNIQUE INDEX uq_reviewer_webauthn_credential_events_supersedes ON reviewer_webauthn_credential_events (supersedes_credential_event_id) WHERE supersedes_credential_event_id IS NOT NULL""",
    ),
)

_IMMUTABLE_TABLES = tuple(
    name for name, _ddl in _TABLE_DDL if name != "issuer_authority_link_heads"
)
_TABLE_NAMES = tuple(name for name, _ddl in _TABLE_DDL)
_INDEX_NAMES = tuple(name for name, _ddl in _INDEX_DDL)
_TRIGGER_NAMES = tuple(
    f"trg_{table_name}_append_only_{operation.lower()}"
    for table_name in _IMMUTABLE_TABLES
    for operation in ("UPDATE", "DELETE")
)


def _trigger_sql(table_name: str, operation: str) -> str:
    trigger_name = f"trg_{table_name}_append_only_{operation.lower()}"
    message = f"{table_name} is append-only: {operation} forbidden"
    return (
        f"CREATE TRIGGER {trigger_name} BEFORE {operation} ON {table_name} "
        f"BEGIN SELECT RAISE(ABORT, '{message}'); END"
    )


def _sqlite_objects(connection: Connection) -> set[tuple[str, str]]:
    rows = connection.execute(
        sa.text("SELECT type, name FROM sqlite_master WHERE type IN ('table', 'index', 'trigger')")
    ).mappings()
    return {(str(row["type"]), str(row["name"])) for row in rows}


def _target_objects() -> set[tuple[str, str]]:
    return (
        {("table", name) for name in _TABLE_NAMES}
        | {("index", name) for name in _INDEX_NAMES}
        | {("trigger", name) for name in _TRIGGER_NAMES}
    )


def _drop_objects(connection: Connection, statements: Iterable[str]) -> None:
    for statement in statements:
        connection.exec_driver_sql(statement)


def _cleanup_failed_upgrade(connection: Connection) -> None:
    _drop_objects(
        connection,
        (
            *(f"DROP TRIGGER IF EXISTS {name}" for name in reversed(_TRIGGER_NAMES)),
            *(f"DROP INDEX IF EXISTS {name}" for name in reversed(_INDEX_NAMES)),
            *(f"DROP TABLE IF EXISTS {name}" for name in reversed(_TABLE_NAMES)),
        ),
    )


def upgrade() -> None:
    connection = op.get_bind()
    collisions = sorted(_sqlite_objects(connection) & _target_objects())
    if collisions:
        rendered = ", ".join(f"{kind}:{name}" for kind, name in collisions)
        raise RuntimeError("0005 refuses to replace pre-existing authority objects: " + rendered)
    try:
        for _name, statement in _TABLE_DDL:
            op.execute(sa.text(statement))
        for _name, statement in _INDEX_DDL:
            op.execute(sa.text(statement))
        for table_name in _IMMUTABLE_TABLES:
            for operation in ("UPDATE", "DELETE"):
                op.execute(sa.text(_trigger_sql(table_name, operation)))
    except Exception:
        _cleanup_failed_upgrade(connection)
        raise


def downgrade() -> None:
    connection = op.get_bind()
    _cleanup_failed_upgrade(connection)
