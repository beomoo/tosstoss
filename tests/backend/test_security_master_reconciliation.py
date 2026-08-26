from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from alembic import command
from pydantic import ValidationError
from tests.backend.conftest import alembic_config
from tests.backend.test_provider_repository import source_contract

from toss_dashboard_api.contracts.base import canonical_json_bytes
from toss_dashboard_api.contracts.enums import (
    Currency,
    Market,
    MissingReason,
    ProviderDataset,
    ProviderDetailBatchStatus,
    ProviderIdentifierKind,
    ProviderIdentifierReason,
    ProviderIdentityState,
    ProviderListingMarket,
    ProviderReconciliationOutcome,
    ProviderSecurityMasterState,
    ProviderSecurityStatus,
    ProviderSecurityType,
    RevisionStatus,
)
from toss_dashboard_api.contracts.provider_identity import (
    PROVIDER_IDENTITY_CONTRACT_VERSION,
    ProviderIdentifierHistory,
)
from toss_dashboard_api.contracts.provider_security_master import (
    TossKoreanMarketDetail,
    TossStockDetailItem,
    TossStockDetailResponse,
    TossStockDiscoveryItem,
    TossStockDiscoveryResponse,
)
from toss_dashboard_api.contracts.provider_source import (
    ProviderResponseMetadata,
    ProviderSourceVersion,
    build_canonical_request,
    build_provider_raw_manifest,
)
from toss_dashboard_api.domain.security_master import (
    SecurityMasterReconciliationService,
    SecurityMasterReplayInput,
)
from toss_dashboard_api.repositories.provider import (
    ProviderContractConflict,
    SQLiteProviderRepository,
)
from toss_dashboard_api.repositories.security_master import SQLiteSecurityMasterRepository
from toss_dashboard_api.storage.database import create_database_engine, session_factory
from toss_dashboard_api.storage.provider_raw import ProviderRawStore

NOW = datetime(2026, 8, 26, 1, 0, tzinfo=UTC)
KR_ISIN_A = "KRTESTA00000"
KR_ISIN_B = "KRTESTB00008"
KR_ISIN_C = "KRTESTC00006"
US_ISIN_A = "USTESTA00007"


def _source(
    engine,
    raw_root: Path,
    *,
    symbols: tuple[str, ...] = ("KRT001",),
    market: Market = Market.KR,
    raw_token: str,
    minute: int,
    prior: ProviderSourceVersion | None = None,
    discovery: bool = False,
) -> ProviderSourceVersion:
    sessions = session_factory(engine)
    raw_store = ProviderRawStore(raw_root)
    repository = SQLiteProviderRepository(sessions, raw_store)
    path = "/api/v1/stocks/all" if discovery else "/api/v1/stocks"
    query: dict[str, object] = {"market": market.value} if discovery else {"symbols": symbols}
    request = build_canonical_request(path, query)  # type: ignore[arg-type]
    raw = raw_store.persist(raw_token.encode("ascii"))
    manifest = build_provider_raw_manifest(
        request=request,
        http_status=200,
        raw_content_hash=raw.raw_content_hash,
        raw_storage_ref=raw.raw_storage_ref,
        fetched_at=NOW + timedelta(minutes=minute),
        response_metadata=ProviderResponseMetadata(content_type="application/json"),
        parser_version="toss-source-parser/0.1.0",
    )
    repository.insert_or_verify_canonical_request(request)
    repository.insert_or_verify_raw_manifest(manifest)
    dataset = ProviderDataset.STOCK_DISCOVERY if discovery else ProviderDataset.STOCK_DETAIL
    source = source_contract(
        request=request,
        manifest=manifest,
        revision_status=(RevisionStatus.ORIGINAL if prior is None else RevisionStatus.AMENDED),
        supersedes_id=None if prior is None else prior.source_version_id,
        dataset=dataset,
        source_locator=(
            "provider://toss-open-api/market/stock-discovery"
            if discovery
            else "provider://toss-open-api/market/stock-detail"
        ),
    )
    repository.append_source_version(source)
    return source


def _service(engine) -> SecurityMasterReconciliationService:
    return SecurityMasterReconciliationService(
        SQLiteSecurityMasterRepository(session_factory(engine))
    )


def _detail(
    symbol: str,
    *,
    isin: str | None = KR_ISIN_A,
    list_date: date | None = date(2020, 1, 2),
    name: str = "테스트 알파",
    market: ProviderListingMarket = ProviderListingMarket.KOSPI,
    security_type: ProviderSecurityType = ProviderSecurityType.STOCK,
    common: bool = True,
    status: ProviderSecurityStatus = ProviderSecurityStatus.ACTIVE,
    currency: Currency = Currency.KRW,
    delist_date: date | None = None,
) -> TossStockDetailItem:
    return TossStockDetailItem(
        symbol=symbol,
        name=name,
        englishName="Test Alpha",
        isinCode=isin,
        market=market,
        securityType=security_type,
        isCommonShare=common,
        status=status,
        currency=currency,
        listDate=list_date,
        delistDate=delist_date,
        sharesOutstanding="1000000",
        leverageFactor=None,
        koreanMarketDetail=(
            None
            if currency == Currency.USD
            else TossKoreanMarketDetail(
                liquidationTrading=False,
                nxtSupported=False,
                krxTradingSuspended=False,
                nxtTradingSuspended=None,
            )
        ),
    )


