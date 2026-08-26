from __future__ import annotations

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from authority_test_helpers import (
    CORP_CODE,
    LATER,
    LATEST_REVISION_HASH,
    NOW,
    PROVIDER_ID,
    RETRIEVAL_FINGERPRINT,
    SECOND_PROVIDER_ID,
    SECOND_PROVIDER_OBSERVATION_ID,
    authority_bundle,
    authority_evidence,
    evidence_application,
    fixture_source_policy,
    production_source_policy,
    seed_provider_lineage,
)
from toss_dashboard_api.contracts.authority import (
    AuthorityBundle,
    AuthorityFreshnessResult,
    AuthorityIdentifierKind,
    AuthorityRetrievalStatus,
    AuthoritySubjectRole,
    IssuerMachineDecisionState,
    build_authority_evidence,
    build_authority_evidence_observation,
    build_authority_identifier_claim,
    build_issuer_decision,
)
from toss_dashboard_api.contracts.enums import Jurisdiction
from toss_dashboard_api.repositories.authority import (
    AuthorityLedgerConflict,
    AuthorityLedgerMode,
    SQLiteAuthorityLedgerRepository,
)
from toss_dashboard_api.storage.database import session_factory
from toss_dashboard_api.storage.models import (
    AuthorityBundleEvidenceApplicationRow,
    AuthorityBundleProviderObservationRow,
    AuthorityBundleScopeResultRow,
    AuthorityIdentifierClaimRow,
    IssuerRow,
    ProviderIdentityMappingRow,
    ProviderSecurityIdentityRow,
    SecurityRow,
)


def _repository(database_context, *, include_second: bool = False):
    sessions = session_factory(database_context.engine)
    seed_provider_lineage(sessions, include_second=include_second)
    policy = production_source_policy()
    return (
        SQLiteAuthorityLedgerRepository(
            sessions,
            production_policy_registry={
                policy.authority_source_policy_id: policy.policy_content_hash
            },
        ),
        sessions,
    )


def _observation(evidence, *, fetched_at=NOW):
    return build_authority_evidence_observation(
        evidence_id=evidence.evidence_id,
        fetched_at=fetched_at,
        raw_content_hash=evidence.raw_content_hash,
        authority_source_locator=evidence.authority_source_locator,
        authority_document_reference=evidence.authority_document_reference,
        retrieval_status=AuthorityRetrievalStatus.SUCCEEDED,
        secret_free_retrieval_fingerprint=RETRIEVAL_FINGERPRINT,
        safe_status_code="OK",
    )


def _persist_through_application(repository):
    policy = production_source_policy()
    evidence = authority_evidence(policy)
    observation = _observation(evidence)
    application = evidence_application(policy, evidence)
    assert repository.insert_or_verify_source_policy(policy).inserted is True
    assert repository.insert_or_verify_evidence(evidence).inserted is True
    assert repository.insert_or_verify_evidence_observation(observation).inserted is True
    assert repository.insert_or_verify_evidence_application(application).inserted is True
    return policy, evidence, observation, application


def test_immutable_insert_or_verify_is_idempotent(database_context) -> None:
    repository, _sessions = _repository(database_context)
    policy, evidence, observation, application = _persist_through_application(repository)

    assert repository.insert_or_verify_source_policy(policy).inserted is False
    assert repository.insert_or_verify_evidence(evidence).inserted is False
    assert repository.insert_or_verify_evidence_observation(observation).inserted is False
    assert repository.insert_or_verify_evidence_application(application).inserted is False


def test_same_evidence_id_with_different_immutable_provenance_is_conflict(
    database_context,
) -> None:
    repository, _sessions = _repository(database_context)
    policy = production_source_policy()
    evidence = authority_evidence(policy)
    changed_values = evidence.model_dump(mode="python")
    for computed in (
        "evidence_id",
        "evidence_content_hash",
        "evidence_provenance_hash",
    ):
        changed_values.pop(computed)
    changed_values["authority_source_locator"] = (
        "https://opendart.fss.or.kr/api/corpCode.xml?presentation=2"
    )
    changed = build_authority_evidence(**changed_values)
    assert changed.evidence_id == evidence.evidence_id
    assert changed.evidence_provenance_hash != evidence.evidence_provenance_hash

    repository.insert_or_verify_source_policy(policy)
    repository.insert_or_verify_evidence(evidence)
    with pytest.raises(AuthorityLedgerConflict, match="conflicting immutable"):
        repository.insert_or_verify_evidence(changed)


def test_application_requires_retrieval_observation(database_context) -> None:
    repository, _sessions = _repository(database_context)
    policy = production_source_policy()
    evidence = authority_evidence(policy)
    application = evidence_application(policy, evidence)
    repository.insert_or_verify_source_policy(policy)
    repository.insert_or_verify_evidence(evidence)

    with pytest.raises(AuthorityLedgerConflict, match="retrieval observation"):
        repository.insert_or_verify_evidence_application(application)


