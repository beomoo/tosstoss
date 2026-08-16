from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any, Self, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

from toss_dashboard_api.contracts.base import (
    NormalizedRecord,
    Sha256,
    UtcDatetime,
    normalized_hash,
    sha256_prefixed,
)
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
from toss_dashboard_api.contracts.packet import AnalysisPacket
from toss_dashboard_api.contracts.quality import DataQualityStatus
from toss_dashboard_api.contracts.security import Security
from toss_dashboard_api.contracts.source import SourceRecord
from toss_dashboard_api.contracts.valuation import ValuationScenario
from toss_dashboard_api.domain.overview import CompanyOverview


class FixtureManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    contract_version: str
    fixture_version: str
    data_mode: str
    generated_at: UtcDatetime
    files: dict[str, Sha256] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_manifest(self) -> Self:
        if self.contract_version != "0.1.0" or self.fixture_version != "0.1.0":
            raise ValueError("unsupported fixture or contract version")
        if self.data_mode != "FIXTURE":
            raise ValueError("fixture manifest must declare FIXTURE mode")
        for relative in self.files:
            path = Path(relative)
            if path.is_absolute() or ".." in path.parts or "\\" in relative:
                raise ValueError("manifest paths must be normalized relative paths")
        return self


class FixtureValidationError(ValueError):
    pass


REQUIRED_FIXTURE_FILES = frozenset(
    {
        "analysis_packet.json",
        "daily_market_flows.json",
        "data_quality_statuses.json",
        "evidence.json",
        "filing_documents.json",
        "filing_sentence_changes.json",
        "financial_facts.json",
        "institution_holding_changes.json",
        "institution_holdings.json",
        "institution_managers.json",
        "issuers.json",
        "price_bars.json",
        "raw/financial_snapshot.fixture.json",
        "raw/kr_filing_amended.fixture.json",
        "raw/kr_filing_original.fixture.json",
        "raw/market_snapshot.fixture.json",
        "raw/us_holding.fixture.json",
        "securities.json",
        "source_records.json",
        "valuation_scenarios.json",
    }
)


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FixtureValidationError(f"invalid fixture file: {path.name}") from exc


def _load_records[RecordT: BaseModel](
    directory: Path, filename: str, model: type[RecordT]
) -> list[RecordT]:
    raw = _load_json(directory / filename)
    if not isinstance(raw, list):
        raise FixtureValidationError(f"{filename} must contain a JSON array")
    records: list[RecordT] = []
    for item in raw:
        records.append(model.model_validate_json(json.dumps(item, ensure_ascii=False)))
    return records


def _assert_unique(records: Sequence[BaseModel], field: str) -> None:
    values = [getattr(record, field) for record in records]
    if len(values) != len(set(values)):
        raise FixtureValidationError(f"duplicate {field}")


def _assert_unique_key(records: Sequence[BaseModel], dataset: str, fields: tuple[str, ...]) -> None:
    seen: set[tuple[object, ...]] = set()
    for record in records:
        key = tuple(getattr(record, field) for field in fields)
        if key in seen:
            raise FixtureValidationError(f"duplicate {dataset} natural key: {fields}")
        seen.add(key)


def _assert_no_cycles(records: Sequence[BaseModel], id_field: str, parent_field: str) -> None:
    parents = {
        cast(str, getattr(record, id_field)): cast(str | None, getattr(record, parent_field))
        for record in records
    }
    for node in parents:
        seen: set[str] = set()
        cursor: str | None = node
        while cursor is not None:
            if cursor in seen:
                raise FixtureValidationError(f"revision cycle detected for {node}")
            seen.add(cursor)
            cursor = parents.get(cursor)


