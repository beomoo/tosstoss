from __future__ import annotations

from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from toss_dashboard_api.contracts.quality import DataQualityStatus
from toss_dashboard_api.contracts.security import Security
from toss_dashboard_api.storage.models import (
    DataQualityStatusRow,
    FixtureImportRunRow,
    IssuerRow,
    SecurityRow,
)

_INTERNAL_ADDITIVE_REVISIONS = frozenset(
    {
        "0002_phase_02_cp3_foundation",
        "0003_phase_02_cp3_b_invariants",
        "0004_phase_02_cp3_c1_security_master",
        "0005_phase_02_cp3_c2_b_issuer_authority",
    }
)


class SQLiteMetadataRepository:
    def __init__(self, sessions: sessionmaker[Session], engine: Engine) -> None:
        self._sessions = sessions
        self._engine = engine

    def list_securities(self) -> list[Security]:
        with self._sessions() as session:
            rows = session.scalars(select(SecurityRow).order_by(SecurityRow.security_id)).all()
            return [Security.model_validate_json(row.payload_json) for row in rows]

    def issuer_exists(self, issuer_id: str) -> bool:
        with self._sessions() as session:
            return session.get(IssuerRow, issuer_id) is not None

    def data_quality_for_issuer(self, issuer_id: str) -> list[DataQualityStatus]:
        with self._sessions() as session:
            rows = session.scalars(
                select(DataQualityStatusRow)
                .where(DataQualityStatusRow.issuer_id == issuer_id)
                .order_by(DataQualityStatusRow.quality_status_id)
            ).all()
            return [DataQualityStatus.model_validate_json(row.payload_json) for row in rows]

    def database_revision(self) -> str:
        with self._engine.connect() as connection:
            try:
                revision = connection.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one()
            except Exception as exc:
                raise RuntimeError("database schema is not migrated") from exc
        actual_revision = str(revision)
        if actual_revision in _INTERNAL_ADDITIVE_REVISIONS:
            # The Phase 1 application API remains pinned to its public foundation
            # revision while Phase 2 provider tables stay internal and additive.
            return "0001_phase_01"
        return actual_revision

    def fixture_version(self) -> str | None:
        with self._sessions() as session:
            row = session.scalar(
                select(FixtureImportRunRow).order_by(FixtureImportRunRow.import_run_id.desc())
            )
            return None if row is None else row.fixture_version

    def fixture_manifest_digest(self) -> str | None:
        with self._sessions() as session:
            row = session.scalar(
                select(FixtureImportRunRow).order_by(FixtureImportRunRow.import_run_id.desc())
            )
            return None if row is None else row.manifest_digest
