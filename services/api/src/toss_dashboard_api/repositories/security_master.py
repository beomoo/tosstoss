from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session, sessionmaker

from toss_dashboard_api.contracts.base import canonical_json_bytes
from toss_dashboard_api.contracts.enums import (
    ProviderDataset,
    ProviderSecurityMasterState,
    ProviderSystem,
)
from toss_dashboard_api.contracts.provider_identity import (
    ProviderIdentifierHistory,
    ProviderSecurityIdentity,
)
from toss_dashboard_api.contracts.provider_security_master import (
    ProviderDetailBatchResult,
    ProviderIdentityStateEvent,
    ProviderSecurityMasterObservation,
    ProviderSecurityMasterRecord,
)
from toss_dashboard_api.contracts.provider_source import CanonicalRequest, ProviderSourceVersion
from toss_dashboard_api.repositories.provider import (
    InsertResult,
    ProviderContractConflict,
    ProviderRepositoryError,
)
from toss_dashboard_api.storage.models import (
    CanonicalRequestRow,
    ProviderDetailBatchResultRow,
    ProviderIdentifierHistoryRow,
    ProviderIdentityStateEventRow,
    ProviderSecurityIdentityRow,
    ProviderSecurityMasterObservationRow,
    ProviderSecurityMasterRecordRow,
    ProviderSourceVersionRow,
)


@dataclass(frozen=True)
class SecurityMasterPersistenceBundle:
    record: ProviderSecurityMasterRecord | None
    observation: ProviderSecurityMasterObservation
    identity_updates: tuple[ProviderSecurityIdentity, ...] = ()
    identifier_history: tuple[ProviderIdentifierHistory, ...] = ()
    state_events: tuple[ProviderIdentityStateEvent, ...] = ()


