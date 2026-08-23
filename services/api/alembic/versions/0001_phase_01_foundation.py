"""Phase 1 SQLite metadata foundation.

Revision ID: 0001_phase_01
Revises: None
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_phase_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "issuers",
        sa.Column("issuer_id", sa.String(128), primary_key=True),
        sa.Column("jurisdiction", sa.String(8), nullable=False),
        sa.Column("corp_code", sa.String(32), unique=True),
        sa.Column("cik", sa.String(32), unique=True),
        sa.Column("normalized_content_hash", sa.String(71), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
    )
    op.create_table(
        "securities",
        sa.Column("security_id", sa.String(128), primary_key=True),
        sa.Column("issuer_id", sa.String(128), sa.ForeignKey("issuers.issuer_id"), nullable=False),
        sa.Column("market", sa.String(8), nullable=False),
        sa.Column("exchange", sa.String(32), nullable=False),
        sa.Column("ticker", sa.String(32), nullable=False),
        sa.Column("share_class", sa.String(32), nullable=False),
        sa.Column("normalized_content_hash", sa.String(71), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.UniqueConstraint("market", "exchange", "ticker", "share_class"),
    )
    op.create_table(
        "source_records",
        sa.Column("source_record_id", sa.String(128), primary_key=True),
        sa.Column("source_system", sa.String(64), nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("external_id", sa.String(128), nullable=False),
        sa.Column(
            "supersedes_id",
            sa.String(128),
            sa.ForeignKey("source_records.source_record_id"),
        ),
        sa.Column("raw_content_hash", sa.String(71), nullable=False),
        sa.Column("normalized_content_hash", sa.String(71), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.UniqueConstraint("source_system", "source_type", "external_id"),
    )
    op.create_table(
        "data_quality_statuses",
        sa.Column("quality_status_id", sa.String(128), primary_key=True),
        sa.Column("issuer_id", sa.String(128), sa.ForeignKey("issuers.issuer_id"), nullable=False),
        sa.Column("source_system", sa.String(64), nullable=False),
        sa.Column("dataset", sa.String(64), nullable=False),
        sa.Column("normalized_content_hash", sa.String(71), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.UniqueConstraint("issuer_id", "source_system", "dataset"),
    )
    op.create_table(
        "fixture_import_runs",
        sa.Column("import_run_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("manifest_digest", sa.String(71), unique=True, nullable=False),
        sa.Column("fixture_version", sa.String(32), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("fixture_import_runs")
    op.drop_table("data_quality_statuses")
    op.drop_table("source_records")
    op.drop_table("securities")
    op.drop_table("issuers")