def _discovery_item(
    symbol: str, *, isin: str | None = KR_ISIN_A, name: str = "테스트 알파"
) -> TossStockDiscoveryItem:
    return TossStockDiscoveryItem(
        symbol=symbol,
        name=name,
        securityType=ProviderSecurityType.STOCK,
        isCommonShare=True,
        isinCode=isin,
    )


def _reconcile(
    service: SecurityMasterReconciliationService,
    source: ProviderSourceVersion,
    *items: TossStockDetailItem,
    market: Market = Market.KR,
):
    return service.reconcile_detail(
        source_version_id=source.source_version_id,
        market=market,
        response=TossStockDetailResponse(result=list(items)),
    )


def _repository(engine) -> SQLiteSecurityMasterRepository:
    return SQLiteSecurityMasterRepository(session_factory(engine))


def test_cp3_c1_offline_fixtures_are_strict_and_non_identifying() -> None:
    fixture_root = Path("fixtures/phase_02/cp3_c1")
    kr_discovery = TossStockDiscoveryResponse.model_validate_json(
        (fixture_root / "stock_discovery_kr.json").read_text(encoding="utf-8")
    )
    us_discovery = TossStockDiscoveryResponse.model_validate_json(
        (fixture_root / "stock_discovery_us.json").read_text(encoding="utf-8")
    )
    kr_detail = TossStockDetailResponse.model_validate_json(
        (fixture_root / "stock_detail_kr.json").read_text(encoding="utf-8")
    )
    us_partial = TossStockDetailResponse.model_validate_json(
        (fixture_root / "stock_detail_us_partial.json").read_text(encoding="utf-8")
    )

    assert [item.symbol for item in kr_discovery.result] == ["KRT001", "KRT002"]
    assert [item.symbol for item in us_discovery.result] == ["USTA", "USTB"]
    assert kr_detail.result[0].sharesOutstanding == Decimal("1000000")
    assert us_partial.result[0].currency == Currency.USD
    combined = "".join(path.read_text(encoding="utf-8") for path in fixture_root.glob("*.json"))
    assert "삼성" not in combined
    assert "Apple" not in combined


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("market", "UNKNOWN_EXCHANGE"),
        ("securityType", "BOND"),
        ("status", "UNKNOWN_STATUS"),
        ("currency", "EUR"),
    ],
)
def test_c_u07_unknown_detail_enums_fail_closed(field: str, value: str) -> None:
    payload = _detail("KRT001").model_dump(mode="json")
    payload[field] = value
    with pytest.raises(ValidationError):
        TossStockDetailItem.model_validate(payload)


def test_strict_dto_rejects_extra_float_and_invalid_isin() -> None:
    payload = _detail("KRT001").model_dump(mode="json")
    payload["unknown"] = "blocked"
    with pytest.raises(ValidationError):
        TossStockDetailItem.model_validate(payload)
    payload.pop("unknown")
    payload["sharesOutstanding"] = 1.5
    with pytest.raises(ValidationError):
        TossStockDetailItem.model_validate(payload)
    payload["sharesOutstanding"] = "1"
    payload["isinCode"] = "KRTESTA00001"
    with pytest.raises(ValidationError):
        TossStockDetailItem.model_validate(payload)
    payload = _detail("KRT001").model_dump(mode="json")
    payload.pop("listDate")
    with pytest.raises(ValidationError):
        TossStockDetailItem.model_validate(payload)


def test_c_m01_stable_duplicate_is_idempotent(database_context, workspace_tmp_path: Path) -> None:
    source = _source(
        database_context.engine,
        workspace_tmp_path / "raw",
        raw_token="stable-a",
        minute=1,
    )
    service = _service(database_context.engine)
    first = _reconcile(service, source, _detail("KRT001"))
    second = _reconcile(service, source, _detail("KRT001"))
    repository = _repository(database_context.engine)

    assert first == second
    assert len(repository.list_identities()) == 1
    assert len(repository.list_records()) == 1
    assert len(repository.list_observations()) == 1


