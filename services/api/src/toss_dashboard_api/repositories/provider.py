from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from toss_dashboard_api.contracts.base import canonical_json_bytes
from toss_dashboard_api.contracts.provider_identity import (
    ProviderIdentifierHistory,
    ProviderIdentityMapping,
    ProviderLatestPointer,
    ProviderSecurityIdentity,
)
from toss_dashboard_api.contracts.provider_source import (
    CanonicalRequest,
    CollectionAttempt,
    ProviderAuditEvent,
    ProviderRawManifest,
    ProviderSourceVersion,
)
from toss_dashboard_api.storage.models import (
    CanonicalRequestRow,
    CollectionAttemptRow,
    ProviderAuditEventRow,
    ProviderIdentifierHistoryRow,
    ProviderIdentityMappingRow,
    ProviderLatestPointerRow,
    ProviderRawManifestRow,
    ProviderSecurityIdentityRow,
    ProviderSourceVersionRow,
)
from toss_dashboard_api.storage.provider_raw import ProviderRawStore


class ProviderRepositoryError(RuntimeError):
    """Safe repository error that never embeds provider payloads or headers."""


class ProviderContractConflict(ProviderRepositoryError):
    """A deterministic identity was reused for different semantic content."""


class ProviderConditionalWriteConflict(ProviderRepositoryError):
    """A latest pointer compare-and-set precondition did not match."""


@dataclass(frozen=True)
class InsertResult[ContractT: BaseModel]:
    record: ContractT
    inserted: bool


def _payload_json(contract: BaseModel) -> str:
    return canonical_json_bytes(contract.model_dump(mode="json")).decode("utf-8")


