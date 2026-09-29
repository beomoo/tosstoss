"""ADR-020 Security storage rows. Integrity is enforced by migration 0008."""

from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from toss_dashboard_api.storage.models import Base


class SecuritySourcePolicyRow(Base):
    __tablename__ = "security_authority_source_policies"

    content_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    audit_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    recorded_at: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    contract_version: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    policy_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    source_namespace: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    authority_classification: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    document_kind: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    subject_role: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    policy_version: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    max_weight: Mapped[int] = mapped_column(Integer, nullable=False, primary_key=False)
    ingestion_mode: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    adapter_version: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    parser_version: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    production_eligible: Mapped[int] = mapped_column(Integer, nullable=False, primary_key=False)
    access_disposition: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    license_disposition: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    origin_mode: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    fixture_taint: Mapped[int] = mapped_column(Integer, nullable=False, primary_key=False)
    test_taint: Mapped[int] = mapped_column(Integer, nullable=False, primary_key=False)
    credential_free_locator_root: Mapped[str] = mapped_column(
        Text, nullable=False, primary_key=False
    )
    predecessor_policy_id: Mapped[str | None] = mapped_column(
        Text, nullable=True, primary_key=False
    )
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)


class SecurityEvidenceRow(Base):
    __tablename__ = "security_authority_evidence"

    content_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    audit_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    recorded_at: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    contract_version: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    evidence_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    source_namespace: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    document_kind: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    accepted_document_identity: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    raw_digest: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    subject_role: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    exact_subject: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    fact_key: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    fact_value: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    origin_mode: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    fixture_taint: Mapped[int] = mapped_column(Integer, nullable=False, primary_key=False)
    test_taint: Mapped[int] = mapped_column(Integer, nullable=False, primary_key=False)
    effective_date: Mapped[str | None] = mapped_column(Text, nullable=True, primary_key=False)
    effective_date_missing_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True, primary_key=False
    )
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)


class SecurityEvidenceObservationRow(Base):
    __tablename__ = "security_authority_evidence_observations"

    content_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    audit_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    recorded_at: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    contract_version: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    observation_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    evidence_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    evidence_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    adapter_version: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    parser_version: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    run_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    retrieved_at: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    source_as_of: Mapped[str | None] = mapped_column(Text, nullable=True, primary_key=False)
    source_as_of_missing_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True, primary_key=False
    )
    access_result: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    raw_digest: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)


class SecurityEvidenceRelationRow(Base):
    __tablename__ = "security_authority_evidence_relations"

    content_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    audit_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    recorded_at: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    contract_version: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    relation_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    prior_evidence_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    prior_evidence_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    successor_evidence_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    successor_evidence_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    relation_kind: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    effective_date: Mapped[str | None] = mapped_column(Text, nullable=True, primary_key=False)
    effective_date_missing_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True, primary_key=False
    )
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)


class SecurityEvidenceApplicationRow(Base):
    __tablename__ = "security_authority_evidence_applications"

    content_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    audit_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    recorded_at: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    provider_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    issuer_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    security_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    contract_version: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    application_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    evidence_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    evidence_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    policy_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    policy_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    source_namespace: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    document_kind: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    subject_role: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    requested_weight: Mapped[int] = mapped_column(Integer, nullable=False, primary_key=False)
    claim_target: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    relation_head_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    fixture_taint: Mapped[int] = mapped_column(Integer, nullable=False, primary_key=False)
    test_taint: Mapped[int] = mapped_column(Integer, nullable=False, primary_key=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)


class SecurityBundleRow(Base):
    __tablename__ = "security_authority_bundles"

    content_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    audit_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    recorded_at: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    provider_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    issuer_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    security_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    contract_version: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    bundle_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    issuer_link_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    issuer_link_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    issuer_link_state: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    issuer_head_state_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    proposed_anchor: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    profile_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    rules_version: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    freshness_version: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    source_policy_set_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    collision_scan_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    membership_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)


