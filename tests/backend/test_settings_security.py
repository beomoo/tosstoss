from pathlib import Path

import pytest
from pydantic import ValidationError

from toss_dashboard_api.config import Settings
from toss_dashboard_api.storage.database import create_database_engine


def test_safe_defaults_are_fail_closed() -> None:
    settings = Settings()
    assert settings.local_only is True
    assert settings.trading_enabled is False
    assert settings.dry_run is True
    assert settings.openai_api_enabled is False
    assert settings.allow_account_endpoints is False
    assert settings.api_host == "127.0.0.1"
    assert settings.database_url == "sqlite:///./var/dashboard.db"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("local_only", False),
        ("trading_enabled", True),
        ("dry_run", False),
        ("openai_api_enabled", True),
        ("allow_account_endpoints", True),
        ("api_host", "0.0.0.0"),
        ("trusted_hosts", ("*",)),
        ("cors_origins", ("*",)),
    ],
)
def test_unsafe_settings_are_rejected(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        Settings(**{field: value})


def test_remote_database_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(database_url="postgresql://remote.invalid/database")


def test_fixture_path_can_be_explicit(workspace_tmp_path: Path) -> None:
    settings = Settings(fixture_dir=workspace_tmp_path)
    assert settings.fixture_dir == workspace_tmp_path


def test_database_engine_creates_the_sqlite_parent(workspace_tmp_path: Path) -> None:
    database_path = workspace_tmp_path / "nested" / "dashboard.db"
    engine = create_database_engine(f"sqlite:///{database_path.as_posix()}")
    try:
        assert database_path.parent.is_dir()
    finally:
        engine.dispose()
