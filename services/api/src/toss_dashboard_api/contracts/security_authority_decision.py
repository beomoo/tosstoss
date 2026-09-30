"""Typed C2 requests and normalized stored source facts."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

from toss_dashboard_api.contracts.base import SafeId, Sha256

FactText = Annotated[str, StringConstraints(min_length=1, max_length=2048)]
StockCode = Annotated[str, StringConstraints(pattern=r"^[0-9]{6}$")]
CorpCode = Annotated[str, StringConstraints(pattern=r"^[0-9]{8}$")]
Cik = Annotated[str, StringConstraints(pattern=r"^[0-9]{10}$")]
Accession = Annotated[str, StringConstraints(pattern=r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$")]
Isin = Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")]


class StrictSourceFact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    fact_version: Literal["security-normalized-source-fact/0.1.0"] = (
        "security-normalized-source-fact/0.1.0"
    )


class KrxStandardCodeFact(StrictSourceFact):
    stock_code: StockCode
    isin: Isin


class KrxIssueBasicFact(StrictSourceFact):
    stock_code: StockCode
    isin: Isin | None
    market: Literal["KOSPI", "KOSDAQ", "KONEX"]
    ticker: FactText
    security_type: FactText
    stock_kind: FactText
    listing_date: date | None
    nationality: FactText | None


class KrxListingLifecycleFact(StrictSourceFact):
    stock_code: StockCode
    market: Literal["KOSPI", "KOSDAQ", "KONEX"]
    ticker: FactText
    security_type: FactText | None
    stock_kind: FactText | None
    listing_date: date | None
    delisting_date: date | None
    delisting_reason: FactText | None
    nationality: FactText | None
    status: Literal["ACTIVE", "SUSPENDED", "DELISTED", "UNKNOWN"]


class OpenDartCorpCodeFact(StrictSourceFact):
    corp_code: CorpCode
    formal_name: FactText
    stock_code: StockCode
    modify_date: date


class SecAccepted8AFact(StrictSourceFact):
    registrant_cik: Cik
    accepted_accession: Accession
    accepted_at: datetime
    filing_document_digest: Sha256
    registered_class_title: FactText
    section_12_basis: FactText
    official_class_discriminator: FactText | None
    exchange_name: FactText | None


class SecAccepted25Fact(StrictSourceFact):
    registrant_cik: Cik
    accepted_accession: Accession
    accepted_at: datetime
    exchange_name: FactText
    class_description: FactText
    effective_date: date
    event_kind: Literal["REMOVAL", "WITHDRAWAL"]


class SecPeriodicCoverFact(StrictSourceFact):
    registrant_cik: Cik
    accepted_accession: Accession
    class_title: FactText
    ticker: FactText | None
    exchange_name: FactText | None


class NasdaqPrimaryFact(StrictSourceFact):
    symbol: FactText
    security_name: FactText
    market_category: FactText
    test_issue: bool
    financial_status: FactText | None
    file_creation_time: datetime
    listing_date: date | None
    state: Literal["ACTIVE", "ISSUE_DELETION", "ISSUE_SUSPENSION"]


class SecurityAuthorityEvaluationRequest(BaseModel):
    """The caller selects a provider identity only; all authority is reconstructed."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    provider_id: SafeId


class SecurityCollisionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    result: Literal["CLEAR", "CONFLICT"]
    reason_codes: tuple[str, ...]
    affected_provider_ids: tuple[SafeId, ...]
    digest: Sha256
