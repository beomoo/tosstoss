from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select, text

from toss_dashboard_api.contracts.base import canonical_json_bytes, sha256_prefixed
from toss_dashboard_api.contracts.enums import (
    CollectionAttemptStatus,
    FinalityStatus,
    FreshnessStatus,
    MappingStatus,
    Market,
    MissingReason,
    ProviderAuditEventType,
    ProviderDataset,
    ProviderIdentifierKind,
    ProviderIdentifierReason,
    ProviderIdentityState,
    ProviderSystem,
    RevisionStatus,
)
from toss_dashboard_api.contracts.provider_identity import (
    PROVIDER_IDENTITY_CONTRACT_VERSION,
    ProviderIdentifierHistory,
    ProviderIdentityMapping,
    ProviderLatestPointer,
    ProviderSecurityIdentity,
    provider_latest_pointer_id,
)
from toss_dashboard_api.contracts.provider_source import (
    PROVIDER_SOURCE_CONTRACT_VERSION,
    CollectionAttempt,
    ProviderAuditEvent,
    ProviderResponseMetadata,
    ProviderSourceVersion,
    build_canonical_request,
    build_provider_raw_manifest,
    provider_source_normalized_hash,
    provider_source_version_id,
)
from toss_dashboard_api.repositories.provider import (
    ProviderConditionalWriteConflict,
    ProviderContractConflict,
    SQLiteProviderRepository,
)
from toss_dashboard_api.storage.database import session_factory
from toss_dashboard_api.storage.models import (
    ProviderAuditEventRow,
    ProviderLatestPointerRow,
    ProviderRawManifestRow,
    ProviderSourceVersionRow,
    SourceRecordRow,
)
from toss_dashboard_api.storage.provider_raw import ProviderRawStore, ProviderRawStoreError

NOW = datetime(2026, 8, 25, 1, 2, 3, tzinfo=UTC)


def repository(database_context, raw_store: ProviderRawStore) -> SQLiteProviderRepository:
    return SQLiteProviderRepository(session_factory(database_context.engine), raw_store)


def source_contract(
    *,
    request,
    manifest,
    source_version_id: str | None = None,
    revision_status: RevisionStatus = RevisionStatus.ORIGINAL,
    supersedes_id: str | None = None,
) -> ProviderSourceVersion:
    payload: dict[str, object] = {
        "source_version_id": "tsrc_pending",
        "provider": ProviderSystem.TOSS_OPEN_API,
        "dataset": ProviderDataset.STOCK_DISCOVERY,
        "canonical_request_id": request.canonical_request_id,
        "raw_response_id": manifest.raw_response_id,
        "source_locator": "provider://toss-open-api/market/stock-discovery",
        "observed_at": None,
        "observed_date": None,
        "published_at": None,
        "fetched_at": NOW,
        "missing_reasons": {
            "observed_at": MissingReason.NOT_PROVIDED,
            "observed_date": MissingReason.NOT_PROVIDED,
            "published_at": MissingReason.NOT_PROVIDED,
        },
        "freshness_status": FreshnessStatus.UNKNOWN,
        "finality_status": FinalityStatus.UNKNOWN,
        "revision_status": revision_status,
        "supersedes_id": supersedes_id,
        "raw_content_hash": manifest.raw_content_hash,
        "parser_version": "toss-source-parser/0.1.0",
        "provider_contract_version": PROVIDER_SOURCE_CONTRACT_VERSION,
        "raw_storage_ref": manifest.raw_storage_ref,
    }
    payload["normalized_content_hash"] = provider_source_normalized_hash(payload)
    payload["source_version_id"] = source_version_id or provider_source_version_id(payload)
    return ProviderSourceVersion.model_validate(payload)


def persisted_graph(database_context, workspace_tmp_path: Path, raw_bytes: bytes = b"first"):
    raw_store = ProviderRawStore(workspace_tmp_path / "raw")
    repo = repository(database_context, raw_store)
    request = build_canonical_request("/api/v1/stocks/all", {"market": "KR"})
    stored = raw_store.persist(raw_bytes)
    manifest = build_provider_raw_manifest(
        request=request,
        http_status=200,
        raw_content_hash=stored.raw_content_hash,
        raw_storage_ref=stored.raw_storage_ref,
        fetched_at=NOW,
        response_metadata=ProviderResponseMetadata(
            request_id="safe-request-1",
            rate_limit=1,
            rate_remaining=0,
            rate_reset_seconds=1,
            content_type="application/json",
        ),
        parser_version="toss-source-parser/0.1.0",
    )
    repo.insert_or_verify_canonical_request(request)
    repo.insert_or_verify_raw_manifest(manifest)
    source = source_contract(request=request, manifest=manifest)
    return repo, request, manifest, source


