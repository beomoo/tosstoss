from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

from toss_dashboard_api.contracts.base import canonical_json_bytes, sha256_prefixed
from toss_dashboard_api.contracts.enums import (
    Currency,
    MappingStatus,
    Market,
    MissingReason,
    ProviderDataset,
    ProviderIdentifierKind,
    ProviderIdentifierReason,
    ProviderIdentityState,
    ProviderListingMarket,
    ProviderReconciliationOutcome,
    ProviderSecurityMasterState,
    ProviderSecurityStatus,
    ProviderSecurityType,
    ProviderSystem,
    RevisionStatus,
)
from toss_dashboard_api.contracts.provider_identity import (
    PROVIDER_IDENTITY_CONTRACT_VERSION,
    ProviderIdentifierHistory,
    ProviderSecurityIdentity,
    provider_identity_id_from_anchor,
)
from toss_dashboard_api.contracts.provider_security_master import (
    ProviderDetailBatchResult,
    ProviderSecurityMasterObservation,
    ProviderSecurityMasterRecord,
    TossStockDetailItem,
    TossStockDetailResponse,
    TossStockDiscoveryItem,
    TossStockDiscoveryResponse,
    build_detail_batch_result,
    build_identity_state_event,
    build_security_master_observation,
    build_security_master_record,
)
from toss_dashboard_api.contracts.provider_source import ProviderSourceVersion
from toss_dashboard_api.repositories.provider import ProviderContractConflict
from toss_dashboard_api.repositories.security_master import (
    SecurityMasterPersistenceBundle,
    SQLiteSecurityMasterRepository,
)

_SUPPORTED_LISTING_MARKETS: dict[Market, frozenset[ProviderListingMarket]] = {
    Market.KR: frozenset({ProviderListingMarket.KOSPI, ProviderListingMarket.KOSDAQ}),
    Market.US: frozenset(
        {
            ProviderListingMarket.NYSE,
            ProviderListingMarket.NASDAQ,
            ProviderListingMarket.AMEX,
        }
    ),
}
_EXPECTED_CURRENCY = {Market.KR: Currency.KRW, Market.US: Currency.USD}


@dataclass(frozen=True)
class SecurityMasterStageResult:
    observations: tuple[ProviderSecurityMasterObservation, ...]
    detail_batch: ProviderDetailBatchResult | None = None


@dataclass(frozen=True)
class SecurityMasterReplayInput:
    source_version_id: str
    market: Market
    kind: Literal["DISCOVERY", "DETAIL"]
    response: TossStockDiscoveryResponse | TossStockDetailResponse


