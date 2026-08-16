from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from sqlalchemy import Engine, Table, select
from sqlalchemy.orm import Session, sessionmaker

from toss_dashboard_api.contracts.base import canonical_json_bytes, sha256_prefixed
from toss_dashboard_api.repositories.fixture import FixtureRepository
from toss_dashboard_api.storage.database import create_database_engine, session_factory
from toss_dashboard_api.storage.models import (
    DataQualityStatusRow,
    FixtureImportRunRow,
    IssuerRow,
    SecurityRow,
    SourceRecordRow,
)


class ImportConflictError(RuntimeError):
    pass


@dataclass(frozen=True)
class ImportResult:
    inserted: int
    updated: int
    unchanged: int
    manifest_digest: str
    fixture_version: str


@dataclass(frozen=True)
class FixtureDatabaseSnapshot:
    row_counts: dict[str, int]
    primary_keys: dict[str, tuple[str, ...]]
    canonical_digest: str


FIXTURE_TABLES: tuple[Table, ...] = (
    cast(Table, IssuerRow.__table__),
    cast(Table, SecurityRow.__table__),
    cast(Table, SourceRecordRow.__table__),
    cast(Table, DataQualityStatusRow.__table__),
    cast(Table, FixtureImportRunRow.__table__),
)


def fixture_database_snapshot(
    sessions: sessionmaker[Session],
) -> FixtureDatabaseSnapshot:
    row_counts: dict[str, int] = {}
    primary_keys: dict[str, tuple[str, ...]] = {}
    rows_by_table: dict[str, list[dict[str, object]]] = {}

    with sessions() as session:
        for table in FIXTURE_TABLES:
            key_columns = tuple(table.primary_key.columns)
            rows = [
                dict(row)
                for row in session.execute(select(*table.columns).order_by(*key_columns)).mappings()
            ]
            row_counts[table.name] = len(rows)
            primary_keys[table.name] = tuple(
                canonical_json_bytes([row[column.name] for column in key_columns]).decode("utf-8")
                for row in rows
            )
            rows_by_table[table.name] = rows

    return FixtureDatabaseSnapshot(
        row_counts=row_counts,
        primary_keys=primary_keys,
        canonical_digest=sha256_prefixed(canonical_json_bytes(rows_by_table)),
    )