def completed_attempt(request_id: str) -> CollectionAttempt:
    return CollectionAttempt(
        attempt_id="attempt_cp3b_001",
        provider=ProviderSystem.TOSS_OPEN_API,
        dataset=ProviderDataset.STOCK_DISCOVERY,
        canonical_request_id=request_id,
        started_at=NOW,
        finished_at=datetime(2026, 8, 25, 1, 2, 4, tzinfo=UTC),
        status=CollectionAttemptStatus.SUCCEEDED,
        records_received=1,
        records_rejected=0,
        safe_result_code="OK",
    )


def audit_event(source_version_id: str, *, event_id: str = "audit_cp3b_001") -> ProviderAuditEvent:
    return ProviderAuditEvent(
        audit_event_id=event_id,
        attempt_id="attempt_cp3b_001",
        source_version_id=source_version_id,
        event_type=ProviderAuditEventType.SOURCE_APPENDED,
        safe_status="SUCCEEDED",
        record_count=1,
        occurred_at=datetime(2026, 8, 25, 1, 2, 4, tzinfo=UTC),
    )


def provider_identity(source_version_id: str) -> ProviderSecurityIdentity:
    anchor = "toss-identity-v1|KR|FIRST_SEEN_RAW|A|evidence"
    digest = hashlib.sha256(anchor.encode()).hexdigest()
    return ProviderSecurityIdentity(
        provider_security_identity_id=f"tpsi_{digest}",
        provider=ProviderSystem.TOSS_OPEN_API,
        market=Market.KR,
        allocation_anchor_hash=f"sha256:{digest}",
        identity_state=ProviderIdentityState.ACTIVE,
        mapping_status=MappingStatus.UNRESOLVED,
        first_source_version_id=source_version_id,
        latest_source_version_id=source_version_id,
        provider_contract_version=PROVIDER_IDENTITY_CONTRACT_VERSION,
    )


def latest_pointer(identity_id: str, source_version_id: str, suffix: str) -> ProviderLatestPointer:
    return ProviderLatestPointer(
        latest_pointer_id=provider_latest_pointer_id(ProviderDataset.STOCK_DISCOVERY, identity_id),
        dataset=ProviderDataset.STOCK_DISCOVERY,
        provider_security_identity_id=identity_id,
        normalized_record_id=f"normalized_{suffix}",
        source_version_id=source_version_id,
        accepted_observed_at=None,
        accepted_observed_date=None,
        state_hash=sha256_prefixed(suffix.encode()),
        provider_contract_version=PROVIDER_IDENTITY_CONTRACT_VERSION,
    )


