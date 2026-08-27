from __future__ import annotations

from datetime import UTC, datetime
from types import MappingProxyType

from toss_dashboard_api.contracts.authority import (
    AuthorityAccessDisposition,
    AuthorityClassification,
    AuthorityIngestionMode,
    AuthorityLicenseDisposition,
    AuthorityOriginDataMode,
    AuthorityScope,
    AuthorityScopeRoleWeight,
    AuthoritySourcePolicy,
    AuthoritySubjectRole,
    AuthorityWeight,
    build_authority_source_policy,
)

SOURCE_POLICY_REGISTRY_VERSION = "issuer-authority-source-registry/0.1.0"
_REGISTERED_AT = datetime(2026, 8, 26, 1, 2, 3, tzinfo=UTC)


def _production_policy(
    *,
    source_namespace: str,
    field_owner: str,
    allowed_document_kinds: tuple[str, ...],
    credential_free_locator_roots: tuple[str, ...],
    scope_role_weights: tuple[AuthorityScopeRoleWeight, ...],
    ingestion_mode: AuthorityIngestionMode,
    adapter_contract_version: str,
    parser_contract_version: str,
) -> AuthoritySourcePolicy:
    return build_authority_source_policy(
        source_namespace=source_namespace,
        field_owner=field_owner,
        authority_classification=AuthorityClassification.OFFICIAL_AUTHORITY,
        allowed_document_kinds=allowed_document_kinds,
        credential_free_locator_roots=credential_free_locator_roots,
        scope_role_weights=scope_role_weights,
        ingestion_mode=ingestion_mode,
        admitted_adapter_contract_versions=(adapter_contract_version,),
        admitted_parser_contract_versions=(parser_contract_version,),
        production_authority_eligible=True,
        required_access_disposition=AuthorityAccessDisposition.PERMITTED,
        required_license_disposition=AuthorityLicenseDisposition.PERMITTED,
        allowed_origin_data_modes=(AuthorityOriginDataMode.PRODUCTION_AUTHORITY,),
        permanent_fixture_test_taint=False,
        registered_at=_REGISTERED_AT,
    )


OPENDART_CORP_CODE_POLICY = _production_policy(
    source_namespace="OPENDART_CORP_CODE",
    field_owner="Financial Supervisory Service OpenDART",
    allowed_document_kinds=("CORP_CODE_XML_V1",),
    credential_free_locator_roots=("https://opendart.fss.or.kr/",),
    scope_role_weights=(
        AuthorityScopeRoleWeight(
            authority_scope=AuthorityScope.ISSUER_REGULATORY_ID,
            subject_role=AuthoritySubjectRole.DART_DISCLOSURE_FILER,
            maximum_weight=AuthorityWeight.DECISIVE,
        ),
    ),
    ingestion_mode=AuthorityIngestionMode.AUTOMATED_OFFICIAL_PUBLIC,
    adapter_contract_version="opendart-corp-code/0.1.0",
    parser_contract_version="opendart-corp-code-parser/0.1.0",
)

OPENDART_COMPANY_OVERVIEW_POLICY = _production_policy(
    source_namespace="OPENDART_COMPANY_OVERVIEW",
    field_owner="Financial Supervisory Service OpenDART",
    allowed_document_kinds=("COMPANY_OVERVIEW_JSON_V1",),
    credential_free_locator_roots=("https://opendart.fss.or.kr/",),
    scope_role_weights=(
        AuthorityScopeRoleWeight(
            authority_scope=AuthorityScope.LEGAL_ENTITY_BRIDGE,
            subject_role=AuthoritySubjectRole.DART_DISCLOSURE_FILER,
            maximum_weight=AuthorityWeight.SUPPORTING,
        ),
        AuthorityScopeRoleWeight(
            authority_scope=AuthorityScope.LEGAL_NAME,
            subject_role=AuthoritySubjectRole.DART_DISCLOSURE_FILER,
            maximum_weight=AuthorityWeight.SUPPORTING,
        ),
    ),
    ingestion_mode=AuthorityIngestionMode.AUTOMATED_OFFICIAL_PUBLIC,
    adapter_contract_version="opendart-company-overview/0.1.0",
    parser_contract_version="opendart-company-overview-parser/0.1.0",
)