def test_c_m02_isin_correction_preserves_old_history_and_requires_review(
    database_context, workspace_tmp_path: Path
) -> None:
    source_a = _source(
        database_context.engine,
        workspace_tmp_path / "raw",
        raw_token="isin-a",
        minute=1,
    )
    service = _service(database_context.engine)
    first = _reconcile(service, source_a, _detail("KRT001", isin=KR_ISIN_A))
    source_b = _source(
        database_context.engine,
        workspace_tmp_path / "raw",
        raw_token="isin-b",
        minute=2,
        prior=source_a,
    )
    second = _reconcile(service, source_b, _detail("KRT001", isin=KR_ISIN_B))
    repository = _repository(database_context.engine)

    assert (
        first.observations[0].provider_security_identity_id
        == second.observations[0].provider_security_identity_id
    )
    assert second.observations[0].staging_state == ProviderSecurityMasterState.QUARANTINED
    assert "IDENTIFIER_CORRECTION_REVIEW" in second.observations[0].reason_codes
    assert {
        entry.identifier_value
        for entry in repository.list_identifier_history()
        if entry.identifier_kind == ProviderIdentifierKind.ISIN
    } == {KR_ISIN_A, KR_ISIN_B}


def test_c_m03_symbol_change_with_unique_isin_reuses_identity(
    database_context, workspace_tmp_path: Path
) -> None:
    source_a = _source(
        database_context.engine,
        workspace_tmp_path / "raw",
        raw_token="symbol-a",
        minute=1,
    )
    service = _service(database_context.engine)
    first = _reconcile(service, source_a, _detail("KRT001"))
    source_b = _source(
        database_context.engine,
        workspace_tmp_path / "raw",
        symbols=("KRT009",),
        raw_token="symbol-b",
        minute=2,
    )
    second = _reconcile(service, source_b, _detail("KRT009"))
    histories = _repository(database_context.engine).list_identifier_history()

    assert (
        first.observations[0].provider_security_identity_id
        == second.observations[0].provider_security_identity_id
    )
    symbols = [
        entry for entry in histories if entry.identifier_kind == ProviderIdentifierKind.SYMBOL
    ]
    assert {entry.identifier_value for entry in symbols} == {"KRT001", "KRT009"}
    assert all(entry.valid_to is None for entry in symbols)
    assert any(
        entry.identifier_value == "KRT009"
        and entry.revision_reason == ProviderIdentifierReason.SYMBOL_CHANGE
        and entry.valid_from is None
        for entry in symbols
    )


def test_p1_01_symbol_transition_uses_semantic_current_identity(
    database_context, workspace_tmp_path: Path
) -> None:
    raw_root = workspace_tmp_path / "raw"
    service = _service(database_context.engine)
    source_old = _source(
        database_context.engine,
        raw_root,
        symbols=("OLD",),
        raw_token="rename-old",
        minute=1,
    )
    first = _reconcile(service, source_old, _detail("OLD", isin=KR_ISIN_A))
    repository = _repository(database_context.engine)
    identity_before = repository.list_identities()[0]

    source_new = _source(
        database_context.engine,
        raw_root,
        symbols=("NEW",),
        raw_token="rename-new",
        minute=2,
    )
    second = _reconcile(service, source_new, _detail("NEW", isin=KR_ISIN_A))
    source_partial = _source(
        database_context.engine,
        raw_root,
        symbols=("NEW",),
        raw_token="rename-new-partial",
        minute=3,
        prior=source_new,
    )
    third = _reconcile(
        service,
        source_partial,
        _detail("NEW", isin=None, list_date=None),
    )

    identities = repository.list_identities()
    identity_id = identity_before.provider_security_identity_id
    assert len(identities) == 1
    assert identities[0].provider_security_identity_id == identity_id
    assert identities[0].allocation_anchor_hash == identity_before.allocation_anchor_hash
    assert {
        first.observations[0].provider_security_identity_id,
        second.observations[0].provider_security_identity_id,
        third.observations[0].provider_security_identity_id,
    } == {identity_id}
    rename_rows = [
        entry
        for entry in repository.list_identifier_history()
        if entry.identifier_kind == ProviderIdentifierKind.SYMBOL
        and entry.revision_reason == ProviderIdentifierReason.SYMBOL_CHANGE
    ]
    assert [(entry.identifier_value, entry.valid_from) for entry in rename_rows] == [("NEW", None)]

    discovery = _source(
        database_context.engine,
        raw_root,
        raw_token="rename-discovery",
        minute=4,
        discovery=True,
    )
    service.stage_discovery(
        source_version_id=discovery.source_version_id,
        market=Market.KR,
        response=TossStockDiscoveryResponse(
            result=[
                _discovery_item("OLD", isin=KR_ISIN_A),
                _discovery_item("NEW", isin=KR_ISIN_A),
            ]
        ),
    )
    discovery_missing = _source(
        database_context.engine,
        raw_root,
        raw_token="rename-discovery-missing",
        minute=5,
        prior=discovery,
        discovery=True,
    )
    missing = service.stage_discovery(
        source_version_id=discovery_missing.source_version_id,
        market=Market.KR,
        response=TossStockDiscoveryResponse(result=[]),
    )
    missing_by_symbol = {item.symbol: item for item in missing.observations}
    assert missing_by_symbol["NEW"].provider_security_identity_id == identity_id
    assert missing_by_symbol["OLD"].provider_security_identity_id is None

    missing_detail_source = _source(
        database_context.engine,
        raw_root,
        symbols=("NEW",),
        raw_token="rename-detail-missing",
        minute=6,
        prior=source_partial,
    )
    missing_detail = _reconcile(service, missing_detail_source)
    assert missing_detail.observations[0].provider_security_identity_id == identity_id
    assert (
        missing_detail.observations[0].reconciliation_outcome
        == ProviderReconciliationOutcome.DETAIL_MISSING
    )


