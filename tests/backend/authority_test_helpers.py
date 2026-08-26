from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session, sessionmaker

from toss_dashboard_api.contracts.authority import (
    AuthorityAccessDisposition,
    AuthorityBundle,
    AuthorityBundleScopeStatus,
    AuthorityClassification,
    AuthorityCollisionScanResult,
    AuthorityEvidence,
    AuthorityEvidenceApplication,
    AuthorityEvidenceApplicationStatus,
    AuthorityEvidenceKind,
    AuthorityIdentifierKind,
    AuthorityIngestionMode,
    AuthorityLegalJurisdictionResult,
    AuthorityLicenseDisposition,
    AuthorityOriginDataMode,
    AuthorityScope,
    AuthorityScopeRoleWeight,
    AuthoritySourcePolicy,
    AuthoritySubjectRole,
    AuthorityTimeMissingReason,
    AuthorityWeight,
    authority_sha256,
    build_authority_bundle_scope_result,
    build_authority_evidence,
    build_authority_evidence_application,
    build_authority_source_policy,
    build_isolated_test_authority_bundle,
    build_production_authority_bundle,
)
from toss_dashboard_api.contracts.enums import Jurisdiction
from toss_dashboard_api.storage.models import (
    CanonicalRequestRow,
    ProviderRawManifestRow,
    ProviderSecurityIdentityRow,
    ProviderSecurityMasterObservationRow,
    ProviderSourceVersionRow,
)

NOW = datetime(2026, 8, 26, 1, 2, 3, tzinfo=UTC)
LATER = datetime(2026, 8, 27, 4, 5, 6, tzinfo=UTC)
RAW_HASH = "sha256:" + ("1" * 64)
RELATION_HEAD_HASH = "sha256:" + ("2" * 64)
RETRIEVAL_FINGERPRINT = "sha256:" + ("3" * 64)
LATEST_REVISION_HASH = "sha256:" + ("4" * 64)
PROVIDER_ID = "provider_security_authority_a"
PROVIDER_OBSERVATION_ID = "provider_observation_authority_a"
SECOND_PROVIDER_ID = "provider_security_authority_b"
SECOND_PROVIDER_OBSERVATION_ID = "provider_observation_authority_b"
CORP_CODE = "00126380"
CORRECTED_CORP_CODE = "00126381"
SECOND_CORRECTED_CORP_CODE = "00126382"


def production_source_policy(
    *,
    registered_at: datetime = NOW,
) -> AuthoritySourcePolicy:
    return build_authority_source_policy(
        source_namespace="OPENDART_CORP_CODE",
        field_owner="Financial Supervisory Service OpenDART",
        authority_classification=AuthorityClassification.OFFICIAL_AUTHORITY,
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
        admitted_adapter_contract_versions=("opendart-corp-code/0.1.0",),
        admitted_parser_contract_versions=("opendart-corp-code-parser/0.1.0",),
        production_authority_eligible=True,
        required_access_disposition=AuthorityAccessDisposition.PERMITTED,
        required_license_disposition=AuthorityLicenseDisposition.PERMITTED,
        allowed_origin_data_modes=(AuthorityOriginDataMode.PRODUCTION_AUTHORITY,),
        permanent_fixture_test_taint=False,
        registered_at=registered_at,
    )


def jurisdiction_source_policy(
    *,
    registered_at: datetime = NOW,
) -> AuthoritySourcePolicy:
    return build_authority_source_policy(
        source_namespace="KR_SUPREME_COURT_IROS",
        field_owner="Supreme Court of Korea Internet Registry",
        authority_classification=AuthorityClassification.OFFICIAL_AUTHORITY,
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
        admitted_adapter_contract_versions=("iros-verified-document/0.1.0",),
        admitted_parser_contract_versions=("iros-verified-document-parser/0.1.0",),
        production_authority_eligible=True,
        required_access_disposition=AuthorityAccessDisposition.PERMITTED,
        required_license_disposition=AuthorityLicenseDisposition.PERMITTED,
        allowed_origin_data_modes=(AuthorityOriginDataMode.PRODUCTION_AUTHORITY,),
        permanent_fixture_test_taint=False,
        registered_at=registered_at,
    )


