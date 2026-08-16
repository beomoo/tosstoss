from fastapi import APIRouter, Request

from toss_dashboard_api import __version__
from toss_dashboard_api.contracts.responses import SafetyStatus, SystemStatusResponse
from toss_dashboard_api.errors import ServiceUnavailableError

router = APIRouter(prefix="/api/v1/system", tags=["system"])


@router.get("/status", response_model=SystemStatusResponse)
def system_status(request: Request) -> SystemStatusResponse:
    settings = request.app.state.settings
    repository = request.app.state.metadata_repository
    try:
        revision = repository.database_revision()
        fixture_version = repository.fixture_version()
    except Exception as exc:
        raise ServiceUnavailableError("System metadata is unavailable") from exc
    if fixture_version is None:
        raise ServiceUnavailableError("Fixture metadata is unavailable")
    return SystemStatusResponse(
        contract_version="0.1.0",
        data_mode="FIXTURE",
        service="toss-dashboard-api",
        version=__version__,
        status="ok",
        database_revision=revision,
        fixture_version=fixture_version,
        safety=SafetyStatus(
            contract_version="0.1.0",
            local_only=settings.local_only,
            trading_enabled=settings.trading_enabled,
            dry_run=settings.dry_run,
            openai_api_enabled=settings.openai_api_enabled,
            allow_account_endpoints=settings.allow_account_endpoints,
        ),
    )
