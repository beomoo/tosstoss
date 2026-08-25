from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Mapping
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Annotated, Any, Literal, Self, cast

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from toss_dashboard_api.contracts.base import (
    DecimalString,
    NonEmptyText,
    SafeId,
    Sha256,
    canonical_json_bytes,
    decimal_to_string,
    sha256_prefixed,
)
from toss_dashboard_api.contracts.enums import (
    Currency,
    Market,
    MissingReason,
    ProviderDetailBatchStatus,
    ProviderIdentityState,
    ProviderListingMarket,
    ProviderReconciliationOutcome,
    ProviderSecurityMasterState,
    ProviderSecurityStatus,
    ProviderSecurityType,
    ProviderSystem,
)

ProviderSecurityMasterContractVersion = Literal["toss-security-master/0.1.0"]
PROVIDER_SECURITY_MASTER_CONTRACT_VERSION: ProviderSecurityMasterContractVersion = (
    "toss-security-master/0.1.0"
)
ProviderSymbol = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Za-z0-9.-]{1,32}$", max_length=32),
]
ProviderName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=256)
]
IsinValue = Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$", max_length=12)]
ReasonCode = Annotated[str, StringConstraints(pattern=r"^[A-Z0-9_]{1,64}$", max_length=64)]


class ProviderSecurityMasterStrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)


class TossStockDiscoveryItem(ProviderSecurityMasterStrictModel):
    symbol: ProviderSymbol
    name: ProviderName
    securityType: ProviderSecurityType
    isCommonShare: bool
    isinCode: IsinValue | None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return unicodedata.normalize("NFC", value)

    @field_validator("isinCode")
    @classmethod
    def validate_isin(cls, value: str | None) -> str | None:
        if value is not None and not is_valid_isin(value):
            raise ValueError("isinCode must be a checksum-valid ISIN")
        return value


class TossStockDiscoveryResponse(ProviderSecurityMasterStrictModel):
    result: list[TossStockDiscoveryItem]

    @model_validator(mode="after")
    def validate_unique_symbols(self) -> Self:
        symbols = [item.symbol for item in self.result]
        if len(symbols) != len(set(symbols)):
            raise ValueError("stock discovery response contains duplicate symbols")
        return self


class TossKoreanMarketDetail(ProviderSecurityMasterStrictModel):
    liquidationTrading: bool
    nxtSupported: bool
    krxTradingSuspended: bool
    nxtTradingSuspended: bool | None


class TossStockDetailItem(ProviderSecurityMasterStrictModel):
    symbol: ProviderSymbol
    name: ProviderName
    englishName: ProviderName | None
    isinCode: IsinValue | None
    market: ProviderListingMarket
    securityType: ProviderSecurityType
    isCommonShare: bool
    status: ProviderSecurityStatus
    currency: Currency
    listDate: date | None
    delistDate: date | None
    sharesOutstanding: DecimalString
    leverageFactor: DecimalString | None
    koreanMarketDetail: TossKoreanMarketDetail | None

    @field_validator("name", "englishName")
    @classmethod
    def normalize_names(cls, value: str | None) -> str | None:
        return None if value is None else unicodedata.normalize("NFC", value)

    @field_validator("isinCode")
    @classmethod
    def validate_isin(cls, value: str | None) -> str | None:
        if value is not None and not is_valid_isin(value):
            raise ValueError("isinCode must be a checksum-valid ISIN")
        return value

    @model_validator(mode="after")
    def validate_numeric_semantics(self) -> Self:
        if self.sharesOutstanding < 0:
            raise ValueError("sharesOutstanding cannot be negative")
        if self.leverageFactor is not None and self.leverageFactor < 0:
            raise ValueError("leverageFactor cannot be negative")
        return self


class TossStockDetailResponse(ProviderSecurityMasterStrictModel):
    result: list[TossStockDetailItem]

    @model_validator(mode="after")
    def validate_unique_symbols(self) -> Self:
        symbols = [item.symbol for item in self.result]
        if len(symbols) != len(set(symbols)):
            raise ValueError("stock detail response contains duplicate symbols")
        return self


