from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
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
