from __future__ import annotations

import hashlib
from datetime import date
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

from toss_dashboard_api.contracts.base import NonEmptyText, SafeId, Sha256, UtcDatetime
from toss_dashboard_api.contracts.enums import (
    MappingStatus,
    Market,
    ProviderDataset,
    ProviderIdentifierKind,
    ProviderIdentifierReason,
    ProviderIdentityState,
    ProviderSystem,
)

ProviderIdentityContractVersion = Literal["toss-identity/0.1.0"]
PROVIDER_IDENTITY_CONTRACT_VERSION: ProviderIdentityContractVersion = "toss-identity/0.1.0"
IdentifierValue = Annotated[NonEmptyText, StringConstraints(max_length=128)]


class ProviderIdentityStrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)


def provider_identity_id_from_anchor(allocation_anchor: str) -> str:
    return f"tpsi_{hashlib.sha256(allocation_anchor.encode('utf-8')).hexdigest()}"


def provider_latest_pointer_id(dataset: ProviderDataset, identity_id: str) -> str:
    digest = hashlib.sha256(f"{dataset.value}|{identity_id}".encode()).hexdigest()
    return f"tlatest_{digest}"


class ProviderSecurityIdentity(ProviderIdentityStrictModel):
    provider_security_identity_id: SafeId
    provider: ProviderSystem
    market: Market
    allocation_anchor_hash: Sha256
    identity_state: ProviderIdentityState
    mapping_status: MappingStatus
    first_source_version_id: SafeId
    latest_source_version_id: SafeId
    provider_contract_version: ProviderIdentityContractVersion

    @model_validator(mode="after")
    def validate_foundation_state(self) -> Self:
        expected_id = f"tpsi_{self.allocation_anchor_hash.removeprefix('sha256:')}"
        if self.provider_security_identity_id != expected_id:
            raise ValueError("provider identity ID does not match immutable anchor hash")
        if self.mapping_status == MappingStatus.VERIFIED:
            raise ValueError("identity foundation cannot self-promote to VERIFIED")
        return self


class ProviderIdentifierHistory(ProviderIdentityStrictModel):
    identifier_history_id: SafeId
    provider_security_identity_id: SafeId
    identifier_kind: ProviderIdentifierKind
    identifier_value: IdentifierValue
    valid_from: date | None
    valid_to: date | None
    source_version_id: SafeId
    revision_reason: ProviderIdentifierReason
    provider_contract_version: ProviderIdentityContractVersion

    @model_validator(mode="after")
    def validate_validity(self) -> Self:
        if self.valid_from is not None and self.valid_to is not None:
            if self.valid_from > self.valid_to:
                raise ValueError("identifier valid_from cannot be after valid_to")
        return self


class ProviderIdentityMapping(ProviderIdentityStrictModel):
    mapping_id: SafeId
    provider_security_identity_id: SafeId
    issuer_id: SafeId | None
    security_id: SafeId | None
    mapping_status: MappingStatus
    evidence_source_version_id: SafeId
    approved_at: UtcDatetime | None
    valid_from: date | None
    valid_to: date | None
    provider_contract_version: ProviderIdentityContractVersion

    @model_validator(mode="after")
    def validate_mapping(self) -> Self:
        if self.mapping_status == MappingStatus.VERIFIED:
            if self.security_id is None or self.issuer_id is None or self.approved_at is None:
                raise ValueError("verified mapping requires issuer, security, and approval time")
        elif (
            self.security_id is not None
            or self.issuer_id is not None
            or self.approved_at is not None
        ):
            raise ValueError("unresolved mapping cannot contain canonical linkage or approval")
        if self.valid_from is not None and self.valid_to is not None:
            if self.valid_from > self.valid_to:
                raise ValueError("mapping valid_from cannot be after valid_to")
        return self


class ProviderLatestPointer(ProviderIdentityStrictModel):
    latest_pointer_id: SafeId
    dataset: ProviderDataset
    provider_security_identity_id: SafeId
    normalized_record_id: SafeId
    source_version_id: SafeId
    accepted_observed_at: UtcDatetime | None
    accepted_observed_date: date | None
    state_hash: Sha256
    provider_contract_version: ProviderIdentityContractVersion

    @model_validator(mode="after")
    def validate_pointer_identity(self) -> Self:
        expected = provider_latest_pointer_id(self.dataset, self.provider_security_identity_id)
        if self.latest_pointer_id != expected:
            raise ValueError("latest pointer ID does not match dataset and provider identity")
        return self
