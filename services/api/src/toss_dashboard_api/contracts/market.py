from datetime import date
from typing import Self

from pydantic import model_validator

from toss_dashboard_api.contracts.base import DecimalString, NormalizedRecord, SafeId, UtcDatetime
from toss_dashboard_api.contracts.enums import (
    AdjustmentStatus,
    Currency,
    FinalityStatus,
    FreshnessStatus,
    Participant,
    RevisionStatus,
)


class PriceBar(NormalizedRecord):
    price_bar_id: SafeId
    security_id: SafeId
    interval: str
    bar_start: UtcDatetime
    exchange_trade_date: date
    open: DecimalString
    high: DecimalString
    low: DecimalString
    close: DecimalString
    volume: DecimalString
    currency: Currency
    adjustment_status: AdjustmentStatus
    source_record_id: SafeId
    freshness_status: FreshnessStatus
    finality_status: FinalityStatus
    revision_status: RevisionStatus

    @model_validator(mode="after")
    def validate_bar(self) -> Self:
        if self.interval != "1d":
            raise ValueError("Phase 1 supports fixture 1d bars only")
        if self.volume < 0:
            raise ValueError("volume must not be negative")
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("high must be at least open, close, and low")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("low must be at most open, close, and high")
        return self


class DailyMarketFlow(NormalizedRecord):
    market_flow_id: SafeId
    security_id: SafeId
    trade_date: date
    participant: Participant
    net_quantity: DecimalString | None
    net_value: DecimalString | None
    currency: Currency
    provisional: bool
    source_record_id: SafeId
    freshness_status: FreshnessStatus
    finality_status: FinalityStatus
    revision_status: RevisionStatus

    @model_validator(mode="after")
    def validate_missing_values(self) -> Self:
        self.require_missing_reasons("net_quantity", "net_value")
        return self
