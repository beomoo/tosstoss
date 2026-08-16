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
        return str(revision)

    def fixture_version(self) -> str | None:
        with self._sessions() as session:
            row = session.scalar(
                select(FixtureImportRunRow).order_by(FixtureImportRunRow.import_run_id.desc())
            )
            return None if row is None else row.fixture_version
