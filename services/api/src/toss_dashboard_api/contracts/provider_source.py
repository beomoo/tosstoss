from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from enum import Enum
from typing import Annotated, Any, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from toss_dashboard_api.contracts.base import (
    NonEmptyText,
    SafeId,
    Sha256,
    UtcDatetime,
    canonical_json_bytes,
    sha256_prefixed,
    utc_to_string,
    validate_utc_datetime,
)
from toss_dashboard_api.contracts.enums import (
    CollectionAttemptStatus,
    FinalityStatus,
    FreshnessStatus,
    MissingReason,
    ProviderAuditEventType,
    ProviderDataset,
    ProviderHttpMethod,
    ProviderSystem,
    RevisionStatus,
)

ProviderSourceContractVersion = Literal["toss-source/0.1.0"]
PROVIDER_SOURCE_CONTRACT_VERSION: ProviderSourceContractVersion = "toss-source/0.1.0"
ProviderPathTemplate = Literal[
    "/api/v1/stocks/all",
    "/api/v1/stocks",
    "/api/v1/prices",
]
ParserVersion = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z][a-z0-9-]*/[0-9]+\.[0-9]+\.[0-9]+$", max_length=64),
]
ProviderSourceLocator = Annotated[
    str,
    StringConstraints(pattern=r"^provider://toss-open-api/[a-z0-9_/-]+$", max_length=256),
]
ProviderRawRef = Annotated[
    str,
    StringConstraints(pattern=r"^provider-raw:sha256/[0-9a-f]{2}/[0-9a-f]{64}$"),
]

_SYMBOL_PATTERN = re.compile(r"^[A-Za-z0-9.-]{1,32}$")
_QUERY_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_FORBIDDEN_QUERY_KEYS = {
    "authorization",
    "access_token",
    "client_id",
    "client_secret",
    "token",
    "cookie",
}
_ALLOWED_QUERY_KEYS: dict[str, frozenset[str]] = {
    "/api/v1/stocks/all": frozenset({"market", "status", "securityType", "commonShare"}),
    "/api/v1/stocks": frozenset({"symbols"}),
    "/api/v1/prices": frozenset({"symbols"}),
}
PROVIDER_DATASET_BY_PATH: dict[str, ProviderDataset] = {
    "/api/v1/stocks/all": ProviderDataset.STOCK_DISCOVERY,
    "/api/v1/stocks": ProviderDataset.STOCK_DETAIL,
    "/api/v1/prices": ProviderDataset.CURRENT_PRICE,
}
PROVIDER_SOURCE_LOCATOR_BY_DATASET: dict[ProviderDataset, str] = {
    ProviderDataset.STOCK_DISCOVERY: "provider://toss-open-api/market/stock-discovery",
    ProviderDataset.STOCK_DETAIL: "provider://toss-open-api/market/stock-detail",
    ProviderDataset.CURRENT_PRICE: "provider://toss-open-api/market/current-price",
    ProviderDataset.DAILY_FLOW: "provider://toss-open-api/market/daily-flow",
}


class ProviderStrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)


def _canonical_symbols(value: object) -> list[str]:
    values: Sequence[object]
    if isinstance(value, str):
        values = value.split(",")
    elif isinstance(value, list | tuple):
        values = value
    else:
        raise ValueError("symbols must be a string or sequence of strings")
    if not values:
        raise ValueError("symbols must not be empty")
    symbols: set[str] = set()
    for item in values:
        if not isinstance(item, str) or _SYMBOL_PATTERN.fullmatch(item) is None:
            raise ValueError("symbols contain an invalid provider symbol")
        symbols.add(item)
    if not 1 <= len(symbols) <= 200:
        raise ValueError("symbols must contain between 1 and 200 unique values")
    return sorted(symbols, key=lambda item: item.encode("ascii"))