class SecurityBundleApplicationRow(Base):
    __tablename__ = "security_authority_bundle_evidence_applications"

    content_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    audit_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    recorded_at: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    provider_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    issuer_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    security_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    contract_version: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    bundle_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    bundle_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    application_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    application_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    member_ordinal: Mapped[int] = mapped_column(Integer, nullable=False, primary_key=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)


class SecurityBundleScopeResultRow(Base):
    __tablename__ = "security_authority_bundle_scope_results"

    content_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    audit_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    recorded_at: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    contract_version: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    bundle_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    bundle_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    result: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    reason_codes: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    owner_application_ids: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)


class SecurityBundleProviderObservationRow(Base):
    __tablename__ = "security_authority_bundle_provider_observations"

    content_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    audit_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    recorded_at: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    contract_version: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    bundle_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    bundle_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    provider_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    observation_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    observation_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    member_ordinal: Mapped[int] = mapped_column(Integer, nullable=False, primary_key=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)


class SecurityIdentifierClaimRow(Base):
    __tablename__ = "security_identifier_claims"

    content_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    audit_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    recorded_at: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    provider_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    issuer_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    security_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    claim_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    application_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    application_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    application_status: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    contract_version: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    identifier_kind: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    identifier_value: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    valid_from: Mapped[str | None] = mapped_column(Text, nullable=True, primary_key=False)
    valid_to: Mapped[str | None] = mapped_column(Text, nullable=True, primary_key=False)
    interval_missing_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True, primary_key=False
    )
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)


class SecurityClassClaimRow(Base):
    __tablename__ = "security_class_claims"

    content_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    audit_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    recorded_at: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    provider_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    issuer_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    security_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    claim_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    application_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    application_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    application_status: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    contract_version: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    instrument_family: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    registered_class_title: Mapped[str | None] = mapped_column(
        Text, nullable=True, primary_key=False
    )
    authority_share_kind: Mapped[str | None] = mapped_column(Text, nullable=True, primary_key=False)
    registered_row_id: Mapped[str | None] = mapped_column(Text, nullable=True, primary_key=False)
    section_12_basis: Mapped[str | None] = mapped_column(Text, nullable=True, primary_key=False)
    missing_reason: Mapped[str | None] = mapped_column(Text, nullable=True, primary_key=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)


class SecurityListingClaimRow(Base):
    __tablename__ = "security_listing_claims"

    content_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    audit_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    recorded_at: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    provider_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    issuer_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    security_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    claim_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    application_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    application_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    application_status: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    contract_version: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    venue: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    market: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    ticker: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    listing_status: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    valid_from: Mapped[str | None] = mapped_column(Text, nullable=True, primary_key=False)
    valid_to: Mapped[str | None] = mapped_column(Text, nullable=True, primary_key=False)
    interval_missing_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True, primary_key=False
    )
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)


class SecurityDecisionRow(Base):
    __tablename__ = "security_decisions"

    content_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    audit_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    recorded_at: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    provider_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    issuer_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    security_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    contract_version: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    decision_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    bundle_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    bundle_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    issuer_link_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    issuer_link_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    issuer_link_state: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    issuer_head_state_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    machine_state: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    reason_codes: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    freshness_result: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    collision_result: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    supersedes_decision_id: Mapped[str | None] = mapped_column(
        Text, nullable=True, primary_key=False
    )
    evaluated_at: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)


class SecurityApprovalChallengeRow(Base):
    __tablename__ = "security_approval_challenges"

    content_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    audit_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    recorded_at: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    provider_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    issuer_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    security_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    decision_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    decision_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    bundle_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    bundle_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    issuer_link_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    issuer_link_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    issuer_link_state: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    issuer_head_state_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    intent_id: Mapped[str | None] = mapped_column(Text, nullable=True, primary_key=False)
    disposition: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    principal_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    role: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    principal_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    os_owner_sid_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    webauthn_credential_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    credential_id_fingerprint: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    public_key_fingerprint: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    expected_head_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    predecessor_approval_event_id: Mapped[str | None] = mapped_column(
        Text, nullable=True, primary_key=False
    )
    predecessor_link_id: Mapped[str | None] = mapped_column(Text, nullable=True, primary_key=False)
    successor_decision_id: Mapped[str | None] = mapped_column(
        Text, nullable=True, primary_key=False
    )
    contract_version: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    challenge_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    challenge_digest: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    issued_at: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    expires_at: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)