class ProviderSecurityMasterRecord(ProviderSecurityMasterStrictModel):
    normalized_record_id: SafeId
    provider: ProviderSystem
    market: Market
    provider_listing_market: ProviderListingMarket
    symbol: ProviderSymbol
    name: ProviderName
    english_name: ProviderName | None
    isin: IsinValue | None
    security_type: ProviderSecurityType
    is_common_share: bool
    status: ProviderSecurityStatus
    currency: Currency
    list_date: date | None
    delist_date: date | None
    shares_outstanding: DecimalString
    leverage_factor: DecimalString | None
    missing_reasons: dict[NonEmptyText, MissingReason]
    normalized_content_hash: Sha256
    provider_contract_version: ProviderSecurityMasterContractVersion

    @model_validator(mode="after")
    def validate_identity(self) -> Self:
        nullable_fields = (
            "english_name",
            "isin",
            "list_date",
            "delist_date",
            "leverage_factor",
        )
        for field_name in nullable_fields:
            value = getattr(self, field_name)
            if value is None and field_name not in self.missing_reasons:
                raise ValueError(f"missing_reasons.{field_name} is required when null")
            if value is not None and field_name in self.missing_reasons:
                raise ValueError(f"missing_reasons.{field_name} is prohibited when present")
        if security_master_record_hash(self) != self.normalized_content_hash:
            raise ValueError("normalized_content_hash does not match security master semantics")
        expected = "psmr_" + self.normalized_content_hash.removeprefix("sha256:")
        if self.normalized_record_id != expected:
            raise ValueError("normalized_record_id does not match security master semantics")
        return self


class ProviderSecurityMasterObservation(ProviderSecurityMasterStrictModel):
    observation_id: SafeId
    source_version_id: SafeId
    normalized_record_id: SafeId | None
    provider_security_identity_id: SafeId | None
    provider: ProviderSystem
    market: Market
    symbol: ProviderSymbol
    name: ProviderName
    security_type: ProviderSecurityType
    is_common_share: bool
    isin: IsinValue | None
    staging_state: ProviderSecurityMasterState
    reconciliation_outcome: ProviderReconciliationOutcome
    identity_state_after: ProviderIdentityState | None
    eligible_for_mapping: bool
    collision_identity_ids: tuple[SafeId, ...]
    reason_codes: tuple[ReasonCode, ...]
    provider_contract_version: ProviderSecurityMasterContractVersion

    @model_validator(mode="after")
    def validate_observation(self) -> Self:
        if tuple(sorted(set(self.collision_identity_ids))) != self.collision_identity_ids:
            raise ValueError("collision_identity_ids must be unique and sorted")
        if tuple(sorted(set(self.reason_codes))) != self.reason_codes:
            raise ValueError("reason_codes must be unique and sorted")
        if self.eligible_for_mapping:
            if (
                self.staging_state != ProviderSecurityMasterState.ELIGIBLE_FOR_MAPPING
                or self.provider_security_identity_id is None
                or self.identity_state_after != ProviderIdentityState.ACTIVE
                or self.collision_identity_ids
            ):
                raise ValueError("eligible mapping observation has contradictory state")
        digest = hashlib.sha256(
            canonical_json_bytes(
                {
                    "source_version_id": self.source_version_id,
                    "normalized_record_id": self.normalized_record_id,
                    "provider_security_identity_id": self.provider_security_identity_id,
                    "provider": self.provider.value,
                    "market": self.market.value,
                    "symbol": self.symbol,
                    "staging_state": self.staging_state.value,
                    "reconciliation_outcome": self.reconciliation_outcome.value,
                    "identity_state_after": (
                        None
                        if self.identity_state_after is None
                        else self.identity_state_after.value
                    ),
                    "eligible_for_mapping": self.eligible_for_mapping,
                    "collision_identity_ids": list(self.collision_identity_ids),
                    "reason_codes": list(self.reason_codes),
                    "provider_contract_version": self.provider_contract_version,
                }
            )
        ).hexdigest()
        if self.observation_id != f"psmo_{digest}":
            raise ValueError("observation_id does not match staging observation semantics")
        return self


