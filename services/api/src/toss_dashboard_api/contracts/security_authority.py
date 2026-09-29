"""ADR-020 closed Security ledger contracts; no source admission or approval runtime."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Annotated, Any, ClassVar, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from toss_dashboard_api.contracts.base import SafeId, Sha256

RULES_VERSION = "security-authority-rules/0.1.0"
ID_VERSION = "security-authority-id/1"
Text = Annotated[str, StringConstraints(min_length=1, max_length=2048)]
Token = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")]
SourceToken = Annotated[str, StringConstraints(pattern=r"^[A-Z][A-Z0-9_]{0,127}$")]
AuthorityLocator = Annotated[
    str,
    StringConstraints(
        max_length=2048,
        pattern=r"^(?:https|authority-verification|fixture)://[A-Za-z0-9][A-Za-z0-9._~/-]*$",
    ),
]
Rank = Annotated[int, Field(strict=True, ge=0, le=3)]
Count = Annotated[int, Field(strict=True, ge=0, le=4294967295)]
Flag = Literal[0, 1]


class Scope(StrEnum):
    SECURITY_IDENTIFIER = "SECURITY_IDENTIFIER"
    INSTRUMENT_CLASS = "INSTRUMENT_CLASS"
    REGISTERED_CLASS = "REGISTERED_CLASS"
    LISTING_VENUE = "LISTING_VENUE"
    LISTING_STATUS = "LISTING_STATUS"
    LISTING_INTERVAL = "LISTING_INTERVAL"
    ISSUER_SECURITY_BRIDGE = "ISSUER_SECURITY_BRIDGE"
    PROVIDER_SECURITY_BRIDGE = "PROVIDER_SECURITY_BRIDGE"
    IDENTIFIER_PROVENANCE = "IDENTIFIER_PROVENANCE"


class SubjectRole(StrEnum):
    KRX_ISSUE = "KRX_ISSUE"
    DART_ISSUER = "DART_ISSUER"
    SEC_REGISTRANT = "SEC_REGISTRANT"
    EXCHANGE_ISSUE = "EXCHANGE_ISSUE"
    PROVIDER_SUBJECT = "PROVIDER_SUBJECT"


class InstrumentFamily(StrEnum):
    COMMON_EQUITY = "COMMON_EQUITY"
    PREFERRED_EQUITY = "PREFERRED_EQUITY"
    ADR = "ADR"
    ETF = "ETF"
    ETN = "ETN"
    WARRANT = "WARRANT"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


Disposition = Literal["APPROVED", "REJECTED", "REVOKED", "SUPERSEDED"]
LinkState = Literal["APPROVED", "REVIEW_REQUIRED", "REVOKED", "SUPERSEDED"]
MachineState = Literal["UNRESOLVED", "READY_FOR_MANUAL_REVIEW", "STALE", "REVIEW_REQUIRED"]
Origin = Literal["PRODUCTION_AUTHORITY", "TEST_ONLY"]
Access = Literal["PERMITTED", "RESTRICTED", "UNVERIFIED"]
Ingestion = Literal[
    "AUTOMATED_OFFICIAL_PUBLIC",
    "HUMAN_ASSISTED_VERIFIED_DOCUMENT",
    "PROVENANCE_ONLY",
    "TEST_ISOLATED_ONLY",
]


def _normalize(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return _normalize(value.model_dump(mode="python"))
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if value is None or type(value) in (int, bool):
        return value
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timezone required")
        return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("string keys required")
            normalized = unicodedata.normalize("NFC", key)
            if normalized in result:
                raise ValueError("duplicate normalized key")
            result[normalized] = _normalize(item)
        return result
    if isinstance(value, list | tuple):
        return [_normalize(item) for item in value]
    raise ValueError("unsupported canonical value; binary floats are forbidden")


def canonical_security_bytes(value: Any) -> bytes:
    return json.dumps(
        _normalize(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def security_hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_security_bytes(value)).hexdigest()


def strict_security_json(raw: str) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            key = unicodedata.normalize("NFC", key)
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    def reject(value: str) -> Any:
        raise ValueError("non-integer numeric JSON value: " + value)

    return json.loads(raw, object_pairs_hook=pairs, parse_float=reject, parse_constant=reject)


def _component(value: str, pattern: str) -> str:
    if not isinstance(value, str) or re.fullmatch(pattern, value) is None:
        raise ValueError("invalid anchor component")
    return value


def kr_anchor(issuer_id: str, isin: str) -> str:
    _component(issuer_id, r"[a-z][a-z0-9_]{2,127}")
    _component(isin, r"[A-Z]{2}[A-Z0-9]{9}[0-9]")
    expanded = "".join(str(ord(c) - 55) if c.isalpha() else c for c in isin)
    total = 0
    for index, c in enumerate(reversed(expanded)):
        digit = int(c) * (2 if index % 2 else 1)
        total += digit // 10 + digit % 10
    if total % 10:
        raise ValueError("invalid ISIN check digit")
    return f"security-v1|{issuer_id}|KRX_ISIN|{isin}"


class RegisteredClassIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    verified_registrant_cik: Annotated[str, StringConstraints(pattern=r"^[0-9]{10}$")]
    accepted_accession: Annotated[str, StringConstraints(pattern=r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$")]
    filing_document_digest: Sha256
    filing_form: Text
    registered_class_title: Text
    section_12_basis: Text
    official_class_discriminator: Text | None
    registered_exchange_text: Text | None

    def class_row_id(self) -> str:
        return security_hash(self)


def us_anchor(issuer_id: str, identity: RegisteredClassIdentity) -> str:
    _component(issuer_id, r"[a-z][a-z0-9_]{2,127}")
    return (
        f"security-v1|{issuer_id}|SEC_REGISTERED_CLASS|"
        f"{identity.verified_registrant_cik}/{identity.accepted_accession}/"
        f"{identity.class_row_id()}"
    )


def security_id_for_anchor(anchor: str) -> str:
    parts = anchor.split("|")
    if len(parts) != 4 or parts[0] != "security-v1":
        raise ValueError("invalid Security anchor")
    _component(parts[1], r"[a-z][a-z0-9_]{2,127}")
    if parts[2] == "KRX_ISIN":
        kr_anchor(parts[1], parts[3])
    elif parts[2] == "SEC_REGISTERED_CLASS":
        _component(parts[3], r"[0-9]{10}/[0-9]{10}-[0-9]{2}-[0-9]{6}/sha256:[0-9a-f]{64}")
    else:
        raise ValueError("unsupported anchor kind")
    return "security_" + hashlib.sha256(unicodedata.normalize("NFC", anchor).encode()).hexdigest()


class SecurityRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    identity_fields: ClassVar[tuple[str, ...]] = ()
    audit_fields: ClassVar[tuple[str, ...]] = ("recorded_at",)
    content_hash: Sha256
    audit_hash: Sha256
    recorded_at: datetime

    def semantic_payload(self) -> dict[str, Any]:
        excluded = {*self.identity_fields, *self.audit_fields, "content_hash", "audit_hash"}
        return self.model_dump(mode="python", exclude=excluded)

    @model_validator(mode="after")
    def validate_hashes(self) -> Self:
        if self.content_hash != security_hash(self.semantic_payload()):
            raise ValueError("Security content hash mismatch")
        if self.audit_hash != security_hash(self.model_dump(exclude={"audit_hash"})):
            raise ValueError("Security audit hash mismatch")
        for name in ("reason_codes", "owner_application_ids"):
            values = getattr(self, name, None)
            if values is not None and tuple(sorted(set(values))) != values:
                raise ValueError("set-valued contract arrays must be sorted and unique")
        for field, reason in (
            ("effective_date", "effective_date_missing_reason"),
            ("source_as_of", "source_as_of_missing_reason"),
        ):
            if hasattr(self, field) and (
                (getattr(self, field) is None) != (getattr(self, reason) is not None)
            ):
                raise ValueError("source date requires its exact null reason")
        data = self.model_dump(mode="python")
        if "valid_from" in data:
            start, end = data["valid_from"], data["valid_to"]
            if start is not None and end is not None and start > end:
                raise ValueError("authority interval is reversed")
            interval_reason = data.get("interval_missing_reason", data.get("missing_reason"))
            if (start is None or end is None) and interval_reason is None:
                raise ValueError("missing authority interval requires a reason")
        canonical_security_bytes(self)
        return self


def seal_security_record[T: SecurityRecord](kind: type[T], **fields: Any) -> T:
    """Seal explicit facts, never evaluate authority or perform an approval."""
    fields = dict(fields)
    excluded = {*kind.identity_fields, *kind.audit_fields, "content_hash", "audit_hash"}
    fields["content_hash"] = security_hash({k: v for k, v in fields.items() if k not in excluded})
    fields["audit_hash"] = security_hash(fields)
    return kind.model_validate_json(canonical_security_bytes(fields))


class SourcePolicy(SecurityRecord):
    identity_fields = ("policy_id",)
    contract_version: Literal["security-authority-source-policy/0.1.0"]
    policy_id: SafeId
    source_namespace: SourceToken
    authority_classification: Literal[
        "OFFICIAL_AUTHORITY", "SUPPORTING_EVIDENCE", "DISCOVERY_ONLY", "UNVERIFIED"
    ]
    document_kind: SourceToken
    scope: Scope
    subject_role: SubjectRole
    policy_version: Token
    max_weight: Rank
    ingestion_mode: Ingestion
    adapter_version: Text
    parser_version: Text
    production_eligible: Flag
    access_disposition: Access
    license_disposition: Access
    origin_mode: Origin
    fixture_taint: Flag
    test_taint: Flag
    credential_free_locator_root: AuthorityLocator
    predecessor_policy_id: SafeId | None

    @model_validator(mode="after")
    def eligibility(self) -> Self:
        if self.credential_free_locator_root.startswith("fixture://") and (
            self.production_eligible
            or self.origin_mode != "TEST_ONLY"
            or self.ingestion_mode != "TEST_ISOLATED_ONLY"
            or not (self.fixture_taint or self.test_taint)
            or self.max_weight
        ):
            raise ValueError("fixture locator requires a zero-weight isolated test policy")
        if self.production_eligible and (
            self.fixture_taint
            or self.test_taint
            or self.origin_mode != "PRODUCTION_AUTHORITY"
            or self.access_disposition != "PERMITTED"
            or self.license_disposition != "PERMITTED"
            or self.source_namespace == "CGS"
            or self.ingestion_mode in ("PROVENANCE_ONLY", "TEST_ISOLATED_ONLY")
        ):
            raise ValueError("policy is not production eligible")
        if (self.fixture_taint or self.test_taint) and self.max_weight:
            raise ValueError("tainted evidence has ZERO authority")
        return self


class Evidence(SecurityRecord):
    identity_fields = ("evidence_id",)
    contract_version: Literal["security-authority-evidence/0.1.0"]
    evidence_id: SafeId
    source_namespace: SourceToken
    document_kind: SourceToken
    accepted_document_identity: Text
    raw_digest: Sha256
    subject_role: SubjectRole
    exact_subject: Text
    fact_key: Token
    fact_value: Text
    origin_mode: Origin
    fixture_taint: Flag
    test_taint: Flag
    effective_date: date | None
    effective_date_missing_reason: Literal["NOT_SUPPLIED_BY_AUTHORITY"] | None

    @model_validator(mode="after")
    def missing_date(self) -> Self:
        if (self.effective_date is None) != (self.effective_date_missing_reason is not None):
            raise ValueError("authority date/null reason mismatch")
        return self


class EvidenceObservation(SecurityRecord):
    identity_fields = ("observation_id",)
    audit_fields = ("recorded_at", "retrieved_at", "run_id")
    contract_version: Literal["security-authority-evidence-observation/0.1.0"]
    observation_id: SafeId
    evidence_id: SafeId
    evidence_hash: Sha256
    adapter_version: Text
    parser_version: Text
    run_id: SafeId
    retrieved_at: datetime
    source_as_of: datetime | None
    source_as_of_missing_reason: Literal["NOT_SUPPLIED_BY_AUTHORITY"] | None
    access_result: Literal["SUCCEEDED", "FAILED", "UNAVAILABLE"]
    raw_digest: Sha256


class EvidenceRelation(SecurityRecord):
    identity_fields = ("relation_id",)
    contract_version: Literal["security-authority-evidence-relation/0.1.0"]
    relation_id: SafeId
    prior_evidence_id: SafeId
    prior_evidence_hash: Sha256
    successor_evidence_id: SafeId
    successor_evidence_hash: Sha256
    relation_kind: Literal["CORRECTS", "SUPERSEDES", "SAME_INSTRUMENT_CORRECTION"]
    effective_date: date | None
    effective_date_missing_reason: Literal["NOT_SUPPLIED_BY_AUTHORITY"] | None


class CandidateBinding(SecurityRecord):
    provider_id: SafeId
    issuer_id: SafeId
    security_id: SafeId


class EvidenceApplication(CandidateBinding):
    identity_fields = ("application_id",)
    contract_version: Literal["security-authority-evidence-application/0.1.0"]
    application_id: SafeId
    evidence_id: SafeId
    evidence_hash: Sha256
    policy_id: SafeId
    policy_hash: Sha256
    source_namespace: SourceToken
    document_kind: SourceToken
    scope: Scope
    subject_role: SubjectRole
    requested_weight: Rank
    claim_target: Token
    relation_head_hash: Sha256
    status: Literal["ADMITTED", "SUPPORT_ONLY", "REJECTED"]
    fixture_taint: Flag
    test_taint: Flag


class Bundle(CandidateBinding):
    identity_fields = ("bundle_id",)
    contract_version: Literal["security-authority-bundle/0.1.0"]
    bundle_id: SafeId
    issuer_link_id: SafeId
    issuer_link_hash: Sha256
    issuer_link_state: Literal["APPROVED"]
    issuer_head_state_hash: Sha256
    proposed_anchor: Text
    profile_hash: Sha256
    rules_version: Literal["security-authority-rules/0.1.0"]
    freshness_version: Text
    source_policy_set_hash: Sha256
    collision_scan_hash: Sha256
    membership_hash: Sha256

    @model_validator(mode="after")
    def proposed_identity(self) -> Self:
        if security_id_for_anchor(self.proposed_anchor) != self.security_id:
            raise ValueError("bundle proposed Security does not match its anchor")
        if self.proposed_anchor.split("|")[1] != self.issuer_id:
            raise ValueError("bundle anchor has another issuer")
        return self


class BundleApplication(CandidateBinding):
    identity_fields = ()
    contract_version: Literal["security-authority-bundle/0.1.0"]
    bundle_id: SafeId
    bundle_hash: Sha256
    application_id: SafeId
    application_hash: Sha256
    member_ordinal: Annotated[int, Field(strict=True, ge=0)]


class BundleScopeResult(SecurityRecord):
    identity_fields = ()
    contract_version: Literal["security-authority-bundle-scope-result/0.1.0"]
    bundle_id: SafeId
    bundle_hash: Sha256
    scope: Scope
    result: Literal["SATISFIED", "MISSING", "CONFLICT", "STALE", "UNSUPPORTED"]
    reason_codes: tuple[Token, ...]
    owner_application_ids: tuple[SafeId, ...]


class BundleProviderObservation(SecurityRecord):
    identity_fields = ()
    contract_version: Literal["security-authority-bundle/0.1.0"]
    bundle_id: SafeId
    bundle_hash: Sha256
    provider_id: SafeId
    observation_id: SafeId
    observation_hash: Sha256
    member_ordinal: Annotated[int, Field(strict=True, ge=0)]


class Claim(CandidateBinding):
    identity_fields = ("claim_id",)
    claim_id: SafeId
    application_id: SafeId
    application_hash: Sha256
    application_status: Literal["ADMITTED"]


class IdentifierClaim(Claim):
    scope: Literal["SECURITY_IDENTIFIER"]
    contract_version: Literal["security-identifier-claim/0.1.0"]
    identifier_kind: Literal["KRX_ISIN", "SEC_REGISTERED_CLASS"]
    identifier_value: Text
    valid_from: date | None
    valid_to: date | None
    interval_missing_reason: Literal["NOT_SUPPLIED_BY_AUTHORITY"] | None


class ClassClaim(Claim):
    scope: Literal["INSTRUMENT_CLASS", "REGISTERED_CLASS"]
    contract_version: Literal["security-class-claim/0.1.0"]
    instrument_family: InstrumentFamily
    registered_class_title: Text | None
    authority_share_kind: Text | None
    registered_row_id: Sha256 | None
    section_12_basis: Text | None
    missing_reason: Literal["NOT_SUPPLIED_BY_AUTHORITY"] | None


class ListingClaim(Claim):
    scope: Literal["LISTING_VENUE", "LISTING_STATUS", "LISTING_INTERVAL"]
    contract_version: Literal["security-listing-claim/0.1.0"]
    venue: Token
    market: Token
    ticker: Text
    listing_status: Literal["SCHEDULED", "ACTIVE", "SUSPENDED", "DELISTED", "UNKNOWN"]
    valid_from: date | None
    valid_to: date | None
    interval_missing_reason: Literal["NOT_SUPPLIED_BY_AUTHORITY"] | None


class DecisionBinding(CandidateBinding):
    decision_id: SafeId
    decision_hash: Sha256
    bundle_id: SafeId
    bundle_hash: Sha256
    issuer_link_id: SafeId
    issuer_link_hash: Sha256
    issuer_link_state: Literal["APPROVED"]
    issuer_head_state_hash: Sha256


class Decision(CandidateBinding):
    identity_fields = ("decision_id",)
    audit_fields = ("recorded_at", "evaluated_at")
    contract_version: Literal["security-decision/0.1.0"]
    decision_id: SafeId
    bundle_id: SafeId
    bundle_hash: Sha256
    issuer_link_id: SafeId
    issuer_link_hash: Sha256
    issuer_link_state: Literal["APPROVED"]
    issuer_head_state_hash: Sha256
    machine_state: MachineState
    reason_codes: tuple[Token, ...]
    freshness_result: Literal["FRESH", "STALE", "UNKNOWN"]
    collision_result: Literal["CLEAR", "CONFLICT", "NOT_CHECKED"]
    supersedes_decision_id: SafeId | None
    evaluated_at: datetime


class AuthorizationBinding(DecisionBinding):
    intent_id: SafeId | None
    disposition: Disposition
    principal_id: Annotated[str, StringConstraints(min_length=1, max_length=128)]
    role: Literal["LOCAL_DATA_STEWARD"]
    principal_hash: Sha256
    os_owner_sid_hash: Sha256
    webauthn_credential_id: Annotated[
        str, StringConstraints(pattern=r"^[A-Za-z0-9_-]+$", max_length=2048)
    ]
    credential_id_fingerprint: Sha256
    public_key_fingerprint: Sha256
    expected_head_hash: Sha256
    predecessor_approval_event_id: SafeId | None
    predecessor_link_id: SafeId | None
    successor_decision_id: SafeId | None


class ApprovalChallenge(AuthorizationBinding):
    identity_fields = ("challenge_id",)
    audit_fields = ("recorded_at", "issued_at", "expires_at")
    contract_version: Literal["security-approval-challenge/0.1.0"]
    challenge_id: SafeId
    challenge_digest: Sha256
    issued_at: datetime
    expires_at: datetime


class ChallengeConsumption(SecurityRecord):
    identity_fields = ("consumption_id",)
    audit_fields = ("recorded_at", "consumed_at")
    contract_version: Literal["security-approval-consumption/0.1.0"]
    consumption_id: SafeId
    challenge_id: SafeId
    challenge_hash: Sha256
    terminal_result: Literal["SUCCEEDED", "REJECTED", "EXPIRED", "FAILED"]
    safe_result_code: Token
    consumed_at: datetime


class AuthenticationEvent(AuthorizationBinding):
    identity_fields = ("authentication_event_id",)
    audit_fields = ("recorded_at", "authenticated_at")
    contract_version: Literal["security-reviewer-authentication/0.1.0"]
    authentication_event_id: SafeId
    challenge_id: SafeId
    challenge_hash: Sha256
    consumption_id: SafeId
    consumption_hash: Sha256
    consumption_result: Literal["SUCCEEDED"]
    authentication_result: Literal["VERIFIED"]
    counter_capability: Literal["SIGN_COUNT_SUPPORTED", "NO_USABLE_COUNTER"]
    previous_sign_count: Count | None
    asserted_sign_count: Count | None
    counter_verified: Literal[1]
    rp_id: Literal["localhost"]
    exact_origin: Literal["http://localhost:3000"]
    authentication_policy_version: Text
    client_data_type_verified: Literal[1]
    challenge_verified: Literal[1]
    origin_verified: Literal[1]
    cross_origin_false_verified: Literal[1]
    rp_id_hash_verified: Literal[1]
    user_presence_verified: Literal[1]
    user_verification_verified: Literal[1]
    credential_id_verified: Literal[1]
    signature_verified: Literal[1]
    replay_rejected: Literal[1]
    authenticated_at: datetime

    @model_validator(mode="after")
    def counter(self) -> Self:
        if self.counter_capability == "NO_USABLE_COUNTER":
            if self.previous_sign_count is not None or self.asserted_sign_count is not None:
                raise ValueError("NO_USABLE_COUNTER requires null counts")
        elif (
            self.previous_sign_count is None
            or self.asserted_sign_count is None
            or self.asserted_sign_count <= self.previous_sign_count
        ):
            raise ValueError("supported counter must strictly increase")
        return self


class ApprovalEvent(DecisionBinding):
    identity_fields = ("approval_event_id",)
    audit_fields = ("recorded_at", "reviewed_at")
    contract_version: Literal["security-approval-event/0.1.0"]
    approval_event_id: SafeId
    authentication_event_id: SafeId
    authentication_hash: Sha256
    authentication_result: Literal["VERIFIED"]
    consumption_id: SafeId
    challenge_id: SafeId
    intent_id: SafeId | None
    disposition: Disposition
    predecessor_approval_event_id: SafeId | None
    pair_id: SafeId | None
    successor_decision_id: SafeId | None
    reviewed_at: datetime


class ApprovalEvidenceObservation(SecurityRecord):
    identity_fields = ()
    contract_version: Literal["security-approval-event/0.1.0"]
    approval_event_id: SafeId
    approval_hash: Sha256
    bundle_id: SafeId
    application_id: SafeId
    application_hash: Sha256
    evidence_id: SafeId
    evidence_hash: Sha256
    observation_id: SafeId
    observation_hash: Sha256
    member_ordinal: Annotated[int, Field(strict=True, ge=0)]


class SupersessionPair(SecurityRecord):
    identity_fields = ("pair_id",)
    contract_version: Literal["security-supersession-pair/0.1.0"]
    pair_id: SafeId
    intent_id: SafeId
    provider_id: SafeId
    issuer_id: SafeId
    old_link_id: SafeId
    old_approval_event_id: SafeId
    old_security_id: SafeId
    old_decision_id: SafeId
    old_decision_hash: Sha256
    old_bundle_id: SafeId
    old_bundle_hash: Sha256
    successor_security_id: SafeId
    successor_decision_id: SafeId
    successor_decision_hash: Sha256
    successor_bundle_id: SafeId
    successor_bundle_hash: Sha256
    expected_head_hash: Sha256
    challenge_a: SafeId
    consumption_a: SafeId
    authentication_a: SafeId
    event_a: SafeId
    link_a: SafeId
    challenge_b: SafeId
    consumption_b: SafeId
    authentication_b: SafeId
    event_b: SafeId
    link_b: SafeId


class CanonicalSubject(SecurityRecord):
    identity_fields = ("security_id",)
    contract_version: Literal["security-canonical-subject/0.1.0"]
    security_id: SafeId
    issuer_id: SafeId
    founding_anchor: Text
    anchor_kind: Literal["KRX_ISIN", "SEC_REGISTERED_CLASS"]
    anchor_hash: Sha256

    @model_validator(mode="after")
    def anchor(self) -> Self:
        if (
            security_id_for_anchor(self.founding_anchor) != self.security_id
            or self.founding_anchor.split("|")[1:3] != [self.issuer_id, self.anchor_kind]
            or self.anchor_hash != security_hash(self.founding_anchor)
        ):
            raise ValueError("canonical Security anchor mismatch")
        return self


class AuthorityProfile(SecurityRecord):
    identity_fields = ("profile_id",)
    contract_version: Literal["security-authority-profile/0.1.0"]
    profile_id: SafeId
    security_id: SafeId
    issuer_id: SafeId
    instrument_family: InstrumentFamily
    registered_class_title: Text | None
    authority_share_kind: Text | None
    identifier_kind: Literal["KRX_ISIN", "SEC_REGISTERED_CLASS"]
    identifier_value: Text
    venue: Token
    market: Token
    valid_from: date | None
    valid_to: date | None
    missing_reason: Literal["NOT_SUPPLIED_BY_AUTHORITY"] | None
    identifier_claim_id: SafeId
    identifier_claim_hash: Sha256
    class_claim_id: SafeId
    class_claim_hash: Sha256
    listing_claim_id: SafeId
    listing_claim_hash: Sha256


class AuthorityLink(DecisionBinding):
    identity_fields = ("link_id",)
    contract_version: Literal["security-authority-link/0.1.0"]
    link_id: SafeId
    profile_id: SafeId
    profile_hash: Sha256
    link_state: LinkState
    approval_event_id: SafeId | None
    approval_hash: Sha256 | None
    machine_trigger_decision_id: SafeId | None
    supersedes_link_id: SafeId | None
    pair_id: SafeId | None
    intent_id: SafeId | None


class AuthorityLinkHead(SecurityRecord):
    identity_fields = ("provider_id",)
    contract_version: Literal["security-authority-link-head/0.1.0"]
    provider_id: SafeId
    link_id: SafeId
    link_hash: Sha256
    issuer_id: SafeId
    security_id: SafeId
    profile_id: SafeId
    link_state: LinkState
    state_hash: Sha256
    previous_state_hash: Sha256 | None
