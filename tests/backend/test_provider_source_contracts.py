from __future__ import annotations

import json
from datetime import UTC, date, datetime
from typing import get_args

import pytest
from pydantic import ValidationError

from toss_dashboard_api.contracts.base import ContractVersion, sha256_prefixed
from toss_dashboard_api.contracts.enums import (
    FinalityStatus,
    FreshnessStatus,
    MissingReason,
    ProviderDataset,
    ProviderSystem,
    RevisionStatus,
)
from toss_dashboard_api.contracts.provider_source import (
    PROVIDER_SOURCE_CONTRACT_VERSION,
    CanonicalRequest,
    ProviderResponseMetadata,
    ProviderSourceVersion,
    build_canonical_request,
    build_provider_raw_manifest,
    provider_source_normalized_hash,
    provider_source_version_id,
)


def source_payload(**overrides: object) -> dict[str, object]:
    request = build_canonical_request("/api/v1/prices", {"symbols": ["A"]})
    raw_hash = sha256_prefixed(b'{"result":[]}')
    digest = raw_hash.removeprefix("sha256:")
    payload: dict[str, object] = {
        "source_version_id": "tsrc_pending",
        "provider": ProviderSystem.TOSS_OPEN_API,
        "dataset": ProviderDataset.CURRENT_PRICE,
        "canonical_request_id": request.canonical_request_id,
        "raw_response_id": "traw_original",
        "source_locator": "provider://toss-open-api/market/current-price",
        "observed_at": None,
        "observed_date": None,
        "published_at": None,
        "fetched_at": datetime(2026, 8, 25, 1, 2, 3, tzinfo=UTC),
        "missing_reasons": {
            "observed_at": MissingReason.NOT_PROVIDED,
            "observed_date": MissingReason.NOT_PROVIDED,
            "published_at": MissingReason.NOT_PROVIDED,
        },
        "freshness_status": FreshnessStatus.UNKNOWN,
        "finality_status": FinalityStatus.UNKNOWN,
        "revision_status": RevisionStatus.ORIGINAL,
        "supersedes_id": None,
        "raw_content_hash": raw_hash,
        "parser_version": "toss-source-parser/0.1.0",
        "provider_contract_version": PROVIDER_SOURCE_CONTRACT_VERSION,
        "raw_storage_ref": f"provider-raw:sha256/{digest[:2]}/{digest}",
    }
    payload.update(overrides)
    payload["normalized_content_hash"] = provider_source_normalized_hash(payload)
    if "source_version_id" not in overrides:
        payload["source_version_id"] = provider_source_version_id(payload)
    return payload


def test_provider_source_rejects_extra_field() -> None:
    payload = source_payload(unexpected="value")
    with pytest.raises(ValidationError, match="unexpected"):
        ProviderSourceVersion.model_validate(payload)


def test_provider_local_contract_version_is_exact() -> None:
    payload = source_payload(provider_contract_version="toss-source/0.1.1")
    with pytest.raises(ValidationError, match="provider_contract_version"):
        ProviderSourceVersion.model_validate(payload)


def test_global_contract_version_remains_phase_one_only() -> None:
    assert get_args(ContractVersion) == ("0.1.0",)


@pytest.mark.parametrize("field_name", ["observed_at", "fetched_at"])
def test_provider_source_rejects_naive_datetime(field_name: str) -> None:
    with pytest.raises((ValidationError, ValueError), match="timezone"):
        ProviderSourceVersion.model_validate(source_payload(**{field_name: "2026-08-25T01:02:03"}))


def test_both_observation_fields_null_with_reasons_is_valid() -> None:
    source = ProviderSourceVersion.model_validate(source_payload())
    assert source.observed_at is None
    assert source.observed_date is None
    assert source.missing_reasons["observed_at"] == MissingReason.NOT_PROVIDED
    assert source.freshness_status == FreshnessStatus.UNKNOWN


@pytest.mark.parametrize("field_name", ["observed_at", "observed_date"])
def test_null_observation_without_reason_is_rejected(field_name: str) -> None:
    payload = source_payload()
    reasons = dict(payload["missing_reasons"])  # type: ignore[arg-type]
    reasons.pop(field_name)
    payload["missing_reasons"] = reasons
    payload["normalized_content_hash"] = provider_source_normalized_hash(payload)
    with pytest.raises(ValidationError, match=field_name):
        ProviderSourceVersion.model_validate(payload)


def test_null_published_at_without_reason_is_rejected() -> None:
    payload = source_payload()
    reasons = dict(payload["missing_reasons"])  # type: ignore[arg-type]
    reasons.pop("published_at")
    payload["missing_reasons"] = reasons
    payload["normalized_content_hash"] = provider_source_normalized_hash(payload)
    with pytest.raises(ValidationError, match="published_at"):
        ProviderSourceVersion.model_validate(payload)


def test_fetched_at_is_not_copied_into_missing_observation() -> None:
    source = ProviderSourceVersion.model_validate(source_payload())
    assert source.fetched_at == datetime(2026, 8, 25, 1, 2, 3, tzinfo=UTC)
    assert source.observed_at is None
    assert source.observed_date is None


