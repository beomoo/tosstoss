"""Phase 2 CP3 provider source-trace foundation.

Revision ID: 0002_phase_02_cp3_foundation
Revises: 0001_phase_01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_phase_02_cp3_foundation"
down_revision: str | None = "0001_phase_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "canonical_requests",
        sa.Column("canonical_request_id", sa.String(128), primary_key=True),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("method", sa.String(8), nullable=False),
        sa.Column("path_template", sa.String(256), nullable=False),
        sa.Column("canonical_query_json", sa.Text(), nullable=False),
        sa.Column("canonical_query_hash", sa.String(71), nullable=False),
        sa.Column("provider_contract_version", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
    )
    op.create_table(
        "provider_raw_manifests",
        sa.Column("raw_response_id", sa.String(128), primary_key=True),
        sa.Column(
            "canonical_request_id",
            sa.String(128),
            sa.ForeignKey("canonical_requests.canonical_request_id"),
            nullable=False,
        ),
        sa.Column("http_status", sa.Integer(), nullable=False),
        sa.Column("raw_content_hash", sa.String(71), nullable=False),
        sa.Column("raw_storage_ref", sa.String(128), nullable=False),
        sa.Column("fetched_at", sa.String(35), nullable=False),
        sa.Column("response_metadata_json", sa.Text(), nullable=False),
        sa.Column("provider_contract_version", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.CheckConstraint("http_status >= 100 AND http_status <= 599"),
        sa.UniqueConstraint("canonical_request_id", "http_status", "raw_content_hash"),
    )
    op.create_table(
        "provider_source_versions",
        sa.Column("source_version_id", sa.String(128), primary_key=True),
        sa.Column(
            "canonical_request_id",
            sa.String(128),
            sa.ForeignKey("canonical_requests.canonical_request_id"),
            nullable=False,
        ),
        sa.Column(
            "raw_response_id",
            sa.String(128),
            sa.ForeignKey("provider_raw_manifests.raw_response_id"),
            nullable=False,
        ),
        sa.Column("dataset", sa.String(64), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=False),
        sa.Column("raw_content_hash", sa.String(71), nullable=False),
        sa.Column("provider_contract_version", sa.String(64), nullable=False),
        sa.Column("revision_status", sa.String(32), nullable=False),
        sa.Column(
            "supersedes_id",
            sa.String(128),
            sa.ForeignKey("provider_source_versions.source_version_id"),
        ),
        sa.Column("normalized_content_hash", sa.String(71), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "canonical_request_id",
            "http_status",
            "raw_content_hash",
            "provider_contract_version",
        ),
    )
    op.create_table(
        "collection_attempts",
        sa.Column("attempt_id", sa.String(128), primary_key=True),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("dataset", sa.String(64), nullable=False),
        sa.Column(
            "canonical_request_id",
            sa.String(128),
            sa.ForeignKey("canonical_requests.canonical_request_id"),
        ),
        sa.Column("started_at", sa.String(35), nullable=False),
        sa.Column("finished_at", sa.String(35)),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("records_received", sa.Integer(), nullable=False),
        sa.Column("records_rejected", sa.Integer(), nullable=False),
        sa.Column("safe_result_code", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.CheckConstraint("records_received >= 0"),
        sa.CheckConstraint("records_rejected >= 0"),
    )
    op.create_table(
        "provider_audit_events",
        sa.Column("audit_event_id", sa.String(128), primary_key=True),
        sa.Column(
            "attempt_id",
            sa.String(128),
            sa.ForeignKey("collection_attempts.attempt_id"),
            nullable=False,
        ),
        sa.Column(
            "source_version_id",
            sa.String(128),
            sa.ForeignKey("provider_source_versions.source_version_id"),
        ),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("safe_status", sa.String(64), nullable=False),
        sa.Column("record_count", sa.Integer(), nullable=False),
        sa.Column("occurred_at", sa.String(35), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.CheckConstraint("record_count >= 0"),
    )
    op.create_table(
        "provider_security_identities",
        sa.Column("provider_security_identity_id", sa.String(128), primary_key=True),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("market", sa.String(8), nullable=False),
        sa.Column("allocation_anchor_hash", sa.String(71), nullable=False),
        sa.Column("identity_state", sa.String(32), nullable=False),
        sa.Column("mapping_status", sa.String(32), nullable=False),
        sa.Column(
            "first_source_version_id",
            sa.String(128),
            sa.ForeignKey("provider_source_versions.source_version_id"),
            nullable=False,
        ),
        sa.Column(
            "latest_source_version_id",
            sa.String(128),
            sa.ForeignKey("provider_source_versions.source_version_id"),
            nullable=False,
        ),
        sa.Column("provider_contract_version", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.UniqueConstraint("provider", "allocation_anchor_hash"),
    )
    op.create_table(
        "provider_identifier_history",
        sa.Column("identifier_history_id", sa.String(128), primary_key=True),
        sa.Column(
            "provider_security_identity_id",
            sa.String(128),
            sa.ForeignKey("provider_security_identities.provider_security_identity_id"),
            nullable=False,
        ),
        sa.Column("identifier_kind", sa.String(32), nullable=False),
        sa.Column("identifier_value", sa.String(128), nullable=False),
        sa.Column("valid_from", sa.Date()),
        sa.Column("valid_to", sa.Date()),
        sa.Column(
            "source_version_id",
            sa.String(128),
            sa.ForeignKey("provider_source_versions.source_version_id"),
            nullable=False,
        ),
        sa.Column("revision_reason", sa.String(32), nullable=False),
        sa.Column("provider_contract_version", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.CheckConstraint("valid_to IS NULL OR valid_from IS NULL OR valid_from <= valid_to"),
        sa.UniqueConstraint(
            "provider_security_identity_id",
            "identifier_kind",
            "identifier_value",
            "source_version_id",
        ),
    )
    op.create_table(
        "provider_identity_mappings",
        sa.Column("mapping_id", sa.String(128), primary_key=True),
        sa.Column(
            "provider_security_identity_id",
            sa.String(128),
            sa.ForeignKey("provider_security_identities.provider_security_identity_id"),
            nullable=False,
        ),
        sa.Column("issuer_id", sa.String(128), sa.ForeignKey("issuers.issuer_id")),
        sa.Column("security_id", sa.String(128), sa.ForeignKey("securities.security_id")),
        sa.Column("mapping_status", sa.String(32), nullable=False),
        sa.Column(
            "evidence_source_version_id",
            sa.String(128),
            sa.ForeignKey("provider_source_versions.source_version_id"),
            nullable=False,
        ),
        sa.Column("approved_at", sa.String(35)),
        sa.Column("valid_from", sa.Date()),
        sa.Column("valid_to", sa.Date()),
        sa.Column("provider_contract_version", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "mapping_status != 'VERIFIED' OR "
            "(issuer_id IS NOT NULL AND security_id IS NOT NULL AND approved_at IS NOT NULL)"
        ),
        sa.CheckConstraint("valid_to IS NULL OR valid_from IS NULL OR valid_from <= valid_to"),
    )
    op.create_table(
        "provider_latest_pointers",
        sa.Column("latest_pointer_id", sa.String(128), primary_key=True),
        sa.Column("dataset", sa.String(64), nullable=False),
        sa.Column(
            "provider_security_identity_id",
            sa.String(128),
            sa.ForeignKey("provider_security_identities.provider_security_identity_id"),
            nullable=False,
        ),
        sa.Column("normalized_record_id", sa.String(128), nullable=False),
        sa.Column(
            "source_version_id",
            sa.String(128),
            sa.ForeignKey("provider_source_versions.source_version_id"),
            nullable=False,
        ),
        sa.Column("accepted_observed_at", sa.String(35)),
        sa.Column("accepted_observed_date", sa.Date()),
        sa.Column("state_hash", sa.String(71), nullable=False),
        sa.Column("provider_contract_version", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.UniqueConstraint("dataset", "provider_security_identity_id"),
    )


def downgrade() -> None:
    op.drop_table("provider_latest_pointers")
    op.drop_table("provider_identity_mappings")
    op.drop_table("provider_identifier_history")
    op.drop_table("provider_security_identities")
    op.drop_table("provider_audit_events")
    op.drop_table("collection_attempts")
    op.drop_table("provider_source_versions")
    op.drop_table("provider_raw_manifests")
    op.drop_table("canonical_requests")
