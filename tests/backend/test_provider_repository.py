from __future__ import annotations

import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from pathlib import Path
from threading import Barrier

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import IntegrityError, OperationalError

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
from toss_dashboard_api.repositories.protocols import ProviderRepository
from toss_dashboard_api.repositories.provider import (
    ProviderConditionalWriteConflict,
    ProviderContractConflict,
    SQLiteProviderRepository,
)
from toss_dashboard_api.storage.database import session_factory
from toss_dashboard_api.storage.models import (
    CollectionAttemptRow,
    ProviderAuditEventRow,
    ProviderIdentityMappingRow,
    ProviderLatestPointerRow,
    ProviderRawManifestRow,
    ProviderSourceVersionRow,
    SourceRecordRow,
)
from toss_dashboard_api.storage.provider_raw import ProviderRawStore, ProviderRawStoreError

NOW = datetime(2026, 8, 25, 1, 2, 3, tzinfo=UTC)


def repository(database_context, raw_store: ProviderRawStore) -> SQLiteProviderRepository:
    return SQLiteProviderRepository(session_factory(database_context.engine), raw_store)


def require_provider_repository_protocol(value: ProviderRepository) -> ProviderRepository:
    return value


def source_contract(
    *,
    request,
    manifest,
    source_version_id: str | None = None,
    revision_status: RevisionStatus = RevisionStatus.ORIGINAL,
    supersedes_id: str | None = None,
    dataset: ProviderDataset = ProviderDataset.STOCK_DISCOVERY,
    source_locator: str = "provider://toss-open-api/market/stock-discovery",
    fetched_at: datetime | None = None,
    parser_version: str = "toss-source-parser/0.1.0",
    observed_at: datetime | None = None,
    observed_date: date | None = None,
    freshness_status: FreshnessStatus = FreshnessStatus.UNKNOWN,
) -> ProviderSourceVersion:
    missing_reasons = {"published_at": MissingReason.NOT_PROVIDED}
    if observed_at is None:
        missing_reasons["observed_at"] = MissingReason.NOT_PROVIDED
    if observed_date is None:
        missing_reasons["observed_date"] = MissingReason.NOT_PROVIDED
    payload: dict[str, object] = {
        "source_version_id": "tsrc_pending",
        "provider": ProviderSystem.TOSS_OPEN_API,
        "dataset": dataset,
        "canonical_request_id": request.canonical_request_id,
        "raw_response_id": manifest.raw_response_id,
        "source_locator": source_locator,
        "observed_at": observed_at,
        "observed_date": observed_date,
        "published_at": None,
        "fetched_at": manifest.fetched_at if fetched_at is None else fetched_at,
        "missing_reasons": missing_reasons,
        "freshness_status": freshness_status,
        "finality_status": FinalityStatus.UNKNOWN,
        "revision_status": revision_status,
        "supersedes_id": supersedes_id,
        "raw_content_hash": manifest.raw_content_hash,
        "parser_version": parser_version,
        "provider_contract_version": PROVIDER_SOURCE_CONTRACT_VERSION,
        "raw_storage_ref": manifest.raw_storage_ref,
    }
    payload["normalized_content_hash"] = provider_source_normalized_hash(payload)
    payload["source_version_id"] = source_version_id or provider_source_version_id(payload)
    return ProviderSourceVersion.model_validate(payload)


def persisted_graph(
    database_context,
    workspace_tmp_path: Path,
    raw_bytes: bytes = b"first",
    *,
    market: str = "KR",
):
    raw_store = ProviderRawStore(workspace_tmp_path / "raw")
    repo = repository(database_context, raw_store)
    request = build_canonical_request("/api/v1/stocks/all", {"market": market})
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


def changed_source_candidate(
    repo: SQLiteProviderRepository,
    request,
    raw_store: ProviderRawStore,
    *,
    raw_bytes: bytes,
    revision_status: RevisionStatus = RevisionStatus.ORIGINAL,
    supersedes_id: str | None = None,
    fetched_at: datetime | None = None,
) -> ProviderSourceVersion:
    stored = raw_store.persist(raw_bytes)
    manifest = build_provider_raw_manifest(
        request=request,
        http_status=200,
        raw_content_hash=stored.raw_content_hash,
        raw_storage_ref=stored.raw_storage_ref,
        fetched_at=(datetime(2026, 8, 25, 1, 3, tzinfo=UTC) if fetched_at is None else fetched_at),
        response_metadata=ProviderResponseMetadata(content_type="application/json"),
        parser_version="toss-source-parser/0.1.0",
    )
    repo.insert_or_verify_raw_manifest(manifest)
    return source_contract(
        request=request,
        manifest=manifest,
        revision_status=revision_status,
        supersedes_id=supersedes_id,
    )


def source_version_row(source: ProviderSourceVersion) -> ProviderSourceVersionRow:
    return ProviderSourceVersionRow(
        source_version_id=source.source_version_id,
        canonical_request_id=source.canonical_request_id,
        raw_response_id=source.raw_response_id,
        dataset=source.dataset.value,
        http_status=200,
        raw_content_hash=source.raw_content_hash,
        provider_contract_version=source.provider_contract_version,
        revision_status=source.revision_status.value,
        supersedes_id=source.supersedes_id,
        normalized_content_hash=source.normalized_content_hash,
        payload_json=canonical_json_bytes(source.model_dump(mode="json")).decode("utf-8"),
    )


def persisted_dataset_graph(
    database_context,
    workspace_tmp_path: Path,
    *,
    path: str,
    query: dict[str, object],
    dataset: ProviderDataset,
    source_locator: str,
    raw_bytes: bytes,
    observed_at: datetime | None = None,
):
    raw_store = ProviderRawStore(workspace_tmp_path / "raw")
    repo = repository(database_context, raw_store)
    request = build_canonical_request(path, query)  # type: ignore[arg-type]
    stored = raw_store.persist(raw_bytes)
    manifest = build_provider_raw_manifest(
        request=request,
        http_status=200,
        raw_content_hash=stored.raw_content_hash,
        raw_storage_ref=stored.raw_storage_ref,
        fetched_at=NOW,
        response_metadata=ProviderResponseMetadata(content_type="application/json"),
        parser_version="toss-source-parser/0.1.0",
    )
    repo.insert_or_verify_canonical_request(request)
    repo.insert_or_verify_raw_manifest(manifest)
    source = source_contract(
        request=request,
        manifest=manifest,
        dataset=dataset,
        source_locator=source_locator,
        observed_at=observed_at,
    )
    return repo, request, manifest, source


