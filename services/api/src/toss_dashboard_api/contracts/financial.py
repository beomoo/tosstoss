from datetime import date
from typing import Self

from pydantic import model_validator

from toss_dashboard_api.contracts.base import DecimalString, NormalizedRecord, SafeId
from toss_dashboard_api.contracts.enums import (
    Consolidation,
    Currency,
    FinalityStatus,
    ReportType,
    RevisionStatus,
    StatementType,
)


class FinancialFact(NormalizedRecord):
    financial_fact_id: SafeId
    issuer_id: SafeId
    report_type: ReportType
    fiscal_period: str
    statement: StatementType
    account_code: str
    account_name_original: str
    value: DecimalString | None
    currency: Currency
    unit_scale: DecimalString
    consolidation: Consolidation
    period_start: date
    period_end: date
    source_record_id: SafeId
    finality_status: FinalityStatus
    revision_status: RevisionStatus

    @model_validator(mode="after")
    def validate_period_and_value(self) -> Self:
        self.require_missing_reasons("value")
        if self.period_start > self.period_end:
            raise ValueError("period_start must not be after period_end")
        if self.unit_scale <= 0:
            raise ValueError("unit_scale must be positive")
        return self
