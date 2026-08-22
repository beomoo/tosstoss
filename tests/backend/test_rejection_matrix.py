from __future__ import annotations

import copy
import hashlib
import json
import shutil
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError
from tests.backend.conftest import FIXTURE_DIR, INVALID_FIXTURE_DIR

from toss_dashboard_api.contracts.base import normalized_hash
from toss_dashboard_api.contracts.evidence import Evidence
from toss_dashboard_api.contracts.filing import FilingDocument, FilingSentenceChange
from toss_dashboard_api.contracts.financial import FinancialFact
from toss_dashboard_api.contracts.institution import (
    InstitutionHolding,
    InstitutionHoldingChange,
)
from toss_dashboard_api.contracts.issuer import Issuer
from toss_dashboard_api.contracts.market import DailyMarketFlow, PriceBar
from toss_dashboard_api.contracts.packet import AnalysisPacket
from toss_dashboard_api.contracts.quality import DataQualityStatus
from toss_dashboard_api.contracts.source import SourceRecord
from toss_dashboard_api.contracts.valuation import ValuationScenario
from toss_dashboard_api.fixtures.importer import FixtureImporter, ImportConflictError
from toss_dashboard_api.repositories.fixture import (
    FixtureRepository,
    FixtureValidationError,
    _assert_no_cycles,
)
from toss_dashboard_api.storage.database import session_factory


def _invalid_text(filename: str) -> str:
    return (INVALID_FIXTURE_DIR / filename).read_text(encoding="utf-8")


def _invalid_json(filename: str) -> object:
    return json.loads(_invalid_text(filename))


def _copy_fixture(workspace_tmp_path: Path) -> Path:
    destination = workspace_tmp_path / "fixture"
    shutil.copytree(FIXTURE_DIR, destination)
    return destination


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _refresh_manifest(directory: Path, filename: str) -> None:
    path = directory / filename
    digest = f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"
    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"][filename] = digest
    _write_json(manifest_path, manifest)


def _rehash_payload(model: type[BaseModel], payload: dict[str, object]) -> None:
    payload["normalized_content_hash"] = "sha256:" + "0" * 64
    record = model.model_validate_json(json.dumps(payload, ensure_ascii=False))
    payload["normalized_content_hash"] = normalized_hash(record)


def _mutate_record(
    directory: Path,
    filename: str,
    model: type[BaseModel],
    *,
    index: int = 0,
    updates: dict[str, object],
) -> None:
    path = directory / filename
    records = json.loads(path.read_text(encoding="utf-8"))
    records[index].update(updates)
    _rehash_payload(model, records[index])
    _write_json(path, records)
    _refresh_manifest(directory, filename)


def _mutate_packet(directory: Path, update: Callable[[dict[str, Any]], None]) -> None:
    path = directory / "analysis_packet.json"
    packet = json.loads(path.read_text(encoding="utf-8"))
    update(packet)
    _rehash_payload(AnalysisPacket, packet)
    _write_json(path, packet)
    _refresh_manifest(directory, "analysis_packet.json")


def test_rejection_01_required_stable_id_is_absent() -> None:
    with pytest.raises(ValidationError, match="issuer_id"):
        Issuer.model_validate_json(_invalid_text("required_id_absent.json"))


def test_rejection_02_naive_timestamp() -> None:
    with pytest.raises(ValidationError, match="timezone"):
        PriceBar.model_validate_json(_invalid_text("naive_timestamp.json"))


@pytest.mark.parametrize("token", ["100.25", "NaN", "Infinity", "-Infinity"])
def test_rejection_03_json_number_or_nonfinite_decimal(token: str) -> None:
    payload = _invalid_text("decimal_number.json").replace("100.25", token)
    with pytest.raises(ValidationError, match="open"):
        PriceBar.model_validate_json(payload)


def test_rejection_04_null_without_missing_reason() -> None:
    with pytest.raises(ValidationError, match="missing_reasons.cik"):
        Issuer.model_validate_json(_invalid_text("missing_reason_absent.json"))


def test_rejection_05_unknown_enum() -> None:
    with pytest.raises(ValidationError, match="jurisdiction"):
        Issuer.model_validate_json(_invalid_text("unknown_enum.json"))


def test_rejection_05_unknown_contract_version() -> None:
    payload = json.loads(_invalid_text("unknown_enum.json"))
    payload["jurisdiction"] = "KR"
    payload["contract_version"] = "0.2.0"
    with pytest.raises(ValidationError, match="contract_version"):
        Issuer.model_validate_json(json.dumps(payload))