def canonicalize_provider_query(
    path_template: ProviderPathTemplate,
    query: Mapping[str, object],
) -> str:
    allowed = _ALLOWED_QUERY_KEYS[path_template]
    if any(not isinstance(key, str) for key in query):
        raise ValueError("query keys must be strings")
    lowered_keys = {key.lower().replace("-", "_") for key in query}
    if lowered_keys.intersection(_FORBIDDEN_QUERY_KEYS):
        raise ValueError("query contains prohibited authentication or account metadata")
    unknown = set(query) - allowed
    if unknown:
        raise ValueError("query contains keys outside the exact path contract")
    if path_template in {"/api/v1/stocks", "/api/v1/prices"} and set(query) != {"symbols"}:
        raise ValueError("this path requires exactly the symbols query field")
    if path_template == "/api/v1/stocks/all" and "market" not in query:
        raise ValueError("stock discovery requires market")

    normalized: dict[str, object] = {}
    for key in sorted(query):
        value = query[key]
        if key == "symbols":
            normalized[key] = _canonical_symbols(value)
        elif key == "commonShare":
            if not isinstance(value, bool):
                raise ValueError("commonShare must be a JSON boolean")
            normalized[key] = value
        else:
            if not isinstance(value, str) or _QUERY_TOKEN_PATTERN.fullmatch(value) is None:
                raise ValueError("query token must use the provider-safe token grammar")
            lowered_value = value.lower()
            if "secret" in lowered_value or "token" in lowered_value or "bearer" in lowered_value:
                raise ValueError("query token contains prohibited authentication material")
            if key == "market" and value not in {"KR", "US"}:
                raise ValueError("market query must be KR or US")
            if key == "status" and value != "ACTIVE":
                raise ValueError("stock discovery status must be ACTIVE")
            normalized[key] = value
    return canonical_json_bytes(normalized).decode("utf-8")


def _request_digest_payload(
    *,
    provider: ProviderSystem,
    method: ProviderHttpMethod,
    path_template: str,
    canonical_query_json: str,
    provider_contract_version: str,
) -> bytes:
    return canonical_json_bytes(
        {
            "provider": provider.value,
            "method": method.value,
            "path_template": path_template,
            "canonical_query": json.loads(canonical_query_json),
            "provider_contract_version": provider_contract_version,
        }
    )


class CanonicalRequest(ProviderStrictModel):
    canonical_request_id: SafeId
    provider: ProviderSystem
    method: ProviderHttpMethod
    path_template: ProviderPathTemplate
    canonical_query_json: Annotated[NonEmptyText, StringConstraints(max_length=8192)]
    canonical_query_hash: Sha256
    provider_contract_version: ProviderSourceContractVersion

    @model_validator(mode="after")
    def validate_deterministic_identity(self) -> Self:
        parsed = json.loads(self.canonical_query_json)
        if not isinstance(parsed, dict):
            raise ValueError("canonical query must be a JSON object")
        if canonicalize_provider_query(self.path_template, parsed) != self.canonical_query_json:
            raise ValueError("canonical query does not match the exact path contract")
        canonical = canonical_json_bytes(parsed).decode("utf-8")
        if canonical != self.canonical_query_json:
            raise ValueError("canonical_query_json is not canonical JSON")
        expected_query_hash = sha256_prefixed(self.canonical_query_json.encode("utf-8"))
        if self.canonical_query_hash != expected_query_hash:
            raise ValueError("canonical_query_hash does not match canonical query")
        digest = hashlib.sha256(
            _request_digest_payload(
                provider=self.provider,
                method=self.method,
                path_template=self.path_template,
                canonical_query_json=self.canonical_query_json,
                provider_contract_version=self.provider_contract_version,
            )
        ).hexdigest()
        if self.canonical_request_id != f"treq_{digest}":
            raise ValueError("canonical_request_id does not match request semantics")
        return self


def build_canonical_request(
    path_template: ProviderPathTemplate,
    query: Mapping[str, object],
    *,
    provider: ProviderSystem = ProviderSystem.TOSS_OPEN_API,
    method: ProviderHttpMethod = ProviderHttpMethod.GET,
    provider_contract_version: ProviderSourceContractVersion = PROVIDER_SOURCE_CONTRACT_VERSION,
) -> CanonicalRequest:
    canonical_query_json = canonicalize_provider_query(path_template, query)
    query_hash = sha256_prefixed(canonical_query_json.encode("utf-8"))
    digest = hashlib.sha256(
        _request_digest_payload(
            provider=provider,
            method=method,
            path_template=path_template,
            canonical_query_json=canonical_query_json,
            provider_contract_version=provider_contract_version,
        )
    ).hexdigest()
    return CanonicalRequest(
        canonical_request_id=f"treq_{digest}",
        provider=provider,
        method=method,
        path_template=path_template,
        canonical_query_json=canonical_query_json,
        canonical_query_hash=query_hash,
        provider_contract_version=provider_contract_version,
    )