def fixture_source_policy(
    *,
    registered_at: datetime = NOW,
) -> AuthoritySourcePolicy:
    return build_authority_source_policy(
        source_namespace="FIXTURE_KR_REGULATOR",
        field_owner="Isolated test factory",
        authority_classification=AuthorityClassification.UNVERIFIED,
        allowed_document_kinds=("SYNTHETIC_JSON_V1",),
        credential_free_locator_roots=("fixture://authority/",),
        scope_role_weights=(
            AuthorityScopeRoleWeight(
                authority_scope=AuthorityScope.ISSUER_REGULATORY_ID,
                subject_role=AuthoritySubjectRole.DART_DISCLOSURE_FILER,
                maximum_weight=AuthorityWeight.ZERO,
            ),
        ),
        ingestion_mode=AuthorityIngestionMode.TEST_ISOLATED_ONLY,
        admitted_adapter_contract_versions=("fixture-authority/0.1.0",),
        admitted_parser_contract_versions=("fixture-parser/0.1.0",),
        production_authority_eligible=False,
        required_access_disposition=AuthorityAccessDisposition.UNVERIFIED,
        required_license_disposition=AuthorityLicenseDisposition.UNVERIFIED,
        allowed_origin_data_modes=(AuthorityOriginDataMode.TEST_ONLY,),
        permanent_fixture_test_taint=True,
        registered_at=registered_at,
    )


def authority_evidence(
    policy: AuthoritySourcePolicy,
    *,
    raw_content_hash: str = RAW_HASH,
    raw_claim_value: object = CORP_CODE,
    normalized_claim_value: object = CORP_CODE,
    lineage_ancestor_tainted: bool = False,
) -> AuthorityEvidence:
    fixture = policy.permanent_fixture_test_taint
    locator = (
        "fixture://authority/corp-code.json"
        if fixture
        else "https://opendart.fss.or.kr/api/corpCode.xml"
    )
    return build_authority_evidence(
        authority_source_policy_id=policy.authority_source_policy_id,
        authority_source_identifier=policy.source_namespace,
        authority_classification=policy.authority_classification,
        authority_source_locator=locator,
        authority_document_reference=f"corp-code-record-{normalized_claim_value}",
        source_document_kind=policy.allowed_document_kinds[0],
        authority_external_key=f"corp-code-record-{normalized_claim_value}",
        raw_content_hash=raw_content_hash,
        parser_contract_version=policy.admitted_parser_contract_versions[0],
        evidence_kind=(
            AuthorityEvidenceKind.PROVENANCE_ONLY if fixture else AuthorityEvidenceKind.ASSERTION
        ),
        authority_scope=AuthorityScope.ISSUER_REGULATORY_ID,
        subject_role=AuthoritySubjectRole.DART_DISCLOSURE_FILER,
        policy_maximum_issuer_authority_weight=(
            AuthorityWeight.ZERO if fixture else AuthorityWeight.DECISIVE
        ),
        claim_field="corp_list.corp.corp_code",
        raw_claim_value=raw_claim_value,
        normalized_claim_value=normalized_claim_value,
        authority_published_at=None,
        authority_accepted_at=None,
        authority_as_of_date=None,
        authority_effective_at=None,
        authority_effective_date=None,
        authority_time_missing_reasons={
            "authority_published_at": (AuthorityTimeMissingReason.NOT_SUPPLIED_BY_AUTHORITY),
            "authority_accepted_at": (AuthorityTimeMissingReason.NOT_SUPPLIED_BY_AUTHORITY),
            "authority_as_of_date": (AuthorityTimeMissingReason.NOT_SUPPLIED_BY_AUTHORITY),
            "authority_effective_at": (AuthorityTimeMissingReason.NOT_SUPPLIED_BY_AUTHORITY),
            "authority_effective_date": (AuthorityTimeMissingReason.NOT_SUPPLIED_BY_AUTHORITY),
        },
        access_disposition=policy.required_access_disposition,
        license_disposition=policy.required_license_disposition,
        origin_data_mode=(
            AuthorityOriginDataMode.TEST_ONLY
            if fixture
            else AuthorityOriginDataMode.PRODUCTION_AUTHORITY
        ),
        origin_adapter_class=policy.admitted_adapter_contract_versions[0],
        origin_source_system=policy.source_namespace,
        lineage_tainted=(fixture or lineage_ancestor_tainted),
        lineage_ancestor_tainted=lineage_ancestor_tainted,
        lineage_ancestor_hashes=(("sha256:" + ("a" * 64),) if lineage_ancestor_tainted else ()),
    )


