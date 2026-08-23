from fastapi import APIRouter

from toss_dashboard_api import __version__
from toss_dashboard_api.contracts.responses import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        contract_version="0.1.0",
        service="toss-dashboard-api",
        version=__version__,
        data_mode="FIXTURE",
        status="ok",
    )