def test_canonical_request_insert_or_verify_is_idempotent(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, request, _, _ = persisted_graph(database_context, workspace_tmp_path)
    assert repo.insert_or_verify_canonical_request(request).inserted is False


def test_same_request_id_with_conflicting_payload_fails_closed(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, request, _, _ = persisted_graph(database_context, workspace_tmp_path)
    conflicting = request.model_copy(update={"canonical_query_json": '{"market":"US"}'})
    with pytest.raises(ProviderContractConflict, match="conflicting content"):
        repo.insert_or_verify_canonical_request(conflicting)


def test_raw_manifest_insert_or_verify_is_idempotent(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, _, manifest, _ = persisted_graph(database_context, workspace_tmp_path)
    assert repo.insert_or_verify_raw_manifest(manifest).inserted is False


def test_raw_manifest_cannot_publish_before_durable_raw_object(
    database_context, workspace_tmp_path: Path
) -> None:
    raw_store = ProviderRawStore(workspace_tmp_path / "raw")
    repo = repository(database_context, raw_store)
    request = build_canonical_request("/api/v1/stocks/all", {"market": "KR"})
    repo.insert_or_verify_canonical_request(request)
    digest = "0" * 64
    manifest = build_provider_raw_manifest(
        request=request,
        http_status=200,
        raw_content_hash=f"sha256:{digest}",
        raw_storage_ref=f"provider-raw:sha256/00/{digest}",
        fetched_at=NOW,
        response_metadata=ProviderResponseMetadata(content_type="application/json"),
        parser_version="toss-source-parser/0.1.0",
    )
    with pytest.raises(ProviderRawStoreError, match="unsafe|durably published"):
        repo.insert_or_verify_raw_manifest(manifest)
    with database_context.engine.connect() as connection:
        assert (
            connection.execute(
                select(func.count()).select_from(ProviderRawManifestRow)
            ).scalar_one()
            == 0
        )


def test_same_raw_id_with_conflicting_payload_fails_closed(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, _, manifest, _ = persisted_graph(database_context, workspace_tmp_path)
    conflicting = manifest.model_copy(update={"http_status": 201})
    with pytest.raises(ProviderContractConflict, match="conflicting content"):
        repo.insert_or_verify_raw_manifest(conflicting)


def test_same_request_and_raw_hash_creates_no_duplicate_source(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, _, _, source = persisted_graph(database_context, workspace_tmp_path)
    assert repo.append_source_version(source).inserted is True
    assert repo.append_source_version(source).inserted is False
    with database_context.engine.connect() as connection:
        count = connection.execute(select(func.count()).select_from(ProviderSourceVersionRow))
        assert count.scalar_one() == 1


def test_duplicate_semantics_with_another_source_id_returns_existing_version(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, _, _, source = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(source)
    bypassed = source.model_copy(update={"source_version_id": "tsrc_clock_suffix_forbidden"})
    result = repo.append_source_version(bypassed)
    assert result.inserted is False
    assert result.record.source_version_id == source.source_version_id


def test_same_request_different_raw_hash_appends_revision_and_preserves_old(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, request, _, original = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(original)
    stored = ProviderRawStore(workspace_tmp_path / "raw").persist(b"second")
    revised_manifest = build_provider_raw_manifest(
        request=request,
        http_status=200,
        raw_content_hash=stored.raw_content_hash,
        raw_storage_ref=stored.raw_storage_ref,
        fetched_at=datetime(2026, 8, 25, 1, 3, tzinfo=UTC),
        response_metadata=ProviderResponseMetadata(content_type="application/json"),
        parser_version="toss-source-parser/0.1.0",
    )
    repo.insert_or_verify_raw_manifest(revised_manifest)
    revised = source_contract(
        request=request,
        manifest=revised_manifest,
        revision_status=RevisionStatus.AMENDED,
        supersedes_id=original.source_version_id,
    )
    assert repo.append_source_version(revised).inserted is True
    chain = repo.source_revision_chain(revised.source_version_id)
    assert [item.source_version_id for item in chain] == [
        revised.source_version_id,
        original.source_version_id,
    ]


def test_collection_attempt_and_audit_are_append_only(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, request, _, source = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(source)
    attempt = completed_attempt(request.canonical_request_id)
    assert repo.record_collection_attempt(attempt).inserted is True
    assert repo.record_collection_attempt(attempt).inserted is False
    event = audit_event(source.source_version_id)
    assert repo.append_audit_event(event).inserted is True
    assert repo.append_audit_event(event).inserted is False


def test_source_and_audit_publish_atomically(database_context, workspace_tmp_path: Path) -> None:
    repo, request, _, source = persisted_graph(database_context, workspace_tmp_path)
    repo.record_collection_attempt(completed_attempt(request.canonical_request_id))
    result = repo.record_source_version_with_audit(source, audit_event(source.source_version_id))
    assert result.inserted is True
    with database_context.engine.connect() as connection:
        assert (
            connection.execute(
                select(func.count()).select_from(ProviderSourceVersionRow)
            ).scalar_one()
            == 1
        )
        assert (
            connection.execute(select(func.count()).select_from(ProviderAuditEventRow)).scalar_one()
            == 1
        )


def test_source_and_audit_exception_rolls_back_partial_database_publish(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, request, _, source = persisted_graph(database_context, workspace_tmp_path)
    repo.record_collection_attempt(completed_attempt(request.canonical_request_id))
    existing_event = audit_event(source.source_version_id)
    repo.append_audit_event(existing_event.model_copy(update={"source_version_id": None}))
    conflicting = existing_event.model_copy(update={"safe_status": "FAILED"})
    with pytest.raises(ProviderContractConflict):
        repo.record_source_version_with_audit(source, conflicting)
    with database_context.engine.connect() as connection:
        assert (
            connection.execute(
                select(func.count()).select_from(ProviderSourceVersionRow)
            ).scalar_one()
            == 0
        )


def test_identity_insert_is_idempotent_and_anchor_immutable(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, _, _, source = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(source)
    identity = provider_identity(source.source_version_id)
    assert repo.insert_or_verify_identity(identity).inserted is True
    assert repo.insert_or_verify_identity(identity).inserted is False
    conflicting = identity.model_copy(update={"identity_state": ProviderIdentityState.QUARANTINED})
    with pytest.raises(ProviderContractConflict, match="conflicting content"):
        repo.insert_or_verify_identity(conflicting)


def test_identifier_history_enrichment_appends_without_overwrite(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, _, _, source = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(source)
    identity = provider_identity(source.source_version_id)
    repo.insert_or_verify_identity(identity)
    symbol = ProviderIdentifierHistory(
        identifier_history_id="pih_symbol_a",
        provider_security_identity_id=identity.provider_security_identity_id,
        identifier_kind=ProviderIdentifierKind.SYMBOL,
        identifier_value="A",
        valid_from=None,
        valid_to=None,
        source_version_id=source.source_version_id,
        revision_reason=ProviderIdentifierReason.INITIAL,
        provider_contract_version=PROVIDER_IDENTITY_CONTRACT_VERSION,
    )
    isin = symbol.model_copy(
        update={
            "identifier_history_id": "pih_isin_a",
            "identifier_kind": ProviderIdentifierKind.ISIN,
            "identifier_value": "KR0000000001",
            "revision_reason": ProviderIdentifierReason.ENRICHMENT,
        }
    )
    assert repo.append_identifier_history(symbol).inserted is True
    assert repo.append_identifier_history(isin).inserted is True
    assert repo.append_identifier_history(symbol).inserted is False


def test_unresolved_mapping_stores_no_fake_canonical_identifier(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, _, _, source = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(source)
    identity = provider_identity(source.source_version_id)
    repo.insert_or_verify_identity(identity)
    mapping = ProviderIdentityMapping(
        mapping_id="pmap_unresolved_a",
        provider_security_identity_id=identity.provider_security_identity_id,
        issuer_id=None,
        security_id=None,
        mapping_status=MappingStatus.UNRESOLVED,
        evidence_source_version_id=source.source_version_id,
        approved_at=None,
        valid_from=None,
        valid_to=None,
        provider_contract_version=PROVIDER_IDENTITY_CONTRACT_VERSION,
    )
    assert repo.record_identity_mapping(mapping).inserted is True
    assert repo.record_identity_mapping(mapping).inserted is False


def test_verified_mapping_without_canonical_security_is_rejected() -> None:
    with pytest.raises(ValidationError, match="verified mapping"):
        ProviderIdentityMapping(
            mapping_id="pmap_invalid_verified",
            provider_security_identity_id="tpsi_" + "0" * 64,
            issuer_id=None,
            security_id=None,
            mapping_status=MappingStatus.VERIFIED,
            evidence_source_version_id="tsrc_evidence",
            approved_at=NOW,
            valid_from=None,
            valid_to=None,
            provider_contract_version=PROVIDER_IDENTITY_CONTRACT_VERSION,
        )


def test_latest_pointer_compare_and_set_is_atomic_and_idempotent(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, _, _, source = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(source)
    identity = provider_identity(source.source_version_id)
    repo.insert_or_verify_identity(identity)
    first = latest_pointer(identity.provider_security_identity_id, source.source_version_id, "one")
    assert repo.conditional_write_latest(first, expected_state_hash=None).inserted is True
    assert (
        repo.conditional_write_latest(first, expected_state_hash=first.state_hash).inserted is False
    )
    second = latest_pointer(identity.provider_security_identity_id, source.source_version_id, "two")
    assert (
        repo.conditional_write_latest(second, expected_state_hash=first.state_hash).inserted is True
    )
    assert (
        repo.read_latest_pointer(first.dataset.value, identity.provider_security_identity_id)
        == second
    )


def test_latest_pointer_failed_precondition_preserves_last_known_good(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, _, _, source = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(source)
    identity = provider_identity(source.source_version_id)
    repo.insert_or_verify_identity(identity)
    first = latest_pointer(identity.provider_security_identity_id, source.source_version_id, "one")
    repo.conditional_write_latest(first, expected_state_hash=None)
    second = latest_pointer(identity.provider_security_identity_id, source.source_version_id, "two")
    with pytest.raises(ProviderConditionalWriteConflict, match="precondition"):
        repo.conditional_write_latest(second, expected_state_hash=sha256_prefixed(b"stale"))
    assert (
        repo.read_latest_pointer(first.dataset.value, identity.provider_security_identity_id)
        == first
    )


def test_latest_failure_does_not_rollback_source_history(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, _, _, source = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(source)
    identity = provider_identity(source.source_version_id)
    repo.insert_or_verify_identity(identity)
    pointer = latest_pointer(
        identity.provider_security_identity_id, source.source_version_id, "one"
    )
    with pytest.raises(ProviderConditionalWriteConflict):
        repo.conditional_write_latest(pointer, expected_state_hash=sha256_prefixed(b"wrong"))
    assert repo.source_revision_chain(source.source_version_id) == [source]


def test_validation_rejection_can_preserve_raw_and_source_without_latest(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, _, _, source = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(source)
    with database_context.engine.connect() as connection:
        assert (
            connection.execute(
                select(func.count()).select_from(ProviderRawManifestRow)
            ).scalar_one()
            == 1
        )
        assert (
            connection.execute(
                select(func.count()).select_from(ProviderSourceVersionRow)
            ).scalar_one()
            == 1
        )
        assert (
            connection.execute(
                select(func.count()).select_from(ProviderLatestPointerRow)
            ).scalar_one()
            == 0
        )


def test_provider_tables_persist_no_authentication_or_account_fields(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, _, _, source = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(source)
    forbidden_fragments = [
        "author" + "ization",
        "client" + "_secret",
        "access" + "_token",
        "x-" + "tossinvest-account",
    ]
    with database_context.engine.connect() as connection:
        values = connection.execute(
            text(
                "SELECT payload_json FROM canonical_requests "
                "UNION ALL SELECT payload_json FROM provider_raw_manifests "
                "UNION ALL SELECT payload_json FROM provider_source_versions"
            )
        ).scalars()
        persisted = "\n".join(values).lower()
    assert all(fragment not in persisted for fragment in forbidden_fragments)


def test_provider_source_does_not_use_phase_one_clock_suffix_natural_key(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, _, _, source = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(source)
    with database_context.engine.connect() as connection:
        assert (
            connection.execute(select(func.count()).select_from(SourceRecordRow)).scalar_one() >= 1
        )
        external_ids = connection.execute(select(SourceRecordRow.external_id)).scalars().all()
    assert all("2026-08-25T01:02:03" not in value for value in external_ids)


def test_provider_source_version_id_is_hash_derived_not_clock_suffixed(
    database_context, workspace_tmp_path: Path
) -> None:
    _, _, _, source = persisted_graph(database_context, workspace_tmp_path)
    assert source.source_version_id.startswith("tsrc_")
    assert len(source.source_version_id) == len("tsrc_") + 64
    assert source.source_version_id == provider_source_version_id(source.model_dump(mode="json"))


def test_repository_exception_does_not_embed_conflicting_payload(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, request, _, _ = persisted_graph(database_context, workspace_tmp_path)
    marker = "private-provider-body-marker"
    conflicting = request.model_copy(update={"canonical_query_json": marker})
    with pytest.raises(ProviderContractConflict) as captured:
        repo.insert_or_verify_canonical_request(conflicting)
    assert marker not in str(captured.value)
    assert marker not in repr(captured.value)


def test_identity_anchor_hash_and_id_are_deterministic(
    database_context, workspace_tmp_path: Path
) -> None:
    _, _, _, source = persisted_graph(database_context, workspace_tmp_path)
    first = provider_identity(source.source_version_id)
    second = provider_identity(source.source_version_id)
    assert first == second
    assert first.provider_security_identity_id.removeprefix("tpsi_") == (
        first.allocation_anchor_hash.removeprefix("sha256:")
    )


def test_provider_hash_canonicalization_has_no_binary_float() -> None:
    payload = {"decimal": "123.4500", "count": 1}
    rendered = canonical_json_bytes(payload)
    assert rendered == b'{"count":1,"decimal":"123.4500"}'
