"""Add CP3-C1 security-master staging and reconciliation history.

Revision ID: 0004_phase_02_cp3_c1_security_master
Revises: 0003_phase_02_cp3_b_invariants
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_phase_02_cp3_c1_security_master"
down_revision: str | None = "0003_phase_02_cp3_b_invariants"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _create_table(created_tables: list[str], name: str, *elements: object) -> None:
    op.create_table(name, *elements)
    created_tables.append(name)


def _upgrade_tables(created_tables: list[str]) -> None:
    _create_table(
        created_tables,
        "provider_security_master_records",
        sa.Column("normalized_record_id", sa.String(128), primary_key=True),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("market", sa.String(8), nullable=False),
        sa.Column("provider_listing_market", sa.String(32), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("normalized_content_hash", sa.String(71), nullable=False),
        sa.Column("provider_contract_version", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.UniqueConstraint("normalized_content_hash"),
    )
    _create_table(
        created_tables,
        "provider_security_master_observations",
        sa.Column("observation_id", sa.String(128), primary_key=True),
        sa.Column(
            "source_version_id",
            sa.String(128),
            sa.ForeignKey("provider_source_versions.source_version_id"),
            nullable=False,
        ),
        sa.Column(
            "normalized_record_id",
            sa.String(128),
            sa.ForeignKey("provider_security_master_records.normalized_record_id"),
        ),
        sa.Column(
            "provider_security_identity_id",
            sa.String(128),
            sa.ForeignKey("provider_security_identities.provider_security_identity_id"),
        ),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("market", sa.String(8), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("staging_state", sa.String(32), nullable=False),
        sa.Column("reconciliation_outcome", sa.String(32), nullable=False),
        sa.Column("eligible_for_mapping", sa.Integer(), nullable=False),
        sa.Column("provider_contract_version", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.CheckConstraint("eligible_for_mapping IN (0, 1)"),
        sa.UniqueConstraint(
            "source_version_id",
            "symbol",
            "staging_state",
            "reconciliation_outcome",
        ),
    )
    _create_table(
        created_tables,
        "provider_identity_state_events",
        sa.Column("state_event_id", sa.String(128), primary_key=True),
        sa.Column(
            "provider_security_identity_id",
            sa.String(128),
            sa.ForeignKey("provider_security_identities.provider_security_identity_id"),
            nullable=False,
        ),
        sa.Column(
            "source_version_id",
            sa.String(128),
            sa.ForeignKey("provider_source_versions.source_version_id"),
            nullable=False,
        ),
        sa.Column("identity_state", sa.String(32), nullable=False),
        sa.Column("staging_state", sa.String(32), nullable=False),
        sa.Column("reason_code", sa.String(64), nullable=False),
        sa.Column("provider_contract_version", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "provider_security_identity_id",
            "source_version_id",
            "identity_state",
            "staging_state",
            "reason_code",
        ),
    )
    _create_table(
        created_tables,
        "provider_detail_batch_results",
        sa.Column("batch_result_id", sa.String(128), primary_key=True),
        sa.Column(
            "source_version_id",
            sa.String(128),
            sa.ForeignKey("provider_source_versions.source_version_id"),
            unique=True,
            nullable=False,
        ),
        sa.Column("requested_count", sa.Integer(), nullable=False),
        sa.Column("received_count", sa.Integer(), nullable=False),
        sa.Column("missing_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("provider_contract_version", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.CheckConstraint("requested_count >= 1 AND requested_count <= 200"),
        sa.CheckConstraint("received_count >= 0 AND received_count <= requested_count"),
        sa.CheckConstraint("missing_count = requested_count - received_count"),
    )


def upgrade() -> None:
    created_tables: list[str] = []
    try:
        _upgrade_tables(created_tables)
    except Exception:
        cleanup_failure: Exception | None = None
        for table_name in reversed(created_tables):
            try:
                op.drop_table(table_name)
            except Exception as exc:
                cleanup_failure = exc
                break
        if cleanup_failure is not None:
            raise RuntimeError(
                "CP3-C1 security-master migration cleanup failed closed"
            ) from cleanup_failure
        raise


def downgrade() -> None:
    op.drop_table("provider_detail_batch_results")
    op.drop_table("provider_identity_state_events")
    op.drop_table("provider_security_master_observations")
    op.drop_table("provider_security_master_records")
