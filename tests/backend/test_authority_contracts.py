from __future__ import annotations

from datetime import timedelta

import pytest
from pydantic import ValidationError

from authority_test_helpers import (
    CORP_CODE,
    LATER,
    LATEST_REVISION_HASH,
    NOW,
    PROVIDER_ID,
    PROVIDER_OBSERVATION_ID,
    RAW_HASH,
    RELATION_HEAD_HASH,
    RETRIEVAL_FINGERPRINT,
    authority_bundle,
    authority_evidence,
    evidence_application,
    fixture_source_policy,
    production_source_policy,
)
from toss_dashboard_api.contracts.authority import (
    AuthorityAccessDisposition,
    AuthorityBundleScopeStatus,
    AuthorityClassification,
    AuthorityCollisionScanResult,
    AuthorityEvidenceApplication,
    AuthorityEvidenceApplicationStatus,
    AuthorityFreshnessResult,
    AuthorityIdentifierKind,
    AuthorityIngestionMode,
    AuthorityLegalJurisdictionResult,
    AuthorityLicenseDisposition,
    AuthorityOriginDataMode,
    AuthorityRetrievalStatus,
    AuthorityScope,
    AuthorityScopeRoleWeight,
    AuthoritySourcePolicy,
    AuthoritySubjectRole,
    AuthorityWeight,
    IssuerMachineDecisionState,
    build_authority_bundle_scope_result,
    build_authority_evidence,
    build_authority_evidence_application,
    build_authority_evidence_observation,
    build_authority_source_policy,
    build_issuer_decision,
    build_production_authority_bundle,
)
from toss_dashboard_api.contracts.enums import Jurisdiction, MappingStatus


def test_source_policy_identity_excludes_registration_time() -> None:
    first = production_source_policy(registered_at=NOW)
    replay = production_source_policy(registered_at=LATER)

    assert first.authority_source_policy_id == replay.authority_source_policy_id
    assert first.policy_content_hash == replay.policy_content_hash
    assert first.registered_at != replay.registered_at


def test_source_policy_scope_role_matrix_is_exact_and_ceiling_is_deterministic() -> None:
    policy = production_source_policy()

    assert (
        policy.maximum_weight_for(
            AuthorityScope.ISSUER_REGULATORY_ID,
            AuthoritySubjectRole.DART_DISCLOSURE_FILER,
        )
        == AuthorityWeight.DECISIVE
    )
    assert (
        policy.maximum_weight_for(
            AuthorityScope.LEGAL_JURISDICTION,
            AuthoritySubjectRole.DART_DISCLOSURE_FILER,
        )
        == AuthorityWeight.ZERO
    )


def test_production_policy_rejects_wildcard_and_fixture_root() -> None:
    rule = AuthorityScopeRoleWeight(
        authority_scope=AuthorityScope.ISSUER_REGULATORY_ID,
        subject_role=AuthoritySubjectRole.DART_DISCLOSURE_FILER,
        maximum_weight=AuthorityWeight.DECISIVE,
    )
    with pytest.raises(ValidationError):
        build_authority_source_policy(
            source_namespace="TEST_WILDCARD",
            field_owner="Invalid",
            authority_classification=AuthorityClassification.OFFICIAL_AUTHORITY,
            allowed_document_kinds=("DOCUMENT_V1",),
            credential_free_locator_roots=("fixture://authority/",),
            scope_role_weights=(rule,),
            ingestion_mode=AuthorityIngestionMode.AUTOMATED_OFFICIAL_PUBLIC,
            admitted_adapter_contract_versions=("adapter/0.1.0",),
            admitted_parser_contract_versions=("parser/0.1.0",),
            production_authority_eligible=True,
            required_access_disposition=AuthorityAccessDisposition.PERMITTED,
            required_license_disposition=AuthorityLicenseDisposition.PERMITTED,
            allowed_origin_data_modes=(AuthorityOriginDataMode.PRODUCTION_AUTHORITY,),
            permanent_fixture_test_taint=False,
            registered_at=NOW,
        )