def test_p1_01_ambiguous_current_symbol_fails_closed(
    database_context, workspace_tmp_path: Path
) -> None:
    raw_root = workspace_tmp_path / "raw"
    source = _source(
        database_context.engine,
        raw_root,
        symbols=("OLD",),
        raw_token="ambiguous-current-base",
        minute=1,
    )
    service = _service(database_context.engine)
    first = _reconcile(service, source, _detail("OLD", isin=KR_ISIN_A))
    identity_id = first.observations[0].provider_security_identity_id
    assert identity_id is not None

    provider_repository = SQLiteProviderRepository(
        session_factory(database_context.engine), ProviderRawStore(raw_root)
    )
    provider_repository.append_identifier_history(
        ProviderIdentifierHistory(
            identifier_history_id="pih_0000000000000000",
            provider_security_identity_id=identity_id,
            identifier_kind=ProviderIdentifierKind.SYMBOL,
            identifier_value="CONFLICT",
            valid_from=None,
            valid_to=None,
            source_version_id=source.source_version_id,
            revision_reason=ProviderIdentifierReason.ENRICHMENT,
            provider_contract_version=PROVIDER_IDENTITY_CONTRACT_VERSION,
        )
    )
    followup = _source(
        database_context.engine,
        raw_root,
        symbols=("OLD",),
        raw_token="ambiguous-current-followup",
        minute=2,
        prior=source,
    )
    observation = _reconcile(service, followup, _detail("OLD", isin=KR_ISIN_A)).observations[0]

    assert observation.eligible_for_mapping is False
    assert observation.staging_state == ProviderSecurityMasterState.QUARANTINED
    assert observation.reconciliation_outcome == ProviderReconciliationOutcome.UNRESOLVED_COLLISION
    assert observation.collision_identity_ids == (identity_id,)
    assert "AMBIGUOUS_CURRENT_IDENTIFIER" in observation.reason_codes
    assert len(_repository(database_context.engine).list_identities()) == 1


def test_c_m04_and_ir_f_duplicate_isin_quarantines_both_without_merge(
    database_context, workspace_tmp_path: Path
) -> None:
    source_a = _source(
        database_context.engine,
        workspace_tmp_path / "raw",
        symbols=("KRT001", "KRT002"),
        raw_token="collision-base",
        minute=1,
    )
    service = _service(database_context.engine)
    _reconcile(
        service,
        source_a,
        _detail("KRT001", isin=None, list_date=None),
        _detail("KRT002", isin=None, list_date=None),
    )
    before_ids = {
        item.provider_security_identity_id
        for item in _repository(database_context.engine).list_identities()
    }
    source_b = _source(
        database_context.engine,
        workspace_tmp_path / "raw",
        symbols=("KRT001", "KRT002"),
        raw_token="collision-enrichment",
        minute=2,
        prior=source_a,
    )
    result = _reconcile(
        service,
        source_b,
        _detail("KRT001", isin=KR_ISIN_C, list_date=None),
        _detail("KRT002", isin=KR_ISIN_C, list_date=None),
    )
    repository = _repository(database_context.engine)
    identities = repository.list_identities()
    affected_observations = [
        item
        for item in repository.list_observations()
        if item.source_version_id == source_b.source_version_id
    ]

    assert len(result.observations) == len(affected_observations) == 2
    assert all(
        item.reconciliation_outcome == ProviderReconciliationOutcome.UNRESOLVED_COLLISION
        and item.staging_state == ProviderSecurityMasterState.QUARANTINED
        and item.eligible_for_mapping is False
        and set(item.collision_identity_ids) == before_ids
        for item in affected_observations
    )
    assert {item.provider_security_identity_id for item in identities} == before_ids
    assert {item.identity_state for item in identities} == {
        ProviderIdentityState.UNRESOLVED_COLLISION
    }
    with database_context.engine.connect() as connection:
        assert (
            connection.exec_driver_sql(
                "SELECT COUNT(*) FROM provider_identity_mappings"
            ).scalar_one()
            == 0
        )