def test_application_same_semantic_id_different_audit_is_typed_conflict(
    database_context,
) -> None:
    repository, _sessions = _repository(database_context)
    policy, evidence, _observation_value, first = _persist_through_application(repository)
    replay = evidence_application(policy, evidence, evaluated_at=LATER)
    assert replay.evidence_application_id == first.evidence_application_id

    with pytest.raises(AuthorityLedgerConflict, match="conflicting immutable"):
        repository.insert_or_verify_evidence_application(replay)


def test_bundle_persists_exact_application_scope_and_provider_membership(
    database_context,
) -> None:
    repository, sessions = _repository(database_context)
    _policy, _evidence, _observation_value, application = _persist_through_application(repository)
    bundle = authority_bundle(application)

    result = repository.insert_or_verify_bundle(bundle)
    assert result.inserted is True
    assert repository.insert_or_verify_bundle(bundle).inserted is False
    assert repository.authority_bundle(bundle.authority_bundle_id) == bundle
    with sessions() as session:
        assert session.scalar(
            select(func.count()).select_from(AuthorityBundleEvidenceApplicationRow)
        ) == len(bundle.evidence_application_members)
        assert session.scalar(
            select(func.count()).select_from(AuthorityBundleScopeResultRow)
        ) == len(bundle.required_scope_results)
        assert session.scalar(
            select(func.count()).select_from(AuthorityBundleProviderObservationRow)
        ) == len(bundle.provider_observation_ids)


def test_bundle_rejects_application_bound_to_another_provider(
    database_context,
) -> None:
    repository, _sessions = _repository(database_context, include_second=True)
    policy, evidence, _observation_value, first = _persist_through_application(repository)
    second = evidence_application(
        policy,
        evidence,
        provider_security_identity_id=SECOND_PROVIDER_ID,
        provider_observation_ids=(SECOND_PROVIDER_OBSERVATION_ID,),
    )
    repository.insert_or_verify_evidence_application(second)
    values = authority_bundle(first).model_dump(mode="python")
    values["evidence_application_members"] = (
        {
            **values["evidence_application_members"][0],
            "evidence_application_id": second.evidence_application_id,
            "application_content_hash": second.application_content_hash,
            "provider_security_identity_id": SECOND_PROVIDER_ID,
        },
    )

    with pytest.raises(ValidationError, match="provider identity mismatch"):
        AuthorityBundle.model_validate(values)


def test_contradictory_identifier_claims_are_both_preserved(
    database_context,
) -> None:
    repository, sessions = _repository(database_context, include_second=True)
    policy, evidence, _observation_value, first_application = _persist_through_application(
        repository
    )
    second_application = evidence_application(
        policy,
        evidence,
        provider_security_identity_id=SECOND_PROVIDER_ID,
        provider_observation_ids=(SECOND_PROVIDER_OBSERVATION_ID,),
    )
    repository.insert_or_verify_evidence_application(second_application)
    first_claim = build_authority_identifier_claim(
        identifier_kind=AuthorityIdentifierKind.DART_CORP_CODE,
        normalized_identifier_value=CORP_CODE,
        candidate_jurisdiction=Jurisdiction.KR,
        provider_security_identity_id=PROVIDER_ID,
        application=first_application,
        evidence=evidence,
        policy=policy,
        claim_role=AuthoritySubjectRole.DART_DISCLOSURE_FILER,
        recorded_at=NOW,
    )
    second_claim = build_authority_identifier_claim(
        identifier_kind=AuthorityIdentifierKind.DART_CORP_CODE,
        normalized_identifier_value=CORP_CODE,
        candidate_jurisdiction=Jurisdiction.KR,
        provider_security_identity_id=SECOND_PROVIDER_ID,
        application=second_application,
        evidence=evidence,
        policy=policy,
        claim_role=AuthoritySubjectRole.DART_DISCLOSURE_FILER,
        recorded_at=LATER,
    )

    repository.insert_or_verify_identifier_claim(first_claim)
    repository.insert_or_verify_identifier_claim(second_claim)
    claims = repository.list_identifier_claims(
        identifier_kind=AuthorityIdentifierKind.DART_CORP_CODE.value,
        normalized_identifier_value=CORP_CODE,
    )
    assert {claim.authority_identifier_claim_id for claim in claims} == {
        first_claim.authority_identifier_claim_id,
        second_claim.authority_identifier_claim_id,
    }
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(AuthorityIdentifierClaimRow)) == 2
        assert session.scalar(select(func.count()).select_from(IssuerRow)) == 2