def test_rejection_06_probability_out_of_range() -> None:
    with pytest.raises(ValidationError, match="probability"):
        ValuationScenario.model_validate_json(_invalid_text("probability_out_of_range.json"))


def test_rejection_06_probability_sum_not_one(workspace_tmp_path: Path) -> None:
    directory = _copy_fixture(workspace_tmp_path)
    _mutate_record(
        directory,
        "valuation_scenarios.json",
        ValuationScenario,
        updates={"probability": "0.21"},
    )
    with pytest.raises(FixtureValidationError, match="sum to 1.00"):
        FixtureRepository(directory)


def test_rejection_07_invalid_ohlc() -> None:
    with pytest.raises(ValidationError, match="high"):
        PriceBar.model_validate_json(_invalid_text("ohlc_high_below_low.json"))


def test_rejection_08_negative_records_count() -> None:
    with pytest.raises(ValidationError, match="records_received"):
        DataQualityStatus.model_validate_json(_invalid_text("negative_records_count.json"))


def test_rejection_09_period_inversion() -> None:
    with pytest.raises(ValidationError, match="period_start"):
        FinancialFact.model_validate_json(_invalid_text("period_inversion.json"))


@pytest.mark.parametrize(
    ("previous_shares", "current_shares", "shares_delta"),
    [("-1", "1", "2"), ("1", "-1", "-2")],
)
def test_institution_holding_change_rejects_negative_snapshot_shares(
    fixture_repository: FixtureRepository,
    previous_shares: str,
    current_shares: str,
    shares_delta: str,
) -> None:
    payload = fixture_repository.institution_holding_changes[0].model_dump(mode="json")
    payload.update(
        {
            "previous_shares": previous_shares,
            "current_shares": current_shares,
            "shares_delta": shares_delta,
        }
    )
    with pytest.raises(ValidationError, match="snapshot share quantities"):
        InstitutionHoldingChange.model_validate_json(json.dumps(payload))


def test_rejection_10_normalized_digest_mismatch(workspace_tmp_path: Path) -> None:
    invalid = _invalid_json("hash_mismatch.json")
    assert isinstance(invalid, dict)
    directory = _copy_fixture(workspace_tmp_path)
    path = directory / "issuers.json"
    records = json.loads(path.read_text(encoding="utf-8"))
    records[0]["normalized_content_hash"] = invalid["declared_hash"]
    _write_json(path, records)
    _refresh_manifest(directory, "issuers.json")
    with pytest.raises(FixtureValidationError, match="normalized hash mismatch"):
        FixtureRepository(directory)


def test_rejection_11_supersedes_cycle_from_invalid_fixture() -> None:
    raw = _invalid_json("revision_cycle.json")
    assert isinstance(raw, list)
    records = [SimpleNamespace(**item) for item in raw]
    with pytest.raises(FixtureValidationError, match="cycle"):
        _assert_no_cycles(records, "source_record_id", "supersedes_id")


def test_rejection_11_self_reference(fixture_repository: FixtureRepository) -> None:
    payload = fixture_repository.source_records[0].model_dump(mode="json")
    payload["supersedes_id"] = payload["source_record_id"]
    payload["missing_reasons"].pop("supersedes_id")
    with pytest.raises(ValidationError, match="supersede itself"):
        SourceRecord.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize(
    ("filename", "model", "index", "updates", "expected"),
    [
        (
            "price_bars.json",
            PriceBar,
            0,
            {"security_id": "security_missing"},
            "security_id",
        ),
        (
            "price_bars.json",
            PriceBar,
            0,
            {"source_record_id": "source_missing"},
            "source_record_id",
        ),
        (
            "financial_facts.json",
            FinancialFact,
            0,
            {"issuer_id": "issuer_missing"},
            "issuer_id",
        ),
        (
            "data_quality_statuses.json",
            DataQualityStatus,
            0,
            {"source_record_id": "source_missing"},
            "source_record_id",
        ),
        (
            "source_records.json",
            SourceRecord,
            1,
            {"supersedes_id": "source_missing"},
            "supersedes_id",
        ),
        (
            "institution_holdings.json",
            InstitutionHolding,
            0,
            {"manager_id": "manager_missing"},
            "manager_id",
        ),
    ],
)
def test_rejection_12_missing_cross_reference(
    workspace_tmp_path: Path,
    filename: str,
    model: type[BaseModel],
    index: int,
    updates: dict[str, object],
    expected: str,
) -> None:
    directory = _copy_fixture(workspace_tmp_path)
    _mutate_record(directory, filename, model, index=index, updates=updates)
    with pytest.raises(FixtureValidationError, match=expected):
        FixtureRepository(directory)