class SecurityChallengeConsumptionRow(Base):
    __tablename__ = "security_approval_challenge_consumptions"

    content_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    audit_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    recorded_at: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    contract_version: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    consumption_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    challenge_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    challenge_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    terminal_result: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    safe_result_code: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    consumed_at: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)


class SecurityAuthenticationEventRow(Base):
    __tablename__ = "security_reviewer_authentication_events"

    content_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    audit_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    recorded_at: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    provider_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    issuer_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    security_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    decision_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    decision_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    bundle_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    bundle_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    issuer_link_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    issuer_link_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    issuer_link_state: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    issuer_head_state_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    intent_id: Mapped[str | None] = mapped_column(Text, nullable=True, primary_key=False)
    disposition: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    principal_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    role: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    principal_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    os_owner_sid_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    webauthn_credential_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    credential_id_fingerprint: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    public_key_fingerprint: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    expected_head_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    predecessor_approval_event_id: Mapped[str | None] = mapped_column(
        Text, nullable=True, primary_key=False
    )
    predecessor_link_id: Mapped[str | None] = mapped_column(Text, nullable=True, primary_key=False)
    successor_decision_id: Mapped[str | None] = mapped_column(
        Text, nullable=True, primary_key=False
    )
    contract_version: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    authentication_event_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    challenge_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    challenge_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    consumption_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    consumption_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    consumption_result: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    authentication_result: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    counter_capability: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    previous_sign_count: Mapped[int | None] = mapped_column(
        Integer, nullable=True, primary_key=False
    )
    asserted_sign_count: Mapped[int | None] = mapped_column(
        Integer, nullable=True, primary_key=False
    )
    counter_verified: Mapped[int] = mapped_column(Integer, nullable=False, primary_key=False)
    rp_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    exact_origin: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    authentication_policy_version: Mapped[str] = mapped_column(
        Text, nullable=False, primary_key=False
    )
    client_data_type_verified: Mapped[int] = mapped_column(
        Integer, nullable=False, primary_key=False
    )
    challenge_verified: Mapped[int] = mapped_column(Integer, nullable=False, primary_key=False)
    origin_verified: Mapped[int] = mapped_column(Integer, nullable=False, primary_key=False)
    cross_origin_false_verified: Mapped[int] = mapped_column(
        Integer, nullable=False, primary_key=False
    )
    rp_id_hash_verified: Mapped[int] = mapped_column(Integer, nullable=False, primary_key=False)
    user_presence_verified: Mapped[int] = mapped_column(Integer, nullable=False, primary_key=False)
    user_verification_verified: Mapped[int] = mapped_column(
        Integer, nullable=False, primary_key=False
    )
    credential_id_verified: Mapped[int] = mapped_column(Integer, nullable=False, primary_key=False)
    signature_verified: Mapped[int] = mapped_column(Integer, nullable=False, primary_key=False)
    replay_rejected: Mapped[int] = mapped_column(Integer, nullable=False, primary_key=False)
    authenticated_at: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)


class SecurityApprovalEventRow(Base):
    __tablename__ = "security_approval_events"

    content_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    audit_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    recorded_at: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    provider_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    issuer_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    security_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    decision_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    decision_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    bundle_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    bundle_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    issuer_link_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    issuer_link_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    issuer_link_state: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    issuer_head_state_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    contract_version: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    approval_event_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    authentication_event_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    authentication_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    authentication_result: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    consumption_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    challenge_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    intent_id: Mapped[str | None] = mapped_column(Text, nullable=True, primary_key=False)
    disposition: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    predecessor_approval_event_id: Mapped[str | None] = mapped_column(
        Text, nullable=True, primary_key=False
    )
    pair_id: Mapped[str | None] = mapped_column(Text, nullable=True, primary_key=False)
    successor_decision_id: Mapped[str | None] = mapped_column(
        Text, nullable=True, primary_key=False
    )
    reviewed_at: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)