def test_p1_02_same_source_duplicate_isin_quarantines_all_new_candidates(
    database_context, workspace_tmp_path: Path
) -> None:
    source = _source(
        database_context.engine,
        workspace_tmp_path / "raw",
        symbols=("KRT001", "KRT002"),
        raw_token="same-source-new-collision",
        minute=1,
    )
    result = _reconcile(
        _service(database_context.engine),
        source,
        _detail("KRT001", isin=KR_ISIN_C),
        _detail("KRT002", isin=KR_ISIN_C, name="테스트 베타"),
    )
    repository = _repository(database_context.engine)
    affected = [
        item
        for item in repository.list_observations()
        if item.source_version_id == source.source_version_id
    ]

    assert len(result.observations) == len(affected) == 2
    assert sum(item.eligible_for_mapping for item in affected) == 0
    assert all(
        item.staging_state == ProviderSecurityMasterState.QUARANTINED
        and item.reconciliation_outcome == ProviderReconciliationOutcome.UNRESOLVED_COLLISION
        and item.provider_security_identity_id is None
        and item.collision_identity_ids == ()
        and "DUPLICATE_ISIN_IN_DETAIL_SOURCE" in item.reason_codes
        for item in affected
    )
    assert repository.list_identities() == []
    assert repository.list_identifier_history() == []
    with database_context.engine.connect() as connection:
        assert (
            connection.exec_driver_sql(
                "SELECT COUNT(*) FROM provider_identity_mappings"
            ).scalar_one()
            == 0
        )


def test_p1_02_duplicate_isin_batch_is_response_order_independent(
    workspace_tmp_path: Path,
) -> None:
    dumps: list[bytes] = []
    for suffix, items in (
        (
            "forward",
            (
                _detail("KRT001", isin=KR_ISIN_C),
                _detail("KRT002", isin=KR_ISIN_C, name="테스트 베타"),
            ),
        ),
        (
            "reverse",
            (
                _detail("KRT002", isin=KR_ISIN_C, name="테스트 베타"),
                _detail("KRT001", isin=KR_ISIN_C),
            ),
        ),
    ):
        database_path = workspace_tmp_path / f"collision-order-{suffix}.sqlite3"
        url = f"sqlite:///{database_path.as_posix()}"
        command.upgrade(alembic_config(url), "head")
        engine = create_database_engine(url)
        try:
            source = _source(
                engine,
                workspace_tmp_path / f"raw-{suffix}",
                symbols=("KRT001", "KRT002"),
                raw_token="same-order-independent-collision",
                minute=1,
            )
            _reconcile(_service(engine), source, *items)
            repository = _repository(engine)
            payload = {
                "identities": [
                    item.model_dump(mode="json") for item in repository.list_identities()
                ],
                "history": [
                    item.model_dump(mode="json") for item in repository.list_identifier_history()
                ],
                "records": [item.model_dump(mode="json") for item in repository.list_records()],
                "observations": [
                    item.model_dump(mode="json") for item in repository.list_observations()
                ],
                "events": [item.model_dump(mode="json") for item in repository.list_state_events()],
                "batches": [
                    item.model_dump(mode="json") for item in repository.list_detail_batches()
                ],
            }
            dumps.append(canonical_json_bytes(payload))
        finally:
            engine.dispose()

    assert dumps[0] == dumps[1]


def test_c_m05_and_ir_d_missing_isin_enriches_without_rekey(
    database_context, workspace_tmp_path: Path
) -> None:
    source_a = _source(
        database_context.engine,
        workspace_tmp_path / "raw",
        raw_token="missing-isin",
        minute=1,
    )
    service = _service(database_context.engine)
    first = _reconcile(service, source_a, _detail("KRT001", isin=None))
    identity_before = _repository(database_context.engine).list_identities()[0]
    record = _repository(database_context.engine).list_records()[0]
    assert record.missing_reasons["isin"] == MissingReason.NOT_PROVIDED
    source_b = _source(
        database_context.engine,
        workspace_tmp_path / "raw",
        raw_token="enriched-isin",
        minute=2,
        prior=source_a,
    )
    second = _reconcile(service, source_b, _detail("KRT001", isin=KR_ISIN_A))
    identity_after = _repository(database_context.engine).list_identities()[0]

    assert (
        first.observations[0].provider_security_identity_id
        == second.observations[0].provider_security_identity_id
    )
    assert identity_before.allocation_anchor_hash == identity_after.allocation_anchor_hash
    assert len(_repository(database_context.engine).list_identities()) == 1


