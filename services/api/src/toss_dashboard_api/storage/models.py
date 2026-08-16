from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
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