class SecurityApprovalEvidenceObservationRow(Base):
    __tablename__ = "security_approval_evidence_observations"

    content_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    audit_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    recorded_at: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    contract_version: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    approval_event_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    approval_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    bundle_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    application_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    application_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    evidence_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    evidence_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    observation_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    observation_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    member_ordinal: Mapped[int] = mapped_column(Integer, nullable=False, primary_key=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)


class SecuritySupersessionPairRow(Base):
    __tablename__ = "security_supersession_pairs"

    content_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    audit_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    recorded_at: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    contract_version: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    pair_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    intent_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    provider_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    issuer_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    old_link_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    old_approval_event_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    old_security_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    old_decision_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    old_decision_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    old_bundle_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    old_bundle_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    successor_security_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    successor_decision_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    successor_decision_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    successor_bundle_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    successor_bundle_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    expected_head_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    challenge_a: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    consumption_a: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    authentication_a: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    event_a: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    link_a: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    challenge_b: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    consumption_b: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    authentication_b: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    event_b: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    link_b: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    old_state: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    disposition_a: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    disposition_b: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    terminal_a: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    terminal_b: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)


class SecurityCanonicalSubjectRow(Base):
    __tablename__ = "canonical_security_subjects"

    content_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    audit_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    recorded_at: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    contract_version: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    security_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    issuer_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    founding_anchor: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    anchor_kind: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    anchor_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)


class SecurityAuthorityProfileRow(Base):
    __tablename__ = "security_authority_profiles"

    content_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    audit_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    recorded_at: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    contract_version: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    profile_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    security_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    issuer_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    instrument_family: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    registered_class_title: Mapped[str | None] = mapped_column(
        Text, nullable=True, primary_key=False
    )
    authority_share_kind: Mapped[str | None] = mapped_column(Text, nullable=True, primary_key=False)
    identifier_kind: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    identifier_value: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    venue: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    market: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    valid_from: Mapped[str | None] = mapped_column(Text, nullable=True, primary_key=False)
    valid_to: Mapped[str | None] = mapped_column(Text, nullable=True, primary_key=False)
    missing_reason: Mapped[str | None] = mapped_column(Text, nullable=True, primary_key=False)
    identifier_claim_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    identifier_claim_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    class_claim_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    class_claim_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    listing_claim_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    listing_claim_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)


class SecurityAuthorityLinkRow(Base):
    __tablename__ = "security_authority_links"

    content_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    audit_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    recorded_at: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    provider_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    issuer_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    security_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    decision_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    decision_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    bundle_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    bundle_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    issuer_link_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    issuer_link_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    issuer_link_state: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    issuer_head_state_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    contract_version: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    link_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    profile_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    profile_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    link_state: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    approval_event_id: Mapped[str | None] = mapped_column(Text, nullable=True, primary_key=False)
    approval_hash: Mapped[str | None] = mapped_column(Text, nullable=True, primary_key=False)
    machine_trigger_decision_id: Mapped[str | None] = mapped_column(
        Text, nullable=True, primary_key=False
    )
    supersedes_link_id: Mapped[str | None] = mapped_column(Text, nullable=True, primary_key=False)
    pair_id: Mapped[str | None] = mapped_column(Text, nullable=True, primary_key=False)
    intent_id: Mapped[str | None] = mapped_column(Text, nullable=True, primary_key=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)


class SecurityAuthorityLinkHeadRow(Base):
    __tablename__ = "security_authority_link_heads"

    content_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    audit_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    recorded_at: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    contract_version: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    provider_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    link_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    link_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    issuer_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    security_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    profile_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    link_state: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    state_hash: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
    previous_state_hash: Mapped[str | None] = mapped_column(Text, nullable=True, primary_key=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, primary_key=False)