@pytest.mark.parametrize("dataset", [ProviderDataset.STOCK_DISCOVERY, ProviderDataset.STOCK_DETAIL])
def test_stock_source_requires_unknown_observation_time(dataset: ProviderDataset) -> None:
    payload = source_payload(dataset=dataset, observed_at="2026-08-25T01:00:00Z")
    reasons = dict(payload["missing_reasons"])  # type: ignore[arg-type]
    reasons.pop("observed_at")
    payload["missing_reasons"] = reasons
    payload["normalized_content_hash"] = provider_source_normalized_hash(payload)
    with pytest.raises(ValidationError, match="do not provide"):
        ProviderSourceVersion.model_validate(payload)


def test_current_price_allows_timestamp_and_forbids_observed_date() -> None:
    payload = source_payload(observed_at="2026-08-25T10:00:00+09:00")
    reasons = dict(payload["missing_reasons"])  # type: ignore[arg-type]
    reasons.pop("observed_at")
    payload["missing_reasons"] = reasons
    payload["normalized_content_hash"] = provider_source_normalized_hash(payload)
    payload["source_version_id"] = provider_source_version_id(payload)
    source = ProviderSourceVersion.model_validate(payload)
    assert source.observed_at == datetime(2026, 8, 25, 1, 0, tzinfo=UTC)

    payload["observed_date"] = date(2026, 8, 25)
    reasons.pop("observed_date")
    payload["normalized_content_hash"] = provider_source_normalized_hash(payload)
    with pytest.raises(ValidationError, match="forbids observed_date"):
        ProviderSourceVersion.model_validate(payload)


def test_daily_flow_requires_date_and_allows_timestamp_plus_date() -> None:
    payload = source_payload(
        dataset=ProviderDataset.DAILY_FLOW,
        observed_at="2026-08-25T10:00:00+09:00",
        observed_date=date(2026, 8, 25),
    )
    reasons = {"published_at": MissingReason.NOT_PROVIDED}
    payload["missing_reasons"] = reasons
    payload["normalized_content_hash"] = provider_source_normalized_hash(payload)
    payload["source_version_id"] = provider_source_version_id(payload)
    source = ProviderSourceVersion.model_validate(payload)
    assert source.dataset == ProviderDataset.DAILY_FLOW
    assert source.observed_date == date(2026, 8, 25)


def test_unknown_dataset_fails_closed() -> None:
    payload = source_payload(dataset="UNKNOWN_DATASET")
    with pytest.raises(ValidationError, match="dataset"):
        ProviderSourceVersion.model_validate(payload)


def test_current_price_without_timestamp_cannot_be_fresh() -> None:
    payload = source_payload(freshness_status=FreshnessStatus.FRESH)
    payload["normalized_content_hash"] = provider_source_normalized_hash(payload)
    with pytest.raises(ValidationError, match="UNKNOWN freshness"):
        ProviderSourceVersion.model_validate(payload)


def test_original_and_revision_link_rules_are_exact() -> None:
    original = ProviderSourceVersion.model_validate(source_payload())
    assert original.revision_status == RevisionStatus.ORIGINAL
    revised = source_payload(
        source_version_id="tsrc_revised",
        revision_status=RevisionStatus.AMENDED,
        supersedes_id=original.source_version_id,
    )
    revised["normalized_content_hash"] = provider_source_normalized_hash(revised)
    revised["source_version_id"] = provider_source_version_id(revised)
    assert ProviderSourceVersion.model_validate(revised).supersedes_id == original.source_version_id

    missing_parent = source_payload(revision_status=RevisionStatus.AMENDED)
    missing_parent["normalized_content_hash"] = provider_source_normalized_hash(missing_parent)
    missing_parent["source_version_id"] = provider_source_version_id(missing_parent)
    with pytest.raises(ValidationError, match="supersedes_id"):
        ProviderSourceVersion.model_validate(missing_parent)


def test_normalized_hash_excludes_fetch_and_storage_identity_fields() -> None:
    first = source_payload()
    second = dict(first)
    second.update(
        {
            "source_version_id": "tsrc_second",
            "raw_response_id": "traw_second",
            "fetched_at": "2026-08-26T01:02:03Z",
            "raw_storage_ref": "provider-raw:sha256/00/" + "0" * 64,
        }
    )
    assert provider_source_normalized_hash(first) == provider_source_normalized_hash(second)


def test_normalized_hash_includes_semantic_time_and_revision() -> None:
    first = source_payload()
    second = dict(first)
    second["finality_status"] = FinalityStatus.FINAL
    assert provider_source_normalized_hash(first) != provider_source_normalized_hash(second)


def test_canonical_request_query_order_does_not_change_identity() -> None:
    first = build_canonical_request(
        "/api/v1/stocks/all",
        {"market": "KR", "status": "ACTIVE", "commonShare": True},
    )
    second = build_canonical_request(
        "/api/v1/stocks/all",
        {"commonShare": True, "status": "ACTIVE", "market": "KR"},
    )
    assert first == second