class ProviderIdentityStateEvent(ProviderSecurityMasterStrictModel):
    state_event_id: SafeId
    provider_security_identity_id: SafeId
    source_version_id: SafeId
    identity_state: ProviderIdentityState
    staging_state: ProviderSecurityMasterState
    reason_code: ReasonCode
    provider_contract_version: ProviderSecurityMasterContractVersion

    @model_validator(mode="after")
    def validate_event_id(self) -> Self:
        digest = hashlib.sha256(
            canonical_json_bytes(
                {
                    "provider_security_identity_id": self.provider_security_identity_id,
                    "source_version_id": self.source_version_id,
                    "identity_state": self.identity_state.value,
                    "staging_state": self.staging_state.value,
                    "reason_code": self.reason_code,
                    "provider_contract_version": self.provider_contract_version,
                }
            )
        ).hexdigest()
        if self.state_event_id != f"pise_{digest}":
            raise ValueError("state_event_id does not match identity-state semantics")
        return self


class ProviderDetailBatchResult(ProviderSecurityMasterStrictModel):
    batch_result_id: SafeId
    source_version_id: SafeId
    requested_symbols: tuple[ProviderSymbol, ...]
    received_symbols: tuple[ProviderSymbol, ...]
    missing_symbols: tuple[ProviderSymbol, ...]
    requested_count: Annotated[int, Field(ge=1, le=200)]
    received_count: Annotated[int, Field(ge=0, le=200)]
    missing_count: Annotated[int, Field(ge=0, le=200)]
    status: ProviderDetailBatchStatus
    provider_contract_version: ProviderSecurityMasterContractVersion

    @model_validator(mode="after")
    def validate_counts_and_identity(self) -> Self:
        for values in (self.requested_symbols, self.received_symbols, self.missing_symbols):
            if tuple(sorted(set(values), key=lambda value: value.encode("ascii"))) != values:
                raise ValueError("detail batch symbol sets must be unique and ASCII sorted")
        requested = set(self.requested_symbols)
        received = set(self.received_symbols)
        missing = set(self.missing_symbols)
        if not received.issubset(requested) or missing != requested - received:
            raise ValueError("detail batch received/missing symbols do not reconcile")
        if (
            self.requested_count != len(requested)
            or self.received_count != len(received)
            or self.missing_count != len(missing)
        ):
            raise ValueError("detail batch counts do not match audited symbol sets")
        expected_status = (
            ProviderDetailBatchStatus.FAILED_EMPTY_RESPONSE
            if not received
            else (
                ProviderDetailBatchStatus.COMPLETE
                if not missing
                else ProviderDetailBatchStatus.PARTIAL
            )
        )
        if self.status != expected_status:
            raise ValueError("detail batch status does not match exact counts")
        digest = hashlib.sha256(
            canonical_json_bytes(
                {
                    "source_version_id": self.source_version_id,
                    "requested_symbols": list(self.requested_symbols),
                    "received_symbols": list(self.received_symbols),
                    "missing_symbols": list(self.missing_symbols),
                    "status": self.status.value,
                    "provider_contract_version": self.provider_contract_version,
                }
            )
        ).hexdigest()
        if self.batch_result_id != f"pdb_{digest}":
            raise ValueError("batch_result_id does not match detail reconciliation semantics")
        return self


def is_valid_isin(value: str) -> bool:
    if re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]", value) is None:
        return False
    expanded = "".join(
        str(ord(character) - 55) if character.isalpha() else character for character in value
    )
    total = 0
    parity = len(expanded) % 2
    for index, character in enumerate(expanded):
        digit = int(character)
        if index % 2 == parity:
            digit *= 2
        total += digit // 10 + digit % 10
    return total % 10 == 0


def security_master_record_hash(
    value: ProviderSecurityMasterRecord | dict[str, object],
) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)
    payload.pop("normalized_record_id", None)
    payload.pop("normalized_content_hash", None)
    return sha256_prefixed(canonical_json_bytes(_security_master_json_value(payload)))


def _security_master_json_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return decimal_to_string(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _security_master_json_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_security_master_json_value(item) for item in value]
    return value


def build_security_master_record(**values: object) -> ProviderSecurityMasterRecord:
    payload = {
        **values,
        "normalized_record_id": "psmr_pending",
        "normalized_content_hash": "sha256:" + "0" * 64,
        "provider_contract_version": PROVIDER_SECURITY_MASTER_CONTRACT_VERSION,
    }
    content_hash = security_master_record_hash(payload)
    payload["normalized_content_hash"] = content_hash
    payload["normalized_record_id"] = "psmr_" + content_hash.removeprefix("sha256:")
    return ProviderSecurityMasterRecord.model_validate(payload)