class SQLiteSecurityMasterRepository:
    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self._sessions = sessions

    def canonical_request(self, canonical_request_id: str) -> CanonicalRequest:
        with self._sessions() as session:
            row = session.get(CanonicalRequestRow, canonical_request_id)
            if row is None:
                raise ProviderRepositoryError("security master source request is missing")
            return CanonicalRequest.model_validate_json(row.payload_json)

    def source_version(self, source_version_id: str) -> ProviderSourceVersion:
        with self._sessions() as session:
            row = session.get(ProviderSourceVersionRow, source_version_id)
            if row is None:
                raise ProviderRepositoryError("security master source version is missing")
            return ProviderSourceVersion.model_validate_json(row.payload_json)

    def list_identities(self) -> list[ProviderSecurityIdentity]:
        with self._sessions() as session:
            rows = session.scalars(
                select(ProviderSecurityIdentityRow).order_by(
                    ProviderSecurityIdentityRow.provider_security_identity_id
                )
            )
            return [ProviderSecurityIdentity.model_validate_json(row.payload_json) for row in rows]

    def list_identifier_history(self) -> list[ProviderIdentifierHistory]:
        with self._sessions() as session:
            rows = session.scalars(
                select(ProviderIdentifierHistoryRow).order_by(
                    ProviderIdentifierHistoryRow.identifier_history_id
                )
            )
            return [ProviderIdentifierHistory.model_validate_json(row.payload_json) for row in rows]

    def list_observations(self) -> list[ProviderSecurityMasterObservation]:
        with self._sessions() as session:
            rows = session.scalars(
                select(ProviderSecurityMasterObservationRow).order_by(
                    ProviderSecurityMasterObservationRow.observation_id
                )
            )
            return [
                ProviderSecurityMasterObservation.model_validate_json(row.payload_json)
                for row in rows
            ]

    def list_records(self) -> list[ProviderSecurityMasterRecord]:
        with self._sessions() as session:
            rows = session.scalars(
                select(ProviderSecurityMasterRecordRow).order_by(
                    ProviderSecurityMasterRecordRow.normalized_record_id
                )
            )
            return [
                ProviderSecurityMasterRecord.model_validate_json(row.payload_json) for row in rows
            ]

    def list_state_events(self) -> list[ProviderIdentityStateEvent]:
        with self._sessions() as session:
            rows = session.scalars(
                select(ProviderIdentityStateEventRow).order_by(
                    ProviderIdentityStateEventRow.state_event_id
                )
            )
            return [
                ProviderIdentityStateEvent.model_validate_json(row.payload_json) for row in rows
            ]

    def list_detail_batches(self) -> list[ProviderDetailBatchResult]:
        with self._sessions() as session:
            rows = session.scalars(
                select(ProviderDetailBatchResultRow).order_by(
                    ProviderDetailBatchResultRow.batch_result_id
                )
            )
            return [ProviderDetailBatchResult.model_validate_json(row.payload_json) for row in rows]

    def record_detail_batch(
        self, result: ProviderDetailBatchResult
    ) -> InsertResult[ProviderDetailBatchResult]:
        payload = _payload_json(result)
        try:
            with self._sessions.begin() as session:
                source = self._required_source(session, result.source_version_id)
                if source.dataset != ProviderDataset.STOCK_DETAIL:
                    raise ProviderContractConflict("detail batch requires STOCK_DETAIL source")
                existing = session.get(ProviderDetailBatchResultRow, result.batch_result_id)
                if existing is not None:
                    return InsertResult(
                        _verify_payload(existing.payload_json, payload, result), False
                    )
                duplicate = session.scalar(
                    select(ProviderDetailBatchResultRow).where(
                        ProviderDetailBatchResultRow.source_version_id == result.source_version_id
                    )
                )
                if duplicate is not None:
                    return InsertResult(
                        _verify_payload(duplicate.payload_json, payload, result), False
                    )
                session.add(
                    ProviderDetailBatchResultRow(
                        batch_result_id=result.batch_result_id,
                        source_version_id=result.source_version_id,
                        requested_count=result.requested_count,
                        received_count=result.received_count,
                        missing_count=result.missing_count,
                        status=result.status.value,
                        provider_contract_version=result.provider_contract_version,
                        payload_json=payload,
                    )
                )
            return InsertResult(result, True)
        except ProviderRepositoryError:
            raise
        except (IntegrityError, OperationalError):
            raise ProviderContractConflict("detail batch persistence conflict") from None

    def persist_bundle(
        self, bundle: SecurityMasterPersistenceBundle
    ) -> InsertResult[ProviderSecurityMasterObservation]:
        try:
            with self._sessions.begin() as session:
                source = self._required_source(session, bundle.observation.source_version_id)
                self._validate_observation_source(source, bundle.observation)
                if bundle.record is not None:
                    self._insert_or_verify_record(session, bundle.record)
                    session.flush()
                for identity in bundle.identity_updates:
                    self._insert_or_transition_identity(session, identity)
                for history in bundle.identifier_history:
                    self._append_identifier_history(session, history)
                for event in bundle.state_events:
                    self._append_state_event(session, event)
                return self._append_observation(session, bundle.observation)
        except ProviderRepositoryError:
            raise
        except (IntegrityError, OperationalError):
            raise ProviderContractConflict("security master persistence conflict") from None

    @staticmethod
    def _required_source(session: Session, source_version_id: str) -> ProviderSourceVersion:
        row = session.get(ProviderSourceVersionRow, source_version_id)
        if row is None:
            raise ProviderRepositoryError("security master record requires existing source lineage")
        return ProviderSourceVersion.model_validate_json(row.payload_json)

    @staticmethod
    def _validate_observation_source(
        source: ProviderSourceVersion, observation: ProviderSecurityMasterObservation
    ) -> None:
        discovery_states = {
            ProviderSecurityMasterState.DISCOVERED,
            ProviderSecurityMasterState.DISCOVERY_MISSING,
        }
        expected = (
            ProviderDataset.STOCK_DISCOVERY
            if observation.staging_state in discovery_states
            else ProviderDataset.STOCK_DETAIL
        )
        if (
            source.provider != observation.provider
            or source.dataset != expected
            or source.provider != ProviderSystem.TOSS_OPEN_API
        ):
            raise ProviderContractConflict(
                "security master observation source trace does not match"
            )

    @staticmethod
    def _insert_or_verify_record(session: Session, record: ProviderSecurityMasterRecord) -> None:
        payload = _payload_json(record)
        existing = session.get(ProviderSecurityMasterRecordRow, record.normalized_record_id)
        if existing is not None:
            _verify_payload(existing.payload_json, payload, record)
            return
        duplicate = session.scalar(
            select(ProviderSecurityMasterRecordRow).where(
                ProviderSecurityMasterRecordRow.normalized_content_hash
                == record.normalized_content_hash
            )
        )
        if duplicate is not None:
            _verify_payload(duplicate.payload_json, payload, record)
            return
        session.add(
            ProviderSecurityMasterRecordRow(
                normalized_record_id=record.normalized_record_id,
                provider=record.provider.value,
                market=record.market.value,
                provider_listing_market=record.provider_listing_market.value,
                symbol=record.symbol,
                status=record.status.value,
                normalized_content_hash=record.normalized_content_hash,
                provider_contract_version=record.provider_contract_version,
                payload_json=payload,
            )
        )

    @staticmethod
    def _insert_or_transition_identity(
        session: Session, identity: ProviderSecurityIdentity
    ) -> None:
        payload = _payload_json(identity)
        existing_row = session.get(
            ProviderSecurityIdentityRow, identity.provider_security_identity_id
        )
        if existing_row is None:
            for source_id in (
                identity.first_source_version_id,
                identity.latest_source_version_id,
            ):
                source = SQLiteSecurityMasterRepository._required_source(session, source_id)
                if source.provider != identity.provider:
                    raise ProviderContractConflict("provider identity source lineage mismatch")
            session.add(
                ProviderSecurityIdentityRow(
                    provider_security_identity_id=identity.provider_security_identity_id,
                    provider=identity.provider.value,
                    market=identity.market.value,
                    allocation_anchor_hash=identity.allocation_anchor_hash,
                    identity_state=identity.identity_state.value,
                    mapping_status=identity.mapping_status.value,
                    first_source_version_id=identity.first_source_version_id,
                    latest_source_version_id=identity.latest_source_version_id,
                    provider_contract_version=identity.provider_contract_version,
                    payload_json=payload,
                )
            )
            session.flush()
            return

        existing = ProviderSecurityIdentity.model_validate_json(existing_row.payload_json)
        immutable_existing = (
            existing.provider_security_identity_id,
            existing.provider,
            existing.market,
            existing.allocation_anchor_hash,
            existing.mapping_status,
            existing.first_source_version_id,
            existing.provider_contract_version,
        )
        immutable_incoming = (
            identity.provider_security_identity_id,
            identity.provider,
            identity.market,
            identity.allocation_anchor_hash,
            identity.mapping_status,
            identity.first_source_version_id,
            identity.provider_contract_version,
        )
        if immutable_existing != immutable_incoming:
            raise ProviderContractConflict(
                "provider identity immutable allocation cannot be changed"
            )
        latest_source = SQLiteSecurityMasterRepository._required_source(
            session, identity.latest_source_version_id
        )
        if latest_source.provider != identity.provider:
            raise ProviderContractConflict("provider identity latest source lineage mismatch")
        if existing == identity:
            return
        session.execute(
            update(ProviderSecurityIdentityRow)
            .where(
                ProviderSecurityIdentityRow.provider_security_identity_id
                == identity.provider_security_identity_id
            )
            .values(
                identity_state=identity.identity_state.value,
                latest_source_version_id=identity.latest_source_version_id,
                payload_json=payload,
            )
        )

    @staticmethod
    def _append_identifier_history(session: Session, history: ProviderIdentifierHistory) -> None:
        payload = _payload_json(history)
        existing = session.get(ProviderIdentifierHistoryRow, history.identifier_history_id)
        if existing is not None:
            _verify_payload(existing.payload_json, payload, history)
            return
        identity = session.get(ProviderSecurityIdentityRow, history.provider_security_identity_id)
        source = SQLiteSecurityMasterRepository._required_source(session, history.source_version_id)
        if identity is None or identity.provider != source.provider.value:
            raise ProviderContractConflict("identifier history source or identity mismatch")
        session.add(
            ProviderIdentifierHistoryRow(
                identifier_history_id=history.identifier_history_id,
                provider_security_identity_id=history.provider_security_identity_id,
                identifier_kind=history.identifier_kind.value,
                identifier_value=history.identifier_value,
                valid_from=history.valid_from,
                valid_to=history.valid_to,
                source_version_id=history.source_version_id,
                revision_reason=history.revision_reason.value,
                provider_contract_version=history.provider_contract_version,
                payload_json=payload,
            )
        )

    @staticmethod
    def _append_state_event(session: Session, event: ProviderIdentityStateEvent) -> None:
        payload = _payload_json(event)
        existing = session.get(ProviderIdentityStateEventRow, event.state_event_id)
        if existing is not None:
            _verify_payload(existing.payload_json, payload, event)
            return
        identity = session.get(ProviderSecurityIdentityRow, event.provider_security_identity_id)
        source = SQLiteSecurityMasterRepository._required_source(session, event.source_version_id)
        if identity is None or identity.provider != source.provider.value:
            raise ProviderContractConflict("identity-state event source or identity mismatch")
        session.add(
            ProviderIdentityStateEventRow(
                state_event_id=event.state_event_id,
                provider_security_identity_id=event.provider_security_identity_id,
                source_version_id=event.source_version_id,
                identity_state=event.identity_state.value,
                staging_state=event.staging_state.value,
                reason_code=event.reason_code,
                provider_contract_version=event.provider_contract_version,
                payload_json=payload,
            )
        )

    @staticmethod
    def _append_observation(
        session: Session, observation: ProviderSecurityMasterObservation
    ) -> InsertResult[ProviderSecurityMasterObservation]:
        payload = _payload_json(observation)
        existing = session.get(ProviderSecurityMasterObservationRow, observation.observation_id)
        if existing is not None:
            return InsertResult(_verify_payload(existing.payload_json, payload, observation), False)
        if observation.normalized_record_id is not None:
            record = session.get(ProviderSecurityMasterRecordRow, observation.normalized_record_id)
            if record is None:
                raise ProviderContractConflict("observation normalized record is missing")
        if observation.provider_security_identity_id is not None:
            identity = session.get(
                ProviderSecurityIdentityRow, observation.provider_security_identity_id
            )
            if identity is None:
                raise ProviderContractConflict("observation provider identity is missing")
        for collision_id in observation.collision_identity_ids:
            if session.get(ProviderSecurityIdentityRow, collision_id) is None:
                raise ProviderContractConflict("collision observation references missing identity")
        session.add(
            ProviderSecurityMasterObservationRow(
                observation_id=observation.observation_id,
                source_version_id=observation.source_version_id,
                normalized_record_id=observation.normalized_record_id,
                provider_security_identity_id=observation.provider_security_identity_id,
                provider=observation.provider.value,
                market=observation.market.value,
                symbol=observation.symbol,
                staging_state=observation.staging_state.value,
                reconciliation_outcome=observation.reconciliation_outcome.value,
                eligible_for_mapping=int(observation.eligible_for_mapping),
                provider_contract_version=observation.provider_contract_version,
                payload_json=payload,
            )
        )
        session.flush()
        return InsertResult(observation, True)


def _payload_json(contract: BaseModel) -> str:
    return canonical_json_bytes(contract.model_dump(mode="json")).decode("utf-8")


def _verify_payload[ContractT](stored: str, incoming: str, contract: ContractT) -> ContractT:
    if stored != incoming:
        raise ProviderContractConflict(
            "deterministic security master identity has conflicting content"
        )
    return contract