# The narrow policy is retained because it is the exact independently reviewed
# B2-A source-policy fixture. The B2-B positive path uses the complete matrix
# policy below, whose content identity is distinct and server owned.
KR_IROS_JURISDICTION_ONLY_POLICY = _production_policy(
    source_namespace="KR_SUPREME_COURT_IROS",
    field_owner="Supreme Court of Korea Internet Registry",
    allowed_document_kinds=("VERIFIED_CORPORATE_REGISTRY_EXTRACT_V1",),
    credential_free_locator_roots=("authority-verification://kr-supreme-court/",),
    scope_role_weights=(
        AuthorityScopeRoleWeight(
            authority_scope=AuthorityScope.LEGAL_JURISDICTION,
            subject_role=AuthoritySubjectRole.KOREAN_REGISTERED_LEGAL_ENTITY,
            maximum_weight=AuthorityWeight.DECISIVE,
        ),
    ),
    ingestion_mode=AuthorityIngestionMode.HUMAN_ASSISTED_VERIFIED_DOCUMENT,
    adapter_contract_version="iros-verified-document/0.1.0",
    parser_contract_version="iros-verified-document-parser/0.1.0",
)

KR_IROS_COMPLETE_POLICY = _production_policy(
    source_namespace="KR_SUPREME_COURT_IROS",
    field_owner="Supreme Court of Korea Internet Registry",
    allowed_document_kinds=("VERIFIED_CORPORATE_REGISTRY_EXTRACT_V1",),
    credential_free_locator_roots=("authority-verification://kr-supreme-court/",),
    scope_role_weights=(
        AuthorityScopeRoleWeight(
            authority_scope=AuthorityScope.LEGAL_ENTITY_BRIDGE,
            subject_role=AuthoritySubjectRole.KOREAN_REGISTERED_LEGAL_ENTITY,
            maximum_weight=AuthorityWeight.DECISIVE,
        ),
        AuthorityScopeRoleWeight(
            authority_scope=AuthorityScope.LEGAL_JURISDICTION,
            subject_role=AuthoritySubjectRole.KOREAN_REGISTERED_LEGAL_ENTITY,
            maximum_weight=AuthorityWeight.DECISIVE,
        ),
        AuthorityScopeRoleWeight(
            authority_scope=AuthorityScope.LEGAL_NAME,
            subject_role=AuthoritySubjectRole.KOREAN_REGISTERED_LEGAL_ENTITY,
            maximum_weight=AuthorityWeight.DECISIVE,
        ),
    ),
    ingestion_mode=AuthorityIngestionMode.HUMAN_ASSISTED_VERIFIED_DOCUMENT,
    adapter_contract_version="iros-verified-document/0.1.0",
    parser_contract_version="iros-verified-document-parser/0.1.0",
)

SEC_ACCEPTED_FILING_POLICY = _production_policy(
    source_namespace="SEC_EDGAR_ACCEPTED_FILING",
    field_owner="U.S. Securities and Exchange Commission EDGAR",
    allowed_document_kinds=(
        "SEC_ACCEPTED_ISSUER_FILING_JSON_V1",
        "SEC_REGISTRANT_LATEST_STATUS_JSON_V1",
    ),
    credential_free_locator_roots=("https://www.sec.gov/Archives/edgar/data/",),
    scope_role_weights=(
        AuthorityScopeRoleWeight(
            authority_scope=AuthorityScope.ISSUER_REGULATORY_ID,
            subject_role=AuthoritySubjectRole.SEC_REGISTRANT,
            maximum_weight=AuthorityWeight.DECISIVE,
        ),
        AuthorityScopeRoleWeight(
            authority_scope=AuthorityScope.LEGAL_ENTITY_BRIDGE,
            subject_role=AuthoritySubjectRole.SEC_REGISTRANT,
            maximum_weight=AuthorityWeight.SUPPORTING,
        ),
        AuthorityScopeRoleWeight(
            authority_scope=AuthorityScope.LEGAL_NAME,
            subject_role=AuthoritySubjectRole.SEC_REGISTRANT,
            maximum_weight=AuthorityWeight.SUPPORTING,
        ),
        AuthorityScopeRoleWeight(
            authority_scope=AuthorityScope.REGISTRANT_ROLE,
            subject_role=AuthoritySubjectRole.SEC_REGISTRANT,
            maximum_weight=AuthorityWeight.DECISIVE,
        ),
    ),
    ingestion_mode=AuthorityIngestionMode.AUTOMATED_OFFICIAL_PUBLIC,
    adapter_contract_version="sec-edgar-accepted-filing/0.1.0",
    parser_contract_version="sec-edgar-registrant-parser/0.1.0",
)