@pytest.mark.parametrize("locator", _invalid_json("unsafe_locators.json"))
def test_rejection_13_unsafe_locator(fixture_repository: FixtureRepository, locator: str) -> None:
    payload = fixture_repository.source_records[0].model_dump(mode="json")
    payload["source_locator"] = locator
    with pytest.raises(ValidationError, match="source locator"):
        SourceRecord.model_validate_json(json.dumps(payload))


def test_rejection_14_same_stable_id_different_hash(database_context) -> None:
    changed = database_context.analytics.issuers[0]
    database_context.analytics.issuers[0] = changed.model_copy(
        update={"normalized_content_hash": "sha256:" + "a" * 64}
    )
    with pytest.raises(ImportConflictError, match="stable ID conflict"):
        FixtureImporter(session_factory(database_context.engine)).import_repository(
            database_context.analytics
        )


@pytest.mark.parametrize(
    ("filename", "model", "id_field", "dataset"),
    [
        ("price_bars.json", PriceBar, "price_bar_id", "PriceBar"),
        ("daily_market_flows.json", DailyMarketFlow, "market_flow_id", "DailyMarketFlow"),
        ("financial_facts.json", FinancialFact, "financial_fact_id", "FinancialFact"),
        ("filing_documents.json", FilingDocument, "filing_id", "FilingDocument"),
        (
            "filing_sentence_changes.json",
            FilingSentenceChange,
            "change_id",
            "FilingSentenceChange",
        ),
        ("institution_holdings.json", InstitutionHolding, "holding_id", "InstitutionHolding"),
        (
            "institution_holding_changes.json",
            InstitutionHoldingChange,
            "holding_change_id",
            "InstitutionHoldingChange",
        ),
        (
            "valuation_scenarios.json",
            ValuationScenario,
            "valuation_scenario_id",
            "ValuationScenario",
        ),
        ("evidence.json", Evidence, "evidence_id", "Evidence"),
        (
            "data_quality_statuses.json",
            DataQualityStatus,
            "quality_status_id",
            "DataQualityStatus",
        ),
    ],
)
def test_dataset_natural_keys_are_unique(
    workspace_tmp_path: Path,
    filename: str,
    model: type[BaseModel],
    id_field: str,
    dataset: str,
) -> None:
    directory = _copy_fixture(workspace_tmp_path)
    path = directory / filename
    records = json.loads(path.read_text(encoding="utf-8"))
    duplicate = copy.deepcopy(records[0])
    duplicate[id_field] = f"duplicate_{duplicate[id_field]}"
    _rehash_payload(model, duplicate)
    records.append(duplicate)
    _write_json(path, records)
    _refresh_manifest(directory, filename)
    with pytest.raises(FixtureValidationError, match=f"duplicate {dataset} natural key"):
        FixtureRepository(directory)


@pytest.mark.parametrize(
    ("filename", "model", "updates", "expected"),
    [
        ("price_bars.json", PriceBar, {"currency": "USD"}, "currency"),
        (
            "filing_sentence_changes.json",
            FilingSentenceChange,
            {"issuer_id": "issuer_us_synthetic"},
            "previous_filing_id",
        ),
        (
            "valuation_scenarios.json",
            ValuationScenario,
            {"input_data_ids": ["holding_us_synthetic_2026q2"]},
            "input_data_ids",
        ),
        (
            "data_quality_statuses.json",
            DataQualityStatus,
            {"source_record_id": "source_us_holding"},
            "source_record_id",
        ),
        (
            "institution_holding_changes.json",
            InstitutionHoldingChange,
            {"current_period": "2026-09-30"},
            "current_period",
        ),
    ],
)
def test_cross_record_owner_and_semantic_consistency(
    workspace_tmp_path: Path,
    filename: str,
    model: type[BaseModel],
    updates: dict[str, object],
    expected: str,
) -> None:
    directory = _copy_fixture(workspace_tmp_path)
    _mutate_record(directory, filename, model, updates=updates)
    with pytest.raises(FixtureValidationError, match=expected):
        FixtureRepository(directory)