def completed_attempt(
    request_id: str,
    *,
    attempt_id: str = "attempt_cp3b_001",
    dataset: ProviderDataset = ProviderDataset.STOCK_DISCOVERY,
) -> CollectionAttempt:
    return CollectionAttempt(
        attempt_id=attempt_id,
        provider=ProviderSystem.TOSS_OPEN_API,
        dataset=dataset,
        canonical_request_id=request_id,
        started_at=NOW,
        finished_at=datetime(2026, 8, 25, 1, 2, 4, tzinfo=UTC),
        status=CollectionAttemptStatus.SUCCEEDED,
        records_received=1,
        records_rejected=0,
        safe_result_code="OK",
    )


def audit_event(
    source_version_id: str | None,
    *,
    event_id: str = "audit_cp3b_001",
    attempt_id: str = "attempt_cp3b_001",
    event_type: ProviderAuditEventType = ProviderAuditEventType.SOURCE_APPENDED,
) -> ProviderAuditEvent:
    return ProviderAuditEvent(
        audit_event_id=event_id,
        attempt_id=attempt_id,
        source_version_id=source_version_id,
        event_type=event_type,
        safe_status="SUCCEEDED",
        record_count=1,
        occurred_at=datetime(2026, 8, 25, 1, 2, 4, tzinfo=UTC),
    )


def provider_identity(
    source_version_id: str,
    *,
    identity_state: ProviderIdentityState = ProviderIdentityState.ACTIVE,
    anchor_token: str = "A",
) -> ProviderSecurityIdentity:
    anchor = f"toss-identity-v1|KR|FIRST_SEEN_RAW|{anchor_token}|evidence"
    digest = hashlib.sha256(anchor.encode()).hexdigest()
    return ProviderSecurityIdentity(
        provider_security_identity_id=f"tpsi_{digest}",
        provider=ProviderSystem.TOSS_OPEN_API,
        market=Market.KR,
        allocation_anchor_hash=f"sha256:{digest}",
        identity_state=identity_state,
        mapping_status=MappingStatus.UNRESOLVED,
        first_source_version_id=source_version_id,
        latest_source_version_id=source_version_id,
        provider_contract_version=PROVIDER_IDENTITY_CONTRACT_VERSION,
    )


def verified_mapping(
    identity_id: str,
    source_version_id: str,
    *,
    mapping_id: str = "pmap_verified_a",
    issuer_id: str = "issuer_kr_synthetic",
    security_id: str = "security_kr_synthetic_common",
    valid_from: date | None = None,
    valid_to: date | None = None,
) -> ProviderIdentityMapping:
    return ProviderIdentityMapping(
        mapping_id=mapping_id,
        provider_security_identity_id=identity_id,
        issuer_id=issuer_id,
        security_id=security_id,
        mapping_status=MappingStatus.VERIFIED,
        evidence_source_version_id=source_version_id,
        approved_at=NOW,
        valid_from=valid_from,
        valid_to=valid_to,
        provider_contract_version=PROVIDER_IDENTITY_CONTRACT_VERSION,
    )


def latest_pointer(
    identity_id: str,
    source_version_id: str,
    suffix: str,
    *,
    dataset: ProviderDataset = ProviderDataset.STOCK_DISCOVERY,
    observed_at: datetime | None = None,
) -> ProviderLatestPointer:
    normalized_suffix = suffix.replace("-", "_")
    return ProviderLatestPointer(
        latest_pointer_id=provider_latest_pointer_id(dataset, identity_id),
        dataset=dataset,
        provider_security_identity_id=identity_id,
        normalized_record_id=f"normalized_{normalized_suffix}",
        source_version_id=source_version_id,
        accepted_observed_at=observed_at,
        accepted_observed_date=None,
        state_hash=sha256_prefixed(suffix.encode()),
        provider_contract_version=PROVIDER_IDENTITY_CONTRACT_VERSION,
    )


