from fastapi import APIRouter, Request

from toss_dashboard_api.contracts.responses import SecuritiesResponse
from toss_dashboard_api.errors import ServiceUnavailableError

router = APIRouter(prefix="/api/v1", tags=["securities"])


@router.get("/securities", response_model=SecuritiesResponse)
def securities(request: Request) -> SecuritiesResponse:
    try:
        records = request.app.state.metadata_repository.list_securities()
    except Exception as exc:
        raise ServiceUnavailableError("Security metadata is unavailable") from exc
    return SecuritiesResponse(
        contract_version="0.1.0",
        data_mode="FIXTURE",
        data=records,
        count=len(records),
    )