def test_same_evidence_under_different_retrieval_times_has_same_evidence_id() -> None:
    policy = production_source_policy()
    evidence = authority_evidence(policy)
    replay = authority_evidence(policy)
    first_observation = build_authority_evidence_observation(
        evidence_id=evidence.evidence_id,
        fetched_at=NOW,
        raw_content_hash=evidence.raw_content_hash,
        authority_source_locator=evidence.authority_source_locator,
        authority_document_reference=evidence.authority_document_reference,
        retrieval_status=AuthorityRetrievalStatus.SUCCEEDED,
        secret_free_retrieval_fingerprint=RETRIEVAL_FINGERPRINT,
        safe_status_code="OK",
    )
    later_observation = build_authority_evidence_observation(
        evidence_id=evidence.evidence_id,
        fetched_at=LATER,
        raw_content_hash=evidence.raw_content_hash,
        authority_source_locator=evidence.authority_source_locator,
        authority_document_reference=evidence.authority_document_reference,
        retrieval_status=AuthorityRetrievalStatus.SUCCEEDED,
        secret_free_retrieval_fingerprint=RETRIEVAL_FINGERPRINT,
        safe_status_code="OK",
    )

    assert replay.evidence_id == evidence.evidence_id
    assert later_observation.evidence_id == first_observation.evidence_id
    assert (
        later_observation.authority_evidence_observation_id
        != first_observation.authority_evidence_observation_id
    )


def test_raw_claim_value_is_required_independently_of_document_hash() -> None:
    with pytest.raises(ValueError, match="raw_claim_value is required"):
        authority_evidence(
            production_source_policy(),
            raw_content_hash=RAW_HASH,
            raw_claim_value=None,
        )


def test_raw_and_normalized_claim_values_are_both_semantic() -> None:
    policy = production_source_policy()
    first = authority_evidence(policy, raw_claim_value="00126380")
    changed_raw = authority_evidence(policy, raw_claim_value=" 00126380 ")
    changed_normalized = authority_evidence(
        policy,
        normalized_claim_value="00126381",
    )

    assert first.evidence_id != changed_raw.evidence_id
    assert first.evidence_id != changed_normalized.evidence_id


def test_fixture_policy_has_permanent_zero_weight_taint() -> None:
    policy = fixture_source_policy()
    evidence = authority_evidence(policy)
    application = evidence_application(policy, evidence)

    assert policy.permanent_fixture_test_taint is True
    assert policy.production_authority_eligible is False
    assert policy.maximum_issuer_authority_weight == AuthorityWeight.ZERO
    assert evidence.lineage_tainted is True
    assert application.production_authority_admitted is False
    assert application.effective_issuer_authority_weight == AuthorityWeight.ZERO


def test_fixture_namespace_cannot_be_relabelled_as_production_policy() -> None:
    fixture = fixture_source_policy()
    values = fixture.model_dump(mode="python")
    values.update(
        production_authority_eligible=True,
        permanent_fixture_test_taint=False,
        ingestion_mode=AuthorityIngestionMode.AUTOMATED_OFFICIAL_PUBLIC,
        allowed_origin_data_modes=(AuthorityOriginDataMode.PRODUCTION_AUTHORITY,),
    )

    with pytest.raises(
        ValidationError,
        match="fixture/test namespace must retain permanent taint",
    ):
        AuthoritySourcePolicy.model_validate(values)


