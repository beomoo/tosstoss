from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session, sessionmaker

from toss_dashboard_api.contracts.base import canonical_json_bytes
from toss_dashboard_api.contracts.enums import (
    MappingStatus,
    ProviderAuditEventType,
    ProviderDataset,
    ProviderIdentityState,
    RevisionStatus,
)
from toss_dashboard_api.contracts.provider_identity import (
    ProviderIdentifierHistory,
    ProviderIdentityMapping,
    ProviderLatestPointer,
    ProviderSecurityIdentity,
)
from toss_dashboard_api.contracts.provider_source import (
    PROVIDER_DATASET_BY_PATH,
    PROVIDER_SOURCE_LOCATOR_BY_DATASET,
    CanonicalRequest,
    CollectionAttempt,
    ProviderAuditEvent,
    ProviderRawManifest,
    ProviderSourceVersion,
)
from toss_dashboard_api.storage.models import (
    CanonicalRequestRow,
    CollectionAttemptRow,
    IssuerRow,
    ProviderAuditEventRow,
    ProviderIdentifierHistoryRow,
    ProviderIdentityMappingRow,
    ProviderLatestPointerRow,
    ProviderRawManifestRow,
    ProviderSecurityIdentityRow,
    ProviderSourceVersionRow,
    SecurityRow,
)
from toss_dashboard_api.storage.provider_raw import ProviderRawStore


class ProviderRepositoryError(RuntimeError):
    """Safe repository error that never embeds provider payloads or headers."""


class ProviderContractConflict(ProviderRepositoryError):
    """A deterministic identity was reused for different semantic content."""


class ProviderConditionalWriteConflict(ProviderRepositoryError):
    """A latest pointer compare-and-set precondition did not match."""