class SQLiteProviderRepository:
    def __init__(self, sessions: sessionmaker[Session], raw_store: ProviderRawStore) -> None:
        self._sessions = sessions
        self._raw_store = raw_store

    def insert_or_verify_canonical_request(
        self, request: CanonicalRequest
    ) -> InsertResult[CanonicalRequest]:
        payload = _payload_json(request)
        with self._sessions.begin() as session:
            row = session.get(CanonicalRequestRow, request.canonical_request_id)
            if row is not None:
                return InsertResult(self._verify_payload(row.payload_json, payload, request), False)
            session.add(
                CanonicalRequestRow(
                    canonical_request_id=request.canonical_request_id,
                    provider=request.provider.value,
                    method=request.method.value,
                    path_template=request.path_template,
                    canonical_query_json=request.canonical_query_json,
                    canonical_query_hash=request.canonical_query_hash,
                    provider_contract_version=request.provider_contract_version,
                    payload_json=payload,
                )
            )
        return InsertResult(request, True)

    def insert_or_verify_raw_manifest(
        self, manifest: ProviderRawManifest
    ) -> InsertResult[ProviderRawManifest]:
        self._raw_store.verify(manifest.raw_storage_ref, manifest.raw_content_hash)
        payload = _payload_json(manifest)
        with self._sessions.begin() as session:
            request = session.get(CanonicalRequestRow, manifest.canonical_request_id)
            if request is None:
                raise ProviderRepositoryError(
                    "raw manifest references an unknown canonical request"
                )
            self._verify_manifest_request(request, manifest)
            row = session.get(ProviderRawManifestRow, manifest.raw_response_id)
            if row is not None:
                return InsertResult(
                    self._verify_payload(row.payload_json, payload, manifest), False
                )
            duplicate = session.scalar(
                select(ProviderRawManifestRow).where(
                    ProviderRawManifestRow.canonical_request_id == manifest.canonical_request_id,
                    ProviderRawManifestRow.http_status == manifest.http_status,
                    ProviderRawManifestRow.raw_content_hash == manifest.raw_content_hash,
                )
            )
            if duplicate is not None:
                return InsertResult(
                    ProviderRawManifest.model_validate_json(duplicate.payload_json), False
                )
            session.add(self._raw_manifest_row(manifest, payload))
        return InsertResult(manifest, True)

    def append_source_version(
        self, version: ProviderSourceVersion
    ) -> InsertResult[ProviderSourceVersion]:
        with self._sessions.begin() as session:
            return self._append_source_version(session, version)

    def record_source_version_with_audit(
        self,
        version: ProviderSourceVersion,
        event: ProviderAuditEvent,
    ) -> InsertResult[ProviderSourceVersion]:
        if event.source_version_id != version.source_version_id:
            raise ProviderRepositoryError("audit event does not reference the source version")
        with self._sessions.begin() as session:
            result = self._append_source_version(session, version)
            self._append_audit_event(session, event)
            return result

    def source_revision_chain(self, source_version_id: str) -> list[ProviderSourceVersion]:
        with self._sessions() as session:
            chain: list[ProviderSourceVersion] = []
            seen: set[str] = set()
            current = source_version_id
            while current:
                if current in seen:
                    raise ProviderRepositoryError("provider source revision cycle detected")
                seen.add(current)
                row = session.get(ProviderSourceVersionRow, current)
                if row is None:
                    raise ProviderRepositoryError("provider source revision is missing")
                contract = ProviderSourceVersion.model_validate_json(row.payload_json)
                chain.append(contract)
                current = contract.supersedes_id or ""
            return chain

    def record_collection_attempt(
        self, attempt: CollectionAttempt
    ) -> InsertResult[CollectionAttempt]:
        payload = _payload_json(attempt)
        with self._sessions.begin() as session:
            row = session.get(CollectionAttemptRow, attempt.attempt_id)
            if row is not None:
                return InsertResult(self._verify_payload(row.payload_json, payload, attempt), False)
            session.add(
                CollectionAttemptRow(
                    attempt_id=attempt.attempt_id,
                    provider=attempt.provider.value,
                    dataset=attempt.dataset.value,
                    canonical_request_id=attempt.canonical_request_id,
                    started_at=self._json_time(attempt.started_at),
                    finished_at=(
                        None
                        if attempt.finished_at is None
                        else self._json_time(attempt.finished_at)
                    ),
                    status=attempt.status.value,
                    records_received=attempt.records_received,
                    records_rejected=attempt.records_rejected,
                    safe_result_code=attempt.safe_result_code,
                    payload_json=payload,
                )
            )
        return InsertResult(attempt, True)

    def append_audit_event(self, event: ProviderAuditEvent) -> InsertResult[ProviderAuditEvent]:
        with self._sessions.begin() as session:
            return self._append_audit_event(session, event)

    def insert_or_verify_identity(
        self, identity: ProviderSecurityIdentity
    ) -> InsertResult[ProviderSecurityIdentity]:
        payload = _payload_json(identity)
        with self._sessions.begin() as session:
            row = session.get(ProviderSecurityIdentityRow, identity.provider_security_identity_id)
            if row is not None:
                return InsertResult(
                    self._verify_payload(row.payload_json, payload, identity), False
                )
            duplicate = session.scalar(
                select(ProviderSecurityIdentityRow).where(
                    ProviderSecurityIdentityRow.provider == identity.provider.value,
                    ProviderSecurityIdentityRow.allocation_anchor_hash
                    == identity.allocation_anchor_hash,
                )
            )
            if duplicate is not None:
                existing = ProviderSecurityIdentity.model_validate_json(duplicate.payload_json)
                if existing.provider_security_identity_id != identity.provider_security_identity_id:
                    raise ProviderContractConflict("provider allocation anchor identity conflict")
                return InsertResult(existing, False)
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
        return InsertResult(identity, True)

    def append_identifier_history(
        self, history: ProviderIdentifierHistory
    ) -> InsertResult[ProviderIdentifierHistory]:
        payload = _payload_json(history)
        with self._sessions.begin() as session:
            row = session.get(ProviderIdentifierHistoryRow, history.identifier_history_id)
            if row is not None:
                return InsertResult(self._verify_payload(row.payload_json, payload, history), False)
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
        return InsertResult(history, True)

    def record_identity_mapping(
        self, mapping: ProviderIdentityMapping
    ) -> InsertResult[ProviderIdentityMapping]:
        payload = _payload_json(mapping)
        with self._sessions.begin() as session:
            row = session.get(ProviderIdentityMappingRow, mapping.mapping_id)
            if row is not None:
                return InsertResult(self._verify_payload(row.payload_json, payload, mapping), False)
            session.add(
                ProviderIdentityMappingRow(
                    mapping_id=mapping.mapping_id,
                    provider_security_identity_id=mapping.provider_security_identity_id,
                    issuer_id=mapping.issuer_id,
                    security_id=mapping.security_id,
                    mapping_status=mapping.mapping_status.value,
                    evidence_source_version_id=mapping.evidence_source_version_id,
                    approved_at=(
                        None
                        if mapping.approved_at is None
                        else self._json_time(mapping.approved_at)
                    ),
                    valid_from=mapping.valid_from,
                    valid_to=mapping.valid_to,
                    provider_contract_version=mapping.provider_contract_version,
                    payload_json=payload,
                )
            )
        return InsertResult(mapping, True)

    def read_latest_pointer(
        self, dataset: str, provider_security_identity_id: str
    ) -> ProviderLatestPointer | None:
        with self._sessions() as session:
            row = session.scalar(
                select(ProviderLatestPointerRow).where(
                    ProviderLatestPointerRow.dataset == dataset,
                    ProviderLatestPointerRow.provider_security_identity_id
                    == provider_security_identity_id,
                )
            )
            return (
                None if row is None else ProviderLatestPointer.model_validate_json(row.payload_json)
            )

    def conditional_write_latest(
        self,
        pointer: ProviderLatestPointer,
        *,
        expected_state_hash: str | None,
    ) -> InsertResult[ProviderLatestPointer]:
        payload = _payload_json(pointer)
        with self._sessions.begin() as session:
            row = session.scalar(
                select(ProviderLatestPointerRow).where(
                    ProviderLatestPointerRow.dataset == pointer.dataset.value,
                    ProviderLatestPointerRow.provider_security_identity_id
                    == pointer.provider_security_identity_id,
                )
            )
            if row is None:
                if expected_state_hash is not None:
                    raise ProviderConditionalWriteConflict(
                        "latest pointer precondition did not match"
                    )
                session.add(self._latest_pointer_row(pointer, payload))
                return InsertResult(pointer, True)
            if row.state_hash != expected_state_hash:
                raise ProviderConditionalWriteConflict("latest pointer precondition did not match")
            if row.payload_json == payload:
                return InsertResult(pointer, False)
            if row.latest_pointer_id != pointer.latest_pointer_id:
                raise ProviderContractConflict("latest pointer deterministic identity conflict")
            row.normalized_record_id = pointer.normalized_record_id
            row.source_version_id = pointer.source_version_id
            row.accepted_observed_at = (
                None
                if pointer.accepted_observed_at is None
                else self._json_time(pointer.accepted_observed_at)
            )
            row.accepted_observed_date = pointer.accepted_observed_date
            row.state_hash = pointer.state_hash
            row.provider_contract_version = pointer.provider_contract_version
            row.payload_json = payload
            return InsertResult(pointer, True)

    def _append_source_version(
        self, session: Session, version: ProviderSourceVersion
    ) -> InsertResult[ProviderSourceVersion]:
        payload = _payload_json(version)
        row = session.get(ProviderSourceVersionRow, version.source_version_id)
        if row is not None:
            return InsertResult(self._verify_payload(row.payload_json, payload, version), False)
        raw = session.get(ProviderRawManifestRow, version.raw_response_id)
        if raw is None:
            raise ProviderRepositoryError("provider source references an unknown raw manifest")
        if (
            raw.canonical_request_id != version.canonical_request_id
            or raw.raw_content_hash != version.raw_content_hash
            or raw.provider_contract_version != version.provider_contract_version
        ):
            raise ProviderContractConflict("provider source and raw manifest do not match")
        if version.supersedes_id is not None:
            parent = session.get(ProviderSourceVersionRow, version.supersedes_id)
            if parent is None:
                raise ProviderRepositoryError("provider source supersedes an unknown version")
            if parent.canonical_request_id != version.canonical_request_id:
                raise ProviderContractConflict("revision chain crossed canonical requests")
        duplicate = session.scalar(
            select(ProviderSourceVersionRow).where(
                ProviderSourceVersionRow.canonical_request_id == version.canonical_request_id,
                ProviderSourceVersionRow.http_status == raw.http_status,
                ProviderSourceVersionRow.raw_content_hash == version.raw_content_hash,
                ProviderSourceVersionRow.provider_contract_version
                == version.provider_contract_version,
            )
        )
        if duplicate is not None:
            return InsertResult(
                ProviderSourceVersion.model_validate_json(duplicate.payload_json), False
            )
        session.add(
            ProviderSourceVersionRow(
                source_version_id=version.source_version_id,
                canonical_request_id=version.canonical_request_id,
                raw_response_id=version.raw_response_id,
                dataset=version.dataset.value,
                http_status=raw.http_status,
                raw_content_hash=version.raw_content_hash,
                provider_contract_version=version.provider_contract_version,
                revision_status=version.revision_status.value,
                supersedes_id=version.supersedes_id,
                normalized_content_hash=version.normalized_content_hash,
                payload_json=payload,
            )
        )
        session.flush()
        return InsertResult(version, True)

    def _append_audit_event(
        self, session: Session, event: ProviderAuditEvent
    ) -> InsertResult[ProviderAuditEvent]:
        payload = _payload_json(event)
        row = session.get(ProviderAuditEventRow, event.audit_event_id)
        if row is not None:
            return InsertResult(self._verify_payload(row.payload_json, payload, event), False)
        session.add(
            ProviderAuditEventRow(
                audit_event_id=event.audit_event_id,
                attempt_id=event.attempt_id,
                source_version_id=event.source_version_id,
                event_type=event.event_type.value,
                safe_status=event.safe_status,
                record_count=event.record_count,
                occurred_at=self._json_time(event.occurred_at),
                payload_json=payload,
            )
        )
        session.flush()
        return InsertResult(event, True)

    @staticmethod
    def _verify_payload[ContractT: BaseModel](
        stored: str, incoming: str, contract: ContractT
    ) -> ContractT:
        if stored != incoming:
            raise ProviderContractConflict("deterministic identity has conflicting content")
        return contract

    @staticmethod
    def _verify_manifest_request(
        request: CanonicalRequestRow, manifest: ProviderRawManifest
    ) -> None:
        if (
            request.provider != manifest.provider.value
            or request.method != manifest.method.value
            or request.path_template != manifest.path_template
            or request.canonical_query_json != manifest.canonical_query_json
            or request.provider_contract_version != manifest.provider_contract_version
        ):
            raise ProviderContractConflict("raw manifest does not match canonical request")

    @staticmethod
    def _raw_manifest_row(manifest: ProviderRawManifest, payload: str) -> ProviderRawManifestRow:
        return ProviderRawManifestRow(
            raw_response_id=manifest.raw_response_id,
            canonical_request_id=manifest.canonical_request_id,
            http_status=manifest.http_status,
            raw_content_hash=manifest.raw_content_hash,
            raw_storage_ref=manifest.raw_storage_ref,
            fetched_at=SQLiteProviderRepository._json_time(manifest.fetched_at),
            response_metadata_json=canonical_json_bytes(
                manifest.response_metadata.model_dump(mode="json")
            ).decode("utf-8"),
            provider_contract_version=manifest.provider_contract_version,
            payload_json=payload,
        )

    @staticmethod
    def _latest_pointer_row(
        pointer: ProviderLatestPointer, payload: str
    ) -> ProviderLatestPointerRow:
        return ProviderLatestPointerRow(
            latest_pointer_id=pointer.latest_pointer_id,
            dataset=pointer.dataset.value,
            provider_security_identity_id=pointer.provider_security_identity_id,
            normalized_record_id=pointer.normalized_record_id,
            source_version_id=pointer.source_version_id,
            accepted_observed_at=(
                None
                if pointer.accepted_observed_at is None
                else SQLiteProviderRepository._json_time(pointer.accepted_observed_at)
            ),
            accepted_observed_date=pointer.accepted_observed_date,
            state_hash=pointer.state_hash,
            provider_contract_version=pointer.provider_contract_version,
            payload_json=payload,
        )

    @staticmethod
    def _json_time(value: object) -> str:
        return canonical_json_bytes(value).decode("utf-8").strip('"')