def test_copied_fixture_lineage_remains_tainted_after_official_relabel() -> None:
    zero_policy = build_authority_source_policy(
        source_namespace="OPENDART_CORP_CODE",
        field_owner="Financial Supervisory Service OpenDART",
        authority_classification=AuthorityClassification.OFFICIAL_AUTHORITY,
        allowed_document_kinds=("CORP_CODE_XML_V1",),
        credential_free_locator_roots=("https://opendart.fss.or.kr/",),
        scope_role_weights=(
            AuthorityScopeRoleWeight(
                authority_scope=AuthorityScope.ISSUER_REGULATORY_ID,
                subject_role=AuthoritySubjectRole.DART_DISCLOSURE_FILER,
                maximum_weight=AuthorityWeight.ZERO,
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
        registered_at=NOW,
    )
    evidence_values = authority_evidence(production_source_policy()).model_dump(mode="python")
    for computed in (
        "evidence_id",
        "evidence_content_hash",
        "evidence_provenance_hash",
    ):
        evidence_values.pop(computed)
    evidence_values.update(
        authority_source_policy_id=zero_policy.authority_source_policy_id,
        policy_maximum_issuer_authority_weight=AuthorityWeight.ZERO,
        lineage_tainted=True,
        lineage_ancestor_tainted=True,
        lineage_ancestor_hashes=("sha256:" + ("a" * 64),),
    )
    relabelled = build_authority_evidence(**evidence_values)
    application = build_authority_evidence_application(
        policy=zero_policy,
        evidence=relabelled,
        provider_security_identity_id=PROVIDER_ID,
        provider_observation_ids=(PROVIDER_OBSERVATION_ID,),
        candidate_jurisdiction=Jurisdiction.KR,
        candidate_identifier_kind=AuthorityIdentifierKind.DART_CORP_CODE,
        candidate_identifier_value=CORP_CODE,
        claim_target_field="issuer.corp_code",
        requested_status=AuthorityEvidenceApplicationStatus.PROVENANCE_ONLY,
        requested_effective_weight=AuthorityWeight.ZERO,
        reason_codes=("MANUALLY_RELABELLED",),
        authority_relation_head_hash=RELATION_HEAD_HASH,
        evaluated_at=NOW,
    )

    assert relabelled.lineage_tainted is True
    assert application.production_authority_admitted is False
    assert (
        application.application_status == AuthorityEvidenceApplicationStatus.REJECTED_SOURCE_POLICY
    )
    assert "FIXTURE_TEST_LINEAGE_TAINTED" in application.reason_codes


def test_unlisted_scope_application_is_zero_and_unusable() -> None:
    policy = production_source_policy()
    evidence_values = authority_evidence(policy).model_dump(mode="python")
    evidence_values.update(
        authority_scope=AuthorityScope.LEGAL_JURISDICTION,
        policy_maximum_issuer_authority_weight=AuthorityWeight.ZERO,
    )
    evidence_values.pop("evidence_id")
    evidence_values.pop("evidence_content_hash")
    evidence_values.pop("evidence_provenance_hash")
    evidence = build_authority_evidence(**evidence_values)
    application = build_authority_evidence_application(
        policy=policy,
        evidence=evidence,
        provider_security_identity_id=PROVIDER_ID,
        provider_observation_ids=(PROVIDER_OBSERVATION_ID,),
        candidate_jurisdiction=Jurisdiction.KR,
        candidate_identifier_kind=AuthorityIdentifierKind.DART_CORP_CODE,
        candidate_identifier_value=CORP_CODE,
        claim_target_field="issuer.jurisdiction",
        requested_status=AuthorityEvidenceApplicationStatus.APPLIED_DECISIVE,
        requested_effective_weight=AuthorityWeight.DECISIVE,
        reason_codes=("PARSER_LABEL_ONLY",),
        authority_relation_head_hash=RELATION_HEAD_HASH,
        evaluated_at=NOW,
    )

    assert (
        application.application_status == AuthorityEvidenceApplicationStatus.REJECTED_SOURCE_POLICY
    )
    assert application.effective_issuer_authority_weight == AuthorityWeight.ZERO
    assert "SCOPE_ROLE_NOT_ADMITTED" in application.reason_codes


def test_policy_ceiling_cannot_be_raised_by_application_caller() -> None:
    policy = fixture_source_policy()
    evidence = authority_evidence(policy)
    application = build_authority_evidence_application(
        policy=policy,
        evidence=evidence,
        provider_security_identity_id=PROVIDER_ID,
        provider_observation_ids=(PROVIDER_OBSERVATION_ID,),
        candidate_jurisdiction=Jurisdiction.KR,
        candidate_identifier_kind=AuthorityIdentifierKind.DART_CORP_CODE,
        candidate_identifier_value=CORP_CODE,
        claim_target_field="issuer.corp_code",
        requested_status=AuthorityEvidenceApplicationStatus.APPLIED_DECISIVE,
        requested_effective_weight=AuthorityWeight.DECISIVE,
        reason_codes=("CALLER_REQUESTED_DECISIVE",),
        authority_relation_head_hash=RELATION_HEAD_HASH,
        evaluated_at=NOW,
    )

    assert application.effective_issuer_authority_weight == AuthorityWeight.ZERO
    assert "POLICY_WEIGHT_CEILING_EXCEEDED" in application.reason_codes


def test_application_identity_binds_exact_candidate_and_excludes_evaluation_time() -> None:
    policy = production_source_policy()
    evidence = authority_evidence(policy)
    first = evidence_application(policy, evidence, evaluated_at=NOW)
    replay = evidence_application(policy, evidence, evaluated_at=LATER)
    another_candidate = evidence_application(
        policy,
        evidence,
        identifier_value="00126381",
    )

    assert first.evidence_application_id == replay.evidence_application_id
    assert first.application_content_hash == replay.application_content_hash
    assert first.evidence_application_id != another_candidate.evidence_application_id
    assert (
        another_candidate.application_status
        == AuthorityEvidenceApplicationStatus.REJECTED_SUBJECT_MISMATCH
    )


def test_format_valid_corp_code_without_matching_fact_is_not_authority() -> None:
    policy = production_source_policy()
    evidence = authority_evidence(policy)
    application = evidence_application(
        policy,
        evidence,
        identifier_value="87654321",
    )

    assert (
        application.application_status
        == AuthorityEvidenceApplicationStatus.REJECTED_SUBJECT_MISMATCH
    )
    assert application.effective_issuer_authority_weight == AuthorityWeight.ZERO
    assert "REGULATORY_IDENTIFIER_CANDIDATE_MISMATCH" in application.reason_codes


def test_phase_one_fake_corp_code_cannot_enter_production_bundle() -> None:
    policy = production_source_policy()
    application = evidence_application(
        policy,
        authority_evidence(policy),
        identifier_value="90000001",
    )

    with pytest.raises(ValueError, match="synthetic authority identifier"):
        authority_bundle(application, identifier_value="90000001")


def test_phase_one_fake_cik_cannot_enter_production_bundle() -> None:
    policy = production_source_policy()
    evidence = authority_evidence(policy)
    application = build_authority_evidence_application(
        policy=policy,
        evidence=evidence,
        provider_security_identity_id=PROVIDER_ID,
        provider_observation_ids=(PROVIDER_OBSERVATION_ID,),
        candidate_jurisdiction=Jurisdiction.US,
        candidate_identifier_kind=AuthorityIdentifierKind.SEC_REGISTRANT_CIK,
        candidate_identifier_value="9999999999",
        claim_target_field="issuer.cik",
        requested_status=AuthorityEvidenceApplicationStatus.APPLIED_DECISIVE,
        requested_effective_weight=AuthorityWeight.DECISIVE,
        reason_codes=("FORMAT_VALID_ONLY",),
        authority_relation_head_hash=RELATION_HEAD_HASH,
        evaluated_at=NOW,
    )
    scope_results = (
        build_authority_bundle_scope_result(
            authority_scope=AuthorityScope.ISSUER_REGULATORY_ID,
            scope_status=AuthorityBundleScopeStatus.UNUSABLE,
            reason_codes=("REGISTRANT_AUTHORITY_MISSING",),
        ),
        build_authority_bundle_scope_result(
            authority_scope=AuthorityScope.LEGAL_JURISDICTION,
            scope_status=AuthorityBundleScopeStatus.MISSING,
            reason_codes=("JURISDICTION_CONTRACT_REQUIRED",),
        ),
    )

    with pytest.raises(ValueError, match="synthetic authority identifier"):
        build_production_authority_bundle(
            provider_security_identity_id=PROVIDER_ID,
            provider_observation_ids=(PROVIDER_OBSERVATION_ID,),
            candidate_jurisdiction=Jurisdiction.US,
            candidate_identifier_kind=AuthorityIdentifierKind.SEC_REGISTRANT_CIK,
            candidate_identifier_value="9999999999",
            applications=(application,),
            required_scope_results=scope_results,
            legal_jurisdiction_result=(AuthorityLegalJurisdictionResult.UNRESOLVED),
            collision_scan_result=AuthorityCollisionScanResult.CLEAR,
            collision_claim_candidate_fingerprints=(application.candidate_fingerprint,),
            built_at=NOW,
        )


def test_application_tamper_is_detected() -> None:
    policy = production_source_policy()
    application = evidence_application(policy, authority_evidence(policy))
    values = application.model_dump(mode="python")
    values["provider_security_identity_id"] = "provider_security_tampered"

    with pytest.raises(ValidationError, match="application_content_hash"):
        AuthorityEvidenceApplication.model_validate(values)


def test_bundle_identity_is_independent_of_application_input_order() -> None:
    policy = production_source_policy()
    first_evidence = authority_evidence(policy)
    second_evidence = authority_evidence(
        policy,
        raw_content_hash="sha256:" + ("6" * 64),
    )
    first_application = evidence_application(policy, first_evidence)
    second_application = evidence_application(policy, second_evidence)
    base = authority_bundle(first_application)
    values = {
        "provider_security_identity_id": PROVIDER_ID,
        "provider_observation_ids": (PROVIDER_OBSERVATION_ID,),
        "candidate_jurisdiction": Jurisdiction.KR,
        "candidate_identifier_kind": AuthorityIdentifierKind.DART_CORP_CODE,
        "candidate_identifier_value": CORP_CODE,
        "required_scope_results": base.required_scope_results,
        "legal_jurisdiction_result": base.legal_jurisdiction_result,
        "collision_scan_result": base.collision_scan_result,
        "collision_claim_candidate_fingerprints": (first_application.candidate_fingerprint,),
        "built_at": NOW,
    }
    forward = build_production_authority_bundle(
        **values,
        applications=(first_application, second_application),
    )
    reverse = build_production_authority_bundle(
        **values,
        applications=(second_application, first_application),
    )

    assert forward.authority_bundle_id == reverse.authority_bundle_id
    assert forward.bundle_content_hash == reverse.bundle_content_hash


@pytest.mark.parametrize(
    "scope_status",
    [
        AuthorityBundleScopeStatus.MISSING,
        AuthorityBundleScopeStatus.CONFLICT,
        AuthorityBundleScopeStatus.STALE,
        AuthorityBundleScopeStatus.UNUSABLE,
    ],
)
def test_negative_scope_results_are_explicit(
    scope_status: AuthorityBundleScopeStatus,
) -> None:
    result = build_authority_bundle_scope_result(
        authority_scope=AuthorityScope.LEGAL_JURISDICTION,
        scope_status=scope_status,
        reason_codes=(f"EXPLICIT_{scope_status.value}",),
    )

    assert result.scope_status == scope_status
    assert result.reason_codes == (f"EXPLICIT_{scope_status.value}",)


def test_deterministic_decision_identity_excludes_evaluation_time() -> None:
    policy = production_source_policy()
    bundle = authority_bundle(evidence_application(policy, authority_evidence(policy)))
    first = build_issuer_decision(
        bundle=bundle,
        decision_state=IssuerMachineDecisionState.UNRESOLVED,
        reason_codes=("JURISDICTION_CONTRACT_REQUIRED",),
        latest_revision_check_hash=LATEST_REVISION_HASH,
        freshness_policy_version="conservative-approval-freshness/0.1.0",
        freshness_result=AuthorityFreshnessResult.CURRENT,
        collision_scan_hash=bundle.collision_scan_hash,
        evaluated_at=NOW,
    )
    replay = build_issuer_decision(
        bundle=bundle,
        decision_state=IssuerMachineDecisionState.UNRESOLVED,
        reason_codes=("JURISDICTION_CONTRACT_REQUIRED",),
        latest_revision_check_hash=LATEST_REVISION_HASH,
        freshness_policy_version="conservative-approval-freshness/0.1.0",
        freshness_result=AuthorityFreshnessResult.CURRENT,
        collision_scan_hash=bundle.collision_scan_hash,
        evaluated_at=LATER,
    )

    assert first.issuer_decision_id == replay.issuer_decision_id
    assert first.decision_content_hash == replay.decision_content_hash
    assert first.decision_audit_hash != replay.decision_audit_hash


def test_ready_for_review_requires_current_freshness() -> None:
    policy = production_source_policy()
    bundle = authority_bundle(evidence_application(policy, authority_evidence(policy)))

    with pytest.raises(ValidationError, match="requires current evidence"):
        build_issuer_decision(
            bundle=bundle,
            decision_state=IssuerMachineDecisionState.READY_FOR_MANUAL_REVIEW,
            reason_codes=("ALL_REQUIRED_SCOPES_SATISFIED",),
            latest_revision_check_hash=LATEST_REVISION_HASH,
            freshness_policy_version="conservative-approval-freshness/0.1.0",
            freshness_result=AuthorityFreshnessResult.STALE,
            collision_scan_hash=bundle.collision_scan_hash,
            evaluated_at=NOW,
        )


def test_ready_for_review_rejects_incomplete_authority_bundle() -> None:
    policy = production_source_policy()
    bundle = authority_bundle(evidence_application(policy, authority_evidence(policy)))

    with pytest.raises(ValueError, match="complete decisive production bundle"):
        build_issuer_decision(
            bundle=bundle,
            decision_state=IssuerMachineDecisionState.READY_FOR_MANUAL_REVIEW,
            reason_codes=("CALLER_ASSERTED_READY",),
            latest_revision_check_hash=LATEST_REVISION_HASH,
            freshness_policy_version="conservative-approval-freshness/0.1.0",
            freshness_result=AuthorityFreshnessResult.CURRENT,
            collision_scan_hash=bundle.collision_scan_hash,
            evaluated_at=NOW,
        )


def test_machine_states_do_not_include_human_approval_dispositions() -> None:
    assert {state.value for state in IssuerMachineDecisionState} == {
        "UNRESOLVED",
        "READY_FOR_MANUAL_REVIEW",
        "STALE",
        "REVIEW_REQUIRED",
    }


def test_mapping_status_remains_exactly_two_value_phase_contract() -> None:
    assert tuple(status.value for status in MappingStatus) == (
        "VERIFIED",
        "UNRESOLVED",
    )


def test_authority_semantics_reject_binary_float() -> None:
    with pytest.raises(ValueError, match="forbids binary float"):
        authority_evidence(
            production_source_policy(),
            raw_claim_value=1.25,
        )


def test_authority_semantics_normalize_unicode_nfc() -> None:
    policy = production_source_policy()
    first = authority_evidence(policy, raw_claim_value="가")
    decomposed = authority_evidence(policy, raw_claim_value="가")

    assert first.evidence_id == decomposed.evidence_id


def test_current_clock_and_retrieval_age_do_not_enter_bundle_identity() -> None:
    policy = production_source_policy()
    application = evidence_application(policy, authority_evidence(policy))

    first = authority_bundle(application, built_at=NOW)
    later = authority_bundle(application, built_at=NOW + timedelta(days=30))

    assert first.authority_bundle_id == later.authority_bundle_id