def jurisdiction_evidence(
    policy: AuthoritySourcePolicy,
    *,
    raw_content_hash: str = "sha256:" + ("5" * 64),
) -> AuthorityEvidence:
    return build_authority_evidence(
        authority_source_policy_id=policy.authority_source_policy_id,
        authority_source_identifier=policy.source_namespace,
        authority_classification=policy.authority_classification,
        authority_source_locator=(
            "authority-verification://kr-supreme-court/verified-corporate-extract"
        ),
        authority_document_reference="iros-verified-extract-1101110000000",
        source_document_kind=policy.allowed_document_kinds[0],
        authority_external_key="iros-verified-extract-1101110000000",
        raw_content_hash=raw_content_hash,
        parser_contract_version=policy.admitted_parser_contract_versions[0],
        evidence_kind=AuthorityEvidenceKind.ASSERTION,
        authority_scope=AuthorityScope.LEGAL_JURISDICTION,
        subject_role=AuthoritySubjectRole.KOREAN_REGISTERED_LEGAL_ENTITY,
        policy_maximum_issuer_authority_weight=AuthorityWeight.DECISIVE,
        claim_field="registry.legal_jurisdiction",
        raw_claim_value="KR",
        normalized_claim_value="KR",
        authority_published_at=None,
        authority_accepted_at=None,
        authority_as_of_date=None,
        authority_effective_at=None,
        authority_effective_date=None,
        authority_time_missing_reasons={
            "authority_published_at": AuthorityTimeMissingReason.NOT_SUPPLIED_BY_AUTHORITY,
            "authority_accepted_at": AuthorityTimeMissingReason.NOT_SUPPLIED_BY_AUTHORITY,
            "authority_as_of_date": AuthorityTimeMissingReason.NOT_SUPPLIED_BY_AUTHORITY,
            "authority_effective_at": AuthorityTimeMissingReason.NOT_SUPPLIED_BY_AUTHORITY,
            "authority_effective_date": AuthorityTimeMissingReason.NOT_SUPPLIED_BY_AUTHORITY,
        },
        access_disposition=AuthorityAccessDisposition.PERMITTED,
        license_disposition=AuthorityLicenseDisposition.PERMITTED,
        origin_data_mode=AuthorityOriginDataMode.PRODUCTION_AUTHORITY,
        origin_adapter_class=policy.admitted_adapter_contract_versions[0],
        origin_source_system=policy.source_namespace,
        lineage_tainted=False,
        lineage_ancestor_tainted=False,
        lineage_ancestor_hashes=(),
    )


def evidence_application(
    policy: AuthoritySourcePolicy,
    evidence: AuthorityEvidence,
    *,
    provider_security_identity_id: str = PROVIDER_ID,
    provider_observation_ids: tuple[str, ...] = (PROVIDER_OBSERVATION_ID,),
    identifier_value: str = CORP_CODE,
    evaluated_at: datetime = NOW,
    authority_relation_head_hash: str = RELATION_HEAD_HASH,
) -> AuthorityEvidenceApplication:
    fixture = policy.permanent_fixture_test_taint
    return build_authority_evidence_application(
        policy=policy,
        evidence=evidence,
        provider_security_identity_id=provider_security_identity_id,
        provider_observation_ids=provider_observation_ids,
        candidate_jurisdiction=Jurisdiction.KR,
        candidate_identifier_kind=AuthorityIdentifierKind.DART_CORP_CODE,
        candidate_identifier_value=identifier_value,
        claim_target_field="issuer.corp_code",
        requested_status=(
            AuthorityEvidenceApplicationStatus.PROVENANCE_ONLY
            if fixture
            else AuthorityEvidenceApplicationStatus.APPLIED_DECISIVE
        ),
        requested_effective_weight=(AuthorityWeight.ZERO if fixture else AuthorityWeight.DECISIVE),
        reason_codes=("TEST_TAINT_RETAINED" if fixture else "SOURCE_ADMITTED",),
        authority_relation_head_hash=authority_relation_head_hash,
        evaluated_at=evaluated_at,
    )


