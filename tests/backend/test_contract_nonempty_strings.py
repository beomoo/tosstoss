from __future__ import annotations

import json

import pytest
from pydantic import BaseModel, ValidationError
from tests.backend.conftest import FIXTURE_DIR

from toss_dashboard_api.contracts.evidence import Evidence
from toss_dashboard_api.contracts.filing import FilingDocument, FilingSentenceChange
from toss_dashboard_api.contracts.financial import FinancialFact
from toss_dashboard_api.contracts.institution import (
    InstitutionHolding,
    InstitutionHoldingChange,
)
from toss_dashboard_api.contracts.issuer import Issuer
from toss_dashboard_api.contracts.packet import PacketExtensions
from toss_dashboard_api.contracts.quality import DataQualityStatus
from toss_dashboard_api.contracts.security import Security
from toss_dashboard_api.contracts.source import SourceRecord
from toss_dashboard_api.contracts.valuation import ValuationScenario


def _fixture_payload(filename: str, index: int = 0) -> dict[str, object]:
    payload = json.loads((FIXTURE_DIR / filename).read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload[index]
    if isinstance(payload, dict):
        return payload
    raise AssertionError(f"unsupported fixture shape: {filename}")


@pytest.mark.parametrize(
    ("model", "filename", "field"),
    [
        (Evidence, "evidence.json", "claim"),
        (FinancialFact, "financial_facts.json", "account_name_original"),
        (FilingSentenceChange, "filing_sentence_changes.json", "section_key"),
        (InstitutionHolding, "institution_holdings.json", "issuer_name_original"),
        (SourceRecord, "source_records.json", "external_id"),
        (ValuationScenario, "valuation_scenarios.json", "formula_version"),
        (DataQualityStatus, "data_quality_statuses.json", "dataset"),
    ],
)
def test_required_business_text_rejects_blank_or_whitespace(
    model: type[BaseModel], filename: str, field: str
) -> None:
    payload = _fixture_payload(filename)
    payload[field] = " \t "

    with pytest.raises(ValidationError, match=field):
        model.model_validate_json(json.dumps(payload, ensure_ascii=False))


@pytest.mark.parametrize(
    ("model", "filename", "index", "field"),
    [
        (Issuer, "issuers.json", 0, "corp_code"),
        (Security, "securities.json", 1, "cusip"),
        (Evidence, "evidence.json", 0, "source_excerpt"),
        (InstitutionHolding, "institution_holdings.json", 0, "put_call"),
        (DataQualityStatus, "data_quality_statuses.json", 2, "error_message"),
    ],
)
def test_nullable_business_text_rejects_blank_or_whitespace(
    model: type[BaseModel], filename: str, index: int, field: str
) -> None:
    payload = _fixture_payload(filename, index)
    payload[field] = "   "

    with pytest.raises(ValidationError, match=field):
        model.model_validate_json(json.dumps(payload, ensure_ascii=False))


@pytest.mark.parametrize(
    ("model", "filename", "field"),
    [
        (FilingSentenceChange, "filing_sentence_changes.json", "rule_hits"),
        (InstitutionHoldingChange, "institution_holding_changes.json", "limitations"),
        (DataQualityStatus, "data_quality_statuses.json", "quality_flags"),
    ],
)
def test_business_text_list_rejects_blank_entries(
    model: type[BaseModel], filename: str, field: str
) -> None:
    payload = _fixture_payload(filename)
    payload[field] = ["VALID_ENTRY", "  "]

    with pytest.raises(ValidationError, match=field):
        model.model_validate_json(json.dumps(payload, ensure_ascii=False))


@pytest.mark.parametrize("invalid_mapping", [{" ": "value"}, {"key": "\t"}])
def test_extension_text_mapping_rejects_blank_keys_or_values(
    invalid_mapping: dict[str, str],
) -> None:
    packet = _fixture_payload("analysis_packet.json")
    extensions = packet["extensions"]
    assert isinstance(extensions, dict)
    extensions["hypotheses"] = [invalid_mapping]

    with pytest.raises(ValidationError, match="hypotheses"):
        PacketExtensions.model_validate_json(json.dumps(extensions, ensure_ascii=False))


def test_missing_reason_mapping_rejects_blank_keys() -> None:
    payload = _fixture_payload("issuers.json")
    missing_reasons = payload["missing_reasons"]
    assert isinstance(missing_reasons, dict)
    missing_reasons[" "] = "UNAVAILABLE"

    with pytest.raises(ValidationError, match="missing_reasons"):
        Issuer.model_validate_json(json.dumps(payload, ensure_ascii=False))


@pytest.mark.parametrize(
    ("model", "filename", "field"),
    [
        (SourceRecord, "source_records.json", "supersedes_id"),
        (FilingDocument, "filing_documents.json", "supersedes_filing_id"),
    ],
)
def test_null_revision_relationship_requires_missing_reason(
    model: type[BaseModel], filename: str, field: str
) -> None:
    payload = _fixture_payload(filename)
    missing_reasons = payload["missing_reasons"]
    assert isinstance(missing_reasons, dict)
    del missing_reasons[field]

    with pytest.raises(ValidationError, match=field):
        model.model_validate_json(json.dumps(payload, ensure_ascii=False))


@pytest.mark.parametrize(
    ("model", "filename", "field"),
    [
        (SourceRecord, "source_records.json", "supersedes_id"),
        (FilingDocument, "filing_documents.json", "supersedes_filing_id"),
    ],
)
def test_present_revision_relationship_rejects_stale_missing_reason(
    model: type[BaseModel], filename: str, field: str
) -> None:
    payload = _fixture_payload(filename, 1)
    missing_reasons = payload["missing_reasons"]
    assert isinstance(missing_reasons, dict)
    missing_reasons[field] = "NOT_APPLICABLE"

    with pytest.raises(ValidationError, match=field):
        model.model_validate_json(json.dumps(payload, ensure_ascii=False))


def test_business_text_is_trimmed_before_storage() -> None:
    payload = _fixture_payload("evidence.json")
    payload["claim"] = "  합성 근거 문장  "

    record = Evidence.model_validate_json(json.dumps(payload, ensure_ascii=False))

    assert record.claim == "합성 근거 문장"
