from fastapi import APIRouter, Request

from toss_dashboard_api.contracts.responses import AnalysisPacketResponse
from toss_dashboard_api.errors import ServiceUnavailableError

router = APIRouter(prefix="/api/v1/sample", tags=["sample"])


@router.get("/analysis-packet", response_model=AnalysisPacketResponse)
def analysis_packet(request: Request) -> AnalysisPacketResponse:
    try:
        packet = request.app.state.analytics_repository.analysis_packet()
    except Exception as exc:
        raise ServiceUnavailableError("Analysis packet fixture is unavailable") from exc
    if packet is None:
        raise ServiceUnavailableError("Analysis packet fixture is unavailable")
    return AnalysisPacketResponse(
        contract_version="0.1.0",
        data_mode="FIXTURE",
        data=packet,
    )
