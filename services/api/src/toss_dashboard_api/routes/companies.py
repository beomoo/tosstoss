from fastapi import APIRouter, Request

from toss_dashboard_api.contracts.base import SafeId
from toss_dashboard_api.contracts.responses import CompanyOverviewResponse, DataQualityResponse
from toss_dashboard_api.errors import NotFoundError, ServiceUnavailableError

router = APIRouter(prefix="/api/v1/companies", tags=["companies"])


@router.get("/{issuer_id}/overview", response_model=CompanyOverviewResponse)
def company_overview(issuer_id: SafeId, request: Request) -> CompanyOverviewResponse:
    try:
        overview = request.app.state.analytics_repository.company_overview(issuer_id)
    except Exception as exc:
        raise ServiceUnavailableError("Company fixture data is unavailable") from exc
    if overview is None:
        raise NotFoundError("issuer")
    return CompanyOverviewResponse(
        contract_version="0.1.0",
        data_mode="FIXTURE",
        data=overview,
    )


@router.get("/{issuer_id}/data-quality", response_model=DataQualityResponse)
def company_data_quality(issuer_id: SafeId, request: Request) -> DataQualityResponse:
    repository = request.app.state.metadata_repository
    try:
        if not repository.issuer_exists(issuer_id):
            raise NotFoundError("issuer")
        records = repository.data_quality_for_issuer(issuer_id)
    except NotFoundError:
        raise
    except Exception as exc:
        raise ServiceUnavailableError("Data quality metadata is unavailable") from exc
    return DataQualityResponse(
        contract_version="0.1.0",
        data_mode="FIXTURE",
        issuer_id=issuer_id,
        data=records,
        count=len(records),
    )