def test_canonical_request_deduplicates_and_sorts_symbols() -> None:
    request = build_canonical_request("/api/v1/stocks", {"symbols": ["B", "A", "B"]})
    assert json.loads(request.canonical_query_json) == {"symbols": ["A", "B"]}


@pytest.mark.parametrize(
    ("path", "query"),
    [
        ("/api/v1/stocks", {"symbols": ["A", "B"]}),
        ("/api/v1/stocks", {"symbols": ["A", "C"]}),
        ("/api/v1/prices", {"symbols": ["A", "B"]}),
    ],
)
def test_canonical_request_semantic_changes_change_id(path: str, query: dict[str, object]) -> None:
    baseline = build_canonical_request("/api/v1/stocks", {"symbols": ["A"]})
    candidate = build_canonical_request(path, query)  # type: ignore[arg-type]
    assert candidate.canonical_request_id != baseline.canonical_request_id


@pytest.mark.parametrize(
    "prohibited_key",
    [
        "Authorization",
        "client" + "_secret",
        "access" + "_token",
        "cookie",
        "X-" + "Tossinvest-Account",
    ],
)
def test_canonical_request_rejects_authentication_or_account_query(
    prohibited_key: str,
) -> None:
    with pytest.raises(ValueError, match="prohibited|outside"):
        build_canonical_request("/api/v1/stocks/all", {"market": "KR", prohibited_key: "unsafe"})


def test_canonical_request_rejects_unknown_path_template() -> None:
    with pytest.raises(KeyError):
        build_canonical_request("/api/v1/unknown", {})  # type: ignore[arg-type]


def test_canonical_request_is_independent_of_current_time() -> None:
    first = build_canonical_request("/api/v1/prices", {"symbols": "B,A"})
    second = build_canonical_request("/api/v1/prices", {"symbols": ["A", "B"]})
    assert first.canonical_request_id == second.canonical_request_id
    assert first.canonical_query_hash == second.canonical_query_hash


def test_canonical_request_model_rejects_conflicting_identity() -> None:
    request = build_canonical_request("/api/v1/prices", {"symbols": ["A"]})
    payload = request.model_dump(mode="json")
    payload["canonical_request_id"] = "treq_" + "0" * 64
    with pytest.raises(ValidationError, match="request semantics"):
        CanonicalRequest.model_validate_json(json.dumps(payload))


def test_raw_manifest_identity_and_opaque_ref_are_hash_derived() -> None:
    request = build_canonical_request("/api/v1/prices", {"symbols": ["A"]})
    raw_hash = sha256_prefixed(b'{"result":[]}')
    digest = raw_hash.removeprefix("sha256:")
    manifest = build_provider_raw_manifest(
        request=request,
        http_status=200,
        raw_content_hash=raw_hash,
        raw_storage_ref=f"provider-raw:sha256/{digest[:2]}/{digest}",
        fetched_at="2026-08-25T01:02:03Z",
        response_metadata=ProviderResponseMetadata(content_type="application/json"),
        parser_version="toss-source-parser/0.1.0",
    )
    assert manifest.raw_response_id.startswith("traw_")
    assert len(manifest.raw_response_id) == len("traw_") + 64
    assert manifest.raw_storage_ref.endswith(digest)


def test_raw_manifest_rejects_naive_fetched_at() -> None:
    request = build_canonical_request("/api/v1/prices", {"symbols": ["A"]})
    raw_hash = sha256_prefixed(b"raw")
    digest = raw_hash.removeprefix("sha256:")
    with pytest.raises(ValidationError, match="timezone"):
        build_provider_raw_manifest(
            request=request,
            http_status=200,
            raw_content_hash=raw_hash,
            raw_storage_ref=f"provider-raw:sha256/{digest[:2]}/{digest}",
            fetched_at="2026-08-25T01:02:03",
            response_metadata=ProviderResponseMetadata(content_type="application/json"),
            parser_version="toss-source-parser/0.1.0",
        )


def test_response_metadata_rejects_unrestricted_header_fields() -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        ProviderResponseMetadata.model_validate({"author" + "ization": "prohibited-header-value"})


def test_response_metadata_rejects_inconsistent_numeric_rate_values() -> None:
    with pytest.raises(ValidationError, match="cannot exceed"):
        ProviderResponseMetadata(rate_limit=1, rate_remaining=2)


def test_raw_manifest_rejects_ref_that_does_not_match_raw_hash() -> None:
    request = build_canonical_request("/api/v1/prices", {"symbols": ["A"]})
    raw_hash = sha256_prefixed(b"raw")
    with pytest.raises(ValidationError, match="raw_storage_ref"):
        build_provider_raw_manifest(
            request=request,
            http_status=200,
            raw_content_hash=raw_hash,
            raw_storage_ref="provider-raw:sha256/00/" + "0" * 64,
            fetched_at="2026-08-25T01:02:03Z",
            response_metadata=ProviderResponseMetadata(content_type="application/json"),
            parser_version="toss-source-parser/0.1.0",
        )