def test_ir_e_list_date_enrichment_preserves_anchor(
    database_context, workspace_tmp_path: Path
) -> None:
    source_a = _source(
        database_context.engine,
        workspace_tmp_path / "raw",
        raw_token="missing-date",
        minute=1,
    )
    service = _service(database_context.engine)
    _reconcile(service, source_a, _detail("KRT001", isin=None, list_date=None))
    before = _repository(database_context.engine).list_identities()[0]
    source_b = _source(
        database_context.engine,
        workspace_tmp_path / "raw",
        raw_token="enriched-date",
        minute=2,
        prior=source_a,
    )
    _reconcile(service, source_b, _detail("KRT001", isin=None, list_date=date(2021, 2, 3)))
    repository = _repository(database_context.engine)
    after = repository.list_identities()[0]

    assert before.provider_security_identity_id == after.provider_security_identity_id
    assert before.allocation_anchor_hash == after.allocation_anchor_hash
    assert any(
        entry.identifier_kind == ProviderIdentifierKind.LIST_DATE
        for entry in repository.list_identifier_history()
    )


def test_c_m06_ticker_reuse_after_lifecycle_close_allocates_new_identity(
    database_context, workspace_tmp_path: Path
) -> None:
    source_a = _source(
        database_context.engine,
        workspace_tmp_path / "raw",
        raw_token="old-listing",
        minute=1,
    )
    service = _service(database_context.engine)
    first = _reconcile(
        service,
        source_a,
        _detail(
            "KRT001",
            isin=KR_ISIN_A,
            status=ProviderSecurityStatus.DELISTED,
            delist_date=date(2025, 1, 1),
        ),
    )
    source_b = _source(
        database_context.engine,
        workspace_tmp_path / "raw",
        raw_token="new-listing",
        minute=2,
        prior=source_a,
    )
    second = _reconcile(
        service,
        source_b,
        _detail("KRT001", isin=KR_ISIN_B, list_date=date(2026, 1, 2)),
    )
    identities = _repository(database_context.engine).list_identities()

    assert (
        first.observations[0].provider_security_identity_id
        != second.observations[0].provider_security_identity_id
    )
    assert len(identities) == 2
    assert len({identity.allocation_anchor_hash for identity in identities}) == 2


def test_c_m07_name_is_never_merge_evidence(database_context, workspace_tmp_path: Path) -> None:
    source = _source(
        database_context.engine,
        workspace_tmp_path / "raw",
        symbols=("KRT001", "KRT002"),
        raw_token="same-name",
        minute=1,
    )
    service = _service(database_context.engine)
    _reconcile(
        service,
        source,
        _detail("KRT001", isin=KR_ISIN_A, name="동일 테스트 명칭"),
        _detail("KRT002", isin=KR_ISIN_B, name="동일 테스트 명칭"),
    )
    assert len(_repository(database_context.engine).list_identities()) == 2


def test_c_m08_m09_stop_at_unresolved_provider_candidates(
    database_context, workspace_tmp_path: Path
) -> None:
    source = _source(
        database_context.engine,
        workspace_tmp_path / "raw",
        symbols=("KRT001", "KRT002"),
        raw_token="share-classes",
        minute=1,
    )
    service = _service(database_context.engine)
    result = _reconcile(
        service,
        source,
        _detail("KRT001", isin=KR_ISIN_A),
        _detail("KRT002", isin=KR_ISIN_B),
    )
    identities = _repository(database_context.engine).list_identities()

    assert len(identities) == 2
    assert all(identity.mapping_status.value == "UNRESOLVED" for identity in identities)
    assert all(
        item.staging_state == ProviderSecurityMasterState.ELIGIBLE_FOR_MAPPING
        for item in result.observations
    )
    with database_context.engine.connect() as connection:
        assert connection.exec_driver_sql("SELECT COUNT(*) FROM issuers").scalar_one() == 2
        assert connection.exec_driver_sql("SELECT COUNT(*) FROM securities").scalar_one() == 2


@pytest.mark.parametrize(
    ("market", "item"),
    [
        (Market.KR, _detail("KRT001")),
        (
            Market.US,
            _detail(
                "USTA",
                isin=US_ISIN_A,
                market=ProviderListingMarket.NASDAQ,
                currency=Currency.USD,
            ),
        ),
    ],
)
def test_c_u01_u02_kr_us_eligible_candidate(
    database_context, workspace_tmp_path: Path, market: Market, item: TossStockDetailItem
) -> None:
    source = _source(
        database_context.engine,
        workspace_tmp_path / f"raw-{market.value}",
        symbols=(item.symbol,),
        market=market,
        raw_token=f"eligible-{market.value}",
        minute=1,
    )
    result = _reconcile(_service(database_context.engine), source, item, market=market)
    observation = result.observations[0]

    assert observation.market == market
    assert observation.eligible_for_mapping is True
    assert observation.staging_state == ProviderSecurityMasterState.ELIGIBLE_FOR_MAPPING
    assert (
        _repository(database_context.engine).list_identities()[0].mapping_status.value
        == "UNRESOLVED"
    )


