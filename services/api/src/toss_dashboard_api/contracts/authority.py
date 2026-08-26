from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from decimal import Decimal
from enum import Enum, StrEnum
from typing import Annotated, Any, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    NonNegativeInt,
    StringConstraints,
    field_validator,
    model_validator,
)

from toss_dashboard_api.contracts.base import SafeId, Sha256, UtcDatetime, utc_to_string
from toss_dashboard_api.contracts.enums import Jurisdiction

AUTHORITY_EVIDENCE_CONTRACT_VERSION = "issuer-authority-evidence/0.1.0"
AUTHORITY_EVIDENCE_OBSERVATION_CONTRACT_VERSION = "issuer-authority-evidence-observation/0.1.0"
AUTHORITY_EVIDENCE_RELATION_CONTRACT_VERSION = "issuer-authority-evidence-relation/0.1.0"
AUTHORITY_EVIDENCE_APPLICATION_CONTRACT_VERSION = "issuer-authority-evidence-application/0.1.0"
AUTHORITY_SOURCE_POLICY_CONTRACT_VERSION = "issuer-authority-source-policy/0.1.0"
AUTHORITY_BUNDLE_CONTRACT_VERSION = "issuer-authority-bundle/0.1.0"
AUTHORITY_IDENTIFIER_CLAIM_CONTRACT_VERSION = "issuer-authority-identifier-claim/0.1.0"
ISSUER_DECISION_CONTRACT_VERSION = "issuer-decision/0.1.0"
LOCAL_DATA_STEWARD_AUTHENTICATION_CONTRACT_VERSION = "issuer-steward-webauthn/0.1.0"
AUTHORITY_RULE_VERSION = "issuer-authority-rules/0.1.0"
AUTHORITY_SEMANTIC_ID_VERSION = "issuer-authority-id/1"

AuthorityEvidenceContractVersion = Literal["issuer-authority-evidence/0.1.0"]
AuthorityEvidenceObservationContractVersion = Literal["issuer-authority-evidence-observation/0.1.0"]
AuthorityEvidenceRelationContractVersion = Literal["issuer-authority-evidence-relation/0.1.0"]
AuthorityEvidenceApplicationContractVersion = Literal["issuer-authority-evidence-application/0.1.0"]
AuthoritySourcePolicyContractVersion = Literal["issuer-authority-source-policy/0.1.0"]
AuthorityBundleContractVersion = Literal["issuer-authority-bundle/0.1.0"]
AuthorityIdentifierClaimContractVersion = Literal["issuer-authority-identifier-claim/0.1.0"]
IssuerDecisionContractVersion = Literal["issuer-decision/0.1.0"]
LocalDataStewardAuthenticationContractVersion = Literal["issuer-steward-webauthn/0.1.0"]
AuthorityRuleVersion = Literal["issuer-authority-rules/0.1.0"]

AuthorityToken = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Z][A-Z0-9_.:-]{0,127}$", max_length=128),
]
AuthorityComponentVersion = Annotated[
    str,
    StringConstraints(
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}$",
        max_length=128,
    ),
]
AuthorityFieldPath = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Za-z][A-Za-z0-9_.\[\]:-]{0,255}$", max_length=256),
]
AuthorityReasonCode = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$", max_length=128),
]
AuthorityLocator = Annotated[str, StringConstraints(min_length=1, max_length=2048)]
AuthorityDocumentReference = Annotated[str, StringConstraints(min_length=1, max_length=512)]
AuthorityRawStorageReference = Annotated[
    str,
    StringConstraints(pattern=r"^authority-raw:sha256/[0-9a-f]{2}/[0-9a-f]{64}$"),
]


class AuthorityClassification(StrEnum):
    OFFICIAL_AUTHORITY = "OFFICIAL_AUTHORITY"
    SUPPORTING_EVIDENCE = "SUPPORTING_EVIDENCE"
    DISCOVERY_ONLY = "DISCOVERY_ONLY"
    UNSUITABLE_FOR_AUTOMATIC_PROMOTION = "UNSUITABLE_FOR_AUTOMATIC_PROMOTION"
    UNVERIFIED = "UNVERIFIED"


class AuthorityScope(StrEnum):
    ISSUER_REGULATORY_ID = "ISSUER_REGULATORY_ID"
    LEGAL_JURISDICTION = "LEGAL_JURISDICTION"
    LEGAL_ENTITY_BRIDGE = "LEGAL_ENTITY_BRIDGE"
    LEGAL_NAME = "LEGAL_NAME"
    REGISTRANT_ROLE = "REGISTRANT_ROLE"
    SUBMISSION_PROVENANCE = "SUBMISSION_PROVENANCE"


class AuthoritySubjectRole(StrEnum):
    DART_DISCLOSURE_FILER = "DART_DISCLOSURE_FILER"
    KOREAN_REGISTERED_LEGAL_ENTITY = "KOREAN_REGISTERED_LEGAL_ENTITY"
    US_STATE_REGISTERED_LEGAL_ENTITY = "US_STATE_REGISTERED_LEGAL_ENTITY"
    SEC_REGISTRANT = "SEC_REGISTRANT"
    SEC_LOGIN_CIK = "SEC_LOGIN_CIK"
    SEC_FILING_AGENT = "SEC_FILING_AGENT"
    LEGAL_ENTITY = "LEGAL_ENTITY"
    PROVIDER_OBSERVATION = "PROVIDER_OBSERVATION"


class AuthorityWeight(StrEnum):
    ZERO = "ZERO"
    SUPPORTING = "SUPPORTING"
    DECISIVE = "DECISIVE"


class AuthorityIngestionMode(StrEnum):
    AUTOMATED_OFFICIAL_PUBLIC = "AUTOMATED_OFFICIAL_PUBLIC"
    HUMAN_ASSISTED_VERIFIED_DOCUMENT = "HUMAN_ASSISTED_VERIFIED_DOCUMENT"
    PROVENANCE_ONLY = "PROVENANCE_ONLY"
    TEST_ISOLATED_ONLY = "TEST_ISOLATED_ONLY"


class AuthorityAccessDisposition(StrEnum):
    PERMITTED = "PERMITTED"
    RESTRICTED = "RESTRICTED"
    UNVERIFIED = "UNVERIFIED"


class AuthorityLicenseDisposition(StrEnum):
    PERMITTED = "PERMITTED"
    RESTRICTED = "RESTRICTED"
    UNVERIFIED = "UNVERIFIED"


class AuthorityOriginDataMode(StrEnum):
    PRODUCTION_AUTHORITY = "PRODUCTION_AUTHORITY"
    TEST_ONLY = "TEST_ONLY"


class AuthorityEvidenceKind(StrEnum):
    ASSERTION = "ASSERTION"
    CORRECTION = "CORRECTION"
    REVOCATION = "REVOCATION"
    PROVENANCE_ONLY = "PROVENANCE_ONLY"


class AuthorityEvidenceRelationType(StrEnum):
    CORRECTS = "CORRECTS"
    REVOKES = "REVOKES"
    SUPERSEDES = "SUPERSEDES"


class AuthorityEvidenceApplicationStatus(StrEnum):
    APPLIED_DECISIVE = "APPLIED_DECISIVE"
    APPLIED_SUPPORTING = "APPLIED_SUPPORTING"
    PROVENANCE_ONLY = "PROVENANCE_ONLY"
    REJECTED_CONFLICT = "REJECTED_CONFLICT"
    REJECTED_STALE = "REJECTED_STALE"
    REJECTED_UNUSABLE = "REJECTED_UNUSABLE"
    REJECTED_SOURCE_POLICY = "REJECTED_SOURCE_POLICY"
    REJECTED_SUBJECT_MISMATCH = "REJECTED_SUBJECT_MISMATCH"
    REJECTED_UNVERIFIABLE = "REJECTED_UNVERIFIABLE"


class AuthorityBundleScopeStatus(StrEnum):
    SATISFIED = "SATISFIED"
    MISSING = "MISSING"
    CONFLICT = "CONFLICT"
    STALE = "STALE"
    UNSUPPORTED = "UNSUPPORTED"
    UNUSABLE = "UNUSABLE"


class AuthorityLegalJurisdictionResult(StrEnum):
    ESTABLISHED = "ESTABLISHED"
    UNRESOLVED = "UNRESOLVED"
    UNSUPPORTED_BY_CONTRACT = "UNSUPPORTED_BY_CONTRACT"


class AuthorityCollisionScanResult(StrEnum):
    CLEAR = "CLEAR"
    CONFLICT = "CONFLICT"


class AuthorityIdentifierKind(StrEnum):
    DART_CORP_CODE = "DART_CORP_CODE"
    SEC_REGISTRANT_CIK = "SEC_REGISTRANT_CIK"


class AuthorityRetrievalStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    UNAVAILABLE = "UNAVAILABLE"


class AuthorityTimeMissingReason(StrEnum):
    NOT_SUPPLIED_BY_AUTHORITY = "NOT_SUPPLIED_BY_AUTHORITY"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNAVAILABLE = "UNAVAILABLE"


class IssuerMachineDecisionState(StrEnum):
    UNRESOLVED = "UNRESOLVED"
    READY_FOR_MANUAL_REVIEW = "READY_FOR_MANUAL_REVIEW"
    STALE = "STALE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class AuthorityFreshnessResult(StrEnum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"


class ReviewerPrincipalRole(StrEnum):
    LOCAL_DATA_STEWARD = "LOCAL_DATA_STEWARD"