class FixtureRepository:
    """Validated, immutable JSON analytics repository."""

    def __init__(self, fixture_dir: Path) -> None:
        self.fixture_dir = fixture_dir.resolve()
        manifest_raw = (self.fixture_dir / "manifest.json").read_text(encoding="utf-8")
        self.manifest = FixtureManifest.model_validate_json(manifest_raw)
        self.manifest_digest = sha256_prefixed(manifest_raw.encode("utf-8"))
        self._verify_manifest_files()

        self.issuers = _load_records(self.fixture_dir, "issuers.json", Issuer)
        self.securities = _load_records(self.fixture_dir, "securities.json", Security)
        self.source_records = _load_records(self.fixture_dir, "source_records.json", SourceRecord)
        self.price_bars = _load_records(self.fixture_dir, "price_bars.json", PriceBar)
        self.market_flows = _load_records(
            self.fixture_dir, "daily_market_flows.json", DailyMarketFlow
        )
        self.financial_facts = _load_records(
            self.fixture_dir, "financial_facts.json", FinancialFact
        )
        self.institution_managers = _load_records(
            self.fixture_dir, "institution_managers.json", InstitutionManager
        )
        self.institution_holdings = _load_records(
            self.fixture_dir, "institution_holdings.json", InstitutionHolding
        )
        self.institution_holding_changes = _load_records(
            self.fixture_dir,
            "institution_holding_changes.json",
            InstitutionHoldingChange,
        )
        self.filing_documents = _load_records(
            self.fixture_dir, "filing_documents.json", FilingDocument
        )
        self.filing_sentence_changes = _load_records(
            self.fixture_dir, "filing_sentence_changes.json", FilingSentenceChange
        )
        self.valuation_scenarios = _load_records(
            self.fixture_dir, "valuation_scenarios.json", ValuationScenario
        )
        self.evidence = _load_records(self.fixture_dir, "evidence.json", Evidence)
        self.data_quality_statuses = _load_records(
            self.fixture_dir, "data_quality_statuses.json", DataQualityStatus
        )
        packet_raw = _load_json(self.fixture_dir / "analysis_packet.json")
        self.packet = AnalysisPacket.model_validate_json(json.dumps(packet_raw, ensure_ascii=False))
        self._validate_records()

    def _verify_manifest_files(self) -> None:
        declared_files = set(self.manifest.files)
        if declared_files != REQUIRED_FIXTURE_FILES:
            missing = sorted(REQUIRED_FIXTURE_FILES - declared_files)
            extra = sorted(declared_files - REQUIRED_FIXTURE_FILES)
            raise FixtureValidationError(
                f"manifest file set mismatch: missing={missing}, extra={extra}"
            )
        for relative, expected in self.manifest.files.items():
            path = (self.fixture_dir / relative).resolve()
            if self.fixture_dir not in path.parents:
                raise FixtureValidationError("manifest path escaped fixture directory")
            if not path.is_file():
                raise FixtureValidationError(f"manifest file is missing: {relative}")
            actual = sha256_prefixed(path.read_bytes())
            if actual != expected:
                raise FixtureValidationError(f"manifest hash mismatch: {relative}")

    def _validate_records(self) -> None:
        groups: list[tuple[list[NormalizedRecord], str]] = [
            (cast(list[NormalizedRecord], self.issuers), "issuer_id"),
            (cast(list[NormalizedRecord], self.securities), "security_id"),
            (cast(list[NormalizedRecord], self.source_records), "source_record_id"),
            (cast(list[NormalizedRecord], self.price_bars), "price_bar_id"),
            (cast(list[NormalizedRecord], self.market_flows), "market_flow_id"),
            (cast(list[NormalizedRecord], self.financial_facts), "financial_fact_id"),
            (cast(list[NormalizedRecord], self.institution_managers), "manager_id"),
            (cast(list[NormalizedRecord], self.institution_holdings), "holding_id"),
            (
                cast(list[NormalizedRecord], self.institution_holding_changes),
                "holding_change_id",
            ),
            (cast(list[NormalizedRecord], self.filing_documents), "filing_id"),
            (cast(list[NormalizedRecord], self.filing_sentence_changes), "change_id"),
            (cast(list[NormalizedRecord], self.valuation_scenarios), "valuation_scenario_id"),
            (cast(list[NormalizedRecord], self.evidence), "evidence_id"),
            (cast(list[NormalizedRecord], self.data_quality_statuses), "quality_status_id"),
        ]
        for records, id_field in groups:
            _assert_unique(records, id_field)
            for record in records:
                if normalized_hash(record) != record.normalized_content_hash:
                    raise FixtureValidationError(
                        f"normalized hash mismatch: {getattr(record, id_field)}"
                    )
        natural_keys: list[tuple[Sequence[BaseModel], str, tuple[str, ...]]] = [
            (self.issuers, "Issuer", ("jurisdiction", "corp_code", "cik")),
            (
                self.securities,
                "Security",
                ("market", "exchange", "ticker", "share_class"),
            ),
            (
                self.source_records,
                "SourceRecord",
                ("source_system", "source_type", "external_id"),
            ),
            (
                self.price_bars,
                "PriceBar",
                ("security_id", "interval", "bar_start", "adjustment_status"),
            ),
            (
                self.market_flows,
                "DailyMarketFlow",
                ("security_id", "trade_date", "participant"),
            ),
            (
                self.financial_facts,
                "FinancialFact",
                (
                    "issuer_id",
                    "report_type",
                    "fiscal_period",
                    "statement",
                    "account_code",
                    "consolidation",
                    "period_start",
                    "period_end",
                ),
            ),
            (self.institution_managers, "InstitutionManager", ("cik",)),
            (
                self.institution_holdings,
                "InstitutionHolding",
                (
                    "filing_id",
                    "manager_id",
                    "security_id",
                    "cusip_original",
                    "title_of_class",
                    "put_call",
                ),
            ),
            (
                self.institution_holding_changes,
                "InstitutionHoldingChange",
                ("manager_id", "security_id", "previous_period", "current_period"),
            ),
            (
                self.filing_documents,
                "FilingDocument",
                ("issuer_id", "form_type", "period_end", "source_record_id"),
            ),
            (
                self.filing_sentence_changes,
                "FilingSentenceChange",
                (
                    "issuer_id",
                    "previous_filing_id",
                    "current_filing_id",
                    "section_key",
                    "previous_sentence",
                    "current_sentence",
                ),
            ),
            (
                self.valuation_scenarios,
                "ValuationScenario",
                ("valuation_run_id", "scenario"),
            ),
            (
                self.evidence,
                "Evidence",
                (
                    "issuer_id",
                    "evidence_basis",
                    "claim",
                    "observed_at",
                    "source_record_id",
                ),
            ),
            (
                self.data_quality_statuses,
                "DataQualityStatus",
                ("issuer_id", "source_system", "dataset"),
            ),
        ]
        for natural_records, dataset, fields in natural_keys:
            _assert_unique_key(natural_records, dataset, fields)
        if normalized_hash(self.packet) != self.packet.normalized_content_hash:
            raise FixtureValidationError("normalized hash mismatch: analysis packet")

        issuer_by_id = {item.issuer_id: item for item in self.issuers}
        security_by_id = {item.security_id: item for item in self.securities}
        source_by_id = {item.source_record_id: item for item in self.source_records}
        issuer_ids = set(issuer_by_id)
        security_ids = set(security_by_id)
        source_ids = set(source_by_id)
        manager_ids = {item.manager_id for item in self.institution_managers}
        filing_by_id = {item.filing_id: item for item in self.filing_documents}
        filing_ids = set(filing_by_id)
        evidence_ids = {item.evidence_id for item in self.evidence}

        for security_item in self.securities:
            self._require(
                security_item.issuer_id in issuer_ids, security_item.security_id, "issuer_id"
            )
            self._require(
                security_item.market.value
                == issuer_by_id[security_item.issuer_id].jurisdiction.value,
                security_item.security_id,
                "market",
            )
        for source in self.source_records:
            if source.supersedes_id:
                self._require(
                    source.supersedes_id in source_ids,
                    source.source_record_id,
                    "supersedes_id",
                )
                previous_source = source_by_id[source.supersedes_id]
                self._require(
                    previous_source.source_system == source.source_system
                    and previous_source.source_type == source.source_type,
                    source.source_record_id,
                    "supersedes_id",
                )
        for bar in self.price_bars:
            self._require(bar.security_id in security_ids, bar.price_bar_id, "security_id")
            self._require(bar.source_record_id in source_ids, bar.price_bar_id, "source_record_id")
            self._require(
                bar.currency == security_by_id[bar.security_id].currency,
                bar.price_bar_id,
                "currency",
            )
            self._require(
                source_by_id[bar.source_record_id].source_type.value == "MARKET_DATA",
                bar.price_bar_id,
                "source_record_id",
            )
        for flow in self.market_flows:
            self._require(flow.security_id in security_ids, flow.market_flow_id, "security_id")
            self._require(
                flow.source_record_id in source_ids, flow.market_flow_id, "source_record_id"
            )
            self._require(
                flow.currency == security_by_id[flow.security_id].currency,
                flow.market_flow_id,
                "currency",
            )
            self._require(
                source_by_id[flow.source_record_id].source_type.value == "MARKET_DATA",
                flow.market_flow_id,
                "source_record_id",
            )
        for fact in self.financial_facts:
            self._require(fact.issuer_id in issuer_ids, fact.financial_fact_id, "issuer_id")
            self._require(
                fact.source_record_id in source_ids, fact.financial_fact_id, "source_record_id"
            )
            self._require(
                source_by_id[fact.source_record_id].source_type.value == "FINANCIAL",
                fact.financial_fact_id,
                "source_record_id",
            )
        for manager in self.institution_managers:
            self._require(
                manager.reporting_manager_id in manager_ids,
                manager.manager_id,
                "reporting_manager_id",
            )
            if manager.parent_manager_id:
                self._require(
                    manager.parent_manager_id in manager_ids,
                    manager.manager_id,
                    "parent_manager_id",
                )
        for holding in self.institution_holdings:
            self._require(holding.manager_id in manager_ids, holding.holding_id, "manager_id")
            self._require(holding.security_id in security_ids, holding.holding_id, "security_id")
            self._require(
                holding.source_record_id in source_ids, holding.holding_id, "source_record_id"
            )
            self._require(
                source_by_id[holding.source_record_id].source_type.value == "HOLDING",
                holding.holding_id,
                "source_record_id",
            )
        for holding_change in self.institution_holding_changes:
            self._require(
                holding_change.manager_id in manager_ids,
                holding_change.holding_change_id,
                "manager_id",
            )
            self._require(
                holding_change.security_id in security_ids,
                holding_change.holding_change_id,
                "security_id",
            )
            current_holding = next(
                (
                    holding
                    for holding in self.institution_holdings
                    if holding.manager_id == holding_change.manager_id
                    and holding.security_id == holding_change.security_id
                    and holding.report_period == holding_change.current_period
                ),
                None,
            )
            self._require(
                current_holding is not None,
                holding_change.holding_change_id,
                "current_period",
            )
            self._require(
                current_holding is not None
                and current_holding.shares == holding_change.current_shares,
                holding_change.holding_change_id,
                "current_shares",
            )
            previous_holding = next(
                (
                    holding
                    for holding in self.institution_holdings
                    if holding.manager_id == holding_change.manager_id
                    and holding.security_id == holding_change.security_id
                    and holding.report_period == holding_change.previous_period
                ),
                None,
            )
            if previous_holding is not None:
                self._require(
                    previous_holding.shares == holding_change.previous_shares,
                    holding_change.holding_change_id,
                    "previous_shares",
                )
        for filing in self.filing_documents:
            self._require(filing.issuer_id in issuer_ids, filing.filing_id, "issuer_id")
            self._require(
                filing.source_record_id in source_ids, filing.filing_id, "source_record_id"
            )
            self._require(
                filing.jurisdiction == issuer_by_id[filing.issuer_id].jurisdiction,
                filing.filing_id,
                "jurisdiction",
            )
            self._require(
                source_by_id[filing.source_record_id].source_type.value == "FILING",
                filing.filing_id,
                "source_record_id",
            )
            if filing.supersedes_filing_id:
                self._require(
                    filing.supersedes_filing_id in filing_ids,
                    filing.filing_id,
                    "supersedes_filing_id",
                )
                previous_filing = filing_by_id[filing.supersedes_filing_id]
                self._require(
                    previous_filing.issuer_id == filing.issuer_id
                    and previous_filing.jurisdiction == filing.jurisdiction
                    and previous_filing.form_type == filing.form_type
                    and previous_filing.period_end == filing.period_end,
                    filing.filing_id,
                    "supersedes_filing_id",
                )
        for sentence_change in self.filing_sentence_changes:
            self._require(
                sentence_change.issuer_id in issuer_ids, sentence_change.change_id, "issuer_id"
            )
            self._require(
                sentence_change.previous_filing_id in filing_ids,
                sentence_change.change_id,
                "previous_filing_id",
            )
            self._require(
                sentence_change.current_filing_id in filing_ids,
                sentence_change.change_id,
                "current_filing_id",
            )
            self._require(
                filing_by_id[sentence_change.previous_filing_id].issuer_id
                == sentence_change.issuer_id,
                sentence_change.change_id,
                "previous_filing_id",
            )
            self._require(
                filing_by_id[sentence_change.current_filing_id].issuer_id
                == sentence_change.issuer_id,
                sentence_change.change_id,
                "current_filing_id",
            )
            self._require(
                filing_by_id[sentence_change.current_filing_id].supersedes_filing_id
                == sentence_change.previous_filing_id,
                sentence_change.change_id,
                "current_filing_id",
            )
        for evidence_item in self.evidence:
            self._require(
                evidence_item.issuer_id in issuer_ids, evidence_item.evidence_id, "issuer_id"
            )
            if evidence_item.source_record_id:
                self._require(
                    evidence_item.source_record_id in source_ids,
                    evidence_item.evidence_id,
                    "source_record_id",
                )
        for quality in self.data_quality_statuses:
            self._require(quality.issuer_id in issuer_ids, quality.quality_status_id, "issuer_id")
            if quality.source_record_id:
                self._require(
                    quality.source_record_id in source_ids,
                    quality.quality_status_id,
                    "source_record_id",
                )
                self._require(
                    source_by_id[quality.source_record_id].source_system == quality.source_system,
                    quality.quality_status_id,
                    "source_record_id",
                )

        input_records = [
            *(
                (item.price_bar_id, security_by_id[item.security_id].issuer_id, "PriceBar")
                for item in self.price_bars
            ),
            *(
                (
                    item.market_flow_id,
                    security_by_id[item.security_id].issuer_id,
                    "DailyMarketFlow",
                )
                for item in self.market_flows
            ),
            *(
                (item.financial_fact_id, item.issuer_id, "FinancialFact")
                for item in self.financial_facts
            ),
            *(
                (
                    item.holding_id,
                    security_by_id[item.security_id].issuer_id,
                    "InstitutionHolding",
                )
                for item in self.institution_holdings
            ),
            *(
                (
                    item.holding_change_id,
                    security_by_id[item.security_id].issuer_id,
                    "InstitutionHoldingChange",
                )
                for item in self.institution_holding_changes
            ),
            *((item.filing_id, item.issuer_id, "FilingDocument") for item in self.filing_documents),
            *(
                (item.change_id, item.issuer_id, "FilingSentenceChange")
                for item in self.filing_sentence_changes
            ),
            *((item.evidence_id, item.issuer_id, "Evidence") for item in self.evidence),
        ]
        input_owner_ids: dict[str, str] = {}
        input_datasets: dict[str, str] = {}
        for input_id, owner_id, dataset in input_records:
            if input_id in input_owner_ids:
                raise FixtureValidationError(
                    f"ambiguous input data ID {input_id}: {input_datasets[input_id]} and {dataset}"
                )
            input_owner_ids[input_id] = owner_id
            input_datasets[input_id] = dataset
        input_ids = set(input_owner_ids)
        for valuation in self.valuation_scenarios:
            self._require(
                valuation.issuer_id in issuer_ids, valuation.valuation_scenario_id, "issuer_id"
            )
            for valuation_input_id in valuation.input_data_ids:
                self._require(
                    valuation_input_id in input_ids,
                    valuation.valuation_scenario_id,
                    "input_data_ids",
                )
                self._require(
                    input_owner_ids[valuation_input_id] == valuation.issuer_id,
                    valuation.valuation_scenario_id,
                    "input_data_ids",
                )

        _assert_no_cycles(
            cast(list[BaseModel], self.source_records), "source_record_id", "supersedes_id"
        )
        _assert_no_cycles(
            cast(list[BaseModel], self.filing_documents),
            "filing_id",
            "supersedes_filing_id",
        )
        self._validate_raw_hashes()
        self._validate_probabilities()
        self._require(self.packet.issuer_id in issuer_ids, self.packet.packet_id, "issuer_id")
        self._require(
            self.packet.selected_security_id in security_ids,
            self.packet.packet_id,
            "selected_security_id",
        )
        self._require(
            security_by_id[self.packet.selected_security_id].issuer_id == self.packet.issuer_id,
            self.packet.packet_id,
            "selected_security_id",
        )
        for evidence_id in self.packet.evidence_ids:
            self._require(evidence_id in evidence_ids, self.packet.packet_id, "evidence_ids")
            self._require(
                next(item for item in self.evidence if item.evidence_id == evidence_id).issuer_id
                == self.packet.issuer_id,
                self.packet.packet_id,
                "evidence_ids",
            )
        for input_id in self.packet.input_data_ids:
            self._require(input_id in input_ids, self.packet.packet_id, "input_data_ids")
            self._require(
                input_owner_ids[input_id] == self.packet.issuer_id,
                self.packet.packet_id,
                "input_data_ids",
            )
        for entry in self.packet.source_manifest:
            self._require(
                entry.source_record_id in source_ids, self.packet.packet_id, "source_manifest"
            )
            self._require(
                entry.raw_content_hash == source_by_id[entry.source_record_id].raw_content_hash,
                self.packet.packet_id,
                "source_manifest.raw_content_hash",
            )

    def _validate_raw_hashes(self) -> None:
        for source in self.source_records:
            relative = source.raw_storage_ref.removeprefix("fixture-raw:")
            path = (self.fixture_dir / relative).resolve()
            if self.fixture_dir not in path.parents or not path.is_file():
                raise FixtureValidationError(f"invalid raw_storage_ref: {source.source_record_id}")
            if sha256_prefixed(path.read_bytes()) != source.raw_content_hash:
                raise FixtureValidationError(f"raw hash mismatch: {source.source_record_id}")

    def _validate_probabilities(self) -> None:
        totals: defaultdict[tuple[str, str], Decimal] = defaultdict(Decimal)
        scenarios: defaultdict[tuple[str, str], set[str]] = defaultdict(set)
        for item in self.valuation_scenarios:
            key = (item.issuer_id, item.valuation_run_id)
            totals[key] += item.probability
            scenarios[key].add(item.scenario.value)
        for key, total in totals.items():
            if total != Decimal("1.00"):
                raise FixtureValidationError(f"scenario probabilities must sum to 1.00: {key}")
            if scenarios[key] != {"BEAR", "BASE", "BULL"}:
                raise FixtureValidationError(f"scenario set must contain BEAR/BASE/BULL: {key}")

    @staticmethod
    def _require(condition: bool, record_id: str, field: str) -> None:
        if not condition:
            raise FixtureValidationError(f"invalid reference {record_id}.{field}")

    def company_overview(self, issuer_id: str) -> CompanyOverview | None:
        issuer = next((item for item in self.issuers if item.issuer_id == issuer_id), None)
        security = next((item for item in self.securities if item.issuer_id == issuer_id), None)
        if issuer is None or security is None:
            return None
        holdings = [
            item for item in self.institution_holdings if item.security_id == security.security_id
        ]
        manager_ids = {item.manager_id for item in holdings}
        return CompanyOverview(
            contract_version="0.1.0",
            issuer=issuer,
            selected_security_id=security.security_id,
            security=security,
            price_bars=[
                item for item in self.price_bars if item.security_id == security.security_id
            ],
            market_flows=[
                item for item in self.market_flows if item.security_id == security.security_id
            ],
            financial_facts=[item for item in self.financial_facts if item.issuer_id == issuer_id],
            institution_managers=[
                item for item in self.institution_managers if item.manager_id in manager_ids
            ],
            institution_holdings=holdings,
            institution_holding_changes=[
                item
                for item in self.institution_holding_changes
                if item.security_id == security.security_id
            ],
            filing_documents=[
                item for item in self.filing_documents if item.issuer_id == issuer_id
            ],
            filing_sentence_changes=[
                item for item in self.filing_sentence_changes if item.issuer_id == issuer_id
            ],
            valuation_scenarios=[
                item for item in self.valuation_scenarios if item.issuer_id == issuer_id
            ],
            evidence=[item for item in self.evidence if item.issuer_id == issuer_id],
            data_quality=[
                item for item in self.data_quality_statuses if item.issuer_id == issuer_id
            ],
        )

    def analysis_packet(self) -> AnalysisPacket | None:
        return self.packet
