from __future__ import annotations

import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from toss_dashboard_api.config import Settings
from toss_dashboard_api.fixtures.importer import FixtureImporter
from toss_dashboard_api.main import create_app
from toss_dashboard_api.repositories.fixture import FixtureRepository
from toss_dashboard_api.repositories.sqlite import SQLiteMetadataRepository
from toss_dashboard_api.storage.database import create_database_engine, session_factory

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = PROJECT_ROOT / "fixtures" / "phase_01"
INVALID_FIXTURE_DIR = PROJECT_ROOT / "tests" / "fixtures" / "invalid"


def alembic_config(database_url: str) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "services" / "api" / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


@dataclass
class DatabaseContext:
    url: str
    engine: Engine
    metadata: SQLiteMetadataRepository
    analytics: FixtureRepository


@pytest.fixture
def fixture_repository() -> FixtureRepository:
    return FixtureRepository(FIXTURE_DIR)


@pytest.fixture
def workspace_tmp_path() -> Iterator[Path]:
    base = (PROJECT_ROOT / "var" / "tmp" / "backend-tests").resolve()
    base.mkdir(parents=True, exist_ok=True)
    path = (base / uuid.uuid4().hex).resolve()
    if path.parent != base:
        raise RuntimeError("test path escaped its workspace-owned base")
    path.mkdir()
    yield path


@pytest.fixture
def database_context(workspace_tmp_path: Path) -> Iterator[DatabaseContext]:
    database_path = workspace_tmp_path / "phase_01.sqlite3"
    database_url = f"sqlite:///{database_path.as_posix()}"
    command.upgrade(alembic_config(database_url), "head")
    engine = create_database_engine(database_url)
    sessions = session_factory(engine)
    analytics = FixtureRepository(FIXTURE_DIR)
    FixtureImporter(sessions).import_repository(analytics)
    metadata = SQLiteMetadataRepository(sessions, engine)
    yield DatabaseContext(database_url, engine, metadata, analytics)
    engine.dispose()


@pytest.fixture
def api_client(database_context: DatabaseContext) -> Iterator[TestClient]:
    settings = Settings(database_url=database_context.url, fixture_dir=FIXTURE_DIR)
    app = create_app(settings, database_context.metadata, database_context.analytics)
    with TestClient(app) as client:
        yield client