def test_canonical_request_insert_or_verify_is_idempotent(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, request, _, _ = persisted_graph(database_context, workspace_tmp_path)
    assert repo.insert_or_verify_canonical_request(request).inserted is False


def test_provider_repository_protocol_includes_atomic_source_and_audit_method(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, _, _, _ = persisted_graph(database_context, workspace_tmp_path)
    protocol_value = require_provider_repository_protocol(repo)
    assert callable(protocol_value.record_source_version_with_audit)


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


def test_same_raw_bytes_later_fetch_returns_first_seen_immutable_manifest(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, request, manifest, _ = persisted_graph(database_context, workspace_tmp_path)
    later = build_provider_raw_manifest(
        request=request,
        http_status=manifest.http_status,
        raw_content_hash=manifest.raw_content_hash,
        raw_storage_ref=manifest.raw_storage_ref,
        fetched_at=datetime(2026, 8, 25, 2, 2, 3, tzinfo=UTC),
        response_metadata=manifest.response_metadata,
        parser_version=manifest.parser_version,
    )
    result = repo.insert_or_verify_raw_manifest(later)
    assert result.inserted is False
    assert result.record == manifest


def test_same_raw_bytes_changed_safe_telemetry_returns_first_seen_manifest(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, request, manifest, _ = persisted_graph(database_context, workspace_tmp_path)
    later = build_provider_raw_manifest(
        request=request,
        http_status=manifest.http_status,
        raw_content_hash=manifest.raw_content_hash,
        raw_storage_ref=manifest.raw_storage_ref,
        fetched_at=datetime(2026, 8, 25, 2, 2, 3, tzinfo=UTC),
        response_metadata=ProviderResponseMetadata(
            request_id="safe-request-2",
            rate_limit=10,
            rate_remaining=9,
            rate_reset_seconds=5,
            content_type="application/json",
        ),
        parser_version=manifest.parser_version,
    )
    result = repo.insert_or_verify_raw_manifest(later)
    assert result.inserted is False
    assert result.record == manifest


def test_same_raw_bytes_changed_content_type_fails_closed(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, request, manifest, _ = persisted_graph(database_context, workspace_tmp_path)
    conflicting = build_provider_raw_manifest(
        request=request,
        http_status=manifest.http_status,
        raw_content_hash=manifest.raw_content_hash,
        raw_storage_ref=manifest.raw_storage_ref,
        fetched_at=manifest.fetched_at,
        response_metadata=ProviderResponseMetadata(content_type=None),
        parser_version=manifest.parser_version,
    )
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


def test_same_source_later_fetch_returns_first_seen_source_version(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, request, manifest, source = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(source)
    later_manifest = build_provider_raw_manifest(
        request=request,
        http_status=manifest.http_status,
        raw_content_hash=manifest.raw_content_hash,
        raw_storage_ref=manifest.raw_storage_ref,
        fetched_at=datetime(2026, 8, 25, 3, 2, 3, tzinfo=UTC),
        response_metadata=ProviderResponseMetadata(
            request_id="safe-request-later", content_type="application/json"
        ),
        parser_version=manifest.parser_version,
    )
    assert repo.insert_or_verify_raw_manifest(later_manifest).record == manifest
    later_source = source_contract(request=request, manifest=later_manifest)
    result = repo.append_source_version(later_source)
    assert result.inserted is False
    assert result.record == source


def test_duplicate_source_with_different_normalized_hash_fails_closed(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, _, _, source = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(source)
    conflicting = source.model_copy(
        update={"normalized_content_hash": sha256_prefixed(b"different-normalized")}
    )
    with pytest.raises(ProviderContractConflict, match="semantic content"):
        repo.append_source_version(conflicting)


def test_duplicate_source_with_different_parser_version_fails_closed(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, request, manifest, source = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(source)
    conflicting = source_contract(
        request=request,
        manifest=manifest,
        parser_version="toss-source-parser/0.2.0",
    )
    with pytest.raises(ProviderContractConflict, match="semantic content"):
        repo.append_source_version(conflicting)


def test_duplicate_source_with_different_dataset_fails_closed(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, request, manifest, source = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(source)
    conflicting = source_contract(
        request=request,
        manifest=manifest,
        dataset=ProviderDataset.STOCK_DETAIL,
        source_locator="provider://toss-open-api/market/stock-detail",
    )
    with pytest.raises(ProviderContractConflict, match="semantic content"):
        repo.append_source_version(conflicting)


def test_duplicate_source_with_different_revision_link_fails_closed(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, request, manifest, source = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(source)
    conflicting = source_contract(
        request=request,
        manifest=manifest,
        revision_status=RevisionStatus.AMENDED,
        supersedes_id=source.source_version_id,
    )
    with pytest.raises(ProviderContractConflict, match="semantic content"):
        repo.append_source_version(conflicting)


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


def test_second_original_with_different_raw_bytes_is_rejected_and_preserves_root(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, request, _, original = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(original)
    duplicate_root = changed_source_candidate(
        repo,
        request,
        ProviderRawStore(workspace_tmp_path / "raw"),
        raw_bytes=b"second-original",
    )

    with pytest.raises(ProviderContractConflict, match="unique current leaf"):
        repo.append_source_version(duplicate_root)

    with database_context.engine.connect() as connection:
        rows = connection.execute(select(ProviderSourceVersionRow.payload_json)).scalars().all()
    assert rows == [canonical_json_bytes(original.model_dump(mode="json")).decode("utf-8")]


def test_revision_cannot_supersede_a_non_leaf_and_preserves_prior_rows(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, request, _, original = persisted_graph(database_context, workspace_tmp_path)
    raw_store = ProviderRawStore(workspace_tmp_path / "raw")
    repo.append_source_version(original)
    amended = changed_source_candidate(
        repo,
        request,
        raw_store,
        raw_bytes=b"valid-amended",
        revision_status=RevisionStatus.AMENDED,
        supersedes_id=original.source_version_id,
    )
    repo.append_source_version(amended)
    invalid = changed_source_candidate(
        repo,
        request,
        raw_store,
        raw_bytes=b"non-leaf-amended",
        revision_status=RevisionStatus.AMENDED,
        supersedes_id=original.source_version_id,
        fetched_at=datetime(2026, 8, 25, 1, 4, tzinfo=UTC),
    )
    before = repo.source_revision_chain(amended.source_version_id)

    with pytest.raises(ProviderContractConflict, match="unique current leaf"):
        repo.append_source_version(invalid)

    assert repo.source_revision_chain(amended.source_version_id) == before
    with database_context.engine.connect() as connection:
        assert (
            connection.execute(
                select(func.count()).select_from(ProviderSourceVersionRow)
            ).scalar_one()
            == 2
        )


def test_two_independent_source_revision_writers_have_one_winner_and_typed_loser(
    database_context, workspace_tmp_path: Path
) -> None:
    raw_store = ProviderRawStore(workspace_tmp_path / "raw")
    repo, request, _, original = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(original)
    candidates = [
        changed_source_candidate(
            repo,
            request,
            raw_store,
            raw_bytes=f"concurrent-revision-{suffix}".encode(),
            revision_status=RevisionStatus.AMENDED,
            supersedes_id=original.source_version_id,
            fetched_at=datetime(2026, 8, 25, 1, minute, tzinfo=UTC),
        )
        for suffix, minute in (("a", 4), ("b", 5))
    ]
    barrier = Barrier(2)

    def append(candidate: ProviderSourceVersion) -> str:
        independent = repository(database_context, raw_store)
        barrier.wait()
        try:
            independent.append_source_version(candidate)
        except ProviderContractConflict:
            return "TYPED_CONFLICT"
        except (IntegrityError, OperationalError):
            return "RAW_DATABASE_ERROR"
        return "SUCCESS"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(append, candidates))

    assert sorted(outcomes) == ["SUCCESS", "TYPED_CONFLICT"]
    assert "RAW_DATABASE_ERROR" not in outcomes
    with database_context.engine.connect() as connection:
        persisted = (
            connection.execute(
                select(ProviderSourceVersionRow.payload_json).order_by(
                    ProviderSourceVersionRow.source_version_id
                )
            )
            .scalars()
            .all()
        )
    assert len(persisted) == 2
    winner = next(
        candidate
        for candidate in candidates
        if canonical_json_bytes(candidate.model_dump(mode="json")).decode("utf-8") in persisted
    )
    assert repo.source_revision_chain(winner.source_version_id) == [winner, original]


def test_database_unique_index_prevents_a_second_original_root(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, request, _, original = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(original)
    duplicate_root = changed_source_candidate(
        repo,
        request,
        ProviderRawStore(workspace_tmp_path / "raw"),
        raw_bytes=b"database-second-original",
    )
    sessions = session_factory(database_context.engine)

    with pytest.raises(IntegrityError):
        with sessions.begin() as session:
            session.add(source_version_row(duplicate_root))
            session.flush()

    assert repo.source_revision_chain(original.source_version_id) == [original]


def test_database_unique_index_prevents_a_revision_fork(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, request, _, original = persisted_graph(database_context, workspace_tmp_path)
    raw_store = ProviderRawStore(workspace_tmp_path / "raw")
    repo.append_source_version(original)
    first_child = changed_source_candidate(
        repo,
        request,
        raw_store,
        raw_bytes=b"database-first-child",
        revision_status=RevisionStatus.AMENDED,
        supersedes_id=original.source_version_id,
    )
    repo.append_source_version(first_child)
    second_child = changed_source_candidate(
        repo,
        request,
        raw_store,
        raw_bytes=b"database-second-child",
        revision_status=RevisionStatus.AMENDED,
        supersedes_id=original.source_version_id,
        fetched_at=datetime(2026, 8, 25, 1, 4, tzinfo=UTC),
    )
    sessions = session_factory(database_context.engine)

    with pytest.raises(IntegrityError):
        with sessions.begin() as session:
            session.add(source_version_row(second_child))
            session.flush()

    assert repo.source_revision_chain(first_child.source_version_id) == [first_child, original]


def test_source_revision_chain_is_queryable_in_exact_leaf_to_root_order(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, request, _, original = persisted_graph(database_context, workspace_tmp_path)
    raw_store = ProviderRawStore(workspace_tmp_path / "raw")
    repo.append_source_version(original)
    amended = changed_source_candidate(
        repo,
        request,
        raw_store,
        raw_bytes=b"ordered-amended",
        revision_status=RevisionStatus.AMENDED,
        supersedes_id=original.source_version_id,
    )
    repo.append_source_version(amended)
    restated = changed_source_candidate(
        repo,
        request,
        raw_store,
        raw_bytes=b"ordered-restated",
        revision_status=RevisionStatus.AMENDED,
        supersedes_id=amended.source_version_id,
        fetched_at=datetime(2026, 8, 25, 1, 4, tzinfo=UTC),
    )
    repo.append_source_version(restated)

    assert repo.source_revision_chain(restated.source_version_id) == [
        restated,
        amended,
        original,
    ]


def test_prices_path_rejects_daily_flow_source_dataset(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, request, manifest, _ = persisted_dataset_graph(
        database_context,
        workspace_tmp_path,
        path="/api/v1/prices",
        query={"symbols": ["A"]},
        dataset=ProviderDataset.CURRENT_PRICE,
        source_locator="provider://toss-open-api/market/current-price",
        raw_bytes=b"price-daily-flow-mismatch",
    )
    invalid = source_contract(
        request=request,
        manifest=manifest,
        dataset=ProviderDataset.DAILY_FLOW,
        source_locator="provider://toss-open-api/market/daily-flow",
        observed_date=date(2026, 8, 25),
    )
    with pytest.raises(ProviderContractConflict, match="path and source dataset"):
        repo.append_source_version(invalid)


def test_stocks_all_path_rejects_current_price_source_dataset(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, request, manifest, _ = persisted_graph(database_context, workspace_tmp_path)
    invalid = source_contract(
        request=request,
        manifest=manifest,
        dataset=ProviderDataset.CURRENT_PRICE,
        source_locator="provider://toss-open-api/market/current-price",
        observed_at=NOW,
    )
    with pytest.raises(ProviderContractConflict, match="path and source dataset"):
        repo.append_source_version(invalid)


def test_source_rejects_fetched_at_that_does_not_match_raw_observation(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, request, manifest, _ = persisted_graph(database_context, workspace_tmp_path)
    invalid = source_contract(
        request=request,
        manifest=manifest,
        fetched_at=datetime(2026, 8, 25, 2, 2, 3, tzinfo=UTC),
    )
    with pytest.raises(ProviderContractConflict, match="trace does not match"):
        repo.append_source_version(invalid)


def test_source_rejects_parser_that_does_not_match_raw_manifest(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, request, manifest, _ = persisted_graph(database_context, workspace_tmp_path)
    invalid = source_contract(
        request=request,
        manifest=manifest,
        parser_version="toss-source-parser/0.2.0",
    )
    with pytest.raises(ProviderContractConflict, match="trace does not match"):
        repo.append_source_version(invalid)


def test_collection_attempt_rejects_dataset_mismatch_with_request(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, request, _, _ = persisted_graph(database_context, workspace_tmp_path)
    invalid = completed_attempt(request.canonical_request_id, dataset=ProviderDataset.CURRENT_PRICE)
    with pytest.raises(ProviderContractConflict, match="does not match canonical request"):
        repo.record_collection_attempt(invalid)


def test_audit_rejects_attempt_request_mismatch(database_context, workspace_tmp_path: Path) -> None:
    repo, request, _, source = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(source)
    other_request = build_canonical_request("/api/v1/stocks/all", {"market": "US"})
    repo.insert_or_verify_canonical_request(other_request)
    repo.record_collection_attempt(completed_attempt(other_request.canonical_request_id))
    with pytest.raises(ProviderContractConflict, match="attempt and source trace"):
        repo.append_audit_event(audit_event(source.source_version_id))
    assert request.canonical_request_id != other_request.canonical_request_id


def test_audit_rejects_attempt_dataset_mismatch(database_context, workspace_tmp_path: Path) -> None:
    repo, request, _, source = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(source)
    repo.record_collection_attempt(completed_attempt(request.canonical_request_id))
    with database_context.engine.begin() as connection:
        connection.execute(
            update(CollectionAttemptRow)
            .where(CollectionAttemptRow.attempt_id == "attempt_cp3b_001")
            .values(dataset=ProviderDataset.CURRENT_PRICE.value)
        )
    with pytest.raises(ProviderContractConflict, match="attempt and source trace"):
        repo.append_audit_event(audit_event(source.source_version_id))


def test_audit_rejects_attempt_provider_mismatch(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, request, _, source = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(source)
    repo.record_collection_attempt(completed_attempt(request.canonical_request_id))
    with database_context.engine.begin() as connection:
        connection.execute(
            update(CollectionAttemptRow)
            .where(CollectionAttemptRow.attempt_id == "attempt_cp3b_001")
            .values(provider="UNAPPROVED_PROVIDER")
        )
    with pytest.raises(ProviderContractConflict, match="attempt and source trace"):
        repo.append_audit_event(audit_event(source.source_version_id))


def test_source_appended_audit_without_source_is_rejected(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, request, _, _ = persisted_graph(database_context, workspace_tmp_path)
    repo.record_collection_attempt(completed_attempt(request.canonical_request_id))
    event = audit_event(None)
    with pytest.raises(ProviderContractConflict, match="requires a source version"):
        repo.append_audit_event(event)


def test_trace_mismatch_rolls_back_source_and_audit_together(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, _, _, source = persisted_graph(database_context, workspace_tmp_path)
    other_request = build_canonical_request("/api/v1/stocks/all", {"market": "US"})
    repo.insert_or_verify_canonical_request(other_request)
    repo.record_collection_attempt(completed_attempt(other_request.canonical_request_id))
    with pytest.raises(ProviderContractConflict, match="attempt and source trace"):
        repo.record_source_version_with_audit(source, audit_event(source.source_version_id))
    with database_context.engine.connect() as connection:
        assert (
            connection.execute(
                select(func.count()).select_from(ProviderSourceVersionRow)
            ).scalar_one()
            == 0
        )
        assert (
            connection.execute(select(func.count()).select_from(ProviderAuditEventRow)).scalar_one()
            == 0
        )


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


def test_duplicate_observation_records_distinct_attempt_and_audit_without_new_source(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, request, _, source = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(source)
    first_attempt = completed_attempt(request.canonical_request_id)
    duplicate_attempt = completed_attempt(
        request.canonical_request_id, attempt_id="attempt_cp3b_duplicate"
    )
    repo.record_collection_attempt(first_attempt)
    repo.record_collection_attempt(duplicate_attempt)
    repo.append_audit_event(audit_event(source.source_version_id))
    repo.append_audit_event(
        audit_event(
            source.source_version_id,
            event_id="audit_cp3b_duplicate",
            attempt_id=duplicate_attempt.attempt_id,
            event_type=ProviderAuditEventType.DUPLICATE_OBSERVED,
        )
    )
    with database_context.engine.connect() as connection:
        assert (
            connection.execute(select(func.count()).select_from(CollectionAttemptRow)).scalar_one()
            == 2
        )
        assert (
            connection.execute(select(func.count()).select_from(ProviderAuditEventRow)).scalar_one()
            == 2
        )
        assert (
            connection.execute(
                select(func.count()).select_from(ProviderSourceVersionRow)
            ).scalar_one()
            == 1
        )


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
    repo.append_audit_event(
        existing_event.model_copy(
            update={
                "source_version_id": None,
                "event_type": ProviderAuditEventType.RAW_PERSISTED,
            }
        )
    )
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


def test_verified_mapping_rejects_issuer_security_relationship_mismatch(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, _, _, source = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(source)
    identity = provider_identity(source.source_version_id)
    repo.insert_or_verify_identity(identity)
    mapping = verified_mapping(
        identity.provider_security_identity_id,
        source.source_version_id,
        security_id="security_us_synthetic_common",
    )
    with pytest.raises(ProviderContractConflict, match="issuer and security do not match"):
        repo.record_identity_mapping(mapping)


def test_verified_mapping_rejects_missing_issuer(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, _, _, source = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(source)
    identity = provider_identity(source.source_version_id)
    repo.insert_or_verify_identity(identity)
    mapping = verified_mapping(
        identity.provider_security_identity_id,
        source.source_version_id,
        issuer_id="issuer_missing",
    )
    with pytest.raises(ProviderContractConflict, match="existing issuer and security"):
        repo.record_identity_mapping(mapping)


def test_verified_mapping_rejects_missing_security(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, _, _, source = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(source)
    identity = provider_identity(source.source_version_id)
    repo.insert_or_verify_identity(identity)
    mapping = verified_mapping(
        identity.provider_security_identity_id,
        source.source_version_id,
        security_id="security_missing",
    )
    with pytest.raises(ProviderContractConflict, match="existing issuer and security"):
        repo.record_identity_mapping(mapping)


@pytest.mark.parametrize(
    "identity_state",
    [ProviderIdentityState.QUARANTINED, ProviderIdentityState.UNRESOLVED_COLLISION],
)
def test_verified_mapping_rejects_non_active_identity(
    database_context, workspace_tmp_path: Path, identity_state: ProviderIdentityState
) -> None:
    repo, _, _, source = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(source)
    identity = provider_identity(source.source_version_id, identity_state=identity_state)
    repo.insert_or_verify_identity(identity)
    mapping = verified_mapping(identity.provider_security_identity_id, source.source_version_id)
    with pytest.raises(ProviderContractConflict, match="active provider identity"):
        repo.record_identity_mapping(mapping)


def test_verified_mapping_rejects_unrelated_evidence_source(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, _, _, source = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(source)
    identity = provider_identity(source.source_version_id)
    repo.insert_or_verify_identity(identity)
    repo_again, _, _, unrelated = persisted_graph(
        database_context,
        workspace_tmp_path,
        raw_bytes=b"unrelated-evidence",
        market="US",
    )
    repo_again.append_source_version(unrelated)
    mapping = verified_mapping(identity.provider_security_identity_id, unrelated.source_version_id)
    with pytest.raises(ProviderContractConflict, match="outside provider identity lineage"):
        repo.record_identity_mapping(mapping)


def test_verified_mapping_accepts_first_source_lineage_and_valid_relationship(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, _, _, source = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(source)
    identity = provider_identity(source.source_version_id)
    repo.insert_or_verify_identity(identity)
    mapping = verified_mapping(identity.provider_security_identity_id, source.source_version_id)
    result = repo.record_identity_mapping(mapping)
    assert result.inserted is True
    assert result.record == mapping
    assert repo.record_identity_mapping(mapping).inserted is False


def test_second_open_ended_verified_mapping_for_one_identity_is_rejected(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, _, _, source = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(source)
    identity = provider_identity(source.source_version_id)
    repo.insert_or_verify_identity(identity)
    first = verified_mapping(identity.provider_security_identity_id, source.source_version_id)
    second = verified_mapping(
        identity.provider_security_identity_id,
        source.source_version_id,
        mapping_id="pmap_open_ended_b",
        issuer_id="issuer_us_synthetic",
        security_id="security_us_synthetic_common",
    )
    repo.record_identity_mapping(first)

    with pytest.raises(ProviderContractConflict, match="intervals overlap"):
        repo.record_identity_mapping(second)

    with database_context.engine.connect() as connection:
        rows = (
            connection.execute(
                select(ProviderIdentityMappingRow.payload_json).where(
                    ProviderIdentityMappingRow.provider_security_identity_id
                    == identity.provider_security_identity_id
                )
            )
            .scalars()
            .all()
        )
    assert rows == [canonical_json_bytes(first.model_dump(mode="json")).decode("utf-8")]


def test_overlapping_bounded_verified_mapping_intervals_are_rejected(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, _, _, source = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(source)
    identity = provider_identity(source.source_version_id)
    repo.insert_or_verify_identity(identity)
    first = verified_mapping(
        identity.provider_security_identity_id,
        source.source_version_id,
        mapping_id="pmap_bounded_a",
        valid_from=date(2020, 1, 1),
        valid_to=date(2022, 12, 31),
    )
    overlapping = verified_mapping(
        identity.provider_security_identity_id,
        source.source_version_id,
        mapping_id="pmap_bounded_b",
        valid_from=date(2022, 12, 31),
        valid_to=date(2024, 1, 1),
    )
    repo.record_identity_mapping(first)

    with pytest.raises(ProviderContractConflict, match="intervals overlap"):
        repo.record_identity_mapping(overlapping)


def test_open_ended_and_bounded_verified_mapping_overlap_is_rejected(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, _, _, source = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(source)
    identity = provider_identity(source.source_version_id)
    repo.insert_or_verify_identity(identity)
    bounded = verified_mapping(
        identity.provider_security_identity_id,
        source.source_version_id,
        mapping_id="pmap_bounded_before_open",
        valid_from=date(2020, 1, 1),
        valid_to=date(2025, 1, 1),
    )
    open_ended = verified_mapping(
        identity.provider_security_identity_id,
        source.source_version_id,
        mapping_id="pmap_open_after_bounded",
        valid_from=date(2025, 1, 1),
        valid_to=None,
    )
    repo.record_identity_mapping(bounded)

    with pytest.raises(ProviderContractConflict, match="intervals overlap"):
        repo.record_identity_mapping(open_ended)


def test_non_overlapping_historical_verified_mappings_are_allowed(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, _, _, source = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(source)
    identity = provider_identity(source.source_version_id)
    repo.insert_or_verify_identity(identity)
    first = verified_mapping(
        identity.provider_security_identity_id,
        source.source_version_id,
        mapping_id="pmap_historical_a",
        valid_from=None,
        valid_to=date(2021, 12, 31),
    )
    second = verified_mapping(
        identity.provider_security_identity_id,
        source.source_version_id,
        mapping_id="pmap_historical_b",
        issuer_id="issuer_us_synthetic",
        security_id="security_us_synthetic_common",
        valid_from=date(2022, 1, 1),
        valid_to=date(2023, 12, 31),
    )

    assert repo.record_identity_mapping(first).inserted is True
    assert repo.record_identity_mapping(second).inserted is True


def test_verified_mappings_for_different_provider_identities_are_independent(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, _, _, source = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(source)
    identity_a = provider_identity(source.source_version_id, anchor_token="A")
    identity_b = provider_identity(source.source_version_id, anchor_token="B")
    repo.insert_or_verify_identity(identity_a)
    repo.insert_or_verify_identity(identity_b)
    mapping_a = verified_mapping(
        identity_a.provider_security_identity_id,
        source.source_version_id,
        mapping_id="pmap_identity_a",
    )
    mapping_b = verified_mapping(
        identity_b.provider_security_identity_id,
        source.source_version_id,
        mapping_id="pmap_identity_b",
        issuer_id="issuer_us_synthetic",
        security_id="security_us_synthetic_common",
    )

    assert repo.record_identity_mapping(mapping_a).inserted is True
    assert repo.record_identity_mapping(mapping_b).inserted is True


def test_two_independent_verified_mapping_promotions_have_one_winner(
    database_context, workspace_tmp_path: Path
) -> None:
    raw_store = ProviderRawStore(workspace_tmp_path / "raw")
    repo, _, _, source = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(source)
    identity = provider_identity(source.source_version_id)
    repo.insert_or_verify_identity(identity)
    candidates = [
        verified_mapping(
            identity.provider_security_identity_id,
            source.source_version_id,
            mapping_id="pmap_concurrent_a",
        ),
        verified_mapping(
            identity.provider_security_identity_id,
            source.source_version_id,
            mapping_id="pmap_concurrent_b",
            issuer_id="issuer_us_synthetic",
            security_id="security_us_synthetic_common",
        ),
    ]
    barrier = Barrier(2)

    def promote(candidate: ProviderIdentityMapping) -> str:
        independent = repository(database_context, raw_store)
        barrier.wait()
        try:
            independent.record_identity_mapping(candidate)
        except ProviderContractConflict:
            return "TYPED_CONFLICT"
        except (IntegrityError, OperationalError):
            return "RAW_DATABASE_ERROR"
        return "SUCCESS"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(promote, candidates))

    assert sorted(outcomes) == ["SUCCESS", "TYPED_CONFLICT"]
    assert "RAW_DATABASE_ERROR" not in outcomes
    with database_context.engine.connect() as connection:
        rows = (
            connection.execute(
                select(ProviderIdentityMappingRow.payload_json).where(
                    ProviderIdentityMappingRow.provider_security_identity_id
                    == identity.provider_security_identity_id,
                    ProviderIdentityMappingRow.mapping_status == MappingStatus.VERIFIED.value,
                    ProviderIdentityMappingRow.valid_to.is_(None),
                )
            )
            .scalars()
            .all()
        )
    assert len(rows) == 1
    assert ProviderIdentityMapping.model_validate_json(rows[0]) in candidates


def test_verified_mapping_accepts_identifier_history_evidence_lineage(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, request, _, source = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(source)
    identity = provider_identity(source.source_version_id)
    repo.insert_or_verify_identity(identity)
    enriched_source = changed_source_candidate(
        repo,
        request,
        ProviderRawStore(workspace_tmp_path / "raw"),
        raw_bytes=b"identifier-enrichment",
        revision_status=RevisionStatus.AMENDED,
        supersedes_id=source.source_version_id,
    )
    repo.append_source_version(enriched_source)
    history = ProviderIdentifierHistory(
        identifier_history_id="pih_enriched_mapping_evidence",
        provider_security_identity_id=identity.provider_security_identity_id,
        identifier_kind=ProviderIdentifierKind.ISIN,
        identifier_value="KR0000000001",
        valid_from=None,
        valid_to=None,
        source_version_id=enriched_source.source_version_id,
        revision_reason=ProviderIdentifierReason.ENRICHMENT,
        provider_contract_version=PROVIDER_IDENTITY_CONTRACT_VERSION,
    )
    repo.append_identifier_history(history)
    mapping = verified_mapping(
        identity.provider_security_identity_id, enriched_source.source_version_id
    )
    assert repo.record_identity_mapping(mapping).inserted is True


def test_rejected_verified_mapping_preserves_existing_mapping_state(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, _, _, source = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(source)
    identity = provider_identity(source.source_version_id)
    repo.insert_or_verify_identity(identity)
    unresolved = ProviderIdentityMapping(
        mapping_id="pmap_existing_unresolved",
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
    repo.record_identity_mapping(unresolved)
    invalid = verified_mapping(
        identity.provider_security_identity_id,
        source.source_version_id,
        mapping_id="pmap_rejected_verified",
        security_id="security_us_synthetic_common",
    )
    with pytest.raises(ProviderContractConflict):
        repo.record_identity_mapping(invalid)
    with database_context.engine.connect() as connection:
        rows = connection.execute(select(ProviderIdentityMappingRow.payload_json)).scalars().all()
    assert len(rows) == 1
    assert ProviderIdentityMapping.model_validate_json(rows[0]) == unresolved


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


def test_current_price_timestamp_unknown_source_is_latest_eligible(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, _, _, source = persisted_dataset_graph(
        database_context,
        workspace_tmp_path,
        path="/api/v1/prices",
        query={"symbols": ["A"]},
        dataset=ProviderDataset.CURRENT_PRICE,
        source_locator="provider://toss-open-api/market/current-price",
        raw_bytes=b"current-price-timestamp",
        observed_at=NOW,
    )
    repo.append_source_version(source)
    identity = provider_identity(source.source_version_id)
    repo.insert_or_verify_identity(identity)
    pointer = latest_pointer(
        identity.provider_security_identity_id,
        source.source_version_id,
        "current-price",
        dataset=ProviderDataset.CURRENT_PRICE,
        observed_at=NOW,
    )
    assert source.freshness_status == FreshnessStatus.UNKNOWN
    assert repo.conditional_write_latest(pointer, expected_state_hash=None).inserted is True


def test_current_price_null_timestamp_source_is_storable_but_not_latest_eligible(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, _, _, source = persisted_dataset_graph(
        database_context,
        workspace_tmp_path,
        path="/api/v1/prices",
        query={"symbols": ["A"]},
        dataset=ProviderDataset.CURRENT_PRICE,
        source_locator="provider://toss-open-api/market/current-price",
        raw_bytes=b"current-price-null-timestamp",
    )
    assert repo.append_source_version(source).inserted is True
    identity = provider_identity(source.source_version_id)
    repo.insert_or_verify_identity(identity)
    pointer = latest_pointer(
        identity.provider_security_identity_id,
        source.source_version_id,
        "current-price-null",
        dataset=ProviderDataset.CURRENT_PRICE,
    )
    with pytest.raises(ProviderContractConflict, match="not latest eligible"):
        repo.conditional_write_latest(pointer, expected_state_hash=None)
    assert repo.source_revision_chain(source.source_version_id) == [source]


@pytest.mark.parametrize(
    "identity_state",
    [ProviderIdentityState.QUARANTINED, ProviderIdentityState.UNRESOLVED_COLLISION],
)
def test_latest_pointer_rejects_quarantine_or_collision_identity(
    database_context,
    workspace_tmp_path: Path,
    identity_state: ProviderIdentityState,
) -> None:
    repo, _, _, source = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(source)
    identity = provider_identity(source.source_version_id, identity_state=identity_state)
    repo.insert_or_verify_identity(identity)
    pointer = latest_pointer(
        identity.provider_security_identity_id, source.source_version_id, "ineligible"
    )
    with pytest.raises(ProviderContractConflict, match="active provider identity"):
        repo.conditional_write_latest(pointer, expected_state_hash=None)


def test_latest_pointer_rejects_dataset_mismatch_with_source(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, _, _, source = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(source)
    identity = provider_identity(source.source_version_id)
    repo.insert_or_verify_identity(identity)
    pointer = latest_pointer(
        identity.provider_security_identity_id,
        source.source_version_id,
        "wrong-dataset",
        dataset=ProviderDataset.STOCK_DETAIL,
    )
    with pytest.raises(ProviderContractConflict, match="does not match source lineage"):
        repo.conditional_write_latest(pointer, expected_state_hash=None)


def test_latest_pointer_rejects_observation_mismatch_with_source(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, _, _, source = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(source)
    identity = provider_identity(source.source_version_id)
    repo.insert_or_verify_identity(identity)
    pointer = latest_pointer(
        identity.provider_security_identity_id,
        source.source_version_id,
        "wrong-observation",
        observed_at=NOW,
    )
    with pytest.raises(ProviderContractConflict, match="does not match source lineage"):
        repo.conditional_write_latest(pointer, expected_state_hash=None)


def test_latest_pointer_rejects_source_outside_identity_lineage(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, _, _, source = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(source)
    identity = provider_identity(source.source_version_id)
    repo.insert_or_verify_identity(identity)
    repo_again, _, _, unrelated = persisted_graph(
        database_context,
        workspace_tmp_path,
        raw_bytes=b"latest-unrelated-source",
        market="US",
    )
    repo_again.append_source_version(unrelated)
    pointer = latest_pointer(
        identity.provider_security_identity_id, unrelated.source_version_id, "unrelated"
    )
    with pytest.raises(ProviderContractConflict, match="does not match source lineage"):
        repo.conditional_write_latest(pointer, expected_state_hash=None)


def test_two_independent_sessions_cas_exactly_one_writer_wins(
    database_context, workspace_tmp_path: Path
) -> None:
    raw_store = ProviderRawStore(workspace_tmp_path / "raw")
    repo = repository(database_context, raw_store)
    request = build_canonical_request("/api/v1/stocks/all", {"market": "KR"})
    stored = raw_store.persist(b"two-session-cas")
    manifest = build_provider_raw_manifest(
        request=request,
        http_status=200,
        raw_content_hash=stored.raw_content_hash,
        raw_storage_ref=stored.raw_storage_ref,
        fetched_at=NOW,
        response_metadata=ProviderResponseMetadata(content_type="application/json"),
        parser_version="toss-source-parser/0.1.0",
    )
    repo.insert_or_verify_canonical_request(request)
    repo.insert_or_verify_raw_manifest(manifest)
    source = source_contract(request=request, manifest=manifest)
    repo.append_source_version(source)
    identity = provider_identity(source.source_version_id)
    repo.insert_or_verify_identity(identity)
    first = latest_pointer(identity.provider_security_identity_id, source.source_version_id, "one")
    repo.conditional_write_latest(first, expected_state_hash=None)
    candidates = [
        latest_pointer(
            identity.provider_security_identity_id, source.source_version_id, "writer-a"
        ),
        latest_pointer(
            identity.provider_security_identity_id, source.source_version_id, "writer-b"
        ),
    ]
    barrier = Barrier(2)

    def write(candidate: ProviderLatestPointer) -> str:
        independent = repository(database_context, raw_store)
        barrier.wait()
        try:
            independent.conditional_write_latest(candidate, expected_state_hash=first.state_hash)
        except ProviderConditionalWriteConflict:
            return "CONFLICT"
        return "SUCCESS"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(write, candidates))
    assert sorted(outcomes) == ["CONFLICT", "SUCCESS"]
    final = repo.read_latest_pointer(first.dataset.value, identity.provider_security_identity_id)
    assert final in candidates
    assert final is not None
    assert (final.normalized_record_id, final.state_hash) in {
        (candidate.normalized_record_id, candidate.state_hash) for candidate in candidates
    }
    assert repo.source_revision_chain(source.source_version_id) == [source]


def test_two_independent_sessions_first_insert_race_keeps_one_complete_row(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, _, _, source = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(source)
    identity = provider_identity(source.source_version_id)
    repo.insert_or_verify_identity(identity)
    candidates = [
        latest_pointer(
            identity.provider_security_identity_id, source.source_version_id, "insert-a"
        ),
        latest_pointer(
            identity.provider_security_identity_id, source.source_version_id, "insert-b"
        ),
    ]
    raw_store = ProviderRawStore(workspace_tmp_path / "raw")
    barrier = Barrier(2)

    def insert(candidate: ProviderLatestPointer) -> str:
        independent = repository(database_context, raw_store)
        barrier.wait()
        try:
            independent.conditional_write_latest(candidate, expected_state_hash=None)
        except ProviderConditionalWriteConflict:
            return "CONFLICT"
        return "SUCCESS"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(insert, candidates))
    assert sorted(outcomes) == ["CONFLICT", "SUCCESS"]
    with database_context.engine.connect() as connection:
        rows = connection.execute(select(ProviderLatestPointerRow.payload_json)).scalars().all()
    assert len(rows) == 1
    persisted = ProviderLatestPointer.model_validate_json(rows[0])
    assert persisted in candidates


def test_two_independent_sessions_same_first_insert_is_idempotent(
    database_context, workspace_tmp_path: Path
) -> None:
    repo, _, _, source = persisted_graph(database_context, workspace_tmp_path)
    repo.append_source_version(source)
    identity = provider_identity(source.source_version_id)
    repo.insert_or_verify_identity(identity)
    candidate = latest_pointer(
        identity.provider_security_identity_id, source.source_version_id, "same-insert"
    )
    raw_store = ProviderRawStore(workspace_tmp_path / "raw")
    barrier = Barrier(2)

    def insert() -> bool:
        independent = repository(database_context, raw_store)
        barrier.wait()
        return independent.conditional_write_latest(candidate, expected_state_hash=None).inserted

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = [
            future.result() for future in [executor.submit(insert), executor.submit(insert)]
        ]
    assert sorted(outcomes) == [False, True]
    with database_context.engine.connect() as connection:
        assert (
            connection.execute(
                select(func.count()).select_from(ProviderLatestPointerRow)
            ).scalar_one()
            == 1
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