class ProviderResponseMetadata(ProviderStrictModel):
    request_id: Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9._:-]{1,128}$")] | None = None
    rate_limit: Annotated[int, Field(ge=0, le=10000)] | None = None
    rate_remaining: Annotated[int, Field(ge=0, le=10000)] | None = None
    rate_reset_seconds: Annotated[int, Field(ge=0, le=86400)] | None = None
    retry_after_seconds: Annotated[int, Field(ge=0, le=86400)] | None = None
    content_type: Literal["application/json"] | None = None

    @model_validator(mode="after")
    def validate_rate_values(self) -> Self:
        if (
            self.rate_limit is not None
            and self.rate_remaining is not None
            and self.rate_remaining > self.rate_limit
        ):
            raise ValueError("rate_remaining cannot exceed rate_limit")
        return self


class ProviderRawManifest(ProviderStrictModel):
    raw_response_id: SafeId
    canonical_request_id: SafeId
    provider: ProviderSystem
    method: ProviderHttpMethod
    path_template: ProviderPathTemplate
    canonical_query_json: Annotated[NonEmptyText, StringConstraints(max_length=8192)]
    http_status: Annotated[int, Field(ge=100, le=599)]
    raw_content_hash: Sha256
    raw_storage_ref: ProviderRawRef
    fetched_at: UtcDatetime
    response_metadata: ProviderResponseMetadata
    parser_version: ParserVersion
    provider_contract_version: ProviderSourceContractVersion

    @model_validator(mode="after")
    def validate_raw_identity(self) -> Self:
        digest = hashlib.sha256(
            canonical_json_bytes(
                {
                    "canonical_request_id": self.canonical_request_id,
                    "http_status": self.http_status,
                    "raw_content_hash": self.raw_content_hash,
                    "provider_contract_version": self.provider_contract_version,
                }
            )
        ).hexdigest()
        if self.raw_response_id != f"traw_{digest}":
            raise ValueError("raw_response_id does not match raw response semantics")
        expected_ref = self.raw_content_hash.removeprefix("sha256:")
        if self.raw_storage_ref != f"provider-raw:sha256/{expected_ref[:2]}/{expected_ref}":
            raise ValueError("raw_storage_ref does not match raw_content_hash")
        json.loads(self.canonical_query_json)
        return self


def build_provider_raw_manifest(
    *,
    request: CanonicalRequest,
    http_status: int,
    raw_content_hash: Sha256,
    raw_storage_ref: ProviderRawRef,
    fetched_at: Any,
    response_metadata: ProviderResponseMetadata,
    parser_version: ParserVersion,
) -> ProviderRawManifest:
    digest = hashlib.sha256(
        canonical_json_bytes(
            {
                "canonical_request_id": request.canonical_request_id,
                "http_status": http_status,
                "raw_content_hash": raw_content_hash,
                "provider_contract_version": request.provider_contract_version,
            }
        )
    ).hexdigest()
    return ProviderRawManifest(
        raw_response_id=f"traw_{digest}",
        canonical_request_id=request.canonical_request_id,
        provider=request.provider,
        method=request.method,
        path_template=request.path_template,
        canonical_query_json=request.canonical_query_json,
        http_status=http_status,
        raw_content_hash=raw_content_hash,
        raw_storage_ref=raw_storage_ref,
        fetched_at=fetched_at,
        response_metadata=response_metadata,
        parser_version=parser_version,
        provider_contract_version=request.provider_contract_version,
    )


_PROVIDER_SOURCE_HASH_FIELDS = (
    "provider_contract_version",
    "provider",
    "dataset",
    "canonical_request_id",
    "source_locator",
    "observed_at",
    "observed_date",
    "published_at",
    "missing_reasons",
    "finality_status",
    "revision_status",
    "parser_version",
)


def provider_source_normalized_hash(value: Mapping[str, Any] | ProviderSourceVersion) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)
    semantic: dict[str, Any] = {}
    for key in _PROVIDER_SOURCE_HASH_FIELDS:
        item = payload[key]
        if key in {"observed_at", "published_at"} and item is not None:
            item = utc_to_string(validate_utc_datetime(item))
        semantic[key] = _provider_hash_json_value(item)
    return sha256_prefixed(canonical_json_bytes(semantic))


def _provider_hash_json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _provider_hash_json_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_provider_hash_json_value(item) for item in value]
    return value


def provider_source_version_id(value: Mapping[str, Any]) -> str:
    digest = hashlib.sha256(
        canonical_json_bytes(
            {
                "dataset": value["dataset"],
                "canonical_request_id": value["canonical_request_id"],
                "raw_response_id": value["raw_response_id"],
                "normalized_content_hash": value["normalized_content_hash"],
                "provider_contract_version": value["provider_contract_version"],
            }
        )
    ).hexdigest()
    return f"tsrc_{digest}"