@pytest.mark.parametrize(
    "item",
    [
        _detail("KRT001", common=False),
        _detail("KRT001", security_type=ProviderSecurityType.ETF),
        _detail("KRT001", security_type=ProviderSecurityType.ETN),
        _detail("KRT001", security_type=ProviderSecurityType.STOCK_WARRANTS),
    ],
)
def test_c_u03_u04_non_common_and_unsupported_are_quarantined(
    database_context, workspace_tmp_path: Path, item: TossStockDetailItem
) -> None:
    source = _source(
        database_context.engine,
        workspace_tmp_path / "raw",
        raw_token=f"unsupported-{item.securityType.value}-{item.isCommonShare}",
        minute=1,
    )
    observation = _reconcile(_service(database_context.engine), source, item).observations[0]

    assert observation.eligible_for_mapping is False
    assert observation.staging_state == ProviderSecurityMasterState.QUARANTINED
    assert (
        _repository(database_context.engine).list_identities()[0].identity_state
        == ProviderIdentityState.QUARANTINED
    )


def test_c_u05_inactive_preserves_prior_history(database_context, workspace_tmp_path: Path) -> None:
    source_a = _source(
        database_context.engine,
        workspace_tmp_path / "raw",
        raw_token="active",
        minute=1,
    )
    service = _service(database_context.engine)
    _reconcile(service, source_a, _detail("KRT001"))
    history_before = _repository(database_context.engine).list_identifier_history()
    source_b = _source(
        database_context.engine,
        workspace_tmp_path / "raw",
        raw_token="inactive",
        minute=2,
        prior=source_a,
    )
    observation = _reconcile(
        service,
        source_b,
        _detail("KRT001", status=ProviderSecurityStatus.INACTIVE),
    ).observations[0]
    repository = _repository(database_context.engine)

    assert observation.staging_state == ProviderSecurityMasterState.INACTIVE_OBSERVED
    assert observation.eligible_for_mapping is False
    assert repository.list_identities()[0].identity_state == ProviderIdentityState.INACTIVE
    before_payloads = {item.model_dump_json() for item in history_before}
    after_payloads = {item.model_dump_json() for item in repository.list_identifier_history()}
    assert before_payloads.issubset(after_payloads)


def test_c_u06_discovery_disappearance_is_missing_only(
    database_context, workspace_tmp_path: Path
) -> None:
    source_a = _source(
        database_context.engine,
        workspace_tmp_path / "raw",
        raw_token="discovery-present",
        minute=1,
        discovery=True,
    )
    service = _service(database_context.engine)
    service.stage_discovery(
        source_version_id=source_a.source_version_id,
        market=Market.KR,
        response=TossStockDiscoveryResponse(result=[_discovery_item("KRT001")]),
    )
    source_b = _source(
        database_context.engine,
        workspace_tmp_path / "raw",
        raw_token="discovery-empty",
        minute=2,
        prior=source_a,
        discovery=True,
    )
    result = service.stage_discovery(
        source_version_id=source_b.source_version_id,
        market=Market.KR,
        response=TossStockDiscoveryResponse(result=[]),
    )

    assert len(result.observations) == 1
    assert result.observations[0].staging_state == ProviderSecurityMasterState.DISCOVERY_MISSING
    assert (
        result.observations[0].reconciliation_outcome
        == ProviderReconciliationOutcome.DISCOVERY_MISSING
    )
    assert _repository(database_context.engine).list_identifier_history() == []


def test_c_u08_partial_detail_has_exact_counts_and_missing_observation(
    database_context, workspace_tmp_path: Path
) -> None:
    discovery = _source(
        database_context.engine,
        workspace_tmp_path / "raw-discovery",
        raw_token="partial-discovery",
        minute=1,
        discovery=True,
    )
    service = _service(database_context.engine)
    service.stage_discovery(
        source_version_id=discovery.source_version_id,
        market=Market.KR,
        response=TossStockDiscoveryResponse(
            result=[
                _discovery_item("KRT001", isin=KR_ISIN_A),
                _discovery_item("KRT002", isin=KR_ISIN_B, name="테스트 베타"),
            ]
        ),
    )
    detail_source = _source(
        database_context.engine,
        workspace_tmp_path / "raw-detail",
        symbols=("KRT001", "KRT002"),
        raw_token="partial-detail",
        minute=2,
    )
    result = _reconcile(service, detail_source, _detail("KRT001"))

    assert result.detail_batch is not None
    assert result.detail_batch.status == ProviderDetailBatchStatus.PARTIAL
    assert (
        result.detail_batch.requested_count,
        result.detail_batch.received_count,
        result.detail_batch.missing_count,
    ) == (2, 1, 1)
    assert (
        result.observations[1].reconciliation_outcome
        == ProviderReconciliationOutcome.DETAIL_MISSING
    )
    assert result.observations[1].staging_state == ProviderSecurityMasterState.QUARANTINED


