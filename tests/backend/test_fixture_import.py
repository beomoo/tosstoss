import json
from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import func, select
from tests.backend.conftest import FIXTURE_DIR, alembic_config

from toss_dashboard_api.fixtures.importer import (
    FixtureImporter,
    ImportConflictError,
    fixture_database_snapshot,
)
from toss_dashboard_api.repositories.fixture import FixtureRepository
from toss_dashboard_api.storage.database import create_database_engine, session_factory
from toss_dashboard_api.storage.models import FixtureImportRunRow, IssuerRow


def test_fixture_import_is_idempotent(workspace_tmp_path: Path) -> None:
    url = f"sqlite:///{(workspace_tmp_path / 'idempotency.sqlite3').as_posix()}"
    command.upgrade(alembic_config(url), "head")
    engine = create_database_engine(url)
    sessions = session_factory(engine)
    fixtures = FixtureRepository(FIXTURE_DIR)
    importer = FixtureImporter(sessions)
    expected = (
        len(fixtures.issuers)
        + len(fixtures.securities)
        + len(fixtures.source_records)
        + len(fixtures.data_quality_statuses)
    )
    try:
        first = importer.import_repository(fixtures)
        before = fixture_database_snapshot(sessions)
        second = importer.import_repository(fixtures)
        after = fixture_database_snapshot(sessions)
        assert first.inserted == expected
        assert first.updated == 0
        assert first.unchanged == 0
        assert second.inserted == 0
        assert second.updated == 0
        assert second.unchanged == expected
        assert after.row_counts == before.row_counts
        assert after.primary_keys == before.primary_keys
        assert after.canonical_digest == before.canonical_digest
    finally:
        engine.dispose()


def test_same_stable_id_with_different_hash_rolls_back(workspace_tmp_path: Path) -> None:
    url = f"sqlite:///{(workspace_tmp_path / 'conflict.sqlite3').as_posix()}"
    command.upgrade(alembic_config(url), "head")
    engine = create_database_engine(url)
    sessions = session_factory(engine)
    try:
        fixtures = FixtureRepository(FIXTURE_DIR)
        importer = FixtureImporter(sessions)
        importer.import_repository(fixtures)
        before = fixtures.issuers[0]
        fixtures.issuers[0] = before.model_copy(
            update={"normalized_content_hash": "sha256:" + "a" * 64}
        )
        with pytest.raises(ImportConflictError):
            importer.import_repository(fixtures)
        with sessions() as session:
            assert session.scalar(select(func.count()).select_from(IssuerRow)) == 2
            stored = session.get(IssuerRow, before.issuer_id)
            assert stored is not None
            assert stored.normalized_content_hash == before.normalized_content_hash
    finally:
        engine.dispose()


@pytest.mark.parametrize("corruption", ["payload_json", "denormalized_column"])
def test_existing_row_corruption_is_never_accepted_as_unchanged(
    database_context, corruption: str
) -> None:
    sessions = session_factory(database_context.engine)
    with sessions.begin() as session:
        row = session.get(IssuerRow, "issuer_kr_synthetic")
        assert row is not None
        if corruption == "payload_json":
            payload = json.loads(row.payload_json)
            payload["display_name"] = "Corrupted Synthetic Name"
            row.payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        else:
            row.jurisdiction = "US"

    with sessions() as session:
        run_count_before = session.scalar(select(func.count()).select_from(FixtureImportRunRow))
    with pytest.raises(ImportConflictError, match="stored row corruption"):
        FixtureImporter(sessions).import_repository(database_context.analytics)
    with sessions() as session:
        run_count_after = session.scalar(select(func.count()).select_from(FixtureImportRunRow))
        row = session.get(IssuerRow, "issuer_kr_synthetic")
        assert row is not None
        if corruption == "payload_json":
            assert "Corrupted Synthetic Name" in row.payload_json
        else:
            assert row.jurisdiction == "US"
    assert run_count_after == run_count_before