class FixtureImporter:
    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self._sessions = sessions

    def import_repository(self, fixtures: FixtureRepository) -> ImportResult:
        inserted = 0
        unchanged = 0
        with self._sessions.begin() as session:
            for issuer in fixtures.issuers:
                existing_issuer = session.get(IssuerRow, issuer.issuer_id)
                if existing_issuer is not None:
                    self._assert_same_hash(
                        issuer.issuer_id,
                        existing_issuer.normalized_content_hash,
                        issuer.normalized_content_hash,
                    )
                    unchanged += 1
                    continue
                session.add(
                    IssuerRow(
                        issuer_id=issuer.issuer_id,
                        jurisdiction=issuer.jurisdiction.value,
                        corp_code=issuer.corp_code,
                        cik=issuer.cik,
                        normalized_content_hash=issuer.normalized_content_hash,
                        payload_json=issuer.model_dump_json(),
                    )
                )
                inserted += 1
            session.flush()

            for security in fixtures.securities:
                existing_security = session.get(SecurityRow, security.security_id)
                if existing_security is not None:
                    self._assert_same_hash(
                        security.security_id,
                        existing_security.normalized_content_hash,
                        security.normalized_content_hash,
                    )
                    unchanged += 1
                    continue
                session.add(
                    SecurityRow(
                        security_id=security.security_id,
                        issuer_id=security.issuer_id,
                        market=security.market.value,
                        exchange=security.exchange,
                        ticker=security.ticker,
                        share_class=security.share_class.value,
                        normalized_content_hash=security.normalized_content_hash,
                        payload_json=security.model_dump_json(),
                    )
                )
                inserted += 1
            session.flush()

            source_by_id = {item.source_record_id: item for item in fixtures.source_records}
            pending = set(source_by_id)
            while pending:
                progressed = False
                for source_id in sorted(pending):
                    source = source_by_id[source_id]
                    if source.supersedes_id in pending:
                        continue
                    existing_source = session.get(SourceRecordRow, source.source_record_id)
                    if existing_source is not None:
                        self._assert_same_hash(
                            source.source_record_id,
                            existing_source.normalized_content_hash,
                            source.normalized_content_hash,
                        )
                        unchanged += 1
                    else:
                        session.add(
                            SourceRecordRow(
                                source_record_id=source.source_record_id,
                                source_system=source.source_system.value,
                                source_type=source.source_type.value,
                                external_id=source.external_id,
                                supersedes_id=source.supersedes_id,
                                raw_content_hash=source.raw_content_hash,
                                normalized_content_hash=source.normalized_content_hash,
                                payload_json=source.model_dump_json(),
                            )
                        )
                        inserted += 1
                    pending.remove(source_id)
                    progressed = True
                    session.flush()
                    break
                if not progressed:
                    raise ImportConflictError("source revision graph could not be imported")

            for quality in fixtures.data_quality_statuses:
                existing_quality = session.get(DataQualityStatusRow, quality.quality_status_id)
                if existing_quality is not None:
                    self._assert_same_hash(
                        quality.quality_status_id,
                        existing_quality.normalized_content_hash,
                        quality.normalized_content_hash,
                    )
                    unchanged += 1
                    continue
                session.add(
                    DataQualityStatusRow(
                        quality_status_id=quality.quality_status_id,
                        issuer_id=quality.issuer_id,
                        source_system=quality.source_system.value,
                        dataset=quality.dataset,
                        normalized_content_hash=quality.normalized_content_hash,
                        payload_json=quality.model_dump_json(),
                    )
                )
                inserted += 1

            run = session.scalar(
                select(FixtureImportRunRow).where(
                    FixtureImportRunRow.manifest_digest == fixtures.manifest_digest
                )
            )
            if run is None:
                session.add(
                    FixtureImportRunRow(
                        manifest_digest=fixtures.manifest_digest,
                        fixture_version=fixtures.manifest.fixture_version,
                        imported_at=datetime.now(UTC),
                    )
                )

        return ImportResult(
            inserted=inserted,
            updated=0,
            unchanged=unchanged,
            manifest_digest=fixtures.manifest_digest,
            fixture_version=fixtures.manifest.fixture_version,
        )

    @staticmethod
    def _assert_same_hash(record_id: str, stored: str, incoming: str) -> None:
        if stored != incoming:
            raise ImportConflictError(
                f"stable ID conflict for {record_id}; existing records are never overwritten"
            )


def import_fixtures(database_url: str, fixture_dir: Path) -> ImportResult:
    engine: Engine = create_database_engine(database_url)
    try:
        fixtures = FixtureRepository(fixture_dir)
        return FixtureImporter(session_factory(engine)).import_repository(fixtures)
    finally:
        engine.dispose()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import validated Phase 1 synthetic fixtures")
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DASHBOARD_DATABASE_URL", "sqlite:///./var/dashboard.db"),
    )
    parser.add_argument("--fixture-dir", type=Path, required=True)
    parser.add_argument("--verify-idempotency", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    engine: Engine = create_database_engine(args.database_url)
    try:
        fixtures = FixtureRepository(args.fixture_dir)
        sessions = session_factory(engine)
        importer = FixtureImporter(sessions)
        first = importer.import_repository(fixtures)
        payload: dict[str, object] = {"first": asdict(first)}
        if args.verify_idempotency:
            before = fixture_database_snapshot(sessions)
            second = importer.import_repository(fixtures)
            after = fixture_database_snapshot(sessions)
            expected_unchanged = sum(
                len(records)
                for records in (
                    fixtures.issuers,
                    fixtures.securities,
                    fixtures.source_records,
                    fixtures.data_quality_statuses,
                )
            )
            if second.inserted != 0 or second.updated != 0:
                raise ImportConflictError("second fixture import changed persisted rows")
            if second.unchanged != expected_unchanged:
                raise ImportConflictError(
                    "second fixture import did not account for every fixture row"
                )
            if before.row_counts != after.row_counts:
                raise ImportConflictError("row counts changed on the second fixture import")
            if before.primary_keys != after.primary_keys:
                raise ImportConflictError("primary keys changed on the second fixture import")
            if before.canonical_digest != after.canonical_digest:
                raise ImportConflictError(
                    "canonical database digest changed on the second fixture import"
                )
            payload["second"] = asdict(second)
            payload["verification"] = asdict(after)
    finally:
        engine.dispose()
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
