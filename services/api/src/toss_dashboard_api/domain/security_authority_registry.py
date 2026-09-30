"""Closed, server-owned source admission for the C2 Security engine."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime

from toss_dashboard_api.contracts import security_authority as c

REGISTRY_VERSION = "security-authority-source-registry/2026-09-30"
POLICY_VERSION = "c2-source-review-2026-09-30"
ADAPTER_VERSION = "c2-normalized-stored-facts/1"
PARSER_VERSION = "c2-normalized-stored-facts/1"


@dataclass(frozen=True)
class PolicySpec:
    namespace: str
    document_kind: str
    scope: c.Scope
    role: c.SubjectRole
    weight: int
    classification: str = "OFFICIAL_AUTHORITY"
    ingestion: c.Ingestion = "AUTOMATED_OFFICIAL_PUBLIC"
    locator: str = "authority-verification://c2/approved-source/"


def _specs() -> tuple[PolicySpec, ...]:
    owner = 3
    support = 2
    rows = (
        (
            "KRX_STANDARD_CODE",
            "KRX_STANDARD_CODE_RECORD",
            c.SubjectRole.KRX_ISSUE,
            c.Scope.SECURITY_IDENTIFIER,
            owner,
        ),
        (
            "KRX_STANDARD_CODE",
            "KRX_STANDARD_CODE_RECORD",
            c.SubjectRole.KRX_ISSUE,
            c.Scope.IDENTIFIER_PROVENANCE,
            owner,
        ),
        (
            "KRX_STANDARD_CODE",
            "KRX_STANDARD_CODE_RECORD",
            c.SubjectRole.KRX_ISSUE,
            c.Scope.INSTRUMENT_CLASS,
            support,
        ),
        (
            "KRX_ISSUE_BASIC",
            "KRX_ISSUE_BASIC_RECORD",
            c.SubjectRole.KRX_ISSUE,
            c.Scope.INSTRUMENT_CLASS,
            owner,
        ),
        (
            "KRX_ISSUE_BASIC",
            "KRX_ISSUE_BASIC_RECORD",
            c.SubjectRole.KRX_ISSUE,
            c.Scope.LISTING_VENUE,
            owner,
        ),
        (
            "KRX_ISSUE_BASIC",
            "KRX_ISSUE_BASIC_RECORD",
            c.SubjectRole.KRX_ISSUE,
            c.Scope.ISSUER_SECURITY_BRIDGE,
            owner,
        ),
        (
            "KRX_ISSUE_BASIC",
            "KRX_ISSUE_BASIC_RECORD",
            c.SubjectRole.KRX_ISSUE,
            c.Scope.SECURITY_IDENTIFIER,
            support,
        ),
        (
            "KRX_ISSUE_BASIC",
            "KRX_ISSUE_BASIC_RECORD",
            c.SubjectRole.KRX_ISSUE,
            c.Scope.LISTING_INTERVAL,
            support,
        ),
        (
            "KRX_LISTING_LIFECYCLE",
            "KRX_LISTING_LIFECYCLE_RECORD",
            c.SubjectRole.KRX_ISSUE,
            c.Scope.LISTING_STATUS,
            owner,
        ),
        (
            "KRX_LISTING_LIFECYCLE",
            "KRX_LISTING_LIFECYCLE_RECORD",
            c.SubjectRole.KRX_ISSUE,
            c.Scope.LISTING_INTERVAL,
            owner,
        ),
        (
            "KRX_LISTING_LIFECYCLE",
            "KRX_LISTING_LIFECYCLE_RECORD",
            c.SubjectRole.KRX_ISSUE,
            c.Scope.LISTING_VENUE,
            owner,
        ),
        (
            "KRX_LISTING_LIFECYCLE",
            "KRX_LISTING_LIFECYCLE_RECORD",
            c.SubjectRole.KRX_ISSUE,
            c.Scope.INSTRUMENT_CLASS,
            support,
        ),
        (
            "OPENDART_CORP_CODE",
            "OPENDART_CORP_CODE_RECORD",
            c.SubjectRole.DART_ISSUER,
            c.Scope.ISSUER_SECURITY_BRIDGE,
            owner,
        ),
        (
            "SEC_ACCEPTED_8A",
            "SEC_FORM_8A",
            c.SubjectRole.SEC_REGISTRANT,
            c.Scope.REGISTERED_CLASS,
            owner,
        ),
        (
            "SEC_ACCEPTED_8A",
            "SEC_FORM_8A",
            c.SubjectRole.SEC_REGISTRANT,
            c.Scope.IDENTIFIER_PROVENANCE,
            owner,
        ),
        (
            "SEC_ACCEPTED_8A",
            "SEC_FORM_8A",
            c.SubjectRole.SEC_REGISTRANT,
            c.Scope.LISTING_VENUE,
            support,
        ),
        (
            "SEC_ACCEPTED_25",
            "SEC_FORM_25",
            c.SubjectRole.EXCHANGE_ISSUE,
            c.Scope.LISTING_STATUS,
            owner,
        ),
        (
            "SEC_ACCEPTED_25",
            "SEC_FORM_25",
            c.SubjectRole.EXCHANGE_ISSUE,
            c.Scope.LISTING_INTERVAL,
            owner,
        ),
        (
            "SEC_PERIODIC_COVER",
            "SEC_PERIODIC_COVER",
            c.SubjectRole.SEC_REGISTRANT,
            c.Scope.REGISTERED_CLASS,
            support,
        ),
        (
            "SEC_PERIODIC_COVER",
            "SEC_PERIODIC_COVER",
            c.SubjectRole.SEC_REGISTRANT,
            c.Scope.LISTING_VENUE,
            support,
        ),
        (
            "NASDAQ_PRIMARY",
            "NASDAQ_SYMBOL_DIRECTORY",
            c.SubjectRole.EXCHANGE_ISSUE,
            c.Scope.LISTING_VENUE,
            owner,
        ),
        (
            "NASDAQ_PRIMARY",
            "NASDAQ_SYMBOL_DIRECTORY",
            c.SubjectRole.EXCHANGE_ISSUE,
            c.Scope.LISTING_STATUS,
            owner,
        ),
        (
            "NASDAQ_PRIMARY",
            "NASDAQ_SYMBOL_DIRECTORY",
            c.SubjectRole.EXCHANGE_ISSUE,
            c.Scope.LISTING_INTERVAL,
            owner,
        ),
        (
            "NASDAQ_PRIMARY",
            "NASDAQ_SYMBOL_DIRECTORY",
            c.SubjectRole.EXCHANGE_ISSUE,
            c.Scope.REGISTERED_CLASS,
            support,
        ),
        (
            "TOSS_PROVIDER_OBSERVATION",
            "PROVIDER_SECURITY_MASTER",
            c.SubjectRole.PROVIDER_SUBJECT,
            c.Scope.PROVIDER_SECURITY_BRIDGE,
            support,
        ),
    )
    return tuple(
        PolicySpec(
            namespace=namespace,
            document_kind=document_kind,
            role=role,
            scope=scope,
            weight=weight,
            classification="OFFICIAL_AUTHORITY" if weight == owner else "SUPPORTING_EVIDENCE",
            ingestion=(
                "HUMAN_ASSISTED_VERIFIED_DOCUMENT"
                if namespace.startswith("KRX_")
                else "AUTOMATED_OFFICIAL_PUBLIC"
            ),
            locator=(
                "authority-verification://krx/"
                if namespace.startswith("KRX_")
                else "authority-verification://opendart/"
                if namespace == "OPENDART_CORP_CODE"
                else "https://www.sec.gov/"
                if namespace.startswith("SEC_")
                else "https://www.nasdaqtrader.com/"
                if namespace == "NASDAQ_PRIMARY"
                else "authority-verification://provider/toss/"
            ),
        )
        for namespace, document_kind, role, scope, weight in rows
    )


SOURCE_POLICY_SPECS = _specs()
POLICY_BY_KEY = {
    (spec.namespace, spec.document_kind, spec.scope, spec.role): spec
    for spec in SOURCE_POLICY_SPECS
}


def policy_id(spec: PolicySpec) -> str:
    key = "|".join((spec.namespace, spec.document_kind, spec.scope.value, spec.role.value))
    return "sec_policy_" + hashlib.sha256(key.encode("ascii")).hexdigest()


def build_policy(spec: PolicySpec, *, recorded_at: datetime) -> c.SourcePolicy:
    return c.seal_security_record(
        c.SourcePolicy,
        contract_version="security-authority-source-policy/0.1.0",
        policy_id=policy_id(spec),
        source_namespace=spec.namespace,
        authority_classification=spec.classification,
        document_kind=spec.document_kind,
        scope=spec.scope,
        subject_role=spec.role,
        policy_version=POLICY_VERSION,
        max_weight=spec.weight,
        ingestion_mode=spec.ingestion,
        adapter_version=ADAPTER_VERSION,
        parser_version=PARSER_VERSION,
        production_eligible=1,
        access_disposition="PERMITTED",
        license_disposition="PERMITTED",
        origin_mode="PRODUCTION_AUTHORITY",
        fixture_taint=0,
        test_taint=0,
        credential_free_locator_root=spec.locator,
        predecessor_policy_id=None,
        recorded_at=recorded_at.astimezone(UTC),
    )


def exact_policy_for(
    namespace: str, document_kind: str, scope: c.Scope, role: c.SubjectRole
) -> PolicySpec | None:
    return POLICY_BY_KEY.get((namespace, document_kind, scope, role))


def registry_hash(policies: tuple[c.SourcePolicy, ...]) -> str:
    return c.security_hash(sorted((policy.policy_id, policy.content_hash) for policy in policies))