def test_identifier_claim_insertion_has_no_first_writer_canonical_winner(
    database_context,
) -> None:
    repository, sessions = _repository(database_context)
    policy, evidence, _observation_value, application = _persist_through_application(repository)
    before: dict[str, int] = {}
    with sessions() as session:
        for name, model in {
            "issuers": IssuerRow,
            "securities": SecurityRow,
            "verified_mappings": ProviderIdentityMappingRow,
        }.items():
            before[name] = int(session.scalar(select(func.count()).select_from(model)) or 0)
    claim = build_authority_identifier_claim(
        identifier_kind=AuthorityIdentifierKind.DART_CORP_CODE,
        normalized_identifier_value=CORP_CODE,
        candidate_jurisdiction=Jurisdiction.KR,
        provider_security_identity_id=PROVIDER_ID,
        application=application,
        evidence=evidence,
        policy=policy,
        claim_role=AuthoritySubjectRole.DART_DISCLOSURE_FILER,
        recorded_at=NOW,
    )
    repository.insert_or_verify_identifier_claim(claim)

    with sessions() as session:
        assert (
            int(session.scalar(select(func.count()).select_from(IssuerRow)) or 0)
            == before["issuers"]
        )
        assert (
            int(session.scalar(select(func.count()).select_from(SecurityRow)) or 0)
            == before["securities"]
        )
        assert (
            int(
                session.scalar(
                    select(func.count())
                    .select_from(ProviderIdentityMappingRow)
                    .where(ProviderIdentityMappingRow.mapping_status == "VERIFIED")
                )
                or 0
            )
            == 0
        )
        identity = session.get(ProviderSecurityIdentityRow, PROVIDER_ID)
        assert identity is not None
        assert identity.mapping_status == "UNRESOLVED"


def test_deterministic_decision_storage_is_insert_or_verify(database_context) -> None:
    repository, _sessions = _repository(database_context)
    _policy, _evidence, _observation_value, application = _persist_through_application(repository)
    bundle = authority_bundle(application)
    repository.insert_or_verify_bundle(bundle)
    decision = build_issuer_decision(
        bundle=bundle,
        decision_state=IssuerMachineDecisionState.UNRESOLVED,
        reason_codes=("JURISDICTION_CONTRACT_REQUIRED",),
        latest_revision_check_hash=LATEST_REVISION_HASH,
        freshness_policy_version="conservative-approval-freshness/0.1.0",
        freshness_result=AuthorityFreshnessResult.CURRENT,
        collision_scan_hash=bundle.collision_scan_hash,
        evaluated_at=NOW,
    )

    assert repository.insert_or_verify_decision(decision).inserted is True
    assert repository.insert_or_verify_decision(decision).inserted is False
    assert repository.issuer_decision(decision.issuer_decision_id) == decision


@pytest.mark.parametrize("operation", ["UPDATE", "DELETE"])
def test_append_only_trigger_rejects_source_policy_mutation(
    database_context,
    operation: str,
) -> None:
    repository, _sessions = _repository(database_context)
    policy = production_source_policy()
    repository.insert_or_verify_source_policy(policy)
    statement = (
        "UPDATE authority_source_policies SET field_owner = 'tampered' "
        "WHERE authority_source_policy_id = :policy_id"
        if operation == "UPDATE"
        else "DELETE FROM authority_source_policies WHERE authority_source_policy_id = :policy_id"
    )

    with pytest.raises(DBAPIError, match="append-only"):
        with database_context.engine.begin() as connection:
            connection.execute(
                text(statement),
                {"policy_id": policy.authority_source_policy_id},
            )


def test_test_repository_cannot_register_production_policy(database_context) -> None:
    sessions = session_factory(database_context.engine)
    repository = SQLiteAuthorityLedgerRepository(
        sessions,
        mode=AuthorityLedgerMode.TEST_ISOLATED,
    )

    with pytest.raises(AuthorityLedgerConflict, match="test-isolated"):
        repository.insert_or_verify_source_policy(production_source_policy())
    result = repository.insert_or_verify_source_policy(fixture_source_policy())
    assert result.inserted is True


def test_production_policy_requires_exact_server_owned_registry_entry(
    database_context,
) -> None:
    sessions = session_factory(database_context.engine)
    repository = SQLiteAuthorityLedgerRepository(sessions)

    with pytest.raises(AuthorityLedgerConflict, match="server-owned registry"):
        repository.insert_or_verify_source_policy(production_source_policy())


def test_repository_has_no_approval_or_canonical_write_methods() -> None:
    prohibited = {
        "approve",
        "authenticate",
        "create_issuer",
        "create_security",
        "promote",
        "set_mapping_verified",
        "update_link_head",
    }

    assert prohibited.isdisjoint(dir(SQLiteAuthorityLedgerRepository))
