from __future__ import annotations

from pathlib import Path
from typing import Annotated, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    """Fail-closed local settings with optional server-only provider credentials."""

    model_config = SettingsConfigDict(
        extra="ignore",
        case_sensitive=True,
        populate_by_name=True,
        hide_input_in_errors=True,
    )

    app_env: Annotated[str, Field(validation_alias="APP_ENV")] = "development"
    local_only: Annotated[bool, Field(validation_alias="LOCAL_ONLY")] = True
    trading_enabled: Annotated[bool, Field(validation_alias="TRADING_ENABLED")] = False
    dry_run: Annotated[bool, Field(validation_alias="DRY_RUN")] = True
    openai_api_enabled: Annotated[bool, Field(validation_alias="OPENAI_API_ENABLED")] = False
    toss_client_id: Annotated[SecretStr | None, Field(validation_alias="TOSS_CLIENT_ID")] = None
    toss_client_secret: Annotated[
        SecretStr | None, Field(validation_alias="TOSS_CLIENT_SECRET")
    ] = None
    allow_account_endpoints: Annotated[bool, Field(validation_alias="ALLOW_ACCOUNT_ENDPOINTS")] = (
        False
    )
    database_url: Annotated[str, Field(validation_alias="DASHBOARD_DATABASE_URL")] = (
        "sqlite:///./var/dashboard.db"
    )
    fixture_dir: Annotated[Path, Field(validation_alias="DASHBOARD_FIXTURE_DIR")] = (
        PROJECT_ROOT / "fixtures" / "phase_01"
    )
    api_host: Annotated[str, Field(validation_alias="DASHBOARD_API_HOST")] = "127.0.0.1"
    trusted_hosts: tuple[str, ...] = ("127.0.0.1", "localhost", "testserver")
    cors_origins: tuple[str, ...] = (
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    )

    @field_validator("toss_client_id", "toss_client_secret", mode="before")
    @classmethod
    def empty_provider_credential_is_absent(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("database_url")
    @classmethod
    def sqlite_only(cls, value: str) -> str:
        if not (value.startswith("sqlite:///") or value.startswith("sqlite+pysqlite:///")):
            raise ValueError("Phase 1 database must be local SQLite")
        if "?mode=memory" not in value and value.endswith(("/", "\\")):
            raise ValueError("SQLite URL must identify a database file")
        return value

    @model_validator(mode="after")
    def phase_one_fail_closed(self) -> Self:
        unsafe = []
        if not self.local_only:
            unsafe.append("LOCAL_ONLY must be true")
        if self.trading_enabled:
            unsafe.append("TRADING_ENABLED must be false")
        if not self.dry_run:
            unsafe.append("DRY_RUN must be true")
        if self.openai_api_enabled:
            unsafe.append("OPENAI_API_ENABLED must be false")
        if self.allow_account_endpoints:
            unsafe.append("ALLOW_ACCOUNT_ENDPOINTS must be false")
        if self.api_host != "127.0.0.1":
            unsafe.append("DASHBOARD_API_HOST must be 127.0.0.1")
        if not self.trusted_hosts or any(
            host == "*" or host not in {"127.0.0.1", "localhost", "testserver"}
            for host in self.trusted_hosts
        ):
            unsafe.append("trusted hosts must be an exact localhost allowlist")
        if not self.cors_origins or any(
            origin == "*" or origin not in {"http://127.0.0.1:3000", "http://localhost:3000"}
            for origin in self.cors_origins
        ):
            unsafe.append("CORS origins must be exact local frontend origins")
        if unsafe:
            raise ValueError("; ".join(unsafe))
        return self
