from datetime import date
from typing import Annotated, Self

from pydantic import StringConstraints, model_validator

from toss_dashboard_api.contracts.base import NormalizedRecord, SafeId
from toss_dashboard_api.contracts.enums import Currency, MappingStatus, Market, ShareClass

Symbol = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)]


class Security(NormalizedRecord):
    security_id: SafeId
    issuer_id: SafeId
    market: Market
    exchange: Symbol
    ticker: Symbol
    share_class: ShareClass
    currency: Currency
    cusip: str | None
    isin: str | None
    figi: str | None
    mapping_status: MappingStatus
    valid_from: date | None
    valid_to: date | None

    @model_validator(mode="after")
    def validate_security(self) -> Self:
        self.require_missing_reasons("cusip", "isin", "figi", "valid_from", "valid_to")
        if self.market == Market.KR and self.currency != Currency.KRW:
            raise ValueError("KR fixtures must use KRW")
        if self.market == Market.US and self.currency != Currency.USD:
            raise ValueError("US fixtures must use USD")
        if self.valid_from and self.valid_to and self.valid_from > self.valid_to:
            raise ValueError("valid_from must not be after valid_to")
        return self
