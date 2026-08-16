from datetime import date
from typing import Annotated, Self

from pydantic import StringConstraints, model_validator

from toss_dashboard_api.contracts.base import DecimalString, NormalizedRecord, SafeId
from toss_dashboard_api.contracts.enums import (
    Currency,
    HoldingChangeClass,
    ManagerType,
    MappingStatus,
    ReportingStructure,
    SampleResult,
)

InstitutionFilingId = Annotated[
    str,
    StringConstraints(pattern=r"^ifiling_[a-z0-9_]{3,119}$", max_length=128),
]


class InstitutionManager(NormalizedRecord):
    manager_id: SafeId
    display_name: str
    legal_name: str
    cik: str
    manager_type: ManagerType
    parent_manager_id: SafeId | None
    reporting_manager_id: SafeId
    reporting_structure: ReportingStructure
    signal_weight: DecimalString
    active_status: bool

    @model_validator(mode="after")
    def validate_manager(self) -> Self:
        self.require_missing_reasons("parent_manager_id")
        if not 0 <= self.signal_weight <= 1:
            raise ValueError("signal_weight must be between 0 and 1")
        return self


class InstitutionHolding(NormalizedRecord):
    holding_id: SafeId
    # Opaque institutional filing ID; this is intentionally not a FilingDocument FK.
    filing_id: InstitutionFilingId
    manager_id: SafeId
    security_id: SafeId
    cusip_original: str
    issuer_name_original: str
    title_of_class: str
    put_call: str | None
    report_period: date
    shares: DecimalString
    market_value_reported: DecimalString
    reported_currency: Currency
    reported_unit_scale: DecimalString
    portfolio_weight: DecimalString
    mapping_status: MappingStatus
    source_record_id: SafeId

    @model_validator(mode="after")
    def validate_holding(self) -> Self:
        self.require_missing_reasons("put_call")
        if self.shares < 0 or self.market_value_reported < 0:
            raise ValueError("holding quantities must not be negative")
        if self.reported_unit_scale <= 0:
            raise ValueError("reported_unit_scale must be positive")
        if not 0 <= self.portfolio_weight <= 1:
            raise ValueError("portfolio_weight must be between 0 and 1")
        return self


class InstitutionHoldingChange(NormalizedRecord):
    holding_change_id: SafeId
    manager_id: SafeId
    security_id: SafeId
    previous_period: date
    current_period: date
    previous_shares: DecimalString
    current_shares: DecimalString
    shares_delta: DecimalString
    shares_delta_pct: DecimalString | None
    weight_delta: DecimalString
    rank_delta: int
    change_class: HoldingChangeClass
    estimated_trade_effect: DecimalString | None
    confidence: DecimalString
    limitations: list[str]
    result_status: SampleResult

    @model_validator(mode="after")
    def validate_change(self) -> Self:
        self.require_missing_reasons("shares_delta_pct", "estimated_trade_effect")
        if self.previous_period >= self.current_period:
            raise ValueError("previous_period must be before current_period")
        if self.previous_shares < 0 or self.current_shares < 0:
            raise ValueError("snapshot share quantities must not be negative")
        if self.current_shares - self.previous_shares != self.shares_delta:
            raise ValueError("shares_delta must equal current minus previous shares")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        return self