_SOURCE_LINKED_AUDIT_EVENTS = frozenset(
    {
        ProviderAuditEventType.SOURCE_APPENDED,
        ProviderAuditEventType.DUPLICATE_OBSERVED,
        ProviderAuditEventType.LATEST_ACCEPTED,
    }
)


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
                return InsertResult(self._verify_raw_duplicate(row, manifest), False)
            duplicate = session.scalar(
                select(ProviderRawManifestRow).where(
                    ProviderRawManifestRow.canonical_request_id == manifest.canonical_request_id,
                    ProviderRawManifestRow.http_status == manifest.http_status,
                    ProviderRawManifestRow.raw_content_hash == manifest.raw_content_hash,
                )
            )
            if duplicate is not None:
                return InsertResult(self._verify_raw_duplicate(duplicate, manifest), False)
            session.add(self._raw_manifest_row(manifest, payload))
        return InsertResult(manifest, True)

    def append_source_version(
        self, version: ProviderSourceVersion
    ) -> InsertResult[ProviderSourceVersion]:
        try:
            with self._sessions.begin() as session:
                return self._append_source_version(session, version)
        except ProviderRepositoryError:
            raise
        except (IntegrityError, OperationalError):
            raise ProviderContractConflict("provider source revision write conflict") from None

    def record_source_version_with_audit(
        self,
        version: ProviderSourceVersion,
        event: ProviderAuditEvent,
    ) -> InsertResult[ProviderSourceVersion]:
        if event.source_version_id != version.source_version_id:
            raise ProviderRepositoryError("audit event does not reference the source version")
        try:
            with self._sessions.begin() as session:
                result = self._append_source_version(session, version)
                self._append_audit_event(session, event)
                return result
        except ProviderRepositoryError:
            raise
        except (IntegrityError, OperationalError):
            raise ProviderContractConflict("provider source revision write conflict") from None

    def source_revision_chain(self, source_version_id: str) -> list[ProviderSourceVersion]:
        with self._sessions() as session:
            requested = session.get(ProviderSourceVersionRow, source_version_id)
            if requested is None:
                raise ProviderRepositoryError("provider source revision is missing")
            self._validated_source_leaf(session, requested.canonical_request_id)
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
            self._validate_attempt_request(session, attempt)
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
            self._validate_identity_sources(session, identity)
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
            identity = session.get(
                ProviderSecurityIdentityRow, history.provider_security_identity_id
            )
            source = session.get(ProviderSourceVersionRow, history.source_version_id)
            if identity is None or source is None:
                raise ProviderContractConflict(
                    "identifier history requires an existing identity and source"
                )
            source_contract = ProviderSourceVersion.model_validate_json(source.payload_json)
            if identity.provider != source_contract.provider.value:
                raise ProviderContractConflict(
                    "identifier history source does not match identity provider"
                )
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
        try:
            with self._sessions.begin() as session:
                row = session.get(ProviderIdentityMappingRow, mapping.mapping_id)
                if row is not None:
                    return InsertResult(
                        self._verify_payload(row.payload_json, payload, mapping), False
                    )
                self._validate_identity_mapping(session, mapping)
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
        except ProviderRepositoryError:
            raise
        except (IntegrityError, OperationalError):
            raise ProviderContractConflict("verified identity mapping write conflict") from None

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
        try:
            with self._sessions.begin() as session:
                self._validate_latest_eligibility(session, pointer)
                values = self._latest_pointer_values(pointer, payload)
                if expected_state_hash is None:
                    insert_statement = (
                        sqlite_insert(ProviderLatestPointerRow)
                        .values(**values)
                        .on_conflict_do_nothing()
                    )
                    result = session.execute(insert_statement)
                    if result.rowcount == 1:
                        return InsertResult(pointer, True)
                    if result.rowcount != 0:
                        raise ProviderRepositoryError(
                            "latest pointer insert affected an invalid row count"
                        )
                    existing = session.get(ProviderLatestPointerRow, pointer.latest_pointer_id)
                    if existing is not None and existing.payload_json == payload:
                        return InsertResult(
                            ProviderLatestPointer.model_validate_json(existing.payload_json),
                            False,
                        )
                    raise ProviderConditionalWriteConflict(
                        "latest pointer initial insert conflicted"
                    )

                update_statement = (
                    update(ProviderLatestPointerRow)
                    .where(
                        ProviderLatestPointerRow.latest_pointer_id == pointer.latest_pointer_id,
                        ProviderLatestPointerRow.state_hash == expected_state_hash,
                        ProviderLatestPointerRow.payload_json != payload,
                    )
                    .values(
                        normalized_record_id=pointer.normalized_record_id,
                        source_version_id=pointer.source_version_id,
                        accepted_observed_at=values["accepted_observed_at"],
                        accepted_observed_date=pointer.accepted_observed_date,
                        state_hash=pointer.state_hash,
                        provider_contract_version=pointer.provider_contract_version,
                        payload_json=payload,
                    )
                )
                result = session.execute(update_statement)
                if result.rowcount == 1:
                    return InsertResult(pointer, True)
                if result.rowcount == 0:
                    existing = session.get(ProviderLatestPointerRow, pointer.latest_pointer_id)
                    if (
                        existing is not None
                        and existing.state_hash == expected_state_hash
                        and existing.payload_json == payload
                    ):
                        return InsertResult(
                            ProviderLatestPointer.model_validate_json(existing.payload_json),
                            False,
                        )
                    raise ProviderConditionalWriteConflict(
                        "latest pointer precondition did not match"
                    )
                raise ProviderRepositoryError("latest pointer update affected an invalid row count")
        except ProviderRepositoryError:
            raise
        except (IntegrityError, OperationalError):
            raise ProviderRepositoryError("latest pointer database operation failed") from None

    def _append_source_version(
        self, session: Session, version: ProviderSourceVersion
    ) -> InsertResult[ProviderSourceVersion]:
        payload = _payload_json(version)
        row = session.get(ProviderSourceVersionRow, version.source_version_id)
        if row is not None:
            stored = self._verify_source_duplicate(row, version)
            self._validated_source_leaf(session, version.canonical_request_id)
            return InsertResult(stored, False)
        raw = session.get(ProviderRawManifestRow, version.raw_response_id)
        if raw is None:
            raise ProviderRepositoryError("provider source references an unknown raw manifest")
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
            stored = self._verify_source_duplicate(duplicate, version)
            self._validated_source_leaf(session, version.canonical_request_id)
            return InsertResult(stored, False)
        self._validate_source_trace(session, version, raw)
        current_leaf = self._validated_source_leaf(session, version.canonical_request_id)
        if current_leaf is None:
            if (
                version.revision_status != RevisionStatus.ORIGINAL
                or version.supersedes_id is not None
            ):
                raise ProviderContractConflict("first provider source must be an original root")
        elif (
            version.revision_status == RevisionStatus.ORIGINAL
            or version.supersedes_id != current_leaf
        ):
            raise ProviderContractConflict(
                "provider source revision must supersede the unique current leaf"
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

    @staticmethod
    def _validated_source_leaf(session: Session, canonical_request_id: str) -> str | None:
        rows = list(
            session.scalars(
                select(ProviderSourceVersionRow).where(
                    ProviderSourceVersionRow.canonical_request_id == canonical_request_id
                )
            )
        )
        if not rows:
            return None

        nodes: dict[str, tuple[str, str | None]] = {}
        try:
            for row in rows:
                contract = ProviderSourceVersion.model_validate_json(row.payload_json)
                if (
                    contract.source_version_id != row.source_version_id
                    or contract.canonical_request_id != row.canonical_request_id
                    or contract.revision_status.value != row.revision_status
                    or contract.supersedes_id != row.supersedes_id
                ):
                    raise ValueError
                nodes[row.source_version_id] = (row.revision_status, row.supersedes_id)
        except Exception:
            raise ProviderContractConflict("provider source revision history is invalid") from None

        roots = [
            source_id
            for source_id, (status, parent_id) in nodes.items()
            if status == RevisionStatus.ORIGINAL.value and parent_id is None
        ]
        if len(roots) != 1:
            raise ProviderContractConflict(
                "provider source revision history must have one original root"
            )

        valid_statuses = {status.value for status in RevisionStatus}
        children: dict[str, list[str]] = {}
        for source_id, (status, parent_id) in nodes.items():
            if status not in valid_statuses:
                raise ProviderContractConflict("provider source revision history is invalid")
            if status == RevisionStatus.ORIGINAL.value:
                if parent_id is not None:
                    raise ProviderContractConflict("provider source revision history is invalid")
                continue
            if parent_id is None or parent_id not in nodes:
                raise ProviderContractConflict(
                    "provider source revision parent is outside its canonical request"
                )
            children.setdefault(parent_id, []).append(source_id)
            if len(children[parent_id]) > 1:
                raise ProviderContractConflict("provider source revision history contains a fork")

        leaves = [source_id for source_id in nodes if source_id not in children]
        if len(leaves) != 1:
            raise ProviderContractConflict(
                "provider source revision history must have one current leaf"
            )

        visited: set[str] = set()
        current = roots[0]
        while True:
            if current in visited:
                raise ProviderContractConflict("provider source revision history contains a cycle")
            visited.add(current)
            next_versions = children.get(current, [])
            if not next_versions:
                break
            current = next_versions[0]
        if len(visited) != len(nodes) or current != leaves[0]:
            raise ProviderContractConflict("provider source revision history is not linear")
        return current

    def _append_audit_event(
        self, session: Session, event: ProviderAuditEvent
    ) -> InsertResult[ProviderAuditEvent]:
        payload = _payload_json(event)
        row = session.get(ProviderAuditEventRow, event.audit_event_id)
        if row is not None:
            return InsertResult(self._verify_payload(row.payload_json, payload, event), False)
        self._validate_audit_event(session, event)
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
    def _verify_raw_duplicate(
        row: ProviderRawManifestRow, incoming: ProviderRawManifest
    ) -> ProviderRawManifest:
        stored = ProviderRawManifest.model_validate_json(row.payload_json)
        stored_semantics = SQLiteProviderRepository._raw_duplicate_semantics(stored)
        incoming_semantics = SQLiteProviderRepository._raw_duplicate_semantics(incoming)
        if stored_semantics != incoming_semantics:
            raise ProviderContractConflict("raw observation has conflicting content")
        return stored

    @staticmethod
    def _raw_duplicate_semantics(manifest: ProviderRawManifest) -> dict[str, object]:
        semantics: dict[str, object] = manifest.model_dump(mode="json")
        semantics.pop("fetched_at")
        telemetry = manifest.response_metadata.model_dump(mode="json")
        for field_name in (
            "request_id",
            "rate_limit",
            "rate_remaining",
            "rate_reset_seconds",
            "retry_after_seconds",
        ):
            telemetry.pop(field_name)
        semantics["response_metadata"] = telemetry
        return semantics

    @staticmethod
    def _verify_source_duplicate(
        row: ProviderSourceVersionRow, incoming: ProviderSourceVersion
    ) -> ProviderSourceVersion:
        stored = ProviderSourceVersion.model_validate_json(row.payload_json)
        stored_semantics = stored.model_dump(mode="json")
        incoming_semantics = incoming.model_dump(mode="json")
        for field_name in ("source_version_id", "fetched_at"):
            stored_semantics.pop(field_name)
            incoming_semantics.pop(field_name)
        if stored_semantics != incoming_semantics:
            raise ProviderContractConflict("source observation has conflicting semantic content")
        return stored

    @staticmethod
    def _validate_source_trace(
        session: Session,
        version: ProviderSourceVersion,
        raw: ProviderRawManifestRow,
    ) -> None:
        request = session.get(CanonicalRequestRow, version.canonical_request_id)
        if request is None:
            raise ProviderRepositoryError("provider source references an unknown request")
        raw_contract = ProviderRawManifest.model_validate_json(raw.payload_json)
        expected_dataset = PROVIDER_DATASET_BY_PATH.get(request.path_template)
        if expected_dataset is None or expected_dataset != version.dataset:
            raise ProviderContractConflict("provider path and source dataset do not match")
        if version.source_locator != PROVIDER_SOURCE_LOCATOR_BY_DATASET[version.dataset]:
            raise ProviderContractConflict("provider source locator does not match dataset")
        if (
            raw.canonical_request_id != version.canonical_request_id
            or raw_contract.provider != version.provider
            or request.provider != version.provider.value
            or raw.raw_content_hash != version.raw_content_hash
            or raw_contract.raw_storage_ref != version.raw_storage_ref
            or raw_contract.fetched_at != version.fetched_at
            or raw_contract.parser_version != version.parser_version
            or raw.provider_contract_version != version.provider_contract_version
            or request.provider_contract_version != version.provider_contract_version
        ):
            raise ProviderContractConflict("provider source trace does not match request and raw")

    @staticmethod
    def _validate_attempt_request(session: Session, attempt: CollectionAttempt) -> None:
        if attempt.canonical_request_id is None:
            return
        request = session.get(CanonicalRequestRow, attempt.canonical_request_id)
        if request is None:
            raise ProviderRepositoryError("collection attempt references an unknown request")
        expected_dataset = PROVIDER_DATASET_BY_PATH.get(request.path_template)
        if (
            request.provider != attempt.provider.value
            or expected_dataset is None
            or expected_dataset != attempt.dataset
        ):
            raise ProviderContractConflict("collection attempt does not match canonical request")

    @staticmethod
    def _validate_audit_event(session: Session, event: ProviderAuditEvent) -> None:
        attempt = session.get(CollectionAttemptRow, event.attempt_id)
        if attempt is None:
            raise ProviderRepositoryError("audit event references an unknown attempt")
        source_required = event.event_type in _SOURCE_LINKED_AUDIT_EVENTS
        if source_required and event.source_version_id is None:
            raise ProviderContractConflict("source-linked audit event requires a source version")
        if not source_required and event.source_version_id is not None:
            raise ProviderContractConflict("source-free audit event cannot claim a source version")
        if event.source_version_id is None:
            return
        source_row = session.get(ProviderSourceVersionRow, event.source_version_id)
        if source_row is None:
            raise ProviderRepositoryError("audit event references an unknown source version")
        source = ProviderSourceVersion.model_validate_json(source_row.payload_json)
        if (
            attempt.provider != source.provider.value
            or attempt.dataset != source.dataset.value
            or attempt.canonical_request_id != source.canonical_request_id
        ):
            raise ProviderContractConflict("audit attempt and source trace do not match")

    @staticmethod
    def _validate_identity_sources(session: Session, identity: ProviderSecurityIdentity) -> None:
        first = session.get(ProviderSourceVersionRow, identity.first_source_version_id)
        latest = session.get(ProviderSourceVersionRow, identity.latest_source_version_id)
        if first is None or latest is None:
            raise ProviderContractConflict("provider identity requires existing source lineage")
        for row in (first, latest):
            source = ProviderSourceVersion.model_validate_json(row.payload_json)
            if source.provider != identity.provider:
                raise ProviderContractConflict(
                    "provider identity source lineage has a different provider"
                )

    @staticmethod
    def _source_belongs_to_identity(
        session: Session,
        identity: ProviderSecurityIdentityRow,
        source_version_id: str,
    ) -> bool:
        if source_version_id in {
            identity.first_source_version_id,
            identity.latest_source_version_id,
        }:
            return True
        history_id = session.scalar(
            select(ProviderIdentifierHistoryRow.identifier_history_id).where(
                ProviderIdentifierHistoryRow.provider_security_identity_id
                == identity.provider_security_identity_id,
                ProviderIdentifierHistoryRow.source_version_id == source_version_id,
            )
        )
        return history_id is not None

    @classmethod
    def _validate_identity_mapping(cls, session: Session, mapping: ProviderIdentityMapping) -> None:
        identity = session.get(ProviderSecurityIdentityRow, mapping.provider_security_identity_id)
        evidence = session.get(ProviderSourceVersionRow, mapping.evidence_source_version_id)
        if identity is None or evidence is None:
            raise ProviderContractConflict(
                "identity mapping requires existing identity and evidence"
            )
        evidence_contract = ProviderSourceVersion.model_validate_json(evidence.payload_json)
        if (
            identity.provider != evidence_contract.provider.value
            or not cls._source_belongs_to_identity(
                session, identity, mapping.evidence_source_version_id
            )
        ):
            raise ProviderContractConflict("mapping evidence is outside provider identity lineage")
        if mapping.mapping_status != MappingStatus.VERIFIED:
            return
        if identity.identity_state != ProviderIdentityState.ACTIVE.value:
            raise ProviderContractConflict("verified mapping requires an active provider identity")
        issuer = session.get(IssuerRow, mapping.issuer_id)
        security = session.get(SecurityRow, mapping.security_id)
        if issuer is None or security is None:
            raise ProviderContractConflict("verified mapping requires existing issuer and security")
        if security.issuer_id != issuer.issuer_id:
            raise ProviderContractConflict("verified mapping issuer and security do not match")
        existing_mappings = session.scalars(
            select(ProviderIdentityMappingRow).where(
                ProviderIdentityMappingRow.provider_security_identity_id
                == mapping.provider_security_identity_id,
                ProviderIdentityMappingRow.mapping_status == MappingStatus.VERIFIED.value,
            )
        )
        for row in existing_mappings:
            try:
                existing = ProviderIdentityMapping.model_validate_json(row.payload_json)
            except Exception:
                raise ProviderContractConflict(
                    "verified identity mapping history is invalid"
                ) from None
            if cls._mapping_intervals_overlap(existing, mapping):
                raise ProviderContractConflict("verified identity mapping intervals overlap")

    @staticmethod
    def _mapping_intervals_overlap(
        left: ProviderIdentityMapping, right: ProviderIdentityMapping
    ) -> bool:
        left_start = date.min if left.valid_from is None else left.valid_from
        left_end = date.max if left.valid_to is None else left.valid_to
        right_start = date.min if right.valid_from is None else right.valid_from
        right_end = date.max if right.valid_to is None else right.valid_to
        return left_start <= right_end and right_start <= left_end

    @classmethod
    def _validate_latest_eligibility(cls, session: Session, pointer: ProviderLatestPointer) -> None:
        identity = session.get(ProviderSecurityIdentityRow, pointer.provider_security_identity_id)
        source_row = session.get(ProviderSourceVersionRow, pointer.source_version_id)
        if identity is None or source_row is None:
            raise ProviderContractConflict("latest pointer requires existing identity and source")
        if identity.identity_state != ProviderIdentityState.ACTIVE.value:
            raise ProviderContractConflict("latest pointer requires an active provider identity")
        source = ProviderSourceVersion.model_validate_json(source_row.payload_json)
        if (
            source.dataset != pointer.dataset
            or source.provider.value != identity.provider
            or pointer.provider_contract_version != identity.provider_contract_version
            or pointer.accepted_observed_at != source.observed_at
            or pointer.accepted_observed_date != source.observed_date
            or not cls._source_belongs_to_identity(session, identity, pointer.source_version_id)
        ):
            raise ProviderContractConflict("latest pointer does not match source lineage")
        if pointer.dataset == ProviderDataset.CURRENT_PRICE and source.observed_at is None:
            raise ProviderContractConflict(
                "current price without provider timestamp is not latest eligible"
            )

    @staticmethod
    def _latest_pointer_values(pointer: ProviderLatestPointer, payload: str) -> dict[str, object]:
        return {
            "latest_pointer_id": pointer.latest_pointer_id,
            "dataset": pointer.dataset.value,
            "provider_security_identity_id": pointer.provider_security_identity_id,
            "normalized_record_id": pointer.normalized_record_id,
            "source_version_id": pointer.source_version_id,
            "accepted_observed_at": (
                None
                if pointer.accepted_observed_at is None
                else SQLiteProviderRepository._json_time(pointer.accepted_observed_at)
            ),
            "accepted_observed_date": pointer.accepted_observed_date,
            "state_hash": pointer.state_hash,
            "provider_contract_version": pointer.provider_contract_version,
            "payload_json": payload,
        }

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