def jurisdiction_evidence_application(
    policy: AuthoritySourcePolicy,
    evidence: AuthorityEvidence,
    *,
    provider_security_identity_id: str = PROVIDER_ID,
    provider_observation_ids: tuple[str, ...] = (PROVIDER_OBSERVATION_ID,),
    identifier_value: str = CORP_CODE,
    evaluated_at: datetime = NOW,
) -> AuthorityEvidenceApplication:
    return build_authority_evidence_application(
        policy=policy,
        evidence=evidence,
        provider_security_identity_id=provider_security_identity_id,
        provider_observation_ids=provider_observation_ids,
        candidate_jurisdiction=Jurisdiction.KR,
        candidate_identifier_kind=AuthorityIdentifierKind.DART_CORP_CODE,
        candidate_identifier_value=identifier_value,
        claim_target_field="issuer.jurisdiction",
        requested_status=AuthorityEvidenceApplicationStatus.APPLIED_DECISIVE,
        requested_effective_weight=AuthorityWeight.DECISIVE,
        reason_codes=("VERIFIED_FIELD_OWNER_JURISDICTION",),
        authority_relation_head_hash=RELATION_HEAD_HASH,
        evaluated_at=evaluated_at,
    )


def authority_bundle(
    application: AuthorityEvidenceApplication,
    *,
    identifier_value: str = CORP_CODE,
    built_at: datetime = NOW,
) -> AuthorityBundle:
    scope_results = (
        build_authority_bundle_scope_result(
            authority_scope=AuthorityScope.ISSUER_REGULATORY_ID,
            scope_status=(
                AuthorityBundleScopeStatus.SATISFIED
                if application.application_status
                == AuthorityEvidenceApplicationStatus.APPLIED_DECISIVE
                else AuthorityBundleScopeStatus.UNUSABLE
            ),
            reason_codes=(
                "DECISIVE_REGULATORY_ID"
                if application.application_status
                == AuthorityEvidenceApplicationStatus.APPLIED_DECISIVE
                else "TEST_LINEAGE_UNUSABLE",
            ),
        ),
        build_authority_bundle_scope_result(
            authority_scope=AuthorityScope.LEGAL_JURISDICTION,
            scope_status=AuthorityBundleScopeStatus.MISSING,
            reason_codes=("JURISDICTION_CONTRACT_REQUIRED",),
        ),
    )
    values = {
        "provider_security_identity_id": application.provider_security_identity_id,
        "provider_observation_ids": application.provider_observation_ids,
        "candidate_jurisdiction": Jurisdiction.KR,
        "candidate_identifier_kind": AuthorityIdentifierKind.DART_CORP_CODE,
        "candidate_identifier_value": identifier_value,
        "applications": (application,),
        "required_scope_results": scope_results,
        "legal_jurisdiction_result": AuthorityLegalJurisdictionResult.UNRESOLVED,
        "collision_scan_result": AuthorityCollisionScanResult.CLEAR,
        "collision_claim_candidate_fingerprints": (application.candidate_fingerprint,),
        "built_at": built_at,
    }
    if application.production_authority_admitted:
        return build_production_authority_bundle(**values)
    return build_isolated_test_authority_bundle(**values)


