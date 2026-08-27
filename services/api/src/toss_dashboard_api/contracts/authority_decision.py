from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum
from typing import Literal, Self

from pydantic import field_validator, model_validator

from toss_dashboard_api.contracts.authority import (
    AuthorityIdentifierKind,
    AuthorityReasonCode,
    AuthorityStrictModel,
    authority_candidate_fingerprint,
    authority_sha256,
    proposed_issuer_anchor,
)
from toss_dashboard_api.contracts.base import SafeId, Sha256
from toss_dashboard_api.contracts.enums import Jurisdiction

ISSUER_AUTHORITY_DECISION_ENGINE_CONTRACT_VERSION = "issuer-authority-decision-engine/0.1.0"
IssuerAuthorityDecisionEngineContractVersion = Literal["issuer-authority-decision-engine/0.1.0"]


class AuthorityBridgeStatus(StrEnum):
    ESTABLISHED = "ESTABLISHED"
    MISSING = "MISSING"
    CONFLICT = "CONFLICT"
    STALE = "STALE"
    UNUSABLE = "UNUSABLE"


class IssuerAuthorityEvaluationRequest(AuthorityStrictModel):
    contract_version: IssuerAuthorityDecisionEngineContractVersion
    provider_security_identity_id: SafeId
    provider_observation_ids: tuple[SafeId, ...]
    candidate_jurisdiction: Jurisdiction
    candidate_identifier_kind: AuthorityIdentifierKind
    candidate_identifier_value: str
    evidence_ids: tuple[SafeId, ...]

    @field_validator("provider_observation_ids", "evidence_ids")
    @classmethod
    def validate_sorted_ids(cls, value: tuple[str, ...], info: object) -> tuple[str, ...]:
        normalized = tuple(sorted(set(value), key=lambda item: item.encode("utf-8")))
        if len(normalized) != len(value) or normalized != value:
            field_name = getattr(info, "field_name", "IDs")
            raise ValueError(f"{field_name} must be sorted and unique")
        return value

    @model_validator(mode="after")
    def validate_candidate(self) -> Self:
        if not self.provider_observation_ids:
            raise ValueError("issuer authority evaluation requires provider observations")
        proposed_issuer_anchor(
            self.candidate_jurisdiction,
            self.candidate_identifier_kind,
            self.candidate_identifier_value,
        )
        return self


def build_issuer_authority_evaluation_request(
    *,
    provider_security_identity_id: SafeId,
    provider_observation_ids: Sequence[SafeId],
    candidate_jurisdiction: Jurisdiction,
    candidate_identifier_kind: AuthorityIdentifierKind,
    candidate_identifier_value: str,
    evidence_ids: Sequence[SafeId],
) -> IssuerAuthorityEvaluationRequest:
    return IssuerAuthorityEvaluationRequest.model_validate(
        {
            "contract_version": ISSUER_AUTHORITY_DECISION_ENGINE_CONTRACT_VERSION,
            "provider_security_identity_id": provider_security_identity_id,
            "provider_observation_ids": tuple(sorted(set(provider_observation_ids))),
            "candidate_jurisdiction": candidate_jurisdiction,
            "candidate_identifier_kind": candidate_identifier_kind,
            "candidate_identifier_value": candidate_identifier_value,
            "evidence_ids": tuple(sorted(set(evidence_ids))),
        }
    )


class AuthorityBridgeResult(AuthorityStrictModel):
    contract_version: IssuerAuthorityDecisionEngineContractVersion
    candidate_fingerprint: Sha256
    bridge_status: AuthorityBridgeStatus
    authority_evidence_ids: tuple[SafeId, ...]
    provider_observation_ids: tuple[SafeId, ...]
    reason_codes: tuple[AuthorityReasonCode, ...]
    bridge_content_hash: Sha256

    @field_validator("authority_evidence_ids", "provider_observation_ids", "reason_codes")
    @classmethod
    def validate_sorted_values(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(sorted(set(value), key=lambda item: item.encode("utf-8")))
        if normalized != value or len(normalized) != len(value):
            raise ValueError("bridge result values must be sorted and unique")
        return value

    @model_validator(mode="after")
    def validate_hash(self) -> Self:
        expected = authority_sha256(
            {
                "contract_version": self.contract_version,
                "candidate_fingerprint": self.candidate_fingerprint,
                "bridge_status": self.bridge_status,
                "authority_evidence_ids": self.authority_evidence_ids,
                "provider_observation_ids": self.provider_observation_ids,
                "reason_codes": self.reason_codes,
            }
        )
        if self.bridge_content_hash != expected:
            raise ValueError("bridge content hash does not match exact bridge semantics")
        return self


def build_authority_bridge_result(
    *,
    candidate_jurisdiction: Jurisdiction,
    candidate_identifier_kind: AuthorityIdentifierKind,
    candidate_identifier_value: str,
    bridge_status: AuthorityBridgeStatus,
    authority_evidence_ids: Sequence[SafeId],
    provider_observation_ids: Sequence[SafeId],
    reason_codes: Sequence[AuthorityReasonCode],
) -> AuthorityBridgeResult:
    values = {
        "contract_version": ISSUER_AUTHORITY_DECISION_ENGINE_CONTRACT_VERSION,
        "candidate_fingerprint": authority_candidate_fingerprint(
            jurisdiction=candidate_jurisdiction,
            identifier_kind=candidate_identifier_kind,
            identifier_value=candidate_identifier_value,
        ),
        "bridge_status": bridge_status,
        "authority_evidence_ids": tuple(sorted(set(authority_evidence_ids))),
        "provider_observation_ids": tuple(sorted(set(provider_observation_ids))),
        "reason_codes": tuple(sorted(set(reason_codes))),
    }
    return AuthorityBridgeResult.model_validate(
        {**values, "bridge_content_hash": authority_sha256(values)}
    )