def test_filing_supersedes_must_describe_the_same_logical_document(
    workspace_tmp_path: Path,
) -> None:
    directory = _copy_fixture(workspace_tmp_path)
    _mutate_record(
        directory,
        "filing_documents.json",
        FilingDocument,
        index=1,
        updates={"period_end": "2026-09-30"},
    )
    with pytest.raises(FixtureValidationError, match="supersedes_filing_id"):
        FixtureRepository(directory)


def test_sentence_change_requires_a_direct_filing_revision_chain(
    workspace_tmp_path: Path,
) -> None:
    directory = _copy_fixture(workspace_tmp_path)
    _mutate_record(
        directory,
        "filing_sentence_changes.json",
        FilingSentenceChange,
        updates={
            "previous_filing_id": "filing_kr_synthetic_amended",
            "current_filing_id": "filing_kr_synthetic_original",
        },
    )
    with pytest.raises(FixtureValidationError, match="current_filing_id"):
        FixtureRepository(directory)


def test_holding_change_current_shares_match_current_holding(
    workspace_tmp_path: Path,
) -> None:
    directory = _copy_fixture(workspace_tmp_path)
    _mutate_record(
        directory,
        "institution_holding_changes.json",
        InstitutionHoldingChange,
        updates={"current_shares": "1000001", "shares_delta": "200001"},
    )
    with pytest.raises(FixtureValidationError, match="current_shares"):
        FixtureRepository(directory)


def test_holding_change_previous_shares_match_previous_holding(
    workspace_tmp_path: Path,
) -> None:
    directory = _copy_fixture(workspace_tmp_path)
    path = directory / "institution_holdings.json"
    holdings = json.loads(path.read_text(encoding="utf-8"))
    previous = copy.deepcopy(holdings[0])
    previous.update(
        {
            "holding_id": "holding_us_synthetic_2026q1",
            "filing_id": "ifiling_us_synthetic_2026q1",
            "report_period": "2026-03-31",
            "shares": "799999",
        }
    )
    _rehash_payload(InstitutionHolding, previous)
    holdings.append(previous)
    _write_json(path, holdings)
    _refresh_manifest(directory, "institution_holdings.json")
    with pytest.raises(FixtureValidationError, match="previous_shares"):
        FixtureRepository(directory)


def test_cross_dataset_stable_id_collision_is_ambiguous(
    workspace_tmp_path: Path,
) -> None:
    directory = _copy_fixture(workspace_tmp_path)
    _mutate_record(
        directory,
        "financial_facts.json",
        FinancialFact,
        updates={"financial_fact_id": "price_kr_20260813"},
    )
    with pytest.raises(FixtureValidationError, match="ambiguous input data ID"):
        FixtureRepository(directory)


@pytest.mark.parametrize("mode", ["missing", "extra"])
def test_manifest_declares_the_exact_required_file_set(workspace_tmp_path: Path, mode: str) -> None:
    directory = _copy_fixture(workspace_tmp_path)
    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if mode == "missing":
        del manifest["files"]["price_bars.json"]
    else:
        manifest["files"]["unexpected.json"] = "sha256:" + "0" * 64
    _write_json(manifest_path, manifest)
    with pytest.raises(FixtureValidationError, match="manifest file set mismatch"):
        FixtureRepository(directory)


@pytest.mark.parametrize(
    ("update", "expected"),
    [
        (
            lambda packet: packet.update({"selected_security_id": "security_us_synthetic_common"}),
            "selected_security_id",
        ),
        (
            lambda packet: packet.update({"evidence_ids": ["evidence_us_unconfirmed"]}),
            "evidence_ids",
        ),
        (
            lambda packet: packet.update({"input_data_ids": ["holding_us_synthetic_2026q2"]}),
            "input_data_ids",
        ),
        (
            lambda packet: packet["source_manifest"][0].update(
                {"raw_content_hash": "sha256:" + "a" * 64}
            ),
            "source_manifest.raw_content_hash",
        ),
    ],
)
def test_packet_provenance_and_owner_consistency(
    workspace_tmp_path: Path,
    update: Callable[[dict[str, Any]], None],
    expected: str,
) -> None:
    directory = _copy_fixture(workspace_tmp_path)
    _mutate_packet(directory, update)
    with pytest.raises(FixtureValidationError, match=expected):
        FixtureRepository(directory)


def test_institution_filing_id_is_an_independent_opaque_namespace(
    fixture_repository: FixtureRepository,
) -> None:
    holding = fixture_repository.institution_holdings[0]
    corporate_filing_ids = {item.filing_id for item in fixture_repository.filing_documents}
    assert holding.filing_id.startswith("ifiling_")
    assert holding.filing_id not in corporate_filing_ids
