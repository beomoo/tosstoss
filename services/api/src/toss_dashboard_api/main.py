from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import Engine
from starlette.middleware.trustedhost import TrustedHostMiddleware

from toss_dashboard_api import __version__
from toss_dashboard_api.config import Settings
from toss_dashboard_api.contracts.responses import ErrorBody, ErrorEnvelope
from toss_dashboard_api.errors import (
    AppError,
    app_error_handler,
    request_id_for,
    unhandled_error_handler,
)
from toss_dashboard_api.logging_config import configure_logging
from toss_dashboard_api.middleware import RequestIdMiddleware
from toss_dashboard_api.repositories.fixture import FixtureRepository
from toss_dashboard_api.repositories.protocols import AnalyticsRepository, MetadataRepository
from toss_dashboard_api.repositories.sqlite import SQLiteMetadataRepository
from toss_dashboard_api.routes import companies, health, sample, securities, system
from toss_dashboard_api.storage.database import create_database_engine, session_factory

logger = logging.getLogger("toss_dashboard_api")


async def validation_error_handler(request: Request, _exc: RequestValidationError) -> JSONResponse:
    body = ErrorEnvelope(
        contract_version="0.1.0",
        error=ErrorBody(
            code="VALIDATION_ERROR",
            message="The request is invalid",
        ),
        request_id=request_id_for(request),
    )
    return JSONResponse(status_code=422, content=body.model_dump(mode="json"))


def create_app(
    settings: Settings | None = None,
    metadata_repository: MetadataRepository | None = None,
    analytics_repository: AnalyticsRepository | None = None,
) -> FastAPI:
    resolved_settings = settings or Settings()
    injected = metadata_repository is not None or analytics_repository is not None
    if injected and (metadata_repository is None or analytics_repository is None):
        raise ValueError("both repositories must be supplied together")

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        configure_logging()
        engine: Engine | None = None
        metadata: MetadataRepository
        analytics: AnalyticsRepository
        if metadata_repository is None or analytics_repository is None:
            engine = create_database_engine(resolved_settings.database_url)
            metadata = SQLiteMetadataRepository(session_factory(engine), engine)
            analytics = FixtureRepository(resolved_settings.fixture_dir)
            revision = metadata.database_revision()
            if revision != "0001_phase_01":
                raise RuntimeError("database migration revision does not match Phase 1")
            if metadata.fixture_version() != analytics.manifest.fixture_version:
                raise RuntimeError(
                    "fixture import version does not match validated fixture manifest"
                )
        else:
            metadata = metadata_repository
            analytics = analytics_repository
        application.state.metadata_repository = metadata
        application.state.analytics_repository = analytics
        logger.info("api_started", extra={"status": "ok", "stage": "startup"})
        try:
            yield
        finally:
            if engine is not None:
                engine.dispose()

    application = FastAPI(
        title="Toss Investment Research Dashboard Fixture API",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    application.state.settings = resolved_settings
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved_settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["accept", "content-type", "x-request-id"],
    )
    application.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=list(resolved_settings.trusted_hosts),
    )
    application.add_middleware(RequestIdMiddleware)
    application.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    application.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
    application.add_exception_handler(Exception, unhandled_error_handler)
    application.include_router(health.router)
    application.include_router(system.router)
    application.include_router(securities.router)
    application.include_router(companies.router)
    application.include_router(sample.router)
    return application


app = create_app()