SEC_LOGIN_PROVENANCE_POLICY = _production_policy(
    source_namespace="SEC_EDGAR_LOGIN_PROVENANCE",
    field_owner="U.S. Securities and Exchange Commission EDGAR",
    allowed_document_kinds=("SEC_SUBMISSION_PROVENANCE_JSON_V1",),
    credential_free_locator_roots=("https://www.sec.gov/Archives/edgar/data/",),
    scope_role_weights=(
        AuthorityScopeRoleWeight(
            authority_scope=AuthorityScope.SUBMISSION_PROVENANCE,
            subject_role=AuthoritySubjectRole.SEC_FILING_AGENT,
            maximum_weight=AuthorityWeight.ZERO,
        ),
        AuthorityScopeRoleWeight(
            authority_scope=AuthorityScope.SUBMISSION_PROVENANCE,
            subject_role=AuthoritySubjectRole.SEC_LOGIN_CIK,
            maximum_weight=AuthorityWeight.ZERO,
        ),
    ),
    ingestion_mode=AuthorityIngestionMode.PROVENANCE_ONLY,
    adapter_contract_version="sec-edgar-submission-provenance/0.1.0",
    parser_contract_version="sec-edgar-provenance-parser/0.1.0",
)

US_STATE_REGISTRY_DE_POLICY = _production_policy(
    source_namespace="US_STATE_REGISTRY_DE",
    field_owner="Delaware Division of Corporations",
    allowed_document_kinds=("VERIFIED_DOMESTIC_ENTITY_RECORD_V1",),
    credential_free_locator_roots=("authority-verification://us-state-registry-de/",),
    scope_role_weights=(
        AuthorityScopeRoleWeight(
            authority_scope=AuthorityScope.LEGAL_JURISDICTION,
            subject_role=AuthoritySubjectRole.US_STATE_REGISTERED_LEGAL_ENTITY,
            maximum_weight=AuthorityWeight.DECISIVE,
        ),
        AuthorityScopeRoleWeight(
            authority_scope=AuthorityScope.LEGAL_NAME,
            subject_role=AuthoritySubjectRole.US_STATE_REGISTERED_LEGAL_ENTITY,
            maximum_weight=AuthorityWeight.DECISIVE,
        ),
    ),
    ingestion_mode=AuthorityIngestionMode.HUMAN_ASSISTED_VERIFIED_DOCUMENT,
    adapter_contract_version="us-de-verified-document/0.1.0",
    parser_contract_version="us-de-verified-document-parser/0.1.0",
)


PRODUCTION_AUTHORITY_SOURCE_POLICIES = tuple(
    sorted(
        (
            OPENDART_CORP_CODE_POLICY,
            OPENDART_COMPANY_OVERVIEW_POLICY,
            KR_IROS_JURISDICTION_ONLY_POLICY,
            KR_IROS_COMPLETE_POLICY,
            SEC_ACCEPTED_FILING_POLICY,
            SEC_LOGIN_PROVENANCE_POLICY,
            US_STATE_REGISTRY_DE_POLICY,
        ),
        key=lambda policy: policy.authority_source_policy_id,
    )
)

PRODUCTION_AUTHORITY_SOURCE_POLICY_BY_ID = MappingProxyType(
    {policy.authority_source_policy_id: policy for policy in PRODUCTION_AUTHORITY_SOURCE_POLICIES}
)


def server_owned_production_policy(policy_id: str) -> AuthoritySourcePolicy | None:
    return PRODUCTION_AUTHORITY_SOURCE_POLICY_BY_ID.get(policy_id)


def is_exact_server_owned_production_policy(policy: AuthoritySourcePolicy) -> bool:
    registered = server_owned_production_policy(policy.authority_source_policy_id)
    return registered is not None and registered == policy
