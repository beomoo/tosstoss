from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class IssuerRow(Base):
    __tablename__ = "issuers"

    issuer_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    jurisdiction: Mapped[str] = mapped_column(String(8), nullable=False)
    corp_code: Mapped[str | None] = mapped_column(String(32), unique=True)
    cik: Mapped[str | None] = mapped_column(String(32), unique=True)
    normalized_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class SecurityRow(Base):
    __tablename__ = "securities"
    __table_args__ = (UniqueConstraint("market", "exchange", "ticker", "share_class"),)

    security_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    issuer_id: Mapped[str] = mapped_column(ForeignKey("issuers.issuer_id"), nullable=False)
    market: Mapped[str] = mapped_column(String(8), nullable=False)
    exchange: Mapped[str] = mapped_column(String(32), nullable=False)
    ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    share_class: Mapped[str] = mapped_column(String(32), nullable=False)
    normalized_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class SourceRecordRow(Base):
    __tablename__ = "source_records"
    __table_args__ = (UniqueConstraint("source_system", "source_type", "external_id"),)

    source_record_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    source_system: Mapped[str] = mapped_column(String(64), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    supersedes_id: Mapped[str | None] = mapped_column(ForeignKey("source_records.source_record_id"))
    raw_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    normalized_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class DataQualityStatusRow(Base):
    __tablename__ = "data_quality_statuses"
    __table_args__ = (UniqueConstraint("issuer_id", "source_system", "dataset"),)

    quality_status_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    issuer_id: Mapped[str] = mapped_column(ForeignKey("issuers.issuer_id"), nullable=False)
    source_system: Mapped[str] = mapped_column(String(64), nullable=False)
    dataset: Mapped[str] = mapped_column(String(64), nullable=False)
    normalized_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class FixtureImportRunRow(Base):
    __tablename__ = "fixture_import_runs"

    import_run_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    manifest_digest: Mapped[str] = mapped_column(String(71), unique=True, nullable=False)
    fixture_version: Mapped[str] = mapped_column(String(32), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CanonicalRequestRow(Base):
    __tablename__ = "canonical_requests"

    canonical_request_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    method: Mapped[str] = mapped_column(String(8), nullable=False)
    path_template: Mapped[str] = mapped_column(String(256), nullable=False)
    canonical_query_json: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_query_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    provider_contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class ProviderRawManifestRow(Base):
    __tablename__ = "provider_raw_manifests"
    __table_args__ = (
        UniqueConstraint("canonical_request_id", "http_status", "raw_content_hash"),
        CheckConstraint("http_status >= 100 AND http_status <= 599"),
    )

    raw_response_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    canonical_request_id: Mapped[str] = mapped_column(
        ForeignKey("canonical_requests.canonical_request_id"), nullable=False
    )
    http_status: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    raw_storage_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    fetched_at: Mapped[str] = mapped_column(String(35), nullable=False)
    response_metadata_json: Mapped[str] = mapped_column(Text, nullable=False)
    provider_contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class ProviderSourceVersionRow(Base):
    __tablename__ = "provider_source_versions"
    __table_args__ = (
        UniqueConstraint(
            "canonical_request_id",
            "http_status",
            "raw_content_hash",
            "provider_contract_version",
        ),
        Index(
            "uq_provider_source_versions_original_root",
            "canonical_request_id",
            unique=True,
            sqlite_where=text("revision_status = 'ORIGINAL'"),
        ),
        Index(
            "uq_provider_source_versions_supersedes",
            "supersedes_id",
            unique=True,
            sqlite_where=text("supersedes_id IS NOT NULL"),
        ),
    )

    source_version_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    canonical_request_id: Mapped[str] = mapped_column(
        ForeignKey("canonical_requests.canonical_request_id"), nullable=False
    )
    raw_response_id: Mapped[str] = mapped_column(
        ForeignKey("provider_raw_manifests.raw_response_id"), nullable=False
    )
    dataset: Mapped[str] = mapped_column(String(64), nullable=False)
    http_status: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    provider_contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    revision_status: Mapped[str] = mapped_column(String(32), nullable=False)
    supersedes_id: Mapped[str | None] = mapped_column(
        ForeignKey("provider_source_versions.source_version_id")
    )
    normalized_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class CollectionAttemptRow(Base):
    __tablename__ = "collection_attempts"
    __table_args__ = (
        CheckConstraint("records_received >= 0"),
        CheckConstraint("records_rejected >= 0"),
    )

    attempt_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    dataset: Mapped[str] = mapped_column(String(64), nullable=False)
    canonical_request_id: Mapped[str | None] = mapped_column(
        ForeignKey("canonical_requests.canonical_request_id")
    )
    started_at: Mapped[str] = mapped_column(String(35), nullable=False)
    finished_at: Mapped[str | None] = mapped_column(String(35))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    records_received: Mapped[int] = mapped_column(Integer, nullable=False)
    records_rejected: Mapped[int] = mapped_column(Integer, nullable=False)
    safe_result_code: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class ProviderAuditEventRow(Base):
    __tablename__ = "provider_audit_events"
    __table_args__ = (CheckConstraint("record_count >= 0"),)

    audit_event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    attempt_id: Mapped[str] = mapped_column(
        ForeignKey("collection_attempts.attempt_id"), nullable=False
    )
    source_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("provider_source_versions.source_version_id")
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    safe_status: Mapped[str] = mapped_column(String(64), nullable=False)
    record_count: Mapped[int] = mapped_column(Integer, nullable=False)
    occurred_at: Mapped[str] = mapped_column(String(35), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class ProviderSecurityIdentityRow(Base):
    __tablename__ = "provider_security_identities"
    __table_args__ = (UniqueConstraint("provider", "allocation_anchor_hash"),)

    provider_security_identity_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    market: Mapped[str] = mapped_column(String(8), nullable=False)
    allocation_anchor_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    identity_state: Mapped[str] = mapped_column(String(32), nullable=False)
    mapping_status: Mapped[str] = mapped_column(String(32), nullable=False)
    first_source_version_id: Mapped[str] = mapped_column(
        ForeignKey("provider_source_versions.source_version_id"), nullable=False
    )
    latest_source_version_id: Mapped[str] = mapped_column(
        ForeignKey("provider_source_versions.source_version_id"), nullable=False
    )
    provider_contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class ProviderIdentifierHistoryRow(Base):
    __tablename__ = "provider_identifier_history"
    __table_args__ = (
        UniqueConstraint(
            "provider_security_identity_id",
            "identifier_kind",
            "identifier_value",
            "source_version_id",
        ),
        CheckConstraint("valid_to IS NULL OR valid_from IS NULL OR valid_from <= valid_to"),
    )

    identifier_history_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    provider_security_identity_id: Mapped[str] = mapped_column(
        ForeignKey("provider_security_identities.provider_security_identity_id"), nullable=False
    )
    identifier_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    identifier_value: Mapped[str] = mapped_column(String(128), nullable=False)
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)
    source_version_id: Mapped[str] = mapped_column(
        ForeignKey("provider_source_versions.source_version_id"), nullable=False
    )
    revision_reason: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class ProviderIdentityMappingRow(Base):
    __tablename__ = "provider_identity_mappings"
    __table_args__ = (
        CheckConstraint(
            "mapping_status != 'VERIFIED' OR "
            "(issuer_id IS NOT NULL AND security_id IS NOT NULL AND approved_at IS NOT NULL)"
        ),
        CheckConstraint("valid_to IS NULL OR valid_from IS NULL OR valid_from <= valid_to"),
        Index(
            "uq_provider_identity_mappings_current_verified",
            "provider_security_identity_id",
            unique=True,
            sqlite_where=text("mapping_status = 'VERIFIED' AND valid_to IS NULL"),
        ),
    )

    mapping_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    provider_security_identity_id: Mapped[str] = mapped_column(
        ForeignKey("provider_security_identities.provider_security_identity_id"), nullable=False
    )
    issuer_id: Mapped[str | None] = mapped_column(ForeignKey("issuers.issuer_id"))
    security_id: Mapped[str | None] = mapped_column(ForeignKey("securities.security_id"))
    mapping_status: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_source_version_id: Mapped[str] = mapped_column(
        ForeignKey("provider_source_versions.source_version_id"), nullable=False
    )
    approved_at: Mapped[str | None] = mapped_column(String(35))
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)
    provider_contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class ProviderLatestPointerRow(Base):
    __tablename__ = "provider_latest_pointers"
    __table_args__ = (UniqueConstraint("dataset", "provider_security_identity_id"),)

    latest_pointer_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    dataset: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_security_identity_id: Mapped[str] = mapped_column(
        ForeignKey("provider_security_identities.provider_security_identity_id"), nullable=False
    )
    normalized_record_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_version_id: Mapped[str] = mapped_column(
        ForeignKey("provider_source_versions.source_version_id"), nullable=False
    )
    accepted_observed_at: Mapped[str | None] = mapped_column(String(35))
    accepted_observed_date: Mapped[date | None] = mapped_column(Date)
    state_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    provider_contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class ProviderSecurityMasterRecordRow(Base):
    __tablename__ = "provider_security_master_records"
    __table_args__ = (UniqueConstraint("normalized_content_hash"),)

    normalized_record_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    market: Mapped[str] = mapped_column(String(8), nullable=False)
    provider_listing_market: Mapped[str] = mapped_column(String(32), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    normalized_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    provider_contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class ProviderSecurityMasterObservationRow(Base):
    __tablename__ = "provider_security_master_observations"
    __table_args__ = (
        UniqueConstraint(
            "source_version_id",
            "symbol",
            "staging_state",
            "reconciliation_outcome",
        ),
    )

    observation_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    source_version_id: Mapped[str] = mapped_column(
        ForeignKey("provider_source_versions.source_version_id"), nullable=False
    )
    normalized_record_id: Mapped[str | None] = mapped_column(
        ForeignKey("provider_security_master_records.normalized_record_id")
    )
    provider_security_identity_id: Mapped[str | None] = mapped_column(
        ForeignKey("provider_security_identities.provider_security_identity_id")
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    market: Mapped[str] = mapped_column(String(8), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    staging_state: Mapped[str] = mapped_column(String(32), nullable=False)
    reconciliation_outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    eligible_for_mapping: Mapped[int] = mapped_column(Integer, nullable=False)
    provider_contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class ProviderIdentityStateEventRow(Base):
    __tablename__ = "provider_identity_state_events"
    __table_args__ = (
        UniqueConstraint(
            "provider_security_identity_id",
            "source_version_id",
            "identity_state",
            "staging_state",
            "reason_code",
        ),
    )

    state_event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    provider_security_identity_id: Mapped[str] = mapped_column(
        ForeignKey("provider_security_identities.provider_security_identity_id"), nullable=False
    )
    source_version_id: Mapped[str] = mapped_column(
        ForeignKey("provider_source_versions.source_version_id"), nullable=False
    )
    identity_state: Mapped[str] = mapped_column(String(32), nullable=False)
    staging_state: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class ProviderDetailBatchResultRow(Base):
    __tablename__ = "provider_detail_batch_results"

    batch_result_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    source_version_id: Mapped[str] = mapped_column(
        ForeignKey("provider_source_versions.source_version_id"), unique=True, nullable=False
    )
    requested_count: Mapped[int] = mapped_column(Integer, nullable=False)
    received_count: Mapped[int] = mapped_column(Integer, nullable=False)
    missing_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class AuthoritySourcePolicyRow(Base):
    __tablename__ = "authority_source_policies"
    __table_args__ = (
        UniqueConstraint("authority_source_policy_id", "policy_content_hash"),
        CheckConstraint("maximum_issuer_authority_weight IN ('ZERO', 'SUPPORTING', 'DECISIVE')"),
        CheckConstraint(
            "ingestion_mode IN "
            "('AUTOMATED_OFFICIAL_PUBLIC', 'HUMAN_ASSISTED_VERIFIED_DOCUMENT', "
            "'PROVENANCE_ONLY', 'TEST_ISOLATED_ONLY')"
        ),
        CheckConstraint("production_authority_eligible IN (0, 1)"),
        CheckConstraint("permanent_fixture_test_taint IN (0, 1)"),
        CheckConstraint(
            "NOT (production_authority_eligible = 1 AND permanent_fixture_test_taint = 1)"
        ),
        CheckConstraint(
            "permanent_fixture_test_taint = 0 OR maximum_issuer_authority_weight = 'ZERO'"
        ),
        CheckConstraint(
            "production_authority_eligible = 0 "
            "OR (instr(source_namespace, '*') = 0 "
            "AND instr(source_namespace, '?') = 0)"
        ),
    )

    authority_source_policy_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    source_namespace: Mapped[str] = mapped_column(String(128), nullable=False)
    field_owner: Mapped[str] = mapped_column(String(256), nullable=False)
    authority_classification: Mapped[str] = mapped_column(String(64), nullable=False)
    allowed_document_kinds_json: Mapped[str] = mapped_column(Text, nullable=False)
    credential_free_locator_roots_json: Mapped[str] = mapped_column(Text, nullable=False)
    allowed_authority_scopes_json: Mapped[str] = mapped_column(Text, nullable=False)
    allowed_subject_roles_json: Mapped[str] = mapped_column(Text, nullable=False)
    scope_role_weights_json: Mapped[str] = mapped_column(Text, nullable=False)
    maximum_issuer_authority_weight: Mapped[str] = mapped_column(String(16), nullable=False)
    ingestion_mode: Mapped[str] = mapped_column(String(64), nullable=False)
    admitted_adapter_contract_versions_json: Mapped[str] = mapped_column(Text, nullable=False)
    admitted_parser_contract_versions_json: Mapped[str] = mapped_column(Text, nullable=False)
    production_authority_eligible: Mapped[int] = mapped_column(Integer, nullable=False)
    required_access_disposition: Mapped[str] = mapped_column(String(32), nullable=False)
    required_license_disposition: Mapped[str] = mapped_column(String(32), nullable=False)
    allowed_origin_data_modes_json: Mapped[str] = mapped_column(Text, nullable=False)
    permanent_fixture_test_taint: Mapped[int] = mapped_column(Integer, nullable=False)
    predecessor_policy_id: Mapped[str | None] = mapped_column(
        ForeignKey("authority_source_policies.authority_source_policy_id")
    )
    policy_effective_at: Mapped[str | None] = mapped_column(String(35))
    registered_at: Mapped[str] = mapped_column(String(35), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class AuthorityEvidenceRow(Base):
    __tablename__ = "authority_evidence"
    __table_args__ = (
        UniqueConstraint(
            "evidence_id",
            "evidence_content_hash",
            "authority_source_policy_id",
            "authority_scope",
            "policy_maximum_issuer_authority_weight",
        ),
        UniqueConstraint("evidence_content_hash"),
        UniqueConstraint("evidence_provenance_hash"),
        CheckConstraint(
            "policy_maximum_issuer_authority_weight IN ('ZERO', 'SUPPORTING', 'DECISIVE')"
        ),
        CheckConstraint("origin_data_mode IN ('PRODUCTION_AUTHORITY', 'TEST_ONLY')"),
        CheckConstraint("lineage_tainted IN (0, 1)"),
        CheckConstraint("lineage_ancestor_tainted IN (0, 1)"),
        CheckConstraint("lineage_tainted = 0 OR policy_maximum_issuer_authority_weight = 'ZERO'"),
        CheckConstraint(
            "subject_role NOT IN ('SEC_LOGIN_CIK', 'SEC_FILING_AGENT') "
            "OR (authority_scope = 'SUBMISSION_PROVENANCE' "
            "AND evidence_kind = 'PROVENANCE_ONLY' "
            "AND policy_maximum_issuer_authority_weight = 'ZERO')"
        ),
        CheckConstraint("authority_effective_at IS NULL OR authority_effective_date IS NULL"),
    )

    evidence_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    evidence_provenance_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    authority_source_policy_id: Mapped[str] = mapped_column(
        ForeignKey("authority_source_policies.authority_source_policy_id"),
        nullable=False,
    )
    authority_source_identifier: Mapped[str] = mapped_column(String(128), nullable=False)
    authority_classification: Mapped[str] = mapped_column(String(64), nullable=False)
    authority_source_locator: Mapped[str] = mapped_column(Text, nullable=False)
    authority_document_reference: Mapped[str] = mapped_column(String(512), nullable=False)
    source_document_kind: Mapped[str] = mapped_column(String(128), nullable=False)
    authority_external_key: Mapped[str] = mapped_column(String(512), nullable=False)
    authority_source_document_id: Mapped[str] = mapped_column(String(128), nullable=False)
    raw_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    parser_contract_version: Mapped[str] = mapped_column(String(128), nullable=False)
    evidence_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    authority_scope: Mapped[str] = mapped_column(String(64), nullable=False)
    subject_role: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_maximum_issuer_authority_weight: Mapped[str] = mapped_column(String(16), nullable=False)
    claim_field: Mapped[str] = mapped_column(String(256), nullable=False)
    raw_claim_value_json: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_claim_value_json: Mapped[str] = mapped_column(Text, nullable=False)
    authority_published_at: Mapped[str | None] = mapped_column(String(35))
    authority_accepted_at: Mapped[str | None] = mapped_column(String(35))
    authority_as_of_date: Mapped[date | None] = mapped_column(Date)
    authority_effective_at: Mapped[str | None] = mapped_column(String(35))
    authority_effective_date: Mapped[date | None] = mapped_column(Date)
    authority_time_missing_reasons_json: Mapped[str] = mapped_column(Text, nullable=False)
    access_disposition: Mapped[str] = mapped_column(String(32), nullable=False)
    license_disposition: Mapped[str] = mapped_column(String(32), nullable=False)
    origin_data_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    origin_adapter_class: Mapped[str] = mapped_column(String(128), nullable=False)
    origin_source_system: Mapped[str | None] = mapped_column(String(128))
    lineage_tainted: Mapped[int] = mapped_column(Integer, nullable=False)
    lineage_ancestor_tainted: Mapped[int] = mapped_column(Integer, nullable=False)
    lineage_ancestor_hashes_json: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class AuthorityEvidenceObservationRow(Base):
    __tablename__ = "authority_evidence_observations"
    __table_args__ = (
        UniqueConstraint("observation_content_hash"),
        UniqueConstraint(
            "authority_evidence_observation_id",
            "observation_content_hash",
        ),
        Index("ix_authority_evidence_observations_evidence_fetched", "evidence_id", "fetched_at"),
    )

    authority_evidence_observation_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    observation_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    evidence_id: Mapped[str] = mapped_column(
        ForeignKey("authority_evidence.evidence_id"), nullable=False
    )
    fetched_at: Mapped[str] = mapped_column(String(35), nullable=False)
    raw_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    authority_source_locator: Mapped[str] = mapped_column(Text, nullable=False)
    authority_document_reference: Mapped[str] = mapped_column(String(512), nullable=False)
    raw_storage_reference: Mapped[str] = mapped_column(String(128), nullable=False)
    retrieval_status: Mapped[str] = mapped_column(String(32), nullable=False)
    secret_free_retrieval_fingerprint: Mapped[str] = mapped_column(String(71), nullable=False)
    safe_status_code: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class AuthorityEvidenceRelationRow(Base):
    __tablename__ = "authority_evidence_relations"
    __table_args__ = (
        CheckConstraint("predecessor_evidence_id != successor_evidence_id"),
        CheckConstraint("relation_type IN ('CORRECTS', 'REVOKES', 'SUPERSEDES')"),
        CheckConstraint("authority_effective_at IS NULL OR authority_effective_date IS NULL"),
        Index(
            "ix_authority_evidence_relations_predecessor",
            "predecessor_evidence_id",
        ),
        Index("ix_authority_evidence_relations_successor", "successor_evidence_id"),
    )

    authority_evidence_relation_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    relation_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    predecessor_evidence_id: Mapped[str] = mapped_column(
        ForeignKey("authority_evidence.evidence_id"), nullable=False
    )
    successor_evidence_id: Mapped[str] = mapped_column(
        ForeignKey("authority_evidence.evidence_id"), nullable=False
    )
    relation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    authority_effective_at: Mapped[str | None] = mapped_column(String(35))
    authority_effective_date: Mapped[date | None] = mapped_column(Date)
    authority_effective_missing_reason: Mapped[str | None] = mapped_column(String(64))
    recorded_at: Mapped[str] = mapped_column(String(35), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class AuthorityEvidenceApplicationRow(Base):
    __tablename__ = "authority_evidence_applications"
    __table_args__ = (
        ForeignKeyConstraint(
            [
                "evidence_id",
                "evidence_content_hash",
                "authority_source_policy_id",
                "authority_scope",
                "policy_maximum_issuer_authority_weight",
            ],
            [
                "authority_evidence.evidence_id",
                "authority_evidence.evidence_content_hash",
                "authority_evidence.authority_source_policy_id",
                "authority_evidence.authority_scope",
                "authority_evidence.policy_maximum_issuer_authority_weight",
            ],
        ),
        ForeignKeyConstraint(
            ["authority_source_policy_id", "authority_source_policy_content_hash"],
            [
                "authority_source_policies.authority_source_policy_id",
                "authority_source_policies.policy_content_hash",
            ],
        ),
        UniqueConstraint(
            "evidence_application_id",
            "application_content_hash",
            "evidence_id",
            "evidence_content_hash",
            "authority_source_policy_id",
            "authority_source_policy_content_hash",
            "provider_security_identity_id",
            "proposed_issuer_id",
            "candidate_fingerprint",
            "authority_scope",
            "application_status",
            "effective_issuer_authority_weight",
        ),
        UniqueConstraint(
            "evidence_application_id",
            "application_content_hash",
            "evidence_id",
            "evidence_content_hash",
            "authority_source_policy_id",
            "authority_source_policy_content_hash",
            "provider_security_identity_id",
            "proposed_issuer_id",
            "candidate_fingerprint",
            "authority_scope",
        ),
        UniqueConstraint("application_content_hash"),
        CheckConstraint("effective_issuer_authority_weight IN ('ZERO', 'SUPPORTING', 'DECISIVE')"),
        CheckConstraint(
            "policy_maximum_issuer_authority_weight IN ('ZERO', 'SUPPORTING', 'DECISIVE')"
        ),
        CheckConstraint("production_authority_admitted IN (0, 1)"),
        CheckConstraint("lineage_tainted IN (0, 1)"),
        CheckConstraint(
            "lineage_tainted = 0 OR "
            "(production_authority_admitted = 0 "
            "AND effective_issuer_authority_weight = 'ZERO')"
        ),
        CheckConstraint(
            "production_authority_admitted = 1 OR effective_issuer_authority_weight = 'ZERO'"
        ),
        CheckConstraint(
            "(application_status = 'APPLIED_DECISIVE' "
            "AND effective_issuer_authority_weight = 'DECISIVE') "
            "OR (application_status = 'APPLIED_SUPPORTING' "
            "AND effective_issuer_authority_weight = 'SUPPORTING') "
            "OR (application_status NOT IN "
            "('APPLIED_DECISIVE', 'APPLIED_SUPPORTING') "
            "AND effective_issuer_authority_weight = 'ZERO')"
        ),
        Index(
            "ix_authority_evidence_applications_candidate_scope",
            "provider_security_identity_id",
            "proposed_issuer_id",
            "authority_scope",
        ),
    )

    evidence_application_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    application_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    evidence_id: Mapped[str] = mapped_column(String(128), nullable=False)
    evidence_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    provider_security_identity_id: Mapped[str] = mapped_column(
        ForeignKey("provider_security_identities.provider_security_identity_id"),
        nullable=False,
    )
    provider_observation_ids_json: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_issuer_id: Mapped[str] = mapped_column(String(128), nullable=False)
    candidate_fingerprint: Mapped[str] = mapped_column(String(71), nullable=False)
    authority_scope: Mapped[str] = mapped_column(String(64), nullable=False)
    claim_target_field: Mapped[str] = mapped_column(String(256), nullable=False)
    authority_source_policy_id: Mapped[str] = mapped_column(String(128), nullable=False)
    authority_source_policy_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    policy_maximum_issuer_authority_weight: Mapped[str] = mapped_column(String(16), nullable=False)
    application_status: Mapped[str] = mapped_column(String(64), nullable=False)
    effective_issuer_authority_weight: Mapped[str] = mapped_column(String(16), nullable=False)
    reason_codes_json: Mapped[str] = mapped_column(Text, nullable=False)
    authority_relation_head_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    application_rule_version: Mapped[str] = mapped_column(String(64), nullable=False)
    production_authority_admitted: Mapped[int] = mapped_column(Integer, nullable=False)
    lineage_tainted: Mapped[int] = mapped_column(Integer, nullable=False)
    evaluated_at: Mapped[str] = mapped_column(String(35), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class AuthorityBundleRow(Base):
    __tablename__ = "authority_bundles"
    __table_args__ = (
        UniqueConstraint(
            "authority_bundle_id",
            "bundle_content_hash",
            "provider_security_identity_id",
            "proposed_issuer_id",
            "candidate_fingerprint",
        ),
        UniqueConstraint(
            "authority_bundle_id",
            "bundle_content_hash",
            "provider_security_identity_id",
            "proposed_issuer_id",
        ),
        UniqueConstraint("bundle_content_hash"),
        CheckConstraint("bundle_origin_data_mode IN ('PRODUCTION_AUTHORITY', 'TEST_ONLY')"),
        CheckConstraint(
            "(candidate_jurisdiction = 'KR' "
            "AND candidate_identifier_kind = 'DART_CORP_CODE' "
            "AND length(candidate_identifier_value) = 8 "
            "AND candidate_identifier_value NOT GLOB '*[^0-9]*') "
            "OR (candidate_jurisdiction = 'US' "
            "AND candidate_identifier_kind = 'SEC_REGISTRANT_CIK' "
            "AND length(candidate_identifier_value) = 10 "
            "AND candidate_identifier_value NOT GLOB '*[^0-9]*')"
        ),
        CheckConstraint(
            "legal_jurisdiction_result IN ('ESTABLISHED', 'UNRESOLVED', 'UNSUPPORTED_BY_CONTRACT')"
        ),
        CheckConstraint("collision_scan_result IN ('CLEAR', 'CONFLICT')"),
        Index(
            "ix_authority_bundles_candidate",
            "candidate_identifier_kind",
            "candidate_identifier_value",
        ),
    )

    authority_bundle_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    bundle_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    bundle_origin_data_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_security_identity_id: Mapped[str] = mapped_column(
        ForeignKey("provider_security_identities.provider_security_identity_id"),
        nullable=False,
    )
    candidate_jurisdiction: Mapped[str] = mapped_column(String(8), nullable=False)
    candidate_identifier_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    candidate_identifier_value: Mapped[str] = mapped_column(String(10), nullable=False)
    proposed_issuer_anchor: Mapped[str] = mapped_column(String(256), nullable=False)
    proposed_issuer_id: Mapped[str] = mapped_column(String(128), nullable=False)
    candidate_fingerprint: Mapped[str] = mapped_column(String(71), nullable=False)
    legal_jurisdiction_result: Mapped[str] = mapped_column(String(32), nullable=False)
    collision_scan_result: Mapped[str] = mapped_column(String(16), nullable=False)
    collision_claim_candidate_fingerprints_json: Mapped[str] = mapped_column(Text, nullable=False)
    decision_rule_version: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_application_set_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    source_policy_set_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    provider_lineage_set_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    collision_scan_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    built_at: Mapped[str] = mapped_column(String(35), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class AuthorityBundleEvidenceApplicationRow(Base):
    __tablename__ = "authority_bundle_evidence_applications"
    __table_args__ = (
        ForeignKeyConstraint(
            [
                "authority_bundle_id",
                "bundle_content_hash",
                "provider_security_identity_id",
                "proposed_issuer_id",
                "candidate_fingerprint",
            ],
            [
                "authority_bundles.authority_bundle_id",
                "authority_bundles.bundle_content_hash",
                "authority_bundles.provider_security_identity_id",
                "authority_bundles.proposed_issuer_id",
                "authority_bundles.candidate_fingerprint",
            ],
        ),
        ForeignKeyConstraint(
            [
                "evidence_application_id",
                "application_content_hash",
                "evidence_id",
                "evidence_content_hash",
                "authority_source_policy_id",
                "authority_source_policy_content_hash",
                "provider_security_identity_id",
                "proposed_issuer_id",
                "candidate_fingerprint",
                "authority_scope",
                "application_status",
                "effective_issuer_authority_weight",
            ],
            [
                "authority_evidence_applications.evidence_application_id",
                "authority_evidence_applications.application_content_hash",
                "authority_evidence_applications.evidence_id",
                "authority_evidence_applications.evidence_content_hash",
                "authority_evidence_applications.authority_source_policy_id",
                "authority_evidence_applications.authority_source_policy_content_hash",
                "authority_evidence_applications.provider_security_identity_id",
                "authority_evidence_applications.proposed_issuer_id",
                "authority_evidence_applications.candidate_fingerprint",
                "authority_evidence_applications.authority_scope",
                "authority_evidence_applications.application_status",
                "authority_evidence_applications.effective_issuer_authority_weight",
            ],
        ),
        UniqueConstraint("authority_bundle_id", "member_ordinal"),
        CheckConstraint("member_ordinal >= 0"),
    )

    authority_bundle_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    evidence_application_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    member_ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    bundle_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    application_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    evidence_id: Mapped[str] = mapped_column(String(128), nullable=False)
    evidence_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    authority_source_policy_id: Mapped[str] = mapped_column(String(128), nullable=False)
    authority_source_policy_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    provider_security_identity_id: Mapped[str] = mapped_column(String(128), nullable=False)
    proposed_issuer_id: Mapped[str] = mapped_column(String(128), nullable=False)
    candidate_fingerprint: Mapped[str] = mapped_column(String(71), nullable=False)
    authority_scope: Mapped[str] = mapped_column(String(64), nullable=False)
    application_status: Mapped[str] = mapped_column(String(64), nullable=False)
    effective_issuer_authority_weight: Mapped[str] = mapped_column(String(16), nullable=False)
    membership_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class AuthorityBundleScopeResultRow(Base):
    __tablename__ = "authority_bundle_scope_results"
    __table_args__ = (
        ForeignKeyConstraint(
            [
                "authority_bundle_id",
                "bundle_content_hash",
                "provider_security_identity_id",
                "proposed_issuer_id",
                "candidate_fingerprint",
            ],
            [
                "authority_bundles.authority_bundle_id",
                "authority_bundles.bundle_content_hash",
                "authority_bundles.provider_security_identity_id",
                "authority_bundles.proposed_issuer_id",
                "authority_bundles.candidate_fingerprint",
            ],
        ),
        CheckConstraint(
            "scope_status IN "
            "('SATISFIED', 'MISSING', 'CONFLICT', 'STALE', "
            "'UNSUPPORTED', 'UNUSABLE')"
        ),
    )

    authority_bundle_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    authority_scope: Mapped[str] = mapped_column(String(64), primary_key=True)
    bundle_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    provider_security_identity_id: Mapped[str] = mapped_column(String(128), nullable=False)
    proposed_issuer_id: Mapped[str] = mapped_column(String(128), nullable=False)
    candidate_fingerprint: Mapped[str] = mapped_column(String(71), nullable=False)
    scope_status: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_codes_json: Mapped[str] = mapped_column(Text, nullable=False)
    scope_result_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class AuthorityBundleProviderObservationRow(Base):
    __tablename__ = "authority_bundle_provider_observations"
    __table_args__ = (
        ForeignKeyConstraint(
            [
                "authority_bundle_id",
                "bundle_content_hash",
                "provider_security_identity_id",
                "proposed_issuer_id",
                "candidate_fingerprint",
            ],
            [
                "authority_bundles.authority_bundle_id",
                "authority_bundles.bundle_content_hash",
                "authority_bundles.provider_security_identity_id",
                "authority_bundles.proposed_issuer_id",
                "authority_bundles.candidate_fingerprint",
            ],
        ),
        UniqueConstraint("authority_bundle_id", "member_ordinal"),
        CheckConstraint("member_ordinal >= 0"),
    )

    authority_bundle_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    provider_observation_id: Mapped[str] = mapped_column(
        ForeignKey("provider_security_master_observations.observation_id"),
        primary_key=True,
    )
    member_ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    bundle_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    provider_security_identity_id: Mapped[str] = mapped_column(String(128), nullable=False)
    proposed_issuer_id: Mapped[str] = mapped_column(String(128), nullable=False)
    candidate_fingerprint: Mapped[str] = mapped_column(String(71), nullable=False)
    membership_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class AuthorityIdentifierClaimRow(Base):
    __tablename__ = "authority_identifier_claims"
    __table_args__ = (
        ForeignKeyConstraint(
            [
                "evidence_application_id",
                "application_content_hash",
                "evidence_id",
                "evidence_content_hash",
                "authority_source_policy_id",
                "authority_source_policy_content_hash",
                "provider_security_identity_id",
                "proposed_issuer_id",
                "candidate_fingerprint",
                "claim_scope",
            ],
            [
                "authority_evidence_applications.evidence_application_id",
                "authority_evidence_applications.application_content_hash",
                "authority_evidence_applications.evidence_id",
                "authority_evidence_applications.evidence_content_hash",
                "authority_evidence_applications.authority_source_policy_id",
                "authority_evidence_applications.authority_source_policy_content_hash",
                "authority_evidence_applications.provider_security_identity_id",
                "authority_evidence_applications.proposed_issuer_id",
                "authority_evidence_applications.candidate_fingerprint",
                "authority_evidence_applications.authority_scope",
            ],
        ),
        CheckConstraint(
            "(candidate_jurisdiction = 'KR' "
            "AND identifier_kind = 'DART_CORP_CODE' "
            "AND length(normalized_identifier_value) = 8 "
            "AND normalized_identifier_value NOT GLOB '*[^0-9]*') "
            "OR (candidate_jurisdiction = 'US' "
            "AND identifier_kind = 'SEC_REGISTRANT_CIK' "
            "AND length(normalized_identifier_value) = 10 "
            "AND normalized_identifier_value NOT GLOB '*[^0-9]*')"
        ),
        Index(
            "ix_authority_identifier_claims_identifier",
            "identifier_kind",
            "normalized_identifier_value",
        ),
        Index(
            "ix_authority_identifier_claims_provider",
            "provider_security_identity_id",
        ),
    )

    authority_identifier_claim_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    claim_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    identifier_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    normalized_identifier_value: Mapped[str] = mapped_column(String(10), nullable=False)
    candidate_jurisdiction: Mapped[str] = mapped_column(String(8), nullable=False)
    proposed_issuer_id: Mapped[str] = mapped_column(String(128), nullable=False)
    candidate_fingerprint: Mapped[str] = mapped_column(String(71), nullable=False)
    provider_security_identity_id: Mapped[str] = mapped_column(
        ForeignKey("provider_security_identities.provider_security_identity_id"),
        nullable=False,
    )
    evidence_application_id: Mapped[str] = mapped_column(String(128), nullable=False)
    application_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    evidence_id: Mapped[str] = mapped_column(String(128), nullable=False)
    evidence_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    authority_source_policy_id: Mapped[str] = mapped_column(String(128), nullable=False)
    authority_source_policy_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    claim_role: Mapped[str] = mapped_column(String(64), nullable=False)
    claim_scope: Mapped[str] = mapped_column(String(64), nullable=False)
    recorded_at: Mapped[str] = mapped_column(String(35), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class IssuerDecisionRow(Base):
    __tablename__ = "issuer_decisions"
    __table_args__ = (
        ForeignKeyConstraint(
            [
                "authority_bundle_id",
                "authority_bundle_content_hash",
                "provider_security_identity_id",
                "proposed_issuer_id",
            ],
            [
                "authority_bundles.authority_bundle_id",
                "authority_bundles.bundle_content_hash",
                "authority_bundles.provider_security_identity_id",
                "authority_bundles.proposed_issuer_id",
            ],
        ),
        UniqueConstraint(
            "issuer_decision_id",
            "authority_bundle_id",
            "decision_content_hash",
            "authority_bundle_content_hash",
            "provider_security_identity_id",
            "proposed_issuer_id",
        ),
        CheckConstraint(
            "decision_state IN "
            "('UNRESOLVED', 'READY_FOR_MANUAL_REVIEW', 'STALE', 'REVIEW_REQUIRED')"
        ),
        Index(
            "uq_issuer_decisions_bundle_root",
            "authority_bundle_id",
            unique=True,
            sqlite_where=text("supersedes_decision_id IS NULL"),
        ),
        Index(
            "uq_issuer_decisions_supersedes",
            "supersedes_decision_id",
            unique=True,
            sqlite_where=text("supersedes_decision_id IS NOT NULL"),
        ),
    )

    issuer_decision_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    decision_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    decision_audit_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    decision_rule_version: Mapped[str] = mapped_column(String(64), nullable=False)
    authority_bundle_id: Mapped[str] = mapped_column(String(128), nullable=False)
    authority_bundle_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    provider_security_identity_id: Mapped[str] = mapped_column(String(128), nullable=False)
    proposed_issuer_id: Mapped[str] = mapped_column(String(128), nullable=False)
    decision_state: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_codes_json: Mapped[str] = mapped_column(Text, nullable=False)
    latest_revision_check_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    freshness_policy_version: Mapped[str] = mapped_column(String(128), nullable=False)
    freshness_result: Mapped[str] = mapped_column(String(32), nullable=False)
    collision_scan_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    supersedes_decision_id: Mapped[str | None] = mapped_column(
        ForeignKey("issuer_decisions.issuer_decision_id")
    )
    evaluated_at: Mapped[str] = mapped_column(String(35), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class ReviewerPrincipalRow(Base):
    __tablename__ = "reviewer_principals"
    __table_args__ = (
        CheckConstraint("reviewer_role = 'LOCAL_DATA_STEWARD'"),
        CheckConstraint("principal_state IN ('ACTIVE', 'REVOKED')"),
        UniqueConstraint(
            "reviewer_principal_id",
            "reviewer_role",
            "principal_content_hash",
        ),
    )

    reviewer_principal_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    reviewer_role: Mapped[str] = mapped_column(String(32), nullable=False)
    principal_state: Mapped[str] = mapped_column(String(16), nullable=False)
    os_owner_sid_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    enrollment_policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    principal_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    registered_at: Mapped[str] = mapped_column(String(35), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class ReviewerWebauthnCredentialRow(Base):
    __tablename__ = "reviewer_webauthn_credentials"
    __table_args__ = (
        ForeignKeyConstraint(
            ["reviewer_principal_id", "reviewer_role", "principal_content_hash"],
            [
                "reviewer_principals.reviewer_principal_id",
                "reviewer_principals.reviewer_role",
                "reviewer_principals.principal_content_hash",
            ],
        ),
        UniqueConstraint(
            "webauthn_credential_id",
            "reviewer_principal_id",
            "credential_id_fingerprint",
            "public_key_fingerprint",
            "rp_id",
        ),
        UniqueConstraint("credential_id_fingerprint"),
        CheckConstraint("authenticator_attachment = 'platform'"),
        CheckConstraint("resident_key_required = 1"),
        CheckConstraint("user_verification_required = 1"),
        CheckConstraint("sign_count >= 0"),
    )

    webauthn_credential_id: Mapped[str] = mapped_column(String(512), primary_key=True)
    contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    reviewer_principal_id: Mapped[str] = mapped_column(String(128), nullable=False)
    reviewer_role: Mapped[str] = mapped_column(String(32), nullable=False)
    principal_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    credential_id_fingerprint: Mapped[str] = mapped_column(String(71), nullable=False)
    cose_public_key_canonical: Mapped[str] = mapped_column(Text, nullable=False)
    public_key_fingerprint: Mapped[str] = mapped_column(String(71), nullable=False)
    public_key_algorithm: Mapped[str] = mapped_column(String(32), nullable=False)
    authenticator_aaguid: Mapped[str | None] = mapped_column(String(64))
    authenticator_attachment: Mapped[str] = mapped_column(String(16), nullable=False)
    authenticator_transports_json: Mapped[str] = mapped_column(Text, nullable=False)
    counter_capability: Mapped[str] = mapped_column(String(32), nullable=False)
    sign_count: Mapped[int] = mapped_column(Integer, nullable=False)
    rp_id: Mapped[str] = mapped_column(String(255), nullable=False)
    resident_key_required: Mapped[int] = mapped_column(Integer, nullable=False)
    user_verification_required: Mapped[int] = mapped_column(Integer, nullable=False)
    registration_policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    credential_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    registered_at: Mapped[str] = mapped_column(String(35), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class ReviewerWebauthnCredentialEventRow(Base):
    __tablename__ = "reviewer_webauthn_credential_events"
    __table_args__ = (
        CheckConstraint("event_type IN ('REGISTERED', 'REVOKED', 'SUPERSEDED')"),
        Index(
            "uq_reviewer_webauthn_credential_events_supersedes",
            "supersedes_credential_event_id",
            unique=True,
            sqlite_where=text("supersedes_credential_event_id IS NOT NULL"),
        ),
    )

    credential_event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    webauthn_credential_id: Mapped[str] = mapped_column(
        ForeignKey("reviewer_webauthn_credentials.webauthn_credential_id"),
        nullable=False,
    )
    reviewer_principal_id: Mapped[str] = mapped_column(
        ForeignKey("reviewer_principals.reviewer_principal_id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(16), nullable=False)
    structured_reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    supersedes_credential_event_id: Mapped[str | None] = mapped_column(
        ForeignKey("reviewer_webauthn_credential_events.credential_event_id")
    )
    credential_event_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    occurred_at: Mapped[str] = mapped_column(String(35), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class IssuerApprovalChallengeRow(Base):
    __tablename__ = "issuer_approval_challenges"
    __table_args__ = (
        ForeignKeyConstraint(
            [
                "issuer_decision_id",
                "authority_bundle_id",
                "expected_decision_content_hash",
                "expected_bundle_content_hash",
                "provider_security_identity_id",
                "proposed_issuer_id",
            ],
            [
                "issuer_decisions.issuer_decision_id",
                "issuer_decisions.authority_bundle_id",
                "issuer_decisions.decision_content_hash",
                "issuer_decisions.authority_bundle_content_hash",
                "issuer_decisions.provider_security_identity_id",
                "issuer_decisions.proposed_issuer_id",
            ],
        ),
        ForeignKeyConstraint(
            ["reviewer_principal_id", "reviewer_role", "principal_content_hash"],
            [
                "reviewer_principals.reviewer_principal_id",
                "reviewer_principals.reviewer_role",
                "reviewer_principals.principal_content_hash",
            ],
        ),
        UniqueConstraint("challenge_digest"),
        UniqueConstraint("challenge_binding_hash"),
        UniqueConstraint(
            "issuer_approval_challenge_id",
            "reviewer_principal_id",
            "reviewer_role",
            "issuer_decision_id",
            "authority_bundle_id",
            "expected_decision_content_hash",
            "expected_bundle_content_hash",
            "requested_disposition",
        ),
        CheckConstraint(
            "requested_disposition IN ('APPROVED', 'REJECTED', 'REVOKED', 'SUPERSEDED')"
        ),
        CheckConstraint("rp_id = 'localhost'"),
        CheckConstraint("allowed_origin = 'http://localhost:3000'"),
        CheckConstraint("user_verification_required = 1"),
        CheckConstraint("expires_at > issued_at"),
        CheckConstraint("julianday(expires_at) <= julianday(issued_at, '+5 minutes')"),
    )

    issuer_approval_challenge_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    challenge_digest: Mapped[str] = mapped_column(String(71), nullable=False)
    challenge_binding_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    reviewer_principal_id: Mapped[str] = mapped_column(String(128), nullable=False)
    reviewer_role: Mapped[str] = mapped_column(String(32), nullable=False)
    principal_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    issuer_decision_id: Mapped[str] = mapped_column(String(128), nullable=False)
    authority_bundle_id: Mapped[str] = mapped_column(String(128), nullable=False)
    expected_decision_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    expected_bundle_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    provider_security_identity_id: Mapped[str] = mapped_column(String(128), nullable=False)
    proposed_issuer_id: Mapped[str] = mapped_column(String(128), nullable=False)
    requested_disposition: Mapped[str] = mapped_column(String(16), nullable=False)
    predecessor_approval_event_id: Mapped[str | None] = mapped_column(
        ForeignKey("issuer_approval_events.issuer_approval_event_id")
    )
    predecessor_link_id: Mapped[str | None] = mapped_column(
        ForeignKey("issuer_authority_links.issuer_authority_link_id")
    )
    successor_decision_id: Mapped[str | None] = mapped_column(
        ForeignKey("issuer_decisions.issuer_decision_id")
    )
    rp_id: Mapped[str] = mapped_column(String(255), nullable=False)
    allowed_origin: Mapped[str] = mapped_column(String(255), nullable=False)
    user_verification_required: Mapped[int] = mapped_column(Integer, nullable=False)
    authentication_policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    issued_at: Mapped[str] = mapped_column(String(35), nullable=False)
    expires_at: Mapped[str] = mapped_column(String(35), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class IssuerApprovalChallengeConsumptionRow(Base):
    __tablename__ = "issuer_approval_challenge_consumptions"
    __table_args__ = (
        CheckConstraint(
            "terminal_result IN "
            "('SUCCEEDED', 'EXPIRED', 'INVALID_SIGNATURE', "
            "'USER_VERIFICATION_ABSENT', 'ORIGIN_RP_MISMATCH', "
            "'BINDING_MISMATCH', 'REPLAY_REJECTED', 'FAILED_CLOSED')"
        ),
    )

    challenge_consumption_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    issuer_approval_challenge_id: Mapped[str] = mapped_column(
        ForeignKey("issuer_approval_challenges.issuer_approval_challenge_id"),
        unique=True,
        nullable=False,
    )
    terminal_result: Mapped[str] = mapped_column(String(32), nullable=False)
    safe_result_code: Mapped[str] = mapped_column(String(128), nullable=False)
    consumption_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    consumed_at: Mapped[str] = mapped_column(String(35), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class ReviewerAuthenticationEventRow(Base):
    __tablename__ = "reviewer_authentication_events"
    __table_args__ = (
        ForeignKeyConstraint(
            [
                "issuer_approval_challenge_id",
                "reviewer_principal_id",
                "reviewer_role",
                "issuer_decision_id",
                "authority_bundle_id",
                "expected_decision_content_hash",
                "expected_bundle_content_hash",
                "requested_disposition",
            ],
            [
                "issuer_approval_challenges.issuer_approval_challenge_id",
                "issuer_approval_challenges.reviewer_principal_id",
                "issuer_approval_challenges.reviewer_role",
                "issuer_approval_challenges.issuer_decision_id",
                "issuer_approval_challenges.authority_bundle_id",
                "issuer_approval_challenges.expected_decision_content_hash",
                "issuer_approval_challenges.expected_bundle_content_hash",
                "issuer_approval_challenges.requested_disposition",
            ],
        ),
        ForeignKeyConstraint(
            [
                "webauthn_credential_id",
                "reviewer_principal_id",
                "credential_id_fingerprint",
                "public_key_fingerprint",
                "rp_id",
            ],
            [
                "reviewer_webauthn_credentials.webauthn_credential_id",
                "reviewer_webauthn_credentials.reviewer_principal_id",
                "reviewer_webauthn_credentials.credential_id_fingerprint",
                "reviewer_webauthn_credentials.public_key_fingerprint",
                "reviewer_webauthn_credentials.rp_id",
            ],
        ),
        CheckConstraint("authentication_result IN ('VERIFIED', 'REJECTED')"),
        CheckConstraint("rp_id = 'localhost'"),
        CheckConstraint("exact_origin = 'http://localhost:3000'"),
        CheckConstraint("user_presence_verified IN (0, 1)"),
        CheckConstraint("user_verification_verified IN (0, 1)"),
        CheckConstraint("origin_verified IN (0, 1)"),
        CheckConstraint("rp_id_hash_verified IN (0, 1)"),
        CheckConstraint("signature_verified IN (0, 1)"),
        CheckConstraint("counter_verified IN (0, 1)"),
        CheckConstraint("replay_rejected IN (0, 1)"),
        CheckConstraint(
            "authentication_result != 'VERIFIED' "
            "OR (user_presence_verified = 1 "
            "AND user_verification_verified = 1 "
            "AND origin_verified = 1 "
            "AND rp_id_hash_verified = 1 "
            "AND signature_verified = 1 "
            "AND counter_verified = 1 "
            "AND replay_rejected = 1)"
        ),
        UniqueConstraint(
            "authentication_event_id",
            "issuer_approval_challenge_id",
            "reviewer_principal_id",
            "reviewer_role",
            "issuer_decision_id",
            "authority_bundle_id",
            "expected_decision_content_hash",
            "expected_bundle_content_hash",
            "requested_disposition",
            "authentication_result",
            "public_key_fingerprint",
        ),
    )

    authentication_event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    issuer_approval_challenge_id: Mapped[str] = mapped_column(String(128), nullable=False)
    challenge_consumption_id: Mapped[str] = mapped_column(
        ForeignKey("issuer_approval_challenge_consumptions.challenge_consumption_id"),
        unique=True,
        nullable=False,
    )
    reviewer_principal_id: Mapped[str] = mapped_column(String(128), nullable=False)
    reviewer_role: Mapped[str] = mapped_column(String(32), nullable=False)
    webauthn_credential_id: Mapped[str] = mapped_column(String(512), nullable=False)
    credential_id_fingerprint: Mapped[str] = mapped_column(String(71), nullable=False)
    public_key_fingerprint: Mapped[str] = mapped_column(String(71), nullable=False)
    issuer_decision_id: Mapped[str] = mapped_column(String(128), nullable=False)
    authority_bundle_id: Mapped[str] = mapped_column(String(128), nullable=False)
    expected_decision_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    expected_bundle_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    requested_disposition: Mapped[str] = mapped_column(String(16), nullable=False)
    authentication_result: Mapped[str] = mapped_column(String(16), nullable=False)
    authentication_policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    rp_id: Mapped[str] = mapped_column(String(255), nullable=False)
    exact_origin: Mapped[str] = mapped_column(String(255), nullable=False)
    user_presence_verified: Mapped[int] = mapped_column(Integer, nullable=False)
    user_verification_verified: Mapped[int] = mapped_column(Integer, nullable=False)
    origin_verified: Mapped[int] = mapped_column(Integer, nullable=False)
    rp_id_hash_verified: Mapped[int] = mapped_column(Integer, nullable=False)
    signature_verified: Mapped[int] = mapped_column(Integer, nullable=False)
    counter_verified: Mapped[int] = mapped_column(Integer, nullable=False)
    replay_rejected: Mapped[int] = mapped_column(Integer, nullable=False)
    safe_result_code: Mapped[str] = mapped_column(String(128), nullable=False)
    authentication_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    authenticated_at: Mapped[str] = mapped_column(String(35), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class IssuerApprovalEventRow(Base):
    __tablename__ = "issuer_approval_events"
    __table_args__ = (
        ForeignKeyConstraint(
            [
                "issuer_decision_id",
                "authority_bundle_id",
                "decision_content_hash",
                "bundle_content_hash",
                "provider_security_identity_id",
                "proposed_issuer_id",
            ],
            [
                "issuer_decisions.issuer_decision_id",
                "issuer_decisions.authority_bundle_id",
                "issuer_decisions.decision_content_hash",
                "issuer_decisions.authority_bundle_content_hash",
                "issuer_decisions.provider_security_identity_id",
                "issuer_decisions.proposed_issuer_id",
            ],
        ),
        ForeignKeyConstraint(
            [
                "authentication_event_id",
                "issuer_approval_challenge_id",
                "reviewer_principal_id",
                "reviewer_role",
                "issuer_decision_id",
                "authority_bundle_id",
                "decision_content_hash",
                "bundle_content_hash",
                "event_state",
                "authentication_result",
                "credential_public_key_fingerprint",
            ],
            [
                "reviewer_authentication_events.authentication_event_id",
                "reviewer_authentication_events.issuer_approval_challenge_id",
                "reviewer_authentication_events.reviewer_principal_id",
                "reviewer_authentication_events.reviewer_role",
                "reviewer_authentication_events.issuer_decision_id",
                "reviewer_authentication_events.authority_bundle_id",
                "reviewer_authentication_events.expected_decision_content_hash",
                "reviewer_authentication_events.expected_bundle_content_hash",
                "reviewer_authentication_events.requested_disposition",
                "reviewer_authentication_events.authentication_result",
                "reviewer_authentication_events.public_key_fingerprint",
            ],
        ),
        UniqueConstraint("authentication_event_id"),
        UniqueConstraint(
            "issuer_approval_event_id",
            "issuer_decision_id",
            "authority_bundle_id",
            "decision_content_hash",
            "bundle_content_hash",
            "provider_security_identity_id",
            "proposed_issuer_id",
        ),
        CheckConstraint("event_state IN ('APPROVED', 'REJECTED', 'REVOKED', 'SUPERSEDED')"),
        CheckConstraint("reviewer_role = 'LOCAL_DATA_STEWARD'"),
        CheckConstraint("authentication_result = 'VERIFIED'"),
        Index(
            "uq_issuer_approval_events_initial_disposition",
            "issuer_decision_id",
            unique=True,
            sqlite_where=text(
                "predecessor_approval_event_id IS NULL AND event_state IN ('APPROVED', 'REJECTED')"
            ),
        ),
        Index(
            "uq_issuer_approval_events_supersedes",
            "predecessor_approval_event_id",
            unique=True,
            sqlite_where=text("predecessor_approval_event_id IS NOT NULL"),
        ),
    )

    issuer_approval_event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    approval_event_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    approval_event_audit_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    issuer_decision_id: Mapped[str] = mapped_column(String(128), nullable=False)
    decision_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    authority_bundle_id: Mapped[str] = mapped_column(String(128), nullable=False)
    bundle_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    provider_security_identity_id: Mapped[str] = mapped_column(String(128), nullable=False)
    proposed_issuer_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_state: Mapped[str] = mapped_column(String(16), nullable=False)
    reviewer_principal_id: Mapped[str] = mapped_column(String(128), nullable=False)
    reviewer_role: Mapped[str] = mapped_column(String(32), nullable=False)
    authentication_event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    issuer_approval_challenge_id: Mapped[str] = mapped_column(String(128), nullable=False)
    authentication_result: Mapped[str] = mapped_column(String(16), nullable=False)
    authentication_policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    credential_public_key_fingerprint: Mapped[str] = mapped_column(String(71), nullable=False)
    structured_reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    review_note_digest: Mapped[str] = mapped_column(String(71), nullable=False)
    predecessor_approval_event_id: Mapped[str | None] = mapped_column(
        ForeignKey("issuer_approval_events.issuer_approval_event_id")
    )
    successor_decision_id: Mapped[str | None] = mapped_column(
        ForeignKey("issuer_decisions.issuer_decision_id")
    )
    authenticated_at: Mapped[str] = mapped_column(String(35), nullable=False)
    recorded_at: Mapped[str] = mapped_column(String(35), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class IssuerApprovalEvidenceObservationRow(Base):
    __tablename__ = "issuer_approval_evidence_observations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["authority_evidence_observation_id", "observation_content_hash"],
            [
                "authority_evidence_observations.authority_evidence_observation_id",
                "authority_evidence_observations.observation_content_hash",
            ],
        ),
        CheckConstraint("member_ordinal >= 0"),
    )

    issuer_approval_event_id: Mapped[str] = mapped_column(
        ForeignKey("issuer_approval_events.issuer_approval_event_id"),
        primary_key=True,
    )
    authority_evidence_observation_id: Mapped[str] = mapped_column(
        ForeignKey("authority_evidence_observations.authority_evidence_observation_id"),
        primary_key=True,
    )
    member_ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    observation_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    membership_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class IssuerAuthorityLinkRow(Base):
    __tablename__ = "issuer_authority_links"
    __table_args__ = (
        ForeignKeyConstraint(
            [
                "issuer_decision_id",
                "authority_bundle_id",
                "decision_content_hash",
                "bundle_content_hash",
                "provider_security_identity_id",
                "issuer_id",
            ],
            [
                "issuer_decisions.issuer_decision_id",
                "issuer_decisions.authority_bundle_id",
                "issuer_decisions.decision_content_hash",
                "issuer_decisions.authority_bundle_content_hash",
                "issuer_decisions.provider_security_identity_id",
                "issuer_decisions.proposed_issuer_id",
            ],
        ),
        ForeignKeyConstraint(
            [
                "approval_event_id",
                "issuer_decision_id",
                "authority_bundle_id",
                "decision_content_hash",
                "bundle_content_hash",
                "provider_security_identity_id",
                "issuer_id",
            ],
            [
                "issuer_approval_events.issuer_approval_event_id",
                "issuer_approval_events.issuer_decision_id",
                "issuer_approval_events.authority_bundle_id",
                "issuer_approval_events.decision_content_hash",
                "issuer_approval_events.bundle_content_hash",
                "issuer_approval_events.provider_security_identity_id",
                "issuer_approval_events.proposed_issuer_id",
            ],
        ),
        CheckConstraint("link_state IN ('APPROVED', 'REVIEW_REQUIRED', 'REVOKED', 'SUPERSEDED')"),
        CheckConstraint("security_resolution_state = 'UNRESOLVED'"),
        CheckConstraint(
            "(link_state = 'REVIEW_REQUIRED' "
            "AND approval_event_id IS NULL "
            "AND machine_trigger_decision_id IS NOT NULL) "
            "OR (link_state IN ('APPROVED', 'REVOKED', 'SUPERSEDED') "
            "AND approval_event_id IS NOT NULL "
            "AND machine_trigger_decision_id IS NULL)"
        ),
        CheckConstraint(
            "authority_valid_to IS NULL OR authority_valid_from IS NULL "
            "OR authority_valid_from <= authority_valid_to"
        ),
        Index(
            "uq_issuer_authority_links_provider_root",
            "provider_security_identity_id",
            unique=True,
            sqlite_where=text("supersedes_link_id IS NULL"),
        ),
        Index(
            "uq_issuer_authority_links_supersedes",
            "supersedes_link_id",
            unique=True,
            sqlite_where=text("supersedes_link_id IS NOT NULL"),
        ),
    )

    issuer_authority_link_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    link_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    link_audit_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    provider_security_identity_id: Mapped[str] = mapped_column(
        ForeignKey("provider_security_identities.provider_security_identity_id"),
        nullable=False,
    )
    issuer_id: Mapped[str] = mapped_column(ForeignKey("issuers.issuer_id"), nullable=False)
    authority_bundle_id: Mapped[str] = mapped_column(String(128), nullable=False)
    bundle_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    issuer_decision_id: Mapped[str] = mapped_column(String(128), nullable=False)
    decision_content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    approval_event_id: Mapped[str | None] = mapped_column(String(128))
    machine_trigger_decision_id: Mapped[str | None] = mapped_column(
        ForeignKey("issuer_decisions.issuer_decision_id")
    )
    link_state: Mapped[str] = mapped_column(String(32), nullable=False)
    security_resolution_state: Mapped[str] = mapped_column(String(16), nullable=False)
    supersedes_link_id: Mapped[str | None] = mapped_column(
        ForeignKey("issuer_authority_links.issuer_authority_link_id")
    )
    authority_valid_from: Mapped[date | None] = mapped_column(Date)
    authority_valid_to: Mapped[date | None] = mapped_column(Date)
    recorded_at: Mapped[str] = mapped_column(String(35), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class IssuerAuthorityLinkHeadRow(Base):
    __tablename__ = "issuer_authority_link_heads"
    __table_args__ = (
        CheckConstraint("link_state IN ('APPROVED', 'REVIEW_REQUIRED', 'REVOKED', 'SUPERSEDED')"),
        CheckConstraint("security_resolution_state = 'UNRESOLVED'"),
    )

    provider_security_identity_id: Mapped[str] = mapped_column(
        ForeignKey("provider_security_identities.provider_security_identity_id"),
        primary_key=True,
    )
    issuer_authority_link_id: Mapped[str] = mapped_column(
        ForeignKey("issuer_authority_links.issuer_authority_link_id"),
        unique=True,
        nullable=False,
    )
    link_state: Mapped[str] = mapped_column(String(32), nullable=False)
    security_resolution_state: Mapped[str] = mapped_column(String(16), nullable=False)
    state_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    previous_state_hash: Mapped[str | None] = mapped_column(String(71))
    projected_at: Mapped[str] = mapped_column(String(35), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