def review_ready_foundation_bundle(
    regulatory_application: AuthorityEvidenceApplication,
    jurisdiction_application: AuthorityEvidenceApplication,
    *,
    built_at: datetime = NOW,
) -> AuthorityBundle:
    scope_results = (
        build_authority_bundle_scope_result(
            authority_scope=AuthorityScope.ISSUER_REGULATORY_ID,
            scope_status=AuthorityBundleScopeStatus.SATISFIED,
            reason_codes=("DECISIVE_REGULATORY_ID",),
        ),
        build_authority_bundle_scope_result(
            authority_scope=AuthorityScope.LEGAL_JURISDICTION,
            scope_status=AuthorityBundleScopeStatus.SATISFIED,
            reason_codes=("DECISIVE_LEGAL_JURISDICTION",),
        ),
    )
    return build_production_authority_bundle(
        provider_security_identity_id=(regulatory_application.provider_security_identity_id),
        provider_observation_ids=regulatory_application.provider_observation_ids,
        candidate_jurisdiction=Jurisdiction.KR,
        candidate_identifier_kind=AuthorityIdentifierKind.DART_CORP_CODE,
        candidate_identifier_value=CORP_CODE,
        applications=(regulatory_application, jurisdiction_application),
        required_scope_results=scope_results,
        legal_jurisdiction_result=AuthorityLegalJurisdictionResult.ESTABLISHED,
        collision_scan_result=AuthorityCollisionScanResult.CLEAR,
        collision_claim_candidate_fingerprints=(regulatory_application.candidate_fingerprint,),
        built_at=built_at,
    )


def seed_provider_lineage(
    sessions: sessionmaker[Session],
    *,
    include_second: bool = False,
) -> None:
    providers = [(PROVIDER_ID, PROVIDER_OBSERVATION_ID, "005930")]
    if include_second:
        providers.append((SECOND_PROVIDER_ID, SECOND_PROVIDER_OBSERVATION_ID, "000660"))
    with sessions.begin() as session:
        for index, (provider_id, observation_id, symbol) in enumerate(providers):
            request_id = f"canonical_request_authority_{index}"
            raw_id = f"raw_response_authority_{index}"
            source_id = f"provider_source_authority_{index}"
            session.add(
                CanonicalRequestRow(
                    canonical_request_id=request_id,
                    provider="TOSS_OPEN_API",
                    method="GET",
                    path_template="/api/v1/stock-infos",
                    canonical_query_json="{}",
                    canonical_query_hash=authority_sha256({}),
                    provider_contract_version="toss-provider/0.1.0",
                    payload_json="{}",
                )
            )
            session.add(
                ProviderRawManifestRow(
                    raw_response_id=raw_id,
                    canonical_request_id=request_id,
                    http_status=200,
                    raw_content_hash=RAW_HASH,
                    raw_storage_ref=f"raw:sha256/{index}",
                    fetched_at="2026-08-26T01:02:03Z",
                    response_metadata_json="{}",
                    provider_contract_version="toss-provider/0.1.0",
                    payload_json="{}",
                )
            )
            session.add(
                ProviderSourceVersionRow(
                    source_version_id=source_id,
                    canonical_request_id=request_id,
                    raw_response_id=raw_id,
                    dataset="STOCK_DETAIL",
                    http_status=200,
                    raw_content_hash=RAW_HASH,
                    provider_contract_version="toss-provider/0.1.0",
                    revision_status="ORIGINAL",
                    supersedes_id=None,
                    normalized_content_hash=authority_sha256({"provider": provider_id}),
                    payload_json="{}",
                )
            )
            session.flush()
            session.add(
                ProviderSecurityIdentityRow(
                    provider_security_identity_id=provider_id,
                    provider="TOSS_OPEN_API",
                    market="KR",
                    allocation_anchor_hash=authority_sha256({"anchor": provider_id}),
                    identity_state="ACTIVE",
                    mapping_status="UNRESOLVED",
                    first_source_version_id=source_id,
                    latest_source_version_id=source_id,
                    provider_contract_version="toss-provider/0.1.0",
                    payload_json="{}",
                )
            )
            session.flush()
            session.add(
                ProviderSecurityMasterObservationRow(
                    observation_id=observation_id,
                    source_version_id=source_id,
                    normalized_record_id=None,
                    provider_security_identity_id=provider_id,
                    provider="TOSS_OPEN_API",
                    market="KR",
                    symbol=symbol,
                    staging_state="ELIGIBLE_FOR_MAPPING",
                    reconciliation_outcome="IDENTITY_REUSED",
                    eligible_for_mapping=1,
                    provider_contract_version="toss-provider/0.1.0",
                    payload_json="{}",
                )
            )
