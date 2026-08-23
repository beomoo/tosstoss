from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from toss_dashboard_api.contracts.base import (
    ApiEnvelopeBase,
    ContractVersion,
    NonEmptyText,
    SafeId,
    StrictContract,
)
from toss_dashboard_api.contracts.packet import AnalysisPacket
from toss_dashboard_api.contracts.quality import DataQualityStatus
from toss_dashboard_api.contracts.security import Security
from toss_dashboard_api.domain.overview import CompanyOverview


class HealthResponse(StrictContract):
    service: NonEmptyText
    version: NonEmptyText
    data_mode: Literal["FIXTURE"]
    status: NonEmptyText


class SafetyStatus(StrictContract):
    local_only: bool
    trading_enabled: bool
    dry_run: bool
    openai_api_enabled: bool
    allow_account_endpoints: bool


class SystemStatusResponse(ApiEnvelopeBase):
    service: NonEmptyText
    version: NonEmptyText
    status: NonEmptyText
    database_revision: NonEmptyText
    fixture_version: NonEmptyText
    safety: SafetyStatus


class SecuritiesResponse(ApiEnvelopeBase):
    data: list[Security]
    count: int = Field(ge=0)


class CompanyOverviewResponse(ApiEnvelopeBase):
    data: CompanyOverview


class DataQualityResponse(ApiEnvelopeBase):
    issuer_id: SafeId
    data: list[DataQualityStatus]
    count: int = Field(ge=0)


class AnalysisPacketResponse(ApiEnvelopeBase):
    data: AnalysisPacket


class ErrorBody(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    code: NonEmptyText
    message: NonEmptyText


class ErrorEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    contract_version: ContractVersion
    error: ErrorBody
    request_id: NonEmptyText