class SecurityMasterReconciliationService:
    """Offline-only CP3-C1 staging with continuity-first identity reconciliation."""

    def __init__(self, repository: SQLiteSecurityMasterRepository) -> None:
        self._repository = repository

    def stage_discovery(
        self,
        *,
        source_version_id: str,
        market: Market,
        response: TossStockDiscoveryResponse,
    ) -> SecurityMasterStageResult:
        source = self._validated_source(source_version_id, ProviderDataset.STOCK_DISCOVERY)
        request = self._repository.canonical_request(source.canonical_request_id)
        query = json.loads(request.canonical_query_json)
        if request.path_template != "/api/v1/stocks/all" or query.get("market") != market.value:
            raise ProviderContractConflict("discovery source request does not match market")

        observations: list[ProviderSecurityMasterObservation] = []
        for item in sorted(response.result, key=lambda value: value.symbol.encode("ascii")):
            reasons = self._discovery_reason_codes(item)
            observation = build_security_master_observation(
                source_version_id=source_version_id,
                normalized_record_id=None,
                provider_security_identity_id=None,
                provider=ProviderSystem.TOSS_OPEN_API,
                market=market,
                symbol=item.symbol,
                name=item.name,
                security_type=item.securityType,
                is_common_share=item.isCommonShare,
                isin=item.isinCode,
                staging_state=ProviderSecurityMasterState.DISCOVERED,
                reconciliation_outcome=ProviderReconciliationOutcome.DISCOVERY_RECORDED,
                identity_state_after=None,
                eligible_for_mapping=False,
                collision_identity_ids=(),
                reason_codes=reasons,
            )
            persisted = self._repository.persist_bundle(
                SecurityMasterPersistenceBundle(record=None, observation=observation)
            )
            observations.append(persisted.record)

        current_symbols = {item.symbol for item in response.result}
        for prior in self._prior_discovery_snapshot(source, market):
            if prior.symbol in current_symbols:
                continue
            identity = self._unique_active_symbol_identity(market, prior.symbol)
            observation = build_security_master_observation(
                source_version_id=source_version_id,
                normalized_record_id=None,
                provider_security_identity_id=(
                    None if identity is None else identity.provider_security_identity_id
                ),
                provider=ProviderSystem.TOSS_OPEN_API,
                market=market,
                symbol=prior.symbol,
                name=prior.name,
                security_type=prior.security_type,
                is_common_share=prior.is_common_share,
                isin=prior.isin,
                staging_state=ProviderSecurityMasterState.DISCOVERY_MISSING,
                reconciliation_outcome=ProviderReconciliationOutcome.DISCOVERY_MISSING,
                identity_state_after=None if identity is None else identity.identity_state,
                eligible_for_mapping=False,
                collision_identity_ids=(),
                reason_codes=("DISCOVERY_RESPONSE_MISSING",),
            )
            persisted = self._repository.persist_bundle(
                SecurityMasterPersistenceBundle(record=None, observation=observation)
            )
            observations.append(persisted.record)

        return SecurityMasterStageResult(observations=tuple(observations))

    def reconcile_detail(
        self,
        *,
        source_version_id: str,
        market: Market,
        response: TossStockDetailResponse,
    ) -> SecurityMasterStageResult:
        source = self._validated_source(source_version_id, ProviderDataset.STOCK_DETAIL)
        request = self._repository.canonical_request(source.canonical_request_id)
        query = json.loads(request.canonical_query_json)
        if request.path_template != "/api/v1/stocks" or set(query) != {"symbols"}:
            raise ProviderContractConflict("detail source request does not match exact contract")
        requested = tuple(query["symbols"])
        received = tuple(item.symbol for item in response.result)
        if not set(received).issubset(set(requested)):
            raise ProviderContractConflict("detail response contains an unrequested symbol")

        batch = build_detail_batch_result(
            source_version_id=source_version_id,
            requested_symbols=requested,
            received_symbols=received,
        )
        for symbol in batch.missing_symbols:
            if self._latest_discovery_for_symbol(source, market, symbol) is None:
                raise ProviderContractConflict(
                    "missing detail cannot be staged without discovery evidence"
                )
        self._repository.record_detail_batch(batch)
        observations: list[ProviderSecurityMasterObservation] = []
        details = {item.symbol: item for item in response.result}
        for symbol in batch.requested_symbols:
            item = details.get(symbol)
            observation = (
                self._stage_missing_detail(source, market, symbol)
                if item is None
                else self._reconcile_detail_item(source, market, item)
            )
            observations.append(observation)
        return SecurityMasterStageResult(observations=tuple(observations), detail_batch=batch)

    def replay(
        self, inputs: Sequence[SecurityMasterReplayInput]
    ) -> tuple[SecurityMasterStageResult, ...]:
        ordered = sorted(
            inputs,
            key=lambda item: self._source_order(
                self._repository.source_version(item.source_version_id)
            ),
        )
        results: list[SecurityMasterStageResult] = []
        for item in ordered:
            if item.kind == "DISCOVERY":
                if not isinstance(item.response, TossStockDiscoveryResponse):
                    raise TypeError("DISCOVERY replay requires TossStockDiscoveryResponse")
                results.append(
                    self.stage_discovery(
                        source_version_id=item.source_version_id,
                        market=item.market,
                        response=item.response,
                    )
                )
            else:
                if not isinstance(item.response, TossStockDetailResponse):
                    raise TypeError("DETAIL replay requires TossStockDetailResponse")
                results.append(
                    self.reconcile_detail(
                        source_version_id=item.source_version_id,
                        market=item.market,
                        response=item.response,
                    )
                )
        return tuple(results)

    def _reconcile_detail_item(
        self, source: ProviderSourceVersion, market: Market, item: TossStockDetailItem
    ) -> ProviderSecurityMasterObservation:
        record = self._normalized_record(market, item)
        identities = self._market_identities(market)
        history = self._history_by_identity()
        candidates = self._continuity_candidates(source, item, identities, history)
        reason_codes = list(self._detail_reason_codes(market, item))

        if len(candidates) > 1:
            return self._persist_collision(
                source, market, item, record, tuple(candidates.values()), reason_codes
            )

        identity = next(iter(candidates.values()), None)
        if identity is not None:
            record_conflict = self._record_conflict_reason(identity, item)
            if record_conflict is not None:
                reason_codes.append(record_conflict)
                return self._persist_collision(
                    source, market, item, record, (identity,), reason_codes
                )
            conflict_reason = self._identity_conflict_reason(source, item, identity, history)
            if conflict_reason is not None:
                reason_codes.append(conflict_reason)
                return self._persist_collision(
                    source, market, item, record, (identity,), reason_codes
                )
            if identity.identity_state in {
                ProviderIdentityState.QUARANTINED,
                ProviderIdentityState.UNRESOLVED_COLLISION,
            }:
                reason_codes.append("PRIOR_IDENTITY_QUARANTINED")
                return self._persist_collision(
                    source, market, item, record, (identity,), reason_codes
                )
            if self._is_identifier_correction(source, item, identity, history):
                reason_codes.append("IDENTIFIER_CORRECTION_REVIEW")
            self._require_monotonic_source(source, identity)
        else:
            identity = self._allocate_identity(source, market, item)

        new_identity = identity.first_source_version_id == source.source_version_id
        state, staging_state, eligible = self._target_state(market, item, reason_codes)
        transitioned = identity.model_copy(
            update={
                "identity_state": state,
                "latest_source_version_id": source.source_version_id,
            }
        )
        histories = self._identifier_updates(
            source=source,
            market=market,
            item=item,
            identity=identity,
            existing=history.get(identity.provider_security_identity_id, ()),
            initial=new_identity,
        )
        outcome = (
            (
                ProviderReconciliationOutcome.DETAIL_REJECTED
                if "IDENTIFIER_CORRECTION_REVIEW" in reason_codes
                else ProviderReconciliationOutcome.UNSUPPORTED
            )
            if staging_state == ProviderSecurityMasterState.QUARANTINED
            else (
                ProviderReconciliationOutcome.IDENTITY_ALLOCATED
                if new_identity
                else ProviderReconciliationOutcome.IDENTITY_REUSED
            )
        )
        event_reason = self._event_reason(staging_state, new_identity, reason_codes)
        event = build_identity_state_event(
            provider_security_identity_id=transitioned.provider_security_identity_id,
            source_version_id=source.source_version_id,
            identity_state=transitioned.identity_state,
            staging_state=staging_state,
            reason_code=event_reason,
        )
        observation = build_security_master_observation(
            source_version_id=source.source_version_id,
            normalized_record_id=record.normalized_record_id,
            provider_security_identity_id=transitioned.provider_security_identity_id,
            provider=ProviderSystem.TOSS_OPEN_API,
            market=market,
            symbol=item.symbol,
            name=item.name,
            security_type=item.securityType,
            is_common_share=item.isCommonShare,
            isin=item.isinCode,
            staging_state=staging_state,
            reconciliation_outcome=outcome,
            identity_state_after=transitioned.identity_state,
            eligible_for_mapping=eligible,
            collision_identity_ids=(),
            reason_codes=tuple(sorted(set(reason_codes))),
        )
        persisted = self._repository.persist_bundle(
            SecurityMasterPersistenceBundle(
                record=record,
                observation=observation,
                identity_updates=(transitioned,),
                identifier_history=histories,
                state_events=(event,),
            )
        )
        return persisted.record

    def _persist_collision(
        self,
        source: ProviderSourceVersion,
        market: Market,
        item: TossStockDetailItem,
        record: ProviderSecurityMasterRecord,
        candidates: Sequence[ProviderSecurityIdentity],
        reason_codes: list[str],
    ) -> ProviderSecurityMasterObservation:
        reason_codes.append("CONTINUITY_EVIDENCE_COLLISION")
        ordered = tuple(sorted(candidates, key=lambda value: value.provider_security_identity_id))
        for identity in ordered:
            self._require_monotonic_source(source, identity)
        transitioned = tuple(
            identity.model_copy(
                update={
                    "identity_state": ProviderIdentityState.UNRESOLVED_COLLISION,
                    "latest_source_version_id": source.source_version_id,
                }
            )
            for identity in ordered
        )
        events = tuple(
            build_identity_state_event(
                provider_security_identity_id=identity.provider_security_identity_id,
                source_version_id=source.source_version_id,
                identity_state=ProviderIdentityState.UNRESOLVED_COLLISION,
                staging_state=ProviderSecurityMasterState.QUARANTINED,
                reason_code="UNRESOLVED_COLLISION",
            )
            for identity in ordered
        )
        collision_ids = tuple(item.provider_security_identity_id for item in ordered)
        observation = build_security_master_observation(
            source_version_id=source.source_version_id,
            normalized_record_id=record.normalized_record_id,
            provider_security_identity_id=None,
            provider=ProviderSystem.TOSS_OPEN_API,
            market=market,
            symbol=item.symbol,
            name=item.name,
            security_type=item.securityType,
            is_common_share=item.isCommonShare,
            isin=item.isinCode,
            staging_state=ProviderSecurityMasterState.QUARANTINED,
            reconciliation_outcome=ProviderReconciliationOutcome.UNRESOLVED_COLLISION,
            identity_state_after=ProviderIdentityState.UNRESOLVED_COLLISION,
            eligible_for_mapping=False,
            collision_identity_ids=collision_ids,
            reason_codes=tuple(sorted(set(reason_codes))),
        )
        persisted = self._repository.persist_bundle(
            SecurityMasterPersistenceBundle(
                record=record,
                observation=observation,
                identity_updates=transitioned,
                state_events=events,
            )
        )
        return persisted.record

    def _stage_missing_detail(
        self, source: ProviderSourceVersion, market: Market, symbol: str
    ) -> ProviderSecurityMasterObservation:
        discovery = self._latest_discovery_for_symbol(source, market, symbol)
        if discovery is None:
            raise ProviderContractConflict(
                "missing detail cannot be staged without discovery evidence"
            )
        identity = self._unique_active_symbol_identity(market, symbol)
        observation = build_security_master_observation(
            source_version_id=source.source_version_id,
            normalized_record_id=None,
            provider_security_identity_id=(
                None if identity is None else identity.provider_security_identity_id
            ),
            provider=ProviderSystem.TOSS_OPEN_API,
            market=market,
            symbol=symbol,
            name=discovery.name,
            security_type=discovery.security_type,
            is_common_share=discovery.is_common_share,
            isin=discovery.isin,
            staging_state=ProviderSecurityMasterState.QUARANTINED,
            reconciliation_outcome=ProviderReconciliationOutcome.DETAIL_MISSING,
            identity_state_after=None if identity is None else identity.identity_state,
            eligible_for_mapping=False,
            collision_identity_ids=(),
            reason_codes=("DETAIL_RESPONSE_MISSING",),
        )
        persisted = self._repository.persist_bundle(
            SecurityMasterPersistenceBundle(record=None, observation=observation)
        )
        return persisted.record

    def _continuity_candidates(
        self,
        source: ProviderSourceVersion,
        item: TossStockDetailItem,
        identities: tuple[ProviderSecurityIdentity, ...],
        history: dict[str, tuple[ProviderIdentifierHistory, ...]],
    ) -> dict[str, ProviderSecurityIdentity]:
        candidates: dict[str, ProviderSecurityIdentity] = {}
        for identity in identities:
            entries = history.get(identity.provider_security_identity_id, ())
            current_symbol = self._current_identifier(entries, ProviderIdentifierKind.SYMBOL)
            active = identity.identity_state == ProviderIdentityState.ACTIVE
            if (
                active
                and current_symbol is not None
                and current_symbol.identifier_value == item.symbol
            ):
                candidates[identity.provider_security_identity_id] = identity
            if item.isinCode is not None and any(
                entry.identifier_kind == ProviderIdentifierKind.ISIN
                and entry.identifier_value == item.isinCode
                for entry in entries
            ):
                candidates[identity.provider_security_identity_id] = identity
            if item.listDate is not None:
                has_symbol = any(
                    entry.identifier_kind == ProviderIdentifierKind.SYMBOL
                    and entry.identifier_value == item.symbol
                    for entry in entries
                )
                has_list_date = any(
                    entry.identifier_kind == ProviderIdentifierKind.LIST_DATE
                    and entry.identifier_value == item.listDate.isoformat()
                    for entry in entries
                )
                if has_symbol and has_list_date:
                    candidates[identity.provider_security_identity_id] = identity
            if (
                active
                and source.supersedes_id == identity.latest_source_version_id
                and any(
                    entry.identifier_kind == ProviderIdentifierKind.SYMBOL
                    and entry.identifier_value == item.symbol
                    for entry in entries
                )
            ):
                candidates[identity.provider_security_identity_id] = identity
        return candidates

    def _identity_conflict_reason(
        self,
        source: ProviderSourceVersion,
        item: TossStockDetailItem,
        identity: ProviderSecurityIdentity,
        history: dict[str, tuple[ProviderIdentifierHistory, ...]],
    ) -> str | None:
        entries = history.get(identity.provider_security_identity_id, ())
        current_symbol = self._current_identifier(entries, ProviderIdentifierKind.SYMBOL)
        current_isin = self._current_identifier(entries, ProviderIdentifierKind.ISIN)
        current_list_date = self._current_identifier(entries, ProviderIdentifierKind.LIST_DATE)
        correction = (
            source.revision_status == RevisionStatus.AMENDED
            and source.supersedes_id == identity.latest_source_version_id
        )
        if (
            current_symbol is not None
            and current_symbol.identifier_value != item.symbol
            and identity.latest_source_version_id == source.source_version_id
        ):
            return "DUPLICATE_ACTIVE_ISIN"
        if (
            current_isin is not None
            and item.isinCode is not None
            and current_isin.identifier_value != item.isinCode
            and not correction
        ):
            return "ISIN_CHANGE_REQUIRES_REVIEW"
        if (
            current_list_date is not None
            and item.listDate is not None
            and current_list_date.identifier_value != item.listDate.isoformat()
            and not correction
        ):
            return "LIST_DATE_CHANGE_REQUIRES_REVIEW"
        return None

    def _record_conflict_reason(
        self, identity: ProviderSecurityIdentity, item: TossStockDetailItem
    ) -> str | None:
        latest = self._latest_record_for_identity(identity.provider_security_identity_id)
        if latest is None:
            return None
        if (
            latest.security_type != item.securityType
            or latest.is_common_share != item.isCommonShare
        ):
            return "SHARE_CLASS_CHANGE_REQUIRES_REVIEW"
        if latest.provider_listing_market != item.market:
            return "LISTING_MARKET_CHANGE_REQUIRES_REVIEW"
        return None

    def _is_identifier_correction(
        self,
        source: ProviderSourceVersion,
        item: TossStockDetailItem,
        identity: ProviderSecurityIdentity,
        history: dict[str, tuple[ProviderIdentifierHistory, ...]],
    ) -> bool:
        if (
            source.revision_status != RevisionStatus.AMENDED
            or source.supersedes_id != identity.latest_source_version_id
        ):
            return False
        entries = history.get(identity.provider_security_identity_id, ())
        current_isin = self._current_identifier(entries, ProviderIdentifierKind.ISIN)
        current_list_date = self._current_identifier(entries, ProviderIdentifierKind.LIST_DATE)
        return bool(
            (
                current_isin is not None
                and item.isinCode is not None
                and current_isin.identifier_value != item.isinCode
            )
            or (
                current_list_date is not None
                and item.listDate is not None
                and current_list_date.identifier_value != item.listDate.isoformat()
            )
        )

    def _allocate_identity(
        self, source: ProviderSourceVersion, market: Market, item: TossStockDetailItem
    ) -> ProviderSecurityIdentity:
        if item.isinCode is not None:
            anchor = f"toss-identity-v1|{market.value}|ISIN|{item.isinCode}"
        elif item.listDate is not None:
            anchor = (
                f"toss-identity-v1|{market.value}|SYMBOL_LIST_DATE|"
                f"{item.symbol}|{item.listDate.isoformat()}"
            )
        else:
            anchor = (
                f"toss-identity-v1|{market.value}|FIRST_SEEN_RAW|"
                f"{item.symbol}|{source.raw_content_hash}"
            )
        anchor_hash = sha256_prefixed(anchor.encode("utf-8"))
        return ProviderSecurityIdentity(
            provider_security_identity_id=provider_identity_id_from_anchor(anchor),
            provider=ProviderSystem.TOSS_OPEN_API,
            market=market,
            allocation_anchor_hash=anchor_hash,
            identity_state=ProviderIdentityState.ACTIVE,
            mapping_status=MappingStatus.UNRESOLVED,
            first_source_version_id=source.source_version_id,
            latest_source_version_id=source.source_version_id,
            provider_contract_version=PROVIDER_IDENTITY_CONTRACT_VERSION,
        )

    def _identifier_updates(
        self,
        *,
        source: ProviderSourceVersion,
        market: Market,
        item: TossStockDetailItem,
        identity: ProviderSecurityIdentity,
        existing: tuple[ProviderIdentifierHistory, ...],
        initial: bool,
    ) -> tuple[ProviderIdentifierHistory, ...]:
        values: list[
            tuple[ProviderIdentifierKind, str, date | None, date | None, ProviderIdentifierReason]
        ] = []
        current_symbol = self._current_identifier(existing, ProviderIdentifierKind.SYMBOL)
        current_isin = self._current_identifier(existing, ProviderIdentifierKind.ISIN)
        reason = (
            ProviderIdentifierReason.INITIAL if initial else ProviderIdentifierReason.ENRICHMENT
        )
        if current_symbol is not None and current_symbol.identifier_value != item.symbol:
            values.append(
                (
                    ProviderIdentifierKind.SYMBOL,
                    current_symbol.identifier_value,
                    current_symbol.valid_from,
                    item.listDate,
                    ProviderIdentifierReason.SYMBOL_CHANGE,
                )
            )
            symbol_reason = ProviderIdentifierReason.SYMBOL_CHANGE
        else:
            symbol_reason = reason
        valid_to = item.delistDate if item.status == ProviderSecurityStatus.DELISTED else None
        values.extend(
            [
                (
                    ProviderIdentifierKind.SYMBOL,
                    item.symbol,
                    item.listDate,
                    valid_to,
                    symbol_reason,
                ),
                (ProviderIdentifierKind.MARKET, market.value, item.listDate, valid_to, reason),
            ]
        )
        if item.isinCode is not None:
            isin_reason = (
                ProviderIdentifierReason.CORRECTION
                if current_isin is not None and current_isin.identifier_value != item.isinCode
                else reason
            )
            values.append(
                (ProviderIdentifierKind.ISIN, item.isinCode, item.listDate, valid_to, isin_reason)
            )
        if item.listDate is not None:
            values.append(
                (
                    ProviderIdentifierKind.LIST_DATE,
                    item.listDate.isoformat(),
                    item.listDate,
                    valid_to,
                    reason,
                )
            )
        return tuple(
            self._build_identifier_history(
                identity.provider_security_identity_id,
                source.source_version_id,
                kind,
                value,
                valid_from,
                entry_valid_to,
                revision_reason,
            )
            for kind, value, valid_from, entry_valid_to, revision_reason in values
        )

    @staticmethod
    def _build_identifier_history(
        identity_id: str,
        source_version_id: str,
        kind: ProviderIdentifierKind,
        value: str,
        valid_from: date | None,
        valid_to: date | None,
        reason: ProviderIdentifierReason,
    ) -> ProviderIdentifierHistory:
        payload = {
            "provider_security_identity_id": identity_id,
            "identifier_kind": kind.value,
            "identifier_value": value,
            "valid_from": None if valid_from is None else valid_from.isoformat(),
            "valid_to": None if valid_to is None else valid_to.isoformat(),
            "source_version_id": source_version_id,
            "revision_reason": reason.value,
            "provider_contract_version": PROVIDER_IDENTITY_CONTRACT_VERSION,
        }
        digest = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
        return ProviderIdentifierHistory(
            identifier_history_id=f"pih_{digest}",
            provider_security_identity_id=identity_id,
            identifier_kind=kind,
            identifier_value=value,
            valid_from=valid_from,
            valid_to=valid_to,
            source_version_id=source_version_id,
            revision_reason=reason,
            provider_contract_version=PROVIDER_IDENTITY_CONTRACT_VERSION,
        )

    def _normalized_record(
        self, market: Market, item: TossStockDetailItem
    ) -> ProviderSecurityMasterRecord:
        missing: dict[str, MissingReason] = {}
        for field, value, reason in (
            ("english_name", item.englishName, MissingReason.NOT_PROVIDED),
            ("isin", item.isinCode, MissingReason.NOT_PROVIDED),
            ("list_date", item.listDate, MissingReason.NOT_PROVIDED),
            ("delist_date", item.delistDate, MissingReason.NOT_APPLICABLE),
            ("leverage_factor", item.leverageFactor, MissingReason.NOT_APPLICABLE),
        ):
            if value is None:
                missing[field] = reason
        return build_security_master_record(
            provider=ProviderSystem.TOSS_OPEN_API,
            market=market,
            provider_listing_market=item.market,
            symbol=item.symbol,
            name=item.name,
            english_name=item.englishName,
            isin=item.isinCode,
            security_type=item.securityType,
            is_common_share=item.isCommonShare,
            status=item.status,
            currency=item.currency,
            list_date=item.listDate,
            delist_date=item.delistDate,
            shares_outstanding=item.sharesOutstanding,
            leverage_factor=item.leverageFactor,
            missing_reasons=missing,
        )

    @staticmethod
    def _detail_reason_codes(market: Market, item: TossStockDetailItem) -> tuple[str, ...]:
        reasons: list[str] = []
        if item.isinCode is None:
            reasons.append("ISIN_NOT_PROVIDED")
        if item.listDate is None:
            reasons.append("LIST_DATE_NOT_PROVIDED")
        if item.market not in _SUPPORTED_LISTING_MARKETS[market]:
            reasons.append("UNSUPPORTED_LISTING_MARKET")
        if item.securityType != ProviderSecurityType.STOCK:
            reasons.append("UNSUPPORTED_SECURITY_TYPE")
        if not item.isCommonShare:
            reasons.append("NON_COMMON_SHARE")
        if item.currency != _EXPECTED_CURRENCY[market]:
            reasons.append("MARKET_CURRENCY_MISMATCH")
        if item.status == ProviderSecurityStatus.ACTIVE and item.delistDate is not None:
            reasons.append("ACTIVE_WITH_DELIST_DATE")
        if item.status == ProviderSecurityStatus.DELISTED and item.delistDate is None:
            reasons.append("DELISTED_WITHOUT_DELIST_DATE")
        if market == Market.US and item.koreanMarketDetail is not None:
            reasons.append("US_WITH_KOREAN_MARKET_DETAIL")
        return tuple(sorted(reasons))

    @staticmethod
    def _discovery_reason_codes(item: TossStockDiscoveryItem) -> tuple[str, ...]:
        reasons: list[str] = []
        if item.isinCode is None:
            reasons.append("ISIN_NOT_PROVIDED")
        if item.securityType != ProviderSecurityType.STOCK:
            reasons.append("UNSUPPORTED_SECURITY_TYPE")
        if not item.isCommonShare:
            reasons.append("NON_COMMON_SHARE")
        return tuple(sorted(reasons))

    @staticmethod
    def _target_state(
        market: Market, item: TossStockDetailItem, reason_codes: list[str]
    ) -> tuple[ProviderIdentityState, ProviderSecurityMasterState, bool]:
        hard_reasons = set(reason_codes) - {"ISIN_NOT_PROVIDED", "LIST_DATE_NOT_PROVIDED"}
        if hard_reasons:
            return (
                ProviderIdentityState.QUARANTINED,
                ProviderSecurityMasterState.QUARANTINED,
                False,
            )
        if item.status == ProviderSecurityStatus.DELISTED:
            return (
                ProviderIdentityState.INACTIVE,
                ProviderSecurityMasterState.DELISTED_OBSERVED,
                False,
            )
        if item.status in {ProviderSecurityStatus.INACTIVE, ProviderSecurityStatus.SCHEDULED}:
            return (
                ProviderIdentityState.INACTIVE,
                ProviderSecurityMasterState.INACTIVE_OBSERVED,
                False,
            )
        eligible = (
            item.status == ProviderSecurityStatus.ACTIVE
            and item.market in _SUPPORTED_LISTING_MARKETS[market]
            and item.securityType == ProviderSecurityType.STOCK
            and item.isCommonShare
            and item.currency == _EXPECTED_CURRENCY[market]
        )
        return (
            ProviderIdentityState.ACTIVE,
            (
                ProviderSecurityMasterState.ELIGIBLE_FOR_MAPPING
                if eligible
                else ProviderSecurityMasterState.DETAIL_VALID
            ),
            eligible,
        )

    @staticmethod
    def _event_reason(
        staging_state: ProviderSecurityMasterState, initial: bool, reasons: list[str]
    ) -> str:
        if staging_state == ProviderSecurityMasterState.QUARANTINED:
            return sorted(set(reasons))[0]
        if staging_state == ProviderSecurityMasterState.DELISTED_OBSERVED:
            return "DELISTED_OBSERVED"
        if staging_state == ProviderSecurityMasterState.INACTIVE_OBSERVED:
            return "INACTIVE_OBSERVED"
        return "IDENTITY_ALLOCATED" if initial else "IDENTITY_REUSED"

    def _validated_source(
        self, source_version_id: str, dataset: ProviderDataset
    ) -> ProviderSourceVersion:
        source = self._repository.source_version(source_version_id)
        if source.provider != ProviderSystem.TOSS_OPEN_API or source.dataset != dataset:
            raise ProviderContractConflict("security master source dataset/provider mismatch")
        return source

    def _market_identities(self, market: Market) -> tuple[ProviderSecurityIdentity, ...]:
        return tuple(
            identity
            for identity in self._repository.list_identities()
            if identity.provider == ProviderSystem.TOSS_OPEN_API and identity.market == market
        )

    def _history_by_identity(self) -> dict[str, tuple[ProviderIdentifierHistory, ...]]:
        grouped: defaultdict[str, list[ProviderIdentifierHistory]] = defaultdict(list)
        for entry in self._repository.list_identifier_history():
            grouped[entry.provider_security_identity_id].append(entry)
        return {
            identity_id: tuple(sorted(entries, key=self._history_order))
            for identity_id, entries in grouped.items()
        }

    def _history_order(self, entry: ProviderIdentifierHistory) -> tuple[datetime, str, str]:
        source = self._repository.source_version(entry.source_version_id)
        return (*self._source_order(source), entry.identifier_history_id)

    @staticmethod
    def _source_order(source: ProviderSourceVersion) -> tuple[datetime, str]:
        return (source.fetched_at, source.source_version_id)

    def _current_identifier(
        self,
        entries: tuple[ProviderIdentifierHistory, ...],
        kind: ProviderIdentifierKind,
    ) -> ProviderIdentifierHistory | None:
        matching = [entry for entry in entries if entry.identifier_kind == kind]
        return None if not matching else max(matching, key=self._history_order)

    def _require_monotonic_source(
        self, source: ProviderSourceVersion, identity: ProviderSecurityIdentity
    ) -> None:
        latest = self._repository.source_version(identity.latest_source_version_id)
        if self._source_order(source) < self._source_order(latest):
            raise ProviderContractConflict(
                "security master sources must reconcile in (fetched_at, source_version_id) order"
            )

    def _unique_active_symbol_identity(
        self, market: Market, symbol: str
    ) -> ProviderSecurityIdentity | None:
        history = self._history_by_identity()
        matches = [
            identity
            for identity in self._market_identities(market)
            if identity.identity_state == ProviderIdentityState.ACTIVE
            and (
                current := self._current_identifier(
                    history.get(identity.provider_security_identity_id, ()),
                    ProviderIdentifierKind.SYMBOL,
                )
            )
            is not None
            and current.identifier_value == symbol
        ]
        return matches[0] if len(matches) == 1 else None

    def _prior_discovery_snapshot(
        self, source: ProviderSourceVersion, market: Market
    ) -> tuple[ProviderSecurityMasterObservation, ...]:
        grouped: defaultdict[str, list[ProviderSecurityMasterObservation]] = defaultdict(list)
        for observation in self._repository.list_observations():
            if (
                observation.market != market
                or observation.source_version_id == source.source_version_id
                or observation.staging_state != ProviderSecurityMasterState.DISCOVERED
            ):
                continue
            observation_source = self._repository.source_version(observation.source_version_id)
            if observation_source.dataset == ProviderDataset.STOCK_DISCOVERY and self._source_order(
                observation_source
            ) < self._source_order(source):
                grouped[observation.source_version_id].append(observation)
        if not grouped:
            return ()
        latest_id = max(
            grouped,
            key=lambda source_id: self._source_order(self._repository.source_version(source_id)),
        )
        return tuple(sorted(grouped[latest_id], key=lambda item: item.symbol.encode("ascii")))

    def _latest_discovery_for_symbol(
        self, source: ProviderSourceVersion, market: Market, symbol: str
    ) -> ProviderSecurityMasterObservation | None:
        candidates: list[ProviderSecurityMasterObservation] = []
        for observation in self._repository.list_observations():
            if (
                observation.market == market
                and observation.symbol == symbol
                and observation.staging_state == ProviderSecurityMasterState.DISCOVERED
            ):
                observation_source = self._repository.source_version(observation.source_version_id)
                if self._source_order(observation_source) <= self._source_order(source):
                    candidates.append(observation)
        if not candidates:
            return None
        return max(
            candidates,
            key=lambda item: self._source_order(
                self._repository.source_version(item.source_version_id)
            ),
        )

    def _latest_record_for_identity(self, identity_id: str) -> ProviderSecurityMasterRecord | None:
        records = {item.normalized_record_id: item for item in self._repository.list_records()}
        candidates = [
            observation
            for observation in self._repository.list_observations()
            if observation.provider_security_identity_id == identity_id
            and observation.normalized_record_id is not None
        ]
        if not candidates:
            return None
        latest = max(
            candidates,
            key=lambda item: self._source_order(
                self._repository.source_version(item.source_version_id)
            ),
        )
        if latest.normalized_record_id is None:
            raise AssertionError("filtered normalized observation lost its record ID")
        return records[latest.normalized_record_id]