class ReviewerPrincipalState(StrEnum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"


class ReviewerCredentialEventType(StrEnum):
    REGISTERED = "REGISTERED"
    REVOKED = "REVOKED"
    SUPERSEDED = "SUPERSEDED"


class IssuerApprovalDisposition(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REVOKED = "REVOKED"
    SUPERSEDED = "SUPERSEDED"


class IssuerApprovalChallengeResult(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    EXPIRED = "EXPIRED"
    INVALID_SIGNATURE = "INVALID_SIGNATURE"
    USER_VERIFICATION_ABSENT = "USER_VERIFICATION_ABSENT"
    ORIGIN_RP_MISMATCH = "ORIGIN_RP_MISMATCH"
    BINDING_MISMATCH = "BINDING_MISMATCH"
    REPLAY_REJECTED = "REPLAY_REJECTED"
    FAILED_CLOSED = "FAILED_CLOSED"


class ReviewerAuthenticationResult(StrEnum):
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class ReviewerWebauthnCounterCapability(StrEnum):
    SIGN_COUNT_SUPPORTED = "SIGN_COUNT_SUPPORTED"
    NO_USABLE_COUNTER = "NO_USABLE_COUNTER"


class IssuerAuthorityLinkState(StrEnum):
    APPROVED = "APPROVED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REVOKED = "REVOKED"
    SUPERSEDED = "SUPERSEDED"


_WEIGHT_RANK = {
    AuthorityWeight.ZERO: 0,
    AuthorityWeight.SUPPORTING: 1,
    AuthorityWeight.DECISIVE: 2,
}
_FIXTURE_SOURCE_NAMES = {
    "FIXTURE_KR_REGULATOR",
    "FIXTURE_US_REGULATOR",
    "FIXTURE_MARKET",
}
_AUTHORITY_TIME_FIELDS = (
    "authority_published_at",
    "authority_accepted_at",
    "authority_as_of_date",
    "authority_effective_at",
    "authority_effective_date",
)


def _nfc_value(value: Any) -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, Mapping):
        return {_nfc_value(key): _nfc_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(_nfc_value(item) for item in value)
    if isinstance(value, list):
        return [_nfc_value(item) for item in value]
    return value


def _authority_json_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return _authority_json_value(value.model_dump(mode="python"))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("authority timestamp must include a timezone")
        return utc_to_string(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal | float):
        raise ValueError("authority semantic JSON forbids binary float and Decimal")
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("authority semantic JSON object keys must be strings")
            normalized[unicodedata.normalize("NFC", key)] = _authority_json_value(item)
        return normalized
    if isinstance(value, tuple | list):
        return [_authority_json_value(item) for item in value]
    if value is None or isinstance(value, bool | int):
        return value
    raise ValueError(f"unsupported authority semantic value: {type(value).__name__}")


def canonical_authority_json_bytes(value: Any) -> bytes:
    return json.dumps(
        _authority_json_value(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def authority_sha256(value: Any) -> str:
    return f"sha256:{hashlib.sha256(canonical_authority_json_bytes(value)).hexdigest()}"


def authority_semantic_id(prefix: str, value: Any) -> str:
    if re.fullmatch(r"[a-z][a-z0-9]*_", prefix) is None:
        raise ValueError("authority ID prefix is invalid")
    return prefix + authority_sha256(value).removeprefix("sha256:")


def _sorted_unique_text(values: Sequence[str], *, field_name: str) -> tuple[str, ...]:
    normalized = tuple(
        sorted(
            {unicodedata.normalize("NFC", value) for value in values},
            key=lambda item: item.encode("utf-8"),
        )
    )
    if len(normalized) != len(values):
        raise ValueError(f"{field_name} must be unique")
    return normalized


def _sorted_unique_enums[EnumT: Enum](
    values: Sequence[EnumT], *, field_name: str
) -> tuple[EnumT, ...]:
    normalized = tuple(sorted(set(values), key=lambda item: str(item.value).encode("ascii")))
    if len(normalized) != len(values):
        raise ValueError(f"{field_name} must be unique")
    return normalized


def _validate_claim_value(value: Any, *, field_name: str) -> Any:
    if value is None:
        raise ValueError(f"{field_name} is required independently of the document hash")
    normalized = _nfc_value(value)
    canonical_authority_json_bytes(normalized)
    if isinstance(normalized, str) and not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def _validate_authority_locator(value: str) -> str:
    if (
        value.startswith("https://")
        or value.startswith("authority-verification://")
        or value.startswith("fixture://")
    ):
        return value
    raise ValueError("authority locator must be HTTPS, approved verification, or test fixture")


class AuthorityStrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        validate_assignment=True,
        frozen=True,
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_unicode(cls, value: Any) -> Any:
        return _nfc_value(value)


class ReviewerAuthenticationCounterAudit(AuthorityStrictModel):
    """Non-secret append-only signature-counter audit projection."""

    authentication_event_id: SafeId
    contract_version: LocalDataStewardAuthenticationContractVersion
    counter_capability: ReviewerWebauthnCounterCapability
    previous_sign_count: NonNegativeInt | None
    asserted_sign_count: NonNegativeInt | None
    counter_verified: bool
    authentication_result: ReviewerAuthenticationResult
    authenticated_at: UtcDatetime

    @model_validator(mode="after")
    def validate_counter_relation(self) -> Self:
        if self.counter_capability == ReviewerWebauthnCounterCapability.SIGN_COUNT_SUPPORTED:
            if self.previous_sign_count is None or self.asserted_sign_count is None:
                raise ValueError("counter-capable authentication requires both sign counts")
            if self.counter_verified and self.asserted_sign_count <= self.previous_sign_count:
                raise ValueError("verified signature counter must strictly advance")
        elif self.previous_sign_count is not None or self.asserted_sign_count is not None:
            raise ValueError("no-counter authentication must not fabricate sign counts")
        if (
            self.authentication_result == ReviewerAuthenticationResult.VERIFIED
            and not self.counter_verified
        ):
            raise ValueError("verified authentication requires counter policy verification")
        return self


def reconstruct_current_webauthn_sign_count(
    *,
    counter_capability: ReviewerWebauthnCounterCapability,
    registration_sign_count: int | None,
    authentication_events: Sequence[ReviewerAuthenticationCounterAudit],
) -> int | None:
    """Rebuild the current counter from immutable registration and event history."""

    events = tuple(authentication_events)
    if any(event.counter_capability != counter_capability for event in events):
        raise ValueError("authentication counter capability conflicts with credential")
    if counter_capability == ReviewerWebauthnCounterCapability.NO_USABLE_COUNTER:
        if registration_sign_count is not None:
            raise ValueError("no-counter credential must not have a registration sign count")
        return None
    if (
        registration_sign_count is None
        or isinstance(registration_sign_count, bool)
        or registration_sign_count < 0
    ):
        raise ValueError("counter-capable credential requires a non-negative registration count")

    pending = [
        event
        for event in events
        if event.authentication_result == ReviewerAuthenticationResult.VERIFIED
        and event.counter_verified
    ]
    current = registration_sign_count
    while pending:
        successors = [event for event in pending if event.previous_sign_count == current]
        if len(successors) != 1:
            raise ValueError("verified signature-counter history is forked or discontinuous")
        successor = successors[0]
        if successor.asserted_sign_count is None or successor.asserted_sign_count <= current:
            raise ValueError("verified signature counter must strictly advance")
        current = successor.asserted_sign_count
        pending.remove(successor)
    return current


class AuthorityScopeRoleWeight(AuthorityStrictModel):
    authority_scope: AuthorityScope
    subject_role: AuthoritySubjectRole
    maximum_weight: AuthorityWeight


def _policy_semantics(values: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "contract_version": values["contract_version"],
        "source_namespace": values["source_namespace"],
        "field_owner": values["field_owner"],
        "authority_classification": values["authority_classification"],
        "allowed_document_kinds": values["allowed_document_kinds"],
        "credential_free_locator_roots": values["credential_free_locator_roots"],
        "allowed_authority_scopes": values["allowed_authority_scopes"],
        "allowed_subject_roles": values["allowed_subject_roles"],
        "scope_role_weights": values["scope_role_weights"],
        "maximum_issuer_authority_weight": values["maximum_issuer_authority_weight"],
        "ingestion_mode": values["ingestion_mode"],
        "admitted_adapter_contract_versions": values["admitted_adapter_contract_versions"],
        "admitted_parser_contract_versions": values["admitted_parser_contract_versions"],
        "production_authority_eligible": values["production_authority_eligible"],
        "required_access_disposition": values["required_access_disposition"],
        "required_license_disposition": values["required_license_disposition"],
        "allowed_origin_data_modes": values["allowed_origin_data_modes"],
        "permanent_fixture_test_taint": values["permanent_fixture_test_taint"],
        "predecessor_policy_id": values["predecessor_policy_id"],
        "policy_effective_at": values["policy_effective_at"],
    }


class AuthoritySourcePolicy(AuthorityStrictModel):
    authority_source_policy_id: SafeId
    contract_version: AuthoritySourcePolicyContractVersion
    policy_content_hash: Sha256
    source_namespace: AuthorityToken
    field_owner: Annotated[str, StringConstraints(min_length=1, max_length=256)]
    authority_classification: AuthorityClassification
    allowed_document_kinds: tuple[AuthorityToken, ...]
    credential_free_locator_roots: tuple[AuthorityLocator, ...]
    allowed_authority_scopes: tuple[AuthorityScope, ...]
    allowed_subject_roles: tuple[AuthoritySubjectRole, ...]
    scope_role_weights: tuple[AuthorityScopeRoleWeight, ...]
    maximum_issuer_authority_weight: AuthorityWeight
    ingestion_mode: AuthorityIngestionMode
    admitted_adapter_contract_versions: tuple[AuthorityComponentVersion, ...]
    admitted_parser_contract_versions: tuple[AuthorityComponentVersion, ...]
    production_authority_eligible: bool
    required_access_disposition: AuthorityAccessDisposition
    required_license_disposition: AuthorityLicenseDisposition
    allowed_origin_data_modes: tuple[AuthorityOriginDataMode, ...]
    permanent_fixture_test_taint: bool
    predecessor_policy_id: SafeId | None
    policy_effective_at: UtcDatetime | None
    registered_at: UtcDatetime

    @field_validator(
        "allowed_document_kinds",
        "credential_free_locator_roots",
        "admitted_adapter_contract_versions",
        "admitted_parser_contract_versions",
    )
    @classmethod
    def validate_sorted_text_tuple(cls, value: tuple[str, ...], info: Any) -> tuple[str, ...]:
        if not value:
            raise ValueError(f"{info.field_name} must not be empty")
        return _sorted_unique_text(value, field_name=str(info.field_name))

    @field_validator(
        "allowed_authority_scopes",
        "allowed_subject_roles",
        "allowed_origin_data_modes",
    )
    @classmethod
    def validate_sorted_enum_tuple(cls, value: tuple[Enum, ...], info: Any) -> tuple[Enum, ...]:
        if not value:
            raise ValueError(f"{info.field_name} must not be empty")
        return _sorted_unique_enums(value, field_name=str(info.field_name))

    @field_validator("credential_free_locator_roots")
    @classmethod
    def validate_locator_roots(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        for root in value:
            _validate_authority_locator(root)
        return value

    @model_validator(mode="after")
    def validate_policy(self) -> Self:
        ordered_rules = tuple(
            sorted(
                self.scope_role_weights,
                key=lambda item: (
                    item.authority_scope.value.encode("ascii"),
                    item.subject_role.value.encode("ascii"),
                ),
            )
        )
        if self.scope_role_weights != ordered_rules:
            raise ValueError("scope_role_weights must be sorted")
        rule_keys = {(item.authority_scope, item.subject_role) for item in ordered_rules}
        if len(rule_keys) != len(ordered_rules):
            raise ValueError("scope_role_weights must contain unique scope/role pairs")
        if {item.authority_scope for item in ordered_rules} - set(self.allowed_authority_scopes):
            raise ValueError("scope_role_weights contain a scope outside the allowed set")
        if {item.subject_role for item in ordered_rules} - set(self.allowed_subject_roles):
            raise ValueError("scope_role_weights contain a role outside the allowed set")
        expected_maximum = max(
            (item.maximum_weight for item in ordered_rules),
            key=lambda item: _WEIGHT_RANK[item],
            default=AuthorityWeight.ZERO,
        )
        if self.maximum_issuer_authority_weight != expected_maximum:
            raise ValueError("policy maximum weight does not match its exact matrix")
        fixture_namespace = (
            self.source_namespace in _FIXTURE_SOURCE_NAMES
            or self.source_namespace.startswith("FIXTURE_")
            or self.source_namespace.startswith("TEST_")
        )
        if fixture_namespace and not self.permanent_fixture_test_taint:
            raise ValueError("fixture/test namespace must retain permanent taint")
        if self.permanent_fixture_test_taint:
            if self.production_authority_eligible:
                raise ValueError("fixture/test-tainted policy cannot be production eligible")
            if self.ingestion_mode != AuthorityIngestionMode.TEST_ISOLATED_ONLY:
                raise ValueError("fixture/test-tainted policy must be test isolated")
            if any(item.maximum_weight != AuthorityWeight.ZERO for item in self.scope_role_weights):
                raise ValueError("fixture/test-tainted policy must have zero authority weight")
        if self.production_authority_eligible:
            if "*" in self.source_namespace or "?" in self.source_namespace:
                raise ValueError("production source namespace cannot contain a wildcard")
            if AuthorityOriginDataMode.TEST_ONLY in self.allowed_origin_data_modes:
                raise ValueError("production source policy cannot admit test-only lineage")
            if self.ingestion_mode == AuthorityIngestionMode.TEST_ISOLATED_ONLY:
                raise ValueError("production source policy cannot use test ingestion")
            if any(root.startswith("fixture://") for root in self.credential_free_locator_roots):
                raise ValueError("production source policy cannot admit fixture locators")
            if self.required_access_disposition != AuthorityAccessDisposition.PERMITTED:
                raise ValueError("production source policy requires permitted access")
            if self.required_license_disposition != AuthorityLicenseDisposition.PERMITTED:
                raise ValueError("production source policy requires permitted license use")
        if self.predecessor_policy_id == self.authority_source_policy_id:
            raise ValueError("source policy cannot supersede itself")
        expected_hash = authority_sha256(_policy_semantics(self.model_dump(mode="python")))
        if self.policy_content_hash != expected_hash:
            raise ValueError("policy_content_hash does not match policy semantics")
        expected_id = "aspol_" + expected_hash.removeprefix("sha256:")
        if self.authority_source_policy_id != expected_id:
            raise ValueError("authority_source_policy_id does not match policy semantics")
        return self

    def maximum_weight_for(
        self, scope: AuthorityScope, subject_role: AuthoritySubjectRole
    ) -> AuthorityWeight:
        for rule in self.scope_role_weights:
            if rule.authority_scope == scope and rule.subject_role == subject_role:
                return rule.maximum_weight
        return AuthorityWeight.ZERO


def build_authority_source_policy(
    *,
    source_namespace: AuthorityToken,
    field_owner: str,
    authority_classification: AuthorityClassification,
    allowed_document_kinds: Sequence[AuthorityToken],
    credential_free_locator_roots: Sequence[AuthorityLocator],
    scope_role_weights: Sequence[AuthorityScopeRoleWeight],
    ingestion_mode: AuthorityIngestionMode,
    admitted_adapter_contract_versions: Sequence[AuthorityComponentVersion],
    admitted_parser_contract_versions: Sequence[AuthorityComponentVersion],
    production_authority_eligible: bool,
    required_access_disposition: AuthorityAccessDisposition,
    required_license_disposition: AuthorityLicenseDisposition,
    allowed_origin_data_modes: Sequence[AuthorityOriginDataMode],
    permanent_fixture_test_taint: bool,
    registered_at: UtcDatetime,
    predecessor_policy_id: SafeId | None = None,
    policy_effective_at: UtcDatetime | None = None,
) -> AuthoritySourcePolicy:
    rules = tuple(
        sorted(
            scope_role_weights,
            key=lambda item: (
                item.authority_scope.value.encode("ascii"),
                item.subject_role.value.encode("ascii"),
            ),
        )
    )
    maximum = max(
        (item.maximum_weight for item in rules),
        key=lambda item: _WEIGHT_RANK[item],
        default=AuthorityWeight.ZERO,
    )
    values: dict[str, Any] = {
        "contract_version": AUTHORITY_SOURCE_POLICY_CONTRACT_VERSION,
        "source_namespace": source_namespace,
        "field_owner": field_owner,
        "authority_classification": authority_classification,
        "allowed_document_kinds": _sorted_unique_text(
            allowed_document_kinds, field_name="allowed_document_kinds"
        ),
        "credential_free_locator_roots": _sorted_unique_text(
            credential_free_locator_roots, field_name="credential_free_locator_roots"
        ),
        "allowed_authority_scopes": _sorted_unique_enums(
            tuple({item.authority_scope for item in rules}),
            field_name="allowed_authority_scopes",
        ),
        "allowed_subject_roles": _sorted_unique_enums(
            tuple({item.subject_role for item in rules}),
            field_name="allowed_subject_roles",
        ),
        "scope_role_weights": rules,
        "maximum_issuer_authority_weight": maximum,
        "ingestion_mode": ingestion_mode,
        "admitted_adapter_contract_versions": _sorted_unique_text(
            admitted_adapter_contract_versions,
            field_name="admitted_adapter_contract_versions",
        ),
        "admitted_parser_contract_versions": _sorted_unique_text(
            admitted_parser_contract_versions,
            field_name="admitted_parser_contract_versions",
        ),
        "production_authority_eligible": production_authority_eligible,
        "required_access_disposition": required_access_disposition,
        "required_license_disposition": required_license_disposition,
        "allowed_origin_data_modes": _sorted_unique_enums(
            allowed_origin_data_modes, field_name="allowed_origin_data_modes"
        ),
        "permanent_fixture_test_taint": permanent_fixture_test_taint,
        "predecessor_policy_id": predecessor_policy_id,
        "policy_effective_at": policy_effective_at,
        "registered_at": registered_at,
    }
    content_hash = authority_sha256(_policy_semantics(values))
    return AuthoritySourcePolicy.model_validate(
        {
            **values,
            "authority_source_policy_id": ("aspol_" + content_hash.removeprefix("sha256:")),
            "policy_content_hash": content_hash,
        }
    )


def authority_source_document_id(
    *,
    authority_source_identifier: str,
    authority_external_key: str,
    raw_content_hash: str,
) -> str:
    return authority_semantic_id(
        "adoc_",
        {
            "authority_source_identifier": authority_source_identifier,
            "authority_external_key": authority_external_key,
            "raw_content_hash": raw_content_hash,
        },
    )


def _evidence_semantics(values: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "contract_version": values["contract_version"],
        "authority_source_policy_id": values["authority_source_policy_id"],
        "authority_source_identifier": values["authority_source_identifier"],
        "authority_classification": values["authority_classification"],
        "authority_document_reference": values["authority_document_reference"],
        "source_document_kind": values["source_document_kind"],
        "authority_external_key": values["authority_external_key"],
        "authority_source_document_id": values["authority_source_document_id"],
        "raw_content_hash": values["raw_content_hash"],
        "parser_contract_version": values["parser_contract_version"],
        "evidence_kind": values["evidence_kind"],
        "authority_scope": values["authority_scope"],
        "subject_role": values["subject_role"],
        "policy_maximum_issuer_authority_weight": values["policy_maximum_issuer_authority_weight"],
        "claim_field": values["claim_field"],
        "raw_claim_value": values["raw_claim_value"],
        "normalized_claim_value": values["normalized_claim_value"],
        "authority_published_at": values["authority_published_at"],
        "authority_accepted_at": values["authority_accepted_at"],
        "authority_as_of_date": values["authority_as_of_date"],
        "authority_effective_at": values["authority_effective_at"],
        "authority_effective_date": values["authority_effective_date"],
        "authority_time_missing_reasons": values["authority_time_missing_reasons"],
        "access_disposition": values["access_disposition"],
        "license_disposition": values["license_disposition"],
        "origin_data_mode": values["origin_data_mode"],
        "origin_adapter_class": values["origin_adapter_class"],
        "origin_source_system": values["origin_source_system"],
        "lineage_tainted": values["lineage_tainted"],
        "lineage_ancestor_tainted": values["lineage_ancestor_tainted"],
        "lineage_ancestor_hashes": values["lineage_ancestor_hashes"],
    }


def _evidence_provenance(values: Mapping[str, Any]) -> dict[str, Any]:
    return {
        **_evidence_semantics(values),
        "authority_source_locator": values["authority_source_locator"],
    }


class AuthorityEvidence(AuthorityStrictModel):
    evidence_id: SafeId
    contract_version: AuthorityEvidenceContractVersion
    evidence_content_hash: Sha256
    evidence_provenance_hash: Sha256
    authority_source_policy_id: SafeId
    authority_source_identifier: AuthorityToken
    authority_classification: AuthorityClassification
    authority_source_locator: AuthorityLocator
    authority_document_reference: AuthorityDocumentReference
    source_document_kind: AuthorityToken
    authority_external_key: Annotated[str, StringConstraints(min_length=1, max_length=512)]
    authority_source_document_id: SafeId
    raw_content_hash: Sha256
    parser_contract_version: AuthorityComponentVersion
    evidence_kind: AuthorityEvidenceKind
    authority_scope: AuthorityScope
    subject_role: AuthoritySubjectRole
    policy_maximum_issuer_authority_weight: AuthorityWeight
    claim_field: AuthorityFieldPath
    raw_claim_value: Any
    normalized_claim_value: Any
    authority_published_at: UtcDatetime | None
    authority_accepted_at: UtcDatetime | None
    authority_as_of_date: date | None
    authority_effective_at: UtcDatetime | None
    authority_effective_date: date | None
    authority_time_missing_reasons: dict[str, AuthorityTimeMissingReason]
    access_disposition: AuthorityAccessDisposition
    license_disposition: AuthorityLicenseDisposition
    origin_data_mode: AuthorityOriginDataMode
    origin_adapter_class: AuthorityComponentVersion
    origin_source_system: AuthorityToken | None
    lineage_tainted: bool
    lineage_ancestor_tainted: bool
    lineage_ancestor_hashes: tuple[Sha256, ...]

    @field_validator("authority_source_locator")
    @classmethod
    def validate_locator(cls, value: str) -> str:
        return _validate_authority_locator(value)

    @field_validator("raw_claim_value")
    @classmethod
    def validate_raw_claim(cls, value: Any) -> Any:
        return _validate_claim_value(value, field_name="raw_claim_value")

    @field_validator("normalized_claim_value")
    @classmethod
    def validate_normalized_claim(cls, value: Any) -> Any:
        return _validate_claim_value(value, field_name="normalized_claim_value")

    @field_validator("lineage_ancestor_hashes")
    @classmethod
    def validate_lineage_hashes(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _sorted_unique_text(value, field_name="lineage_ancestor_hashes")

    @field_validator("authority_time_missing_reasons")
    @classmethod
    def validate_time_reason_keys(
        cls, value: dict[str, AuthorityTimeMissingReason]
    ) -> dict[str, AuthorityTimeMissingReason]:
        if set(value) - set(_AUTHORITY_TIME_FIELDS):
            raise ValueError("authority time missing reasons contain an unknown field")
        return dict(sorted(value.items()))

    @model_validator(mode="after")
    def validate_evidence(self) -> Self:
        for field_name in _AUTHORITY_TIME_FIELDS:
            field_value = getattr(self, field_name)
            if field_value is None and field_name not in self.authority_time_missing_reasons:
                raise ValueError(f"authority_time_missing_reasons.{field_name} is required")
            if field_value is not None and field_name in self.authority_time_missing_reasons:
                raise ValueError(
                    f"authority_time_missing_reasons.{field_name} is only allowed when null"
                )
        if self.authority_effective_at is not None and self.authority_effective_date is not None:
            raise ValueError("authority effective time and date cannot both be populated")
        expected_document_id = authority_source_document_id(
            authority_source_identifier=self.authority_source_identifier,
            authority_external_key=self.authority_external_key,
            raw_content_hash=self.raw_content_hash,
        )
        if self.authority_source_document_id != expected_document_id:
            raise ValueError("authority_source_document_id does not match source semantics")
        fixture_source = self.origin_source_system in _FIXTURE_SOURCE_NAMES or (
            self.origin_source_system is not None
            and (
                self.origin_source_system.startswith("FIXTURE_")
                or self.origin_source_system.startswith("TEST_")
            )
        )
        if (
            self.origin_data_mode == AuthorityOriginDataMode.TEST_ONLY
            or fixture_source
            or self.lineage_ancestor_tainted
        ) and not self.lineage_tainted:
            raise ValueError("fixture/test/synthetic lineage taint cannot be cleared")
        if self.lineage_tainted and (
            self.policy_maximum_issuer_authority_weight != AuthorityWeight.ZERO
        ):
            raise ValueError("tainted evidence must have zero issuer-authority weight")
        if self.origin_data_mode == AuthorityOriginDataMode.PRODUCTION_AUTHORITY and (
            self.authority_source_locator.startswith("fixture://")
        ):
            raise ValueError("production authority evidence cannot use a fixture locator")
        provenance_roles = {
            AuthoritySubjectRole.SEC_LOGIN_CIK,
            AuthoritySubjectRole.SEC_FILING_AGENT,
        }
        if self.subject_role in provenance_roles:
            if (
                self.authority_scope != AuthorityScope.SUBMISSION_PROVENANCE
                or self.evidence_kind != AuthorityEvidenceKind.PROVENANCE_ONLY
                or self.policy_maximum_issuer_authority_weight != AuthorityWeight.ZERO
            ):
                raise ValueError("login/filing-agent CIK must remain zero-weight provenance")
        expected_content_hash = authority_sha256(
            _evidence_semantics(self.model_dump(mode="python"))
        )
        if self.evidence_content_hash != expected_content_hash:
            raise ValueError("evidence_content_hash does not match evidence semantics")
        if self.evidence_id != ("aev_" + expected_content_hash.removeprefix("sha256:")):
            raise ValueError("evidence_id does not match evidence semantics")
        expected_provenance_hash = authority_sha256(
            _evidence_provenance(self.model_dump(mode="python"))
        )
        if self.evidence_provenance_hash != expected_provenance_hash:
            raise ValueError("evidence_provenance_hash does not match immutable provenance")
        return self


def build_authority_evidence(**values: Any) -> AuthorityEvidence:
    forbidden = {"evidence_id", "evidence_content_hash", "evidence_provenance_hash"}
    if forbidden.intersection(values):
        raise ValueError("computed evidence identity fields cannot be supplied")
    raw_claim = _validate_claim_value(values["raw_claim_value"], field_name="raw_claim_value")
    normalized_claim = _validate_claim_value(
        values["normalized_claim_value"], field_name="normalized_claim_value"
    )
    lineage_hashes = _sorted_unique_text(
        tuple(values.get("lineage_ancestor_hashes", ())),
        field_name="lineage_ancestor_hashes",
    )
    base: dict[str, Any] = {
        **values,
        "contract_version": AUTHORITY_EVIDENCE_CONTRACT_VERSION,
        "raw_claim_value": raw_claim,
        "normalized_claim_value": normalized_claim,
        "lineage_ancestor_hashes": lineage_hashes,
    }
    base["authority_source_document_id"] = authority_source_document_id(
        authority_source_identifier=str(base["authority_source_identifier"]),
        authority_external_key=str(base["authority_external_key"]),
        raw_content_hash=str(base["raw_content_hash"]),
    )
    content_hash = authority_sha256(_evidence_semantics(base))
    base["evidence_content_hash"] = content_hash
    base["evidence_id"] = "aev_" + content_hash.removeprefix("sha256:")
    base["evidence_provenance_hash"] = authority_sha256(_evidence_provenance(base))
    return AuthorityEvidence.model_validate(base)


def _observation_semantics(values: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "contract_version": values["contract_version"],
        "evidence_id": values["evidence_id"],
        "fetched_at": values["fetched_at"],
        "raw_content_hash": values["raw_content_hash"],
        "authority_source_locator": values["authority_source_locator"],
        "authority_document_reference": values["authority_document_reference"],
        "raw_storage_reference": values["raw_storage_reference"],
        "retrieval_status": values["retrieval_status"],
        "secret_free_retrieval_fingerprint": values["secret_free_retrieval_fingerprint"],
        "safe_status_code": values["safe_status_code"],
    }


class AuthorityEvidenceObservation(AuthorityStrictModel):
    authority_evidence_observation_id: SafeId
    contract_version: AuthorityEvidenceObservationContractVersion
    observation_content_hash: Sha256
    evidence_id: SafeId
    fetched_at: UtcDatetime
    raw_content_hash: Sha256
    authority_source_locator: AuthorityLocator
    authority_document_reference: AuthorityDocumentReference
    raw_storage_reference: AuthorityRawStorageReference
    retrieval_status: AuthorityRetrievalStatus
    secret_free_retrieval_fingerprint: Sha256
    safe_status_code: AuthorityReasonCode

    @field_validator("authority_source_locator")
    @classmethod
    def validate_locator(cls, value: str) -> str:
        return _validate_authority_locator(value)

    @model_validator(mode="after")
    def validate_observation(self) -> Self:
        expected_hash = authority_sha256(_observation_semantics(self.model_dump(mode="python")))
        if self.observation_content_hash != expected_hash:
            raise ValueError("observation_content_hash does not match retrieval audit")
        if self.authority_evidence_observation_id != (
            "aeobs_" + expected_hash.removeprefix("sha256:")
        ):
            raise ValueError("authority evidence observation ID does not match audit")
        raw_digest = self.raw_content_hash.removeprefix("sha256:")
        expected_ref = f"authority-raw:sha256/{raw_digest[:2]}/{raw_digest}"
        if self.raw_storage_reference != expected_ref:
            raise ValueError("raw storage reference does not match raw content hash")
        return self


def build_authority_evidence_observation(
    *,
    evidence_id: SafeId,
    fetched_at: UtcDatetime,
    raw_content_hash: Sha256,
    authority_source_locator: AuthorityLocator,
    authority_document_reference: AuthorityDocumentReference,
    retrieval_status: AuthorityRetrievalStatus,
    secret_free_retrieval_fingerprint: Sha256,
    safe_status_code: AuthorityReasonCode,
) -> AuthorityEvidenceObservation:
    digest = raw_content_hash.removeprefix("sha256:")
    values: dict[str, Any] = {
        "contract_version": AUTHORITY_EVIDENCE_OBSERVATION_CONTRACT_VERSION,
        "evidence_id": evidence_id,
        "fetched_at": fetched_at,
        "raw_content_hash": raw_content_hash,
        "authority_source_locator": authority_source_locator,
        "authority_document_reference": authority_document_reference,
        "raw_storage_reference": f"authority-raw:sha256/{digest[:2]}/{digest}",
        "retrieval_status": retrieval_status,
        "secret_free_retrieval_fingerprint": secret_free_retrieval_fingerprint,
        "safe_status_code": safe_status_code,
    }
    content_hash = authority_sha256(_observation_semantics(values))
    return AuthorityEvidenceObservation.model_validate(
        {
            **values,
            "authority_evidence_observation_id": ("aeobs_" + content_hash.removeprefix("sha256:")),
            "observation_content_hash": content_hash,
        }
    )


def _relation_semantics(values: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "contract_version": values["contract_version"],
        "predecessor_evidence_id": values["predecessor_evidence_id"],
        "successor_evidence_id": values["successor_evidence_id"],
        "relation_type": values["relation_type"],
        "authority_effective_at": values["authority_effective_at"],
        "authority_effective_date": values["authority_effective_date"],
        "authority_effective_missing_reason": values["authority_effective_missing_reason"],
    }


class AuthorityEvidenceRelation(AuthorityStrictModel):
    authority_evidence_relation_id: SafeId
    contract_version: AuthorityEvidenceRelationContractVersion
    relation_content_hash: Sha256
    predecessor_evidence_id: SafeId
    successor_evidence_id: SafeId
    relation_type: AuthorityEvidenceRelationType
    authority_effective_at: UtcDatetime | None
    authority_effective_date: date | None
    authority_effective_missing_reason: AuthorityTimeMissingReason | None
    recorded_at: UtcDatetime

    @model_validator(mode="after")
    def validate_relation(self) -> Self:
        if self.predecessor_evidence_id == self.successor_evidence_id:
            raise ValueError("authority evidence cannot relate to itself")
        supplied = (
            self.authority_effective_at is not None or self.authority_effective_date is not None
        )
        if self.authority_effective_at is not None and self.authority_effective_date is not None:
            raise ValueError("relation effective time and date cannot both be populated")
        if supplied == (self.authority_effective_missing_reason is not None):
            raise ValueError("relation effective missing reason must exactly match absence")
        expected_hash = authority_sha256(_relation_semantics(self.model_dump(mode="python")))
        if self.relation_content_hash != expected_hash:
            raise ValueError("relation_content_hash does not match relation semantics")
        if self.authority_evidence_relation_id != ("aer_" + expected_hash.removeprefix("sha256:")):
            raise ValueError("authority evidence relation ID does not match semantics")
        return self


def build_authority_evidence_relation(
    *,
    predecessor_evidence_id: SafeId,
    successor_evidence_id: SafeId,
    relation_type: AuthorityEvidenceRelationType,
    recorded_at: UtcDatetime,
    authority_effective_at: UtcDatetime | None = None,
    authority_effective_date: date | None = None,
    authority_effective_missing_reason: AuthorityTimeMissingReason | None = None,
) -> AuthorityEvidenceRelation:
    values: dict[str, Any] = {
        "contract_version": AUTHORITY_EVIDENCE_RELATION_CONTRACT_VERSION,
        "predecessor_evidence_id": predecessor_evidence_id,
        "successor_evidence_id": successor_evidence_id,
        "relation_type": relation_type,
        "authority_effective_at": authority_effective_at,
        "authority_effective_date": authority_effective_date,
        "authority_effective_missing_reason": authority_effective_missing_reason,
        "recorded_at": recorded_at,
    }
    content_hash = authority_sha256(_relation_semantics(values))
    return AuthorityEvidenceRelation.model_validate(
        {
            **values,
            "authority_evidence_relation_id": ("aer_" + content_hash.removeprefix("sha256:")),
            "relation_content_hash": content_hash,
        }
    )


def proposed_issuer_anchor(
    jurisdiction: Jurisdiction,
    identifier_kind: AuthorityIdentifierKind,
    identifier_value: str,
) -> str:
    if jurisdiction == Jurisdiction.KR:
        if identifier_kind != AuthorityIdentifierKind.DART_CORP_CODE:
            raise ValueError("KR issuer anchor requires DART_CORP_CODE")
        if re.fullmatch(r"[0-9]{8}", identifier_value) is None:
            raise ValueError("DART corp_code must be exactly 8 digits")
    elif jurisdiction == Jurisdiction.US:
        if identifier_kind != AuthorityIdentifierKind.SEC_REGISTRANT_CIK:
            raise ValueError("US issuer anchor requires SEC_REGISTRANT_CIK")
        if re.fullmatch(r"[0-9]{10}", identifier_value) is None:
            raise ValueError("SEC registrant CIK must be zero-padded to 10 digits")
    else:
        raise ValueError("issuer authority contract supports only KR and US")
    normalized_value = unicodedata.normalize("NFC", identifier_value)
    return f"issuer-v1|{jurisdiction.value}|{identifier_kind.value}|{normalized_value}"


def proposed_issuer_id(anchor: str) -> str:
    normalized = unicodedata.normalize("NFC", anchor)
    return "issuer_" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def authority_candidate_fingerprint(
    *,
    jurisdiction: Jurisdiction,
    identifier_kind: AuthorityIdentifierKind,
    identifier_value: str,
) -> str:
    anchor = proposed_issuer_anchor(jurisdiction, identifier_kind, identifier_value)
    return authority_sha256(
        {
            "semantic_id_version": AUTHORITY_SEMANTIC_ID_VERSION,
            "proposed_issuer_anchor": anchor,
            "proposed_issuer_id": proposed_issuer_id(anchor),
        }
    )


def _application_semantics(values: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "contract_version": values["contract_version"],
        "evidence_id": values["evidence_id"],
        "evidence_content_hash": values["evidence_content_hash"],
        "provider_security_identity_id": values["provider_security_identity_id"],
        "provider_observation_ids": values["provider_observation_ids"],
        "proposed_issuer_id": values["proposed_issuer_id"],
        "candidate_fingerprint": values["candidate_fingerprint"],
        "authority_scope": values["authority_scope"],
        "claim_target_field": values["claim_target_field"],
        "authority_source_policy_id": values["authority_source_policy_id"],
        "authority_source_policy_content_hash": values["authority_source_policy_content_hash"],
        "policy_maximum_issuer_authority_weight": values["policy_maximum_issuer_authority_weight"],
        "application_status": values["application_status"],
        "effective_issuer_authority_weight": values["effective_issuer_authority_weight"],
        "reason_codes": values["reason_codes"],
        "authority_relation_head_hash": values["authority_relation_head_hash"],
        "application_rule_version": values["application_rule_version"],
        "production_authority_admitted": values["production_authority_admitted"],
        "lineage_tainted": values["lineage_tainted"],
    }


class AuthorityEvidenceApplication(AuthorityStrictModel):
    evidence_application_id: SafeId
    contract_version: AuthorityEvidenceApplicationContractVersion
    application_content_hash: Sha256
    evidence_id: SafeId
    evidence_content_hash: Sha256
    provider_security_identity_id: SafeId
    provider_observation_ids: tuple[SafeId, ...]
    proposed_issuer_id: SafeId
    candidate_fingerprint: Sha256
    authority_scope: AuthorityScope
    claim_target_field: AuthorityFieldPath
    authority_source_policy_id: SafeId
    authority_source_policy_content_hash: Sha256
    policy_maximum_issuer_authority_weight: AuthorityWeight
    application_status: AuthorityEvidenceApplicationStatus
    effective_issuer_authority_weight: AuthorityWeight
    reason_codes: tuple[AuthorityReasonCode, ...]
    authority_relation_head_hash: Sha256
    application_rule_version: AuthorityRuleVersion
    production_authority_admitted: bool
    lineage_tainted: bool
    evaluated_at: UtcDatetime

    @field_validator("provider_observation_ids", "reason_codes")
    @classmethod
    def validate_sorted_values(cls, value: tuple[str, ...], info: Any) -> tuple[str, ...]:
        return _sorted_unique_text(value, field_name=str(info.field_name))

    @model_validator(mode="after")
    def validate_application(self) -> Self:
        expected_weight = {
            AuthorityEvidenceApplicationStatus.APPLIED_DECISIVE: AuthorityWeight.DECISIVE,
            AuthorityEvidenceApplicationStatus.APPLIED_SUPPORTING: (AuthorityWeight.SUPPORTING),
        }.get(self.application_status, AuthorityWeight.ZERO)
        if self.effective_issuer_authority_weight != expected_weight:
            raise ValueError("application status and effective weight do not match")
        if (
            _WEIGHT_RANK[self.effective_issuer_authority_weight]
            > _WEIGHT_RANK[self.policy_maximum_issuer_authority_weight]
        ):
            raise ValueError("application weight exceeds source-policy ceiling")
        if self.lineage_tainted:
            if self.production_authority_admitted:
                raise ValueError("tainted application cannot be production admitted")
            if self.effective_issuer_authority_weight != AuthorityWeight.ZERO:
                raise ValueError("tainted application must have zero authority weight")
        if not self.production_authority_admitted and (
            self.effective_issuer_authority_weight != AuthorityWeight.ZERO
        ):
            raise ValueError("unadmitted application must have zero authority weight")
        expected_hash = authority_sha256(_application_semantics(self.model_dump(mode="python")))
        if self.application_content_hash != expected_hash:
            raise ValueError("application_content_hash does not match semantics")
        if self.evidence_application_id != ("aeapp_" + expected_hash.removeprefix("sha256:")):
            raise ValueError("evidence application ID does not match semantics")
        return self


def _policy_admits_evidence(
    policy: AuthoritySourcePolicy,
    evidence: AuthorityEvidence,
) -> tuple[bool, tuple[str, ...]]:
    reasons: list[str] = []
    if evidence.authority_source_policy_id != policy.authority_source_policy_id:
        reasons.append("SOURCE_POLICY_ID_MISMATCH")
    if evidence.authority_source_identifier != policy.source_namespace:
        reasons.append("SOURCE_NAMESPACE_NOT_ADMITTED")
    if evidence.authority_classification != policy.authority_classification:
        reasons.append("SOURCE_CLASSIFICATION_MISMATCH")
    if evidence.source_document_kind not in policy.allowed_document_kinds:
        reasons.append("DOCUMENT_KIND_NOT_ADMITTED")
    if evidence.parser_contract_version not in policy.admitted_parser_contract_versions:
        reasons.append("PARSER_CONTRACT_NOT_ADMITTED")
    if evidence.origin_adapter_class not in policy.admitted_adapter_contract_versions:
        reasons.append("ADAPTER_CONTRACT_NOT_ADMITTED")
    if evidence.origin_data_mode not in policy.allowed_origin_data_modes:
        reasons.append("ORIGIN_DATA_MODE_NOT_ADMITTED")
    if not any(
        evidence.authority_source_locator.startswith(root)
        for root in policy.credential_free_locator_roots
    ):
        reasons.append("SOURCE_LOCATOR_ROOT_NOT_ADMITTED")
    matching_rule = next(
        (
            rule
            for rule in policy.scope_role_weights
            if rule.authority_scope == evidence.authority_scope
            and rule.subject_role == evidence.subject_role
        ),
        None,
    )
    maximum = AuthorityWeight.ZERO if matching_rule is None else matching_rule.maximum_weight
    if matching_rule is None:
        reasons.append("SCOPE_ROLE_NOT_ADMITTED")
    if evidence.policy_maximum_issuer_authority_weight != maximum:
        reasons.append("POLICY_WEIGHT_SNAPSHOT_MISMATCH")
    if evidence.access_disposition != policy.required_access_disposition:
        reasons.append("ACCESS_DISPOSITION_NOT_ADMITTED")
    if evidence.license_disposition != policy.required_license_disposition:
        reasons.append("LICENSE_DISPOSITION_NOT_ADMITTED")
    if policy.permanent_fixture_test_taint != evidence.lineage_tainted:
        reasons.append("LINEAGE_TAINT_MISMATCH")
    if evidence.lineage_ancestor_tainted or evidence.lineage_tainted:
        reasons.append("FIXTURE_TEST_LINEAGE_TAINTED")
    return not reasons, _sorted_unique_text(reasons, field_name="admission_reasons")


def build_authority_evidence_application(
    *,
    policy: AuthoritySourcePolicy,
    evidence: AuthorityEvidence,
    provider_security_identity_id: SafeId,
    provider_observation_ids: Sequence[SafeId],
    candidate_jurisdiction: Jurisdiction,
    candidate_identifier_kind: AuthorityIdentifierKind,
    candidate_identifier_value: str,
    claim_target_field: AuthorityFieldPath,
    requested_status: AuthorityEvidenceApplicationStatus,
    requested_effective_weight: AuthorityWeight,
    reason_codes: Sequence[AuthorityReasonCode],
    authority_relation_head_hash: Sha256,
    evaluated_at: UtcDatetime,
) -> AuthorityEvidenceApplication:
    anchor = proposed_issuer_anchor(
        candidate_jurisdiction,
        candidate_identifier_kind,
        candidate_identifier_value,
    )
    issuer_id = proposed_issuer_id(anchor)
    candidate = authority_candidate_fingerprint(
        jurisdiction=candidate_jurisdiction,
        identifier_kind=candidate_identifier_kind,
        identifier_value=candidate_identifier_value,
    )
    admitted, admission_reasons = _policy_admits_evidence(policy, evidence)
    status = requested_status
    effective_weight = requested_effective_weight
    combined_reasons = list(reason_codes)
    expected_requested_weight = {
        AuthorityEvidenceApplicationStatus.APPLIED_DECISIVE: AuthorityWeight.DECISIVE,
        AuthorityEvidenceApplicationStatus.APPLIED_SUPPORTING: AuthorityWeight.SUPPORTING,
    }.get(requested_status, AuthorityWeight.ZERO)
    if requested_effective_weight != expected_requested_weight:
        admitted = False
        combined_reasons.append("REQUESTED_STATUS_WEIGHT_MISMATCH")
    if (
        _WEIGHT_RANK[requested_effective_weight]
        > _WEIGHT_RANK[policy.maximum_weight_for(evidence.authority_scope, evidence.subject_role)]
    ):
        admitted = False
        combined_reasons.append("POLICY_WEIGHT_CEILING_EXCEEDED")
    if not admitted:
        status = AuthorityEvidenceApplicationStatus.REJECTED_SOURCE_POLICY
        effective_weight = AuthorityWeight.ZERO
        combined_reasons.extend(admission_reasons)
    regulatory_subject_mismatch = (
        evidence.authority_scope == AuthorityScope.ISSUER_REGULATORY_ID
        and evidence.normalized_claim_value != candidate_identifier_value
    )
    if admitted and regulatory_subject_mismatch:
        status = AuthorityEvidenceApplicationStatus.REJECTED_SUBJECT_MISMATCH
        effective_weight = AuthorityWeight.ZERO
        combined_reasons.append("REGULATORY_IDENTIFIER_CANDIDATE_MISMATCH")
    values: dict[str, Any] = {
        "contract_version": AUTHORITY_EVIDENCE_APPLICATION_CONTRACT_VERSION,
        "evidence_id": evidence.evidence_id,
        "evidence_content_hash": evidence.evidence_content_hash,
        "provider_security_identity_id": provider_security_identity_id,
        "provider_observation_ids": _sorted_unique_text(
            provider_observation_ids,
            field_name="provider_observation_ids",
        ),
        "proposed_issuer_id": issuer_id,
        "candidate_fingerprint": candidate,
        "authority_scope": evidence.authority_scope,
        "claim_target_field": claim_target_field,
        "authority_source_policy_id": policy.authority_source_policy_id,
        "authority_source_policy_content_hash": policy.policy_content_hash,
        "policy_maximum_issuer_authority_weight": policy.maximum_weight_for(
            evidence.authority_scope, evidence.subject_role
        ),
        "application_status": status,
        "effective_issuer_authority_weight": effective_weight,
        "reason_codes": _sorted_unique_text(
            tuple(set(combined_reasons)),
            field_name="reason_codes",
        ),
        "authority_relation_head_hash": authority_relation_head_hash,
        "application_rule_version": AUTHORITY_RULE_VERSION,
        "production_authority_admitted": (admitted and policy.production_authority_eligible),
        "lineage_tainted": evidence.lineage_tainted,
        "evaluated_at": evaluated_at,
    }
    content_hash = authority_sha256(_application_semantics(values))
    return AuthorityEvidenceApplication.model_validate(
        {
            **values,
            "evidence_application_id": ("aeapp_" + content_hash.removeprefix("sha256:")),
            "application_content_hash": content_hash,
        }
    )


class AuthorityBundleEvidenceApplicationMember(AuthorityStrictModel):
    evidence_application_id: SafeId
    application_content_hash: Sha256
    evidence_id: SafeId
    evidence_content_hash: Sha256
    authority_source_policy_id: SafeId
    authority_source_policy_content_hash: Sha256
    provider_security_identity_id: SafeId
    proposed_issuer_id: SafeId
    candidate_fingerprint: Sha256
    authority_scope: AuthorityScope
    application_status: AuthorityEvidenceApplicationStatus
    effective_issuer_authority_weight: AuthorityWeight
    production_authority_admitted: bool
    lineage_tainted: bool


class AuthorityBundleScopeResult(AuthorityStrictModel):
    authority_scope: AuthorityScope
    scope_status: AuthorityBundleScopeStatus
    reason_codes: tuple[AuthorityReasonCode, ...]
    scope_result_content_hash: Sha256

    @field_validator("reason_codes")
    @classmethod
    def validate_reasons(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("bundle scope result requires at least one reason code")
        return _sorted_unique_text(value, field_name="reason_codes")

    @model_validator(mode="after")
    def validate_scope_result(self) -> Self:
        expected = authority_sha256(
            {
                "authority_scope": self.authority_scope,
                "scope_status": self.scope_status,
                "reason_codes": self.reason_codes,
            }
        )
        if self.scope_result_content_hash != expected:
            raise ValueError("scope result content hash does not match semantics")
        return self


def build_authority_bundle_scope_result(
    *,
    authority_scope: AuthorityScope,
    scope_status: AuthorityBundleScopeStatus,
    reason_codes: Sequence[AuthorityReasonCode],
) -> AuthorityBundleScopeResult:
    reasons = _sorted_unique_text(reason_codes, field_name="reason_codes")
    values = {
        "authority_scope": authority_scope,
        "scope_status": scope_status,
        "reason_codes": reasons,
    }
    return AuthorityBundleScopeResult.model_validate(
        {
            **values,
            "scope_result_content_hash": authority_sha256(values),
        }
    )


def _bundle_semantics(values: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "contract_version": values["contract_version"],
        "bundle_origin_data_mode": values["bundle_origin_data_mode"],
        "provider_security_identity_id": values["provider_security_identity_id"],
        "provider_observation_ids": values["provider_observation_ids"],
        "candidate_jurisdiction": values["candidate_jurisdiction"],
        "candidate_identifier_kind": values["candidate_identifier_kind"],
        "candidate_identifier_value": values["candidate_identifier_value"],
        "proposed_issuer_anchor": values["proposed_issuer_anchor"],
        "proposed_issuer_id": values["proposed_issuer_id"],
        "candidate_fingerprint": values["candidate_fingerprint"],
        "evidence_application_members": values["evidence_application_members"],
        "required_scope_results": values["required_scope_results"],
        "legal_jurisdiction_result": values["legal_jurisdiction_result"],
        "collision_scan_result": values["collision_scan_result"],
        "collision_claim_candidate_fingerprints": values["collision_claim_candidate_fingerprints"],
        "decision_rule_version": values["decision_rule_version"],
        "evidence_application_set_hash": values["evidence_application_set_hash"],
        "source_policy_set_hash": values["source_policy_set_hash"],
        "provider_lineage_set_hash": values["provider_lineage_set_hash"],
        "collision_scan_hash": values["collision_scan_hash"],
    }


class AuthorityBundle(AuthorityStrictModel):
    authority_bundle_id: SafeId
    contract_version: AuthorityBundleContractVersion
    bundle_content_hash: Sha256
    bundle_origin_data_mode: AuthorityOriginDataMode
    provider_security_identity_id: SafeId
    provider_observation_ids: tuple[SafeId, ...]
    candidate_jurisdiction: Jurisdiction
    candidate_identifier_kind: AuthorityIdentifierKind
    candidate_identifier_value: Annotated[
        str, StringConstraints(pattern=r"^(?:[0-9]{8}|[0-9]{10})$")
    ]
    proposed_issuer_anchor: Annotated[str, StringConstraints(min_length=1, max_length=256)]
    proposed_issuer_id: SafeId
    candidate_fingerprint: Sha256
    evidence_application_members: tuple[AuthorityBundleEvidenceApplicationMember, ...]
    required_scope_results: tuple[AuthorityBundleScopeResult, ...]
    legal_jurisdiction_result: AuthorityLegalJurisdictionResult
    collision_scan_result: AuthorityCollisionScanResult
    collision_claim_candidate_fingerprints: tuple[Sha256, ...]
    decision_rule_version: AuthorityRuleVersion
    evidence_application_set_hash: Sha256
    source_policy_set_hash: Sha256
    provider_lineage_set_hash: Sha256
    collision_scan_hash: Sha256
    built_at: UtcDatetime

    @field_validator("provider_observation_ids")
    @classmethod
    def validate_provider_observations(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("bundle requires exact provider observation membership")
        return _sorted_unique_text(value, field_name="provider_observation_ids")

    @field_validator("collision_claim_candidate_fingerprints")
    @classmethod
    def validate_collision_fingerprints(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _sorted_unique_text(
            value,
            field_name="collision_claim_candidate_fingerprints",
        )

    @model_validator(mode="after")
    def validate_bundle(self) -> Self:
        expected_anchor = proposed_issuer_anchor(
            self.candidate_jurisdiction,
            self.candidate_identifier_kind,
            self.candidate_identifier_value,
        )
        if self.proposed_issuer_anchor != expected_anchor:
            raise ValueError("proposed issuer anchor does not match candidate")
        if self.proposed_issuer_id != proposed_issuer_id(expected_anchor):
            raise ValueError("proposed issuer ID does not match candidate anchor")
        expected_candidate = authority_candidate_fingerprint(
            jurisdiction=self.candidate_jurisdiction,
            identifier_kind=self.candidate_identifier_kind,
            identifier_value=self.candidate_identifier_value,
        )
        if self.candidate_fingerprint != expected_candidate:
            raise ValueError("candidate fingerprint does not match candidate")
        application_ids = tuple(
            member.evidence_application_id for member in self.evidence_application_members
        )
        if application_ids != tuple(sorted(set(application_ids))):
            raise ValueError("bundle application members must be sorted and unique")
        for member in self.evidence_application_members:
            if member.provider_security_identity_id != self.provider_security_identity_id:
                raise ValueError("bundle application provider identity mismatch")
            if member.proposed_issuer_id != self.proposed_issuer_id:
                raise ValueError("bundle application proposed issuer mismatch")
            if member.candidate_fingerprint != self.candidate_fingerprint:
                raise ValueError("bundle application candidate fingerprint mismatch")
            if self.bundle_origin_data_mode == AuthorityOriginDataMode.PRODUCTION_AUTHORITY:
                if member.lineage_tainted or not member.production_authority_admitted:
                    raise ValueError("production bundle cannot contain unadmitted lineage")
        scope_keys = tuple(item.authority_scope.value for item in self.required_scope_results)
        if not scope_keys:
            raise ValueError("bundle requires explicit required-scope results")
        if scope_keys != tuple(sorted(set(scope_keys))):
            raise ValueError("bundle scope results must be sorted and unique")
        expected_application_hash = authority_sha256(self.evidence_application_members)
        if self.evidence_application_set_hash != expected_application_hash:
            raise ValueError("evidence application set hash does not match membership")
        policy_set = tuple(
            sorted(
                {
                    (
                        member.authority_source_policy_id,
                        member.authority_source_policy_content_hash,
                    )
                    for member in self.evidence_application_members
                }
            )
        )
        if self.source_policy_set_hash != authority_sha256(policy_set):
            raise ValueError("source policy set hash does not match membership")
        if self.provider_lineage_set_hash != authority_sha256(self.provider_observation_ids):
            raise ValueError("provider lineage set hash does not match membership")
        collision_semantics = {
            "collision_scan_result": self.collision_scan_result,
            "candidate_fingerprints": self.collision_claim_candidate_fingerprints,
        }
        if self.collision_scan_hash != authority_sha256(collision_semantics):
            raise ValueError("collision scan hash does not match bundle scan")
        expected_content_hash = authority_sha256(_bundle_semantics(self.model_dump(mode="python")))
        if self.bundle_content_hash != expected_content_hash:
            raise ValueError("bundle_content_hash does not match bundle semantics")
        if self.authority_bundle_id != ("authb_" + expected_content_hash.removeprefix("sha256:")):
            raise ValueError("authority bundle ID does not match semantics")
        return self


_SYNTHETIC_AUTHORITY_IDENTIFIERS = {"90000001", "9999999998", "9999999999"}


def _application_member(
    application: AuthorityEvidenceApplication,
) -> AuthorityBundleEvidenceApplicationMember:
    return AuthorityBundleEvidenceApplicationMember.model_validate(
        {
            "evidence_application_id": application.evidence_application_id,
            "application_content_hash": application.application_content_hash,
            "evidence_id": application.evidence_id,
            "evidence_content_hash": application.evidence_content_hash,
            "authority_source_policy_id": application.authority_source_policy_id,
            "authority_source_policy_content_hash": (
                application.authority_source_policy_content_hash
            ),
            "provider_security_identity_id": (application.provider_security_identity_id),
            "proposed_issuer_id": application.proposed_issuer_id,
            "candidate_fingerprint": application.candidate_fingerprint,
            "authority_scope": application.authority_scope,
            "application_status": application.application_status,
            "effective_issuer_authority_weight": (application.effective_issuer_authority_weight),
            "production_authority_admitted": (application.production_authority_admitted),
            "lineage_tainted": application.lineage_tainted,
        }
    )


def _build_authority_bundle(
    *,
    bundle_origin_data_mode: AuthorityOriginDataMode,
    provider_security_identity_id: SafeId,
    provider_observation_ids: Sequence[SafeId],
    candidate_jurisdiction: Jurisdiction,
    candidate_identifier_kind: AuthorityIdentifierKind,
    candidate_identifier_value: str,
    applications: Sequence[AuthorityEvidenceApplication],
    required_scope_results: Sequence[AuthorityBundleScopeResult],
    legal_jurisdiction_result: AuthorityLegalJurisdictionResult,
    collision_scan_result: AuthorityCollisionScanResult,
    collision_claim_candidate_fingerprints: Sequence[Sha256],
    built_at: UtcDatetime,
) -> AuthorityBundle:
    anchor = proposed_issuer_anchor(
        candidate_jurisdiction,
        candidate_identifier_kind,
        candidate_identifier_value,
    )
    issuer_id = proposed_issuer_id(anchor)
    candidate = authority_candidate_fingerprint(
        jurisdiction=candidate_jurisdiction,
        identifier_kind=candidate_identifier_kind,
        identifier_value=candidate_identifier_value,
    )
    members = tuple(
        sorted(
            (_application_member(application) for application in applications),
            key=lambda member: member.evidence_application_id,
        )
    )
    scopes = tuple(sorted(required_scope_results, key=lambda item: item.authority_scope.value))
    provider_observations = _sorted_unique_text(
        provider_observation_ids,
        field_name="provider_observation_ids",
    )
    collision_fingerprints = _sorted_unique_text(
        collision_claim_candidate_fingerprints,
        field_name="collision_claim_candidate_fingerprints",
    )
    if bundle_origin_data_mode == AuthorityOriginDataMode.PRODUCTION_AUTHORITY:
        if candidate_identifier_value in _SYNTHETIC_AUTHORITY_IDENTIFIERS:
            raise ValueError("synthetic authority identifier cannot enter production bundle")
        for application in applications:
            if application.lineage_tainted or not application.production_authority_admitted:
                raise ValueError("production bundle rejects fixture/test lineage")
    application_set_hash = authority_sha256(members)
    source_policy_set = tuple(
        sorted(
            {
                (
                    member.authority_source_policy_id,
                    member.authority_source_policy_content_hash,
                )
                for member in members
            }
        )
    )
    collision_semantics = {
        "collision_scan_result": collision_scan_result,
        "candidate_fingerprints": collision_fingerprints,
    }
    values: dict[str, Any] = {
        "contract_version": AUTHORITY_BUNDLE_CONTRACT_VERSION,
        "bundle_origin_data_mode": bundle_origin_data_mode,
        "provider_security_identity_id": provider_security_identity_id,
        "provider_observation_ids": provider_observations,
        "candidate_jurisdiction": candidate_jurisdiction,
        "candidate_identifier_kind": candidate_identifier_kind,
        "candidate_identifier_value": candidate_identifier_value,
        "proposed_issuer_anchor": anchor,
        "proposed_issuer_id": issuer_id,
        "candidate_fingerprint": candidate,
        "evidence_application_members": members,
        "required_scope_results": scopes,
        "legal_jurisdiction_result": legal_jurisdiction_result,
        "collision_scan_result": collision_scan_result,
        "collision_claim_candidate_fingerprints": collision_fingerprints,
        "decision_rule_version": AUTHORITY_RULE_VERSION,
        "evidence_application_set_hash": application_set_hash,
        "source_policy_set_hash": authority_sha256(source_policy_set),
        "provider_lineage_set_hash": authority_sha256(provider_observations),
        "collision_scan_hash": authority_sha256(collision_semantics),
        "built_at": built_at,
    }
    content_hash = authority_sha256(_bundle_semantics(values))
    return AuthorityBundle.model_validate(
        {
            **values,
            "authority_bundle_id": "authb_" + content_hash.removeprefix("sha256:"),
            "bundle_content_hash": content_hash,
        }
    )


def build_production_authority_bundle(**values: Any) -> AuthorityBundle:
    return _build_authority_bundle(
        **values,
        bundle_origin_data_mode=AuthorityOriginDataMode.PRODUCTION_AUTHORITY,
    )


def build_isolated_test_authority_bundle(**values: Any) -> AuthorityBundle:
    return _build_authority_bundle(
        **values,
        bundle_origin_data_mode=AuthorityOriginDataMode.TEST_ONLY,
    )


def _identifier_claim_semantics(values: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "contract_version": values["contract_version"],
        "identifier_kind": values["identifier_kind"],
        "normalized_identifier_value": values["normalized_identifier_value"],
        "candidate_jurisdiction": values["candidate_jurisdiction"],
        "proposed_issuer_id": values["proposed_issuer_id"],
        "candidate_fingerprint": values["candidate_fingerprint"],
        "provider_security_identity_id": values["provider_security_identity_id"],
        "evidence_application_id": values["evidence_application_id"],
        "application_content_hash": values["application_content_hash"],
        "evidence_id": values["evidence_id"],
        "evidence_content_hash": values["evidence_content_hash"],
        "authority_source_policy_id": values["authority_source_policy_id"],
        "authority_source_policy_content_hash": values["authority_source_policy_content_hash"],
        "claim_role": values["claim_role"],
        "claim_scope": values["claim_scope"],
    }


class AuthorityIdentifierClaim(AuthorityStrictModel):
    authority_identifier_claim_id: SafeId
    contract_version: AuthorityIdentifierClaimContractVersion
    claim_content_hash: Sha256
    identifier_kind: AuthorityIdentifierKind
    normalized_identifier_value: Annotated[
        str, StringConstraints(pattern=r"^(?:[0-9]{8}|[0-9]{10})$")
    ]
    candidate_jurisdiction: Jurisdiction
    proposed_issuer_id: SafeId
    candidate_fingerprint: Sha256
    provider_security_identity_id: SafeId
    evidence_application_id: SafeId
    application_content_hash: Sha256
    evidence_id: SafeId
    evidence_content_hash: Sha256
    authority_source_policy_id: SafeId
    authority_source_policy_content_hash: Sha256
    claim_role: AuthoritySubjectRole
    claim_scope: AuthorityScope
    recorded_at: UtcDatetime

    @model_validator(mode="after")
    def validate_claim(self) -> Self:
        anchor = proposed_issuer_anchor(
            self.candidate_jurisdiction,
            self.identifier_kind,
            self.normalized_identifier_value,
        )
        if self.proposed_issuer_id != proposed_issuer_id(anchor):
            raise ValueError("identifier claim proposed issuer does not match identifier")
        expected_candidate = authority_candidate_fingerprint(
            jurisdiction=self.candidate_jurisdiction,
            identifier_kind=self.identifier_kind,
            identifier_value=self.normalized_identifier_value,
        )
        if self.candidate_fingerprint != expected_candidate:
            raise ValueError("identifier claim candidate fingerprint mismatch")
        expected_hash = authority_sha256(
            _identifier_claim_semantics(self.model_dump(mode="python"))
        )
        if self.claim_content_hash != expected_hash:
            raise ValueError("identifier claim content hash does not match semantics")
        if self.authority_identifier_claim_id != ("aic_" + expected_hash.removeprefix("sha256:")):
            raise ValueError("authority identifier claim ID does not match semantics")
        return self


def build_authority_identifier_claim(
    *,
    identifier_kind: AuthorityIdentifierKind,
    normalized_identifier_value: str,
    candidate_jurisdiction: Jurisdiction,
    provider_security_identity_id: SafeId,
    application: AuthorityEvidenceApplication,
    evidence: AuthorityEvidence,
    policy: AuthoritySourcePolicy,
    claim_role: AuthoritySubjectRole,
    recorded_at: UtcDatetime,
) -> AuthorityIdentifierClaim:
    anchor = proposed_issuer_anchor(
        candidate_jurisdiction,
        identifier_kind,
        normalized_identifier_value,
    )
    issuer_id = proposed_issuer_id(anchor)
    candidate = authority_candidate_fingerprint(
        jurisdiction=candidate_jurisdiction,
        identifier_kind=identifier_kind,
        identifier_value=normalized_identifier_value,
    )
    if application.proposed_issuer_id != issuer_id:
        raise ValueError("identifier claim application is bound to another issuer")
    if application.candidate_fingerprint != candidate:
        raise ValueError("identifier claim application candidate mismatch")
    if application.evidence_id != evidence.evidence_id:
        raise ValueError("identifier claim application/evidence mismatch")
    if application.authority_source_policy_id != policy.authority_source_policy_id:
        raise ValueError("identifier claim application/policy mismatch")
    values: dict[str, Any] = {
        "contract_version": AUTHORITY_IDENTIFIER_CLAIM_CONTRACT_VERSION,
        "identifier_kind": identifier_kind,
        "normalized_identifier_value": normalized_identifier_value,
        "candidate_jurisdiction": candidate_jurisdiction,
        "proposed_issuer_id": issuer_id,
        "candidate_fingerprint": candidate,
        "provider_security_identity_id": provider_security_identity_id,
        "evidence_application_id": application.evidence_application_id,
        "application_content_hash": application.application_content_hash,
        "evidence_id": evidence.evidence_id,
        "evidence_content_hash": evidence.evidence_content_hash,
        "authority_source_policy_id": policy.authority_source_policy_id,
        "authority_source_policy_content_hash": policy.policy_content_hash,
        "claim_role": claim_role,
        "claim_scope": application.authority_scope,
        "recorded_at": recorded_at,
    }
    content_hash = authority_sha256(_identifier_claim_semantics(values))
    return AuthorityIdentifierClaim.model_validate(
        {
            **values,
            "authority_identifier_claim_id": ("aic_" + content_hash.removeprefix("sha256:")),
            "claim_content_hash": content_hash,
        }
    )


def _decision_semantics(values: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "contract_version": values["contract_version"],
        "decision_rule_version": values["decision_rule_version"],
        "authority_bundle_id": values["authority_bundle_id"],
        "authority_bundle_content_hash": values["authority_bundle_content_hash"],
        "provider_security_identity_id": values["provider_security_identity_id"],
        "proposed_issuer_id": values["proposed_issuer_id"],
        "decision_state": values["decision_state"],
        "reason_codes": values["reason_codes"],
        "latest_revision_check_hash": values["latest_revision_check_hash"],
        "freshness_policy_version": values["freshness_policy_version"],
        "freshness_result": values["freshness_result"],
        "collision_scan_hash": values["collision_scan_hash"],
        "supersedes_decision_id": values["supersedes_decision_id"],
    }


def bundle_satisfies_review_ready_foundation(bundle: AuthorityBundle) -> bool:
    required_scopes = {
        AuthorityScope.ISSUER_REGULATORY_ID,
        AuthorityScope.LEGAL_JURISDICTION,
    }
    satisfied_scopes = {
        result.authority_scope
        for result in bundle.required_scope_results
        if result.scope_status == AuthorityBundleScopeStatus.SATISFIED
    }
    decisive_scopes = {
        member.authority_scope
        for member in bundle.evidence_application_members
        if member.application_status == AuthorityEvidenceApplicationStatus.APPLIED_DECISIVE
        and member.effective_issuer_authority_weight == AuthorityWeight.DECISIVE
        and member.production_authority_admitted
        and not member.lineage_tainted
    }
    return (
        bundle.bundle_origin_data_mode == AuthorityOriginDataMode.PRODUCTION_AUTHORITY
        and bundle.legal_jurisdiction_result == AuthorityLegalJurisdictionResult.ESTABLISHED
        and bundle.collision_scan_result == AuthorityCollisionScanResult.CLEAR
        and all(
            result.scope_status == AuthorityBundleScopeStatus.SATISFIED
            for result in bundle.required_scope_results
        )
        and required_scopes.issubset(satisfied_scopes)
        and required_scopes.issubset(decisive_scopes)
    )


class IssuerDecision(AuthorityStrictModel):
    issuer_decision_id: SafeId
    contract_version: IssuerDecisionContractVersion
    decision_content_hash: Sha256
    decision_audit_hash: Sha256
    decision_rule_version: AuthorityRuleVersion
    authority_bundle_id: SafeId
    authority_bundle_content_hash: Sha256
    provider_security_identity_id: SafeId
    proposed_issuer_id: SafeId
    decision_state: IssuerMachineDecisionState
    reason_codes: tuple[AuthorityReasonCode, ...]
    latest_revision_check_hash: Sha256
    freshness_policy_version: AuthorityComponentVersion
    freshness_result: AuthorityFreshnessResult
    collision_scan_hash: Sha256
    supersedes_decision_id: SafeId | None
    evaluated_at: UtcDatetime

    @field_validator("reason_codes")
    @classmethod
    def validate_reasons(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("issuer decision requires structured reason codes")
        return _sorted_unique_text(value, field_name="reason_codes")

    @model_validator(mode="after")
    def validate_decision(self) -> Self:
        if self.supersedes_decision_id == self.issuer_decision_id:
            raise ValueError("issuer decision cannot supersede itself")
        if (
            self.decision_state == IssuerMachineDecisionState.READY_FOR_MANUAL_REVIEW
            and self.freshness_result != AuthorityFreshnessResult.CURRENT
        ):
            raise ValueError("review-ready decision requires current evidence")
        expected_hash = authority_sha256(_decision_semantics(self.model_dump(mode="python")))
        if self.decision_content_hash != expected_hash:
            raise ValueError("decision_content_hash does not match semantics")
        if self.issuer_decision_id != ("idec_" + expected_hash.removeprefix("sha256:")):
            raise ValueError("issuer decision ID does not match semantics")
        expected_audit_hash = authority_sha256(
            {
                "decision_content_hash": self.decision_content_hash,
                "evaluated_at": self.evaluated_at,
            }
        )
        if self.decision_audit_hash != expected_audit_hash:
            raise ValueError("decision audit hash does not match audit metadata")
        return self


def build_issuer_decision(
    *,
    bundle: AuthorityBundle,
    decision_state: IssuerMachineDecisionState,
    reason_codes: Sequence[AuthorityReasonCode],
    latest_revision_check_hash: Sha256,
    freshness_policy_version: AuthorityComponentVersion,
    freshness_result: AuthorityFreshnessResult,
    collision_scan_hash: Sha256,
    evaluated_at: UtcDatetime,
    supersedes_decision_id: SafeId | None = None,
) -> IssuerDecision:
    reasons = _sorted_unique_text(reason_codes, field_name="reason_codes")
    values: dict[str, Any] = {
        "contract_version": ISSUER_DECISION_CONTRACT_VERSION,
        "decision_rule_version": AUTHORITY_RULE_VERSION,
        "authority_bundle_id": bundle.authority_bundle_id,
        "authority_bundle_content_hash": bundle.bundle_content_hash,
        "provider_security_identity_id": bundle.provider_security_identity_id,
        "proposed_issuer_id": bundle.proposed_issuer_id,
        "decision_state": decision_state,
        "reason_codes": reasons,
        "latest_revision_check_hash": latest_revision_check_hash,
        "freshness_policy_version": freshness_policy_version,
        "freshness_result": freshness_result,
        "collision_scan_hash": collision_scan_hash,
        "supersedes_decision_id": supersedes_decision_id,
        "evaluated_at": evaluated_at,
    }
    content_hash = authority_sha256(_decision_semantics(values))
    audit_hash = authority_sha256(
        {
            "decision_content_hash": content_hash,
            "evaluated_at": evaluated_at,
        }
    )
    decision = IssuerDecision.model_validate(
        {
            **values,
            "issuer_decision_id": "idec_" + content_hash.removeprefix("sha256:"),
            "decision_content_hash": content_hash,
            "decision_audit_hash": audit_hash,
        }
    )
    if (
        decision_state == IssuerMachineDecisionState.READY_FOR_MANUAL_REVIEW
        and not bundle_satisfies_review_ready_foundation(bundle)
    ):
        raise ValueError("review-ready decision requires complete decisive production bundle")
    return decision
