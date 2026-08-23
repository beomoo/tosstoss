from pydantic import Field

from toss_dashboard_api.contracts.base import SafeId, StrictContract
from toss_dashboard_api.contracts.evidence import Evidence
from toss_dashboard_api.contracts.filing import FilingDocument, FilingSentenceChange
from toss_dashboard_api.contracts.financial import FinancialFact
from toss_dashboard_api.contracts.institution import (
    InstitutionHolding,
    InstitutionHoldingChange,
    InstitutionManager,
)
from toss_dashboard_api.contracts.issuer import Issuer
from toss_dashboard_api.contracts.market import DailyMarketFlow, PriceBar
from toss_dashboard_api.contracts.quality import DataQualityStatus
from toss_dashboard_api.contracts.security import Security
from toss_dashboard_api.contracts.valuation import ValuationScenario


class CompanyOverview(StrictContract):
    issuer: Issuer
    selected_security_id: SafeId
    security: Security
    price_bars: list[PriceBar] = Field(default_factory=list)
    market_flows: list[DailyMarketFlow] = Field(default_factory=list)
    financial_facts: list[FinancialFact] = Field(default_factory=list)
    institution_managers: list[InstitutionManager] = Field(default_factory=list)
    institution_holdings: list[InstitutionHolding] = Field(default_factory=list)
    institution_holding_changes: list[InstitutionHoldingChange] = Field(default_factory=list)
    filing_documents: list[FilingDocument] = Field(default_factory=list)
    filing_sentence_changes: list[FilingSentenceChange] = Field(default_factory=list)
    valuation_scenarios: list[ValuationScenario] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    data_quality: list[DataQualityStatus] = Field(default_factory=list)
