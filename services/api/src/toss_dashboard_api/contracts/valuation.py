from datetime import date
from typing import Self

from pydantic import model_validator

from toss_dashboard_api.contracts.base import DecimalString, NormalizedRecord, SafeId
from toss_dashboard_api.contracts.enums import (
    AssumptionSource,
    Currency,
    SampleResult,
    Scenario,
    ValuationMethod,
)


class ValuationScenario(NormalizedRecord):
    valuation_scenario_id: SafeId
    valuation_run_id: SafeId
    issuer_id: SafeId
    scenario: Scenario
    as_of: date
    method: ValuationMethod
    forecast_eps: DecimalString
    target_multiple: DecimalString
    implied_price: DecimalString
    currency: Currency
    unit_scale: DecimalString
    probability: DecimalString
    assumption_source: AssumptionSource
    formula_version: str
    input_data_ids: list[SafeId]
    result_status: SampleResult

    @model_validator(mode="after")
    def validate_scenario(self) -> Self:
        if not 0 <= self.probability <= 1:
            raise ValueError("probability must be between 0 and 1")
        if self.target_multiple < 0:
            raise ValueError("target_multiple must not be negative")
        if self.unit_scale <= 0:
            raise ValueError("unit_scale must be positive")
        if not self.input_data_ids:
            raise ValueError("input_data_ids must not be empty")
        return self