def build_security_master_observation(**values: object) -> ProviderSecurityMasterObservation:
    payload = {
        **values,
        "observation_id": "psmo_pending",
        "provider_contract_version": PROVIDER_SECURITY_MASTER_CONTRACT_VERSION,
    }
    collision_identity_ids = cast(tuple[str, ...], payload["collision_identity_ids"])
    reason_codes = cast(tuple[str, ...], payload["reason_codes"])
    digest = hashlib.sha256(
        canonical_json_bytes(
            {
                "source_version_id": payload["source_version_id"],
                "normalized_record_id": payload["normalized_record_id"],
                "provider_security_identity_id": payload["provider_security_identity_id"],
                "provider": _enum_value(payload["provider"]),
                "market": _enum_value(payload["market"]),
                "symbol": payload["symbol"],
                "staging_state": _enum_value(payload["staging_state"]),
                "reconciliation_outcome": _enum_value(payload["reconciliation_outcome"]),
                "identity_state_after": _optional_enum_value(payload["identity_state_after"]),
                "eligible_for_mapping": payload["eligible_for_mapping"],
                "collision_identity_ids": list(collision_identity_ids),
                "reason_codes": list(reason_codes),
                "provider_contract_version": PROVIDER_SECURITY_MASTER_CONTRACT_VERSION,
            }
        )
    ).hexdigest()
    payload["observation_id"] = f"psmo_{digest}"
    return ProviderSecurityMasterObservation.model_validate(payload)


def build_identity_state_event(**values: object) -> ProviderIdentityStateEvent:
    payload = {
        **values,
        "state_event_id": "pise_pending",
        "provider_contract_version": PROVIDER_SECURITY_MASTER_CONTRACT_VERSION,
    }
    digest = hashlib.sha256(
        canonical_json_bytes(
            {
                "provider_security_identity_id": payload["provider_security_identity_id"],
                "source_version_id": payload["source_version_id"],
                "identity_state": _enum_value(payload["identity_state"]),
                "staging_state": _enum_value(payload["staging_state"]),
                "reason_code": payload["reason_code"],
                "provider_contract_version": PROVIDER_SECURITY_MASTER_CONTRACT_VERSION,
            }
        )
    ).hexdigest()
    payload["state_event_id"] = f"pise_{digest}"
    return ProviderIdentityStateEvent.model_validate(payload)


def build_detail_batch_result(
    *, source_version_id: str, requested_symbols: tuple[str, ...], received_symbols: tuple[str, ...]
) -> ProviderDetailBatchResult:
    requested = tuple(sorted(set(requested_symbols), key=lambda value: value.encode("ascii")))
    received = tuple(sorted(set(received_symbols), key=lambda value: value.encode("ascii")))
    missing = tuple(sorted(set(requested) - set(received), key=lambda value: value.encode("ascii")))
    status = (
        ProviderDetailBatchStatus.FAILED_EMPTY_RESPONSE
        if not received
        else (
            ProviderDetailBatchStatus.COMPLETE if not missing else ProviderDetailBatchStatus.PARTIAL
        )
    )
    digest = hashlib.sha256(
        canonical_json_bytes(
            {
                "source_version_id": source_version_id,
                "requested_symbols": list(requested),
                "received_symbols": list(received),
                "missing_symbols": list(missing),
                "status": status.value,
                "provider_contract_version": PROVIDER_SECURITY_MASTER_CONTRACT_VERSION,
            }
        )
    ).hexdigest()
    return ProviderDetailBatchResult(
        batch_result_id=f"pdb_{digest}",
        source_version_id=source_version_id,
        requested_symbols=requested,
        received_symbols=received,
        missing_symbols=missing,
        requested_count=len(requested),
        received_count=len(received),
        missing_count=len(missing),
        status=status,
        provider_contract_version=PROVIDER_SECURITY_MASTER_CONTRACT_VERSION,
    )


def _enum_value(value: object) -> object:
    return value.value if hasattr(value, "value") else value


def _optional_enum_value(value: object) -> object:
    return None if value is None else _enum_value(value)