class ProviderSourceVersion(ProviderStrictModel):
    source_version_id: SafeId
    provider: ProviderSystem
    dataset: ProviderDataset
    canonical_request_id: SafeId
    raw_response_id: SafeId
    source_locator: ProviderSourceLocator
    observed_at: UtcDatetime | None
    observed_date: date | None
    published_at: UtcDatetime | None
    fetched_at: UtcDatetime
    missing_reasons: dict[NonEmptyText, MissingReason]
    freshness_status: FreshnessStatus
    finality_status: FinalityStatus
    revision_status: RevisionStatus
    supersedes_id: SafeId | None
    raw_content_hash: Sha256
    normalized_content_hash: Sha256
    parser_version: ParserVersion
    provider_contract_version: ProviderSourceContractVersion
    raw_storage_ref: ProviderRawRef

    @field_validator("missing_reasons")
    @classmethod
    def validate_reason_keys(
        cls, value: dict[NonEmptyText, MissingReason]
    ) -> dict[NonEmptyText, MissingReason]:
        allowed = {"observed_at", "observed_date", "published_at"}
        if set(value) - allowed:
            raise ValueError("provider source missing reasons contain an unknown field")
        return value

    @model_validator(mode="after")
    def validate_source_semantics(self) -> Self:
        for field_name in ("observed_at", "observed_date", "published_at"):
            field_value = getattr(self, field_name)
            if field_value is None and field_name not in self.missing_reasons:
                raise ValueError(f"missing_reasons.{field_name} is required when null")
            if field_value is not None and field_name in self.missing_reasons:
                raise ValueError(f"missing_reasons.{field_name} is only allowed when null")

        if self.dataset in {ProviderDataset.STOCK_DISCOVERY, ProviderDataset.STOCK_DETAIL}:
            if self.observed_at is not None or self.observed_date is not None:
                raise ValueError("stock source datasets do not provide an observation time")
        elif self.dataset == ProviderDataset.CURRENT_PRICE:
            if self.observed_date is not None:
                raise ValueError("current price forbids observed_date")
            if self.freshness_status != FreshnessStatus.UNKNOWN:
                raise ValueError("current price must have UNKNOWN freshness before CP3-D2")
        elif self.dataset == ProviderDataset.DAILY_FLOW and self.observed_date is None:
            raise ValueError("daily flow requires observed_date")

        expected_locator = PROVIDER_SOURCE_LOCATOR_BY_DATASET[self.dataset]
        if self.source_locator != expected_locator:
            raise ValueError("source_locator does not match provider dataset")

        if self.revision_status == RevisionStatus.ORIGINAL and self.supersedes_id is not None:
            raise ValueError("original provider source cannot supersede another version")
        if self.revision_status != RevisionStatus.ORIGINAL and self.supersedes_id is None:
            raise ValueError("revised provider source requires supersedes_id")
        if self.supersedes_id == self.source_version_id:
            raise ValueError("provider source cannot supersede itself")
        if provider_source_normalized_hash(self) != self.normalized_content_hash:
            raise ValueError("normalized_content_hash does not match provider source semantics")
        if provider_source_version_id(self.model_dump(mode="json")) != self.source_version_id:
            raise ValueError("source_version_id does not match immutable source semantics")
        return self


class CollectionAttempt(ProviderStrictModel):
    attempt_id: SafeId
    provider: ProviderSystem
    dataset: ProviderDataset
    canonical_request_id: SafeId | None
    started_at: UtcDatetime
    finished_at: UtcDatetime | None
    status: CollectionAttemptStatus
    records_received: Annotated[int, Field(ge=0)]
    records_rejected: Annotated[int, Field(ge=0)]
    safe_result_code: Annotated[str, StringConstraints(pattern=r"^[A-Z0-9_]{1,64}$")]

    @model_validator(mode="after")
    def validate_attempt_times(self) -> Self:
        if self.finished_at is not None and self.finished_at < self.started_at:
            raise ValueError("finished_at cannot precede started_at")
        if self.status == CollectionAttemptStatus.STARTED and self.finished_at is not None:
            raise ValueError("started attempt cannot have finished_at")
        if self.status != CollectionAttemptStatus.STARTED and self.finished_at is None:
            raise ValueError("finished attempt requires finished_at")
        return self


class ProviderAuditEvent(ProviderStrictModel):
    audit_event_id: SafeId
    attempt_id: SafeId
    source_version_id: SafeId | None
    event_type: ProviderAuditEventType
    safe_status: Annotated[str, StringConstraints(pattern=r"^[A-Z0-9_]{1,64}$")]
    record_count: Annotated[int, Field(ge=0)]
    occurred_at: UtcDatetime