def test_empty_detail_is_never_reported_as_success(
    database_context, workspace_tmp_path: Path
) -> None:
    discovery = _source(
        database_context.engine,
        workspace_tmp_path / "raw-discovery",
        raw_token="empty-discovery-evidence",
        minute=1,
        discovery=True,
    )
    service = _service(database_context.engine)
    service.stage_discovery(
        source_version_id=discovery.source_version_id,
        market=Market.KR,
        response=TossStockDiscoveryResponse(result=[_discovery_item("KRT001")]),
    )
    detail_source = _source(
        database_context.engine,
        workspace_tmp_path / "raw-detail",
        raw_token="empty-detail",
        minute=2,
    )
    result = _reconcile(service, detail_source)

    assert result.detail_batch is not None
    assert result.detail_batch.status == ProviderDetailBatchStatus.FAILED_EMPTY_RESPONSE
    assert result.detail_batch.received_count == 0
    assert (
        result.observations[0].reconciliation_outcome
        == ProviderReconciliationOutcome.DETAIL_MISSING
    )


def test_contradictory_active_delist_date_quarantines_and_preserves_record(
    database_context, workspace_tmp_path: Path
) -> None:
    source = _source(
        database_context.engine,
        workspace_tmp_path / "raw",
        raw_token="contradiction",
        minute=1,
    )
    observation = _reconcile(
        _service(database_context.engine),
        source,
        _detail("KRT001", delist_date=date(2026, 1, 1)),
    ).observations[0]

    assert observation.staging_state == ProviderSecurityMasterState.QUARANTINED
    assert "ACTIVE_WITH_DELIST_DATE" in observation.reason_codes
    assert len(_repository(database_context.engine).list_records()) == 1


def test_market_scope_separates_same_symbol_and_isin(
    database_context, workspace_tmp_path: Path
) -> None:
    kr_source = _source(
        database_context.engine,
        workspace_tmp_path / "raw-kr",
        raw_token="market-kr",
        minute=1,
    )
    service = _service(database_context.engine)
    _reconcile(service, kr_source, _detail("KRT001"))
    us_source = _source(
        database_context.engine,
        workspace_tmp_path / "raw-us",
        symbols=("KRT001",),
        market=Market.US,
        raw_token="market-us",
        minute=2,
        prior=kr_source,
    )
    _reconcile(
        service,
        us_source,
        _detail(
            "KRT001",
            market=ProviderListingMarket.NYSE,
            currency=Currency.USD,
        ),
        market=Market.US,
    )

    identities = _repository(database_context.engine).list_identities()
    assert len(identities) == 2
    assert {identity.market for identity in identities} == {Market.KR, Market.US}


def test_ir_g_clean_rebuild_is_byte_deterministic(workspace_tmp_path: Path) -> None:
    dumps: list[bytes] = []
    for suffix in ("one", "two"):
        database_path = workspace_tmp_path / f"rebuild-{suffix}.sqlite3"
        url = f"sqlite:///{database_path.as_posix()}"
        command.upgrade(alembic_config(url), "head")
        engine = create_database_engine(url)
        try:
            source_a = _source(
                engine,
                workspace_tmp_path / f"raw-{suffix}",
                raw_token="rebuild-first",
                minute=2,
            )
            source_b = _source(
                engine,
                workspace_tmp_path / f"raw-{suffix}",
                raw_token="rebuild-second",
                minute=3,
                prior=source_a,
            )
            service = _service(engine)
            service.replay(
                [
                    SecurityMasterReplayInput(
                        source_version_id=source_b.source_version_id,
                        market=Market.KR,
                        kind="DETAIL",
                        response=TossStockDetailResponse(
                            result=[_detail("KRT001", isin=KR_ISIN_A)]
                        ),
                    ),
                    SecurityMasterReplayInput(
                        source_version_id=source_a.source_version_id,
                        market=Market.KR,
                        kind="DETAIL",
                        response=TossStockDetailResponse(
                            result=[_detail("KRT001", isin=None, list_date=None)]
                        ),
                    ),
                ]
            )
            repository = _repository(engine)
            payload = {
                "identities": [
                    item.model_dump(mode="json") for item in repository.list_identities()
                ],
                "history": [
                    item.model_dump(mode="json") for item in repository.list_identifier_history()
                ],
                "observations": [
                    item.model_dump(mode="json") for item in repository.list_observations()
                ],
                "events": [item.model_dump(mode="json") for item in repository.list_state_events()],
            }
            dumps.append(canonical_json_bytes(payload))
        finally:
            engine.dispose()

    assert dumps[0] == dumps[1]


def test_detail_rejects_unrequested_symbol_without_audit_false_green(
    database_context, workspace_tmp_path: Path
) -> None:
    source = _source(
        database_context.engine,
        workspace_tmp_path / "raw",
        raw_token="unexpected",
        minute=1,
    )
    with pytest.raises(ProviderContractConflict, match="unrequested"):
        _reconcile(_service(database_context.engine), source, _detail("KRT999"))
    assert _repository(database_context.engine).list_detail_batches() == []
