from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session, sessionmaker

from toss_dashboard_api.contracts.authority import (
    AuthorityBundle,
    AuthorityEvidence,
    AuthorityEvidenceApplication,
    AuthorityEvidenceObservation,
    AuthorityEvidenceRelation,
    AuthorityIdentifierClaim,
    AuthoritySourcePolicy,
    IssuerDecision,
    IssuerMachineDecisionState,
    authority_sha256,
    bundle_satisfies_review_ready_foundation,
    canonical_authority_json_bytes,
)
from toss_dashboard_api.contracts.base import utc_to_string
from toss_dashboard_api.contracts.enums import ProviderIdentityState
from toss_dashboard_api.storage.models import (
    AuthorityBundleEvidenceApplicationRow,
    AuthorityBundleProviderObservationRow,
    AuthorityBundleRow,
    AuthorityBundleScopeResultRow,
    AuthorityEvidenceApplicationRow,
    AuthorityEvidenceObservationRow,
    AuthorityEvidenceRelationRow,
    AuthorityEvidenceRow,
    AuthorityIdentifierClaimRow,
    AuthoritySourcePolicyRow,
    IssuerDecisionRow,
    ProviderSecurityIdentityRow,
    ProviderSecurityMasterObservationRow,
)


class AuthorityLedgerMode(StrEnum):
    PRODUCTION_AUTHORITY = "PRODUCTION_AUTHORITY"
    TEST_ISOLATED = "TEST_ISOLATED"


class AuthorityLedgerError(RuntimeError):
    pass


class AuthorityLedgerConflict(AuthorityLedgerError):
    pass


@dataclass(frozen=True)
class AuthorityInsertResult[ContractT: BaseModel]:
    value: ContractT
    inserted: bool


def _payload_json(value: Any) -> str:
    return canonical_authority_json_bytes(value).decode("utf-8")


def _verify_payload[ContractT: BaseModel](
    stored_payload: str,
    incoming_payload: str,
    value: ContractT,
) -> ContractT:
    if stored_payload != incoming_payload:
        raise AuthorityLedgerConflict(
            "deterministic authority identity has conflicting immutable content"
        )
    return value


class SQLiteAuthorityLedgerRepository:
    """Low-level immutable CP3-C2-B2-A ledger persistence only.

    This class deliberately exposes no approval execution, link-head mutation,
    canonical issuer/security write, or ProviderIdentityMapping operation.
    """

    def __init__(
        self,
        sessions: sessionmaker[Session],
        *,
        mode: AuthorityLedgerMode = AuthorityLedgerMode.PRODUCTION_AUTHORITY,
        production_policy_registry: Mapping[str, str] | None = None,
    ) -> None:
        self._sessions = sessions
        self._mode = mode
        self._production_policy_registry = dict(production_policy_registry or {})

    def source_policy(self, policy_id: str) -> AuthoritySourcePolicy:
        with self._sessions() as session:
            row = session.get(AuthoritySourcePolicyRow, policy_id)
            if row is None:
                raise AuthorityLedgerError("authority source policy is missing")
            return AuthoritySourcePolicy.model_validate_json(row.payload_json, strict=False)

    def evidence(self, evidence_id: str) -> AuthorityEvidence:
        with self._sessions() as session:
            row = session.get(AuthorityEvidenceRow, evidence_id)
            if row is None:
                raise AuthorityLedgerError("authority evidence is missing")
            return AuthorityEvidence.model_validate_json(row.payload_json, strict=False)

    def evidence_application(self, application_id: str) -> AuthorityEvidenceApplication:
        with self._sessions() as session:
            row = session.get(AuthorityEvidenceApplicationRow, application_id)
            if row is None:
                raise AuthorityLedgerError("authority evidence application is missing")
            return AuthorityEvidenceApplication.model_validate_json(row.payload_json, strict=False)

    def authority_bundle(self, bundle_id: str) -> AuthorityBundle:
        with self._sessions() as session:
            row = session.get(AuthorityBundleRow, bundle_id)
            if row is None:
                raise AuthorityLedgerError("authority bundle is missing")
            return AuthorityBundle.model_validate_json(row.payload_json, strict=False)

    def issuer_decision(self, decision_id: str) -> IssuerDecision:
        with self._sessions() as session:
            row = session.get(IssuerDecisionRow, decision_id)
            if row is None:
                raise AuthorityLedgerError("issuer decision is missing")
            return IssuerDecision.model_validate_json(row.payload_json, strict=False)

    def insert_or_verify_source_policy(
        self, policy: AuthoritySourcePolicy
    ) -> AuthorityInsertResult[AuthoritySourcePolicy]:
        if self._mode == AuthorityLedgerMode.TEST_ISOLATED and policy.production_authority_eligible:
            raise AuthorityLedgerConflict(
                "test-isolated repository cannot register production authority policy"
            )
        if policy.production_authority_eligible and (
            self._production_policy_registry.get(policy.authority_source_policy_id)
            != policy.policy_content_hash
        ):
            raise AuthorityLedgerConflict(
                "production authority policy is absent from server-owned registry"
            )
        payload = _payload_json(policy)
        try:
            with self._sessions.begin() as session:
                existing = session.get(
                    AuthoritySourcePolicyRow,
                    policy.authority_source_policy_id,
                )
                if existing is not None:
                    return AuthorityInsertResult(
                        _verify_payload(existing.payload_json, payload, policy),
                        False,
                    )
                if policy.predecessor_policy_id is not None:
                    predecessor = session.get(
                        AuthoritySourcePolicyRow,
                        policy.predecessor_policy_id,
                    )
                    if predecessor is None:
                        raise AuthorityLedgerConflict("source policy predecessor does not exist")
                session.add(self._source_policy_row(policy, payload))
            return AuthorityInsertResult(policy, True)
        except AuthorityLedgerError:
            raise
        except (IntegrityError, OperationalError):
            raise AuthorityLedgerConflict("authority source policy persistence conflict") from None

    def insert_or_verify_evidence(
        self, evidence: AuthorityEvidence
    ) -> AuthorityInsertResult[AuthorityEvidence]:
        payload = _payload_json(evidence)
        try:
            with self._sessions.begin() as session:
                policy = self._required_policy(
                    session,
                    evidence.authority_source_policy_id,
                )
                self._validate_evidence_policy(policy, evidence)
                existing = session.get(AuthorityEvidenceRow, evidence.evidence_id)
                if existing is not None:
                    return AuthorityInsertResult(
                        _verify_payload(existing.payload_json, payload, evidence),
                        False,
                    )
                session.add(self._evidence_row(evidence, payload))
            return AuthorityInsertResult(evidence, True)
        except AuthorityLedgerError:
            raise
        except (IntegrityError, OperationalError):
            raise AuthorityLedgerConflict("authority evidence persistence conflict") from None

    def insert_or_verify_evidence_observation(
        self, observation: AuthorityEvidenceObservation
    ) -> AuthorityInsertResult[AuthorityEvidenceObservation]:
        payload = _payload_json(observation)
        try:
            with self._sessions.begin() as session:
                evidence_row = session.get(
                    AuthorityEvidenceRow,
                    observation.evidence_id,
                )
                if evidence_row is None:
                    raise AuthorityLedgerConflict("evidence observation requires existing evidence")
                evidence = AuthorityEvidence.model_validate_json(
                    evidence_row.payload_json, strict=False
                )
                if (
                    observation.raw_content_hash != evidence.raw_content_hash
                    or observation.authority_document_reference
                    != evidence.authority_document_reference
                ):
                    raise AuthorityLedgerConflict(
                        "evidence observation raw/document provenance mismatch"
                    )
                existing = session.get(
                    AuthorityEvidenceObservationRow,
                    observation.authority_evidence_observation_id,
                )
                if existing is not None:
                    return AuthorityInsertResult(
                        _verify_payload(existing.payload_json, payload, observation),
                        False,
                    )
                session.add(self._observation_row(observation, payload))
            return AuthorityInsertResult(observation, True)
        except AuthorityLedgerError:
            raise
        except (IntegrityError, OperationalError):
            raise AuthorityLedgerConflict(
                "authority evidence observation persistence conflict"
            ) from None

    def insert_or_verify_evidence_relation(
        self, relation: AuthorityEvidenceRelation
    ) -> AuthorityInsertResult[AuthorityEvidenceRelation]:
        payload = _payload_json(relation)
        try:
            with self._sessions.begin() as session:
                for evidence_id in (
                    relation.predecessor_evidence_id,
                    relation.successor_evidence_id,
                ):
                    if session.get(AuthorityEvidenceRow, evidence_id) is None:
                        raise AuthorityLedgerConflict("evidence relation endpoint does not exist")
                existing = session.get(
                    AuthorityEvidenceRelationRow,
                    relation.authority_evidence_relation_id,
                )
                if existing is not None:
                    return AuthorityInsertResult(
                        _verify_payload(existing.payload_json, payload, relation),
                        False,
                    )
                session.add(self._relation_row(relation, payload))
            return AuthorityInsertResult(relation, True)
        except AuthorityLedgerError:
            raise
        except (IntegrityError, OperationalError):
            raise AuthorityLedgerConflict(
                "authority evidence relation persistence conflict"
            ) from None

    def insert_or_verify_evidence_application(
        self, application: AuthorityEvidenceApplication
    ) -> AuthorityInsertResult[AuthorityEvidenceApplication]:
        payload = _payload_json(application)
        try:
            with self._sessions.begin() as session:
                evidence = self._required_evidence(session, application.evidence_id)
                policy = self._required_policy(
                    session,
                    application.authority_source_policy_id,
                )
                self._validate_application_dependencies(
                    session,
                    application,
                    evidence,
                    policy,
                )
                existing = session.get(
                    AuthorityEvidenceApplicationRow,
                    application.evidence_application_id,
                )
                if existing is not None:
                    return AuthorityInsertResult(
                        _verify_payload(existing.payload_json, payload, application),
                        False,
                    )
                session.add(self._application_row(application, payload))
            return AuthorityInsertResult(application, True)
        except AuthorityLedgerError:
            raise
        except (IntegrityError, OperationalError):
            raise AuthorityLedgerConflict(
                "authority evidence application persistence conflict"
            ) from None

    def insert_or_verify_bundle(
        self, bundle: AuthorityBundle
    ) -> AuthorityInsertResult[AuthorityBundle]:
        payload = _payload_json(bundle)
        try:
            with self._sessions.begin() as session:
                self._validate_bundle_dependencies(session, bundle)
                existing = session.get(
                    AuthorityBundleRow,
                    bundle.authority_bundle_id,
                )
                if existing is not None:
                    self._verify_stored_bundle(session, existing, payload, bundle)
                    return AuthorityInsertResult(bundle, False)
                session.add(self._bundle_row(bundle, payload))
                session.flush()
                self._append_bundle_membership(session, bundle)
            return AuthorityInsertResult(bundle, True)
        except AuthorityLedgerError:
            raise
        except (IntegrityError, OperationalError):
            raise AuthorityLedgerConflict("authority bundle persistence conflict") from None

    def insert_or_verify_identifier_claim(
        self, claim: AuthorityIdentifierClaim
    ) -> AuthorityInsertResult[AuthorityIdentifierClaim]:
        payload = _payload_json(claim)
        try:
            with self._sessions.begin() as session:
                application = self._required_application(
                    session,
                    claim.evidence_application_id,
                )
                if (
                    application.application_content_hash != claim.application_content_hash
                    or application.evidence_id != claim.evidence_id
                    or application.evidence_content_hash != claim.evidence_content_hash
                    or application.authority_source_policy_id != claim.authority_source_policy_id
                    or application.authority_source_policy_content_hash
                    != claim.authority_source_policy_content_hash
                    or application.provider_security_identity_id
                    != claim.provider_security_identity_id
                    or application.proposed_issuer_id != claim.proposed_issuer_id
                    or application.candidate_fingerprint != claim.candidate_fingerprint
                    or application.authority_scope != claim.claim_scope
                ):
                    raise AuthorityLedgerConflict(
                        "identifier claim does not match exact application"
                    )
                existing = session.get(
                    AuthorityIdentifierClaimRow,
                    claim.authority_identifier_claim_id,
                )
                if existing is not None:
                    return AuthorityInsertResult(
                        _verify_payload(existing.payload_json, payload, claim),
                        False,
                    )
                session.add(self._identifier_claim_row(claim, payload))
            return AuthorityInsertResult(claim, True)
        except AuthorityLedgerError:
            raise
        except (IntegrityError, OperationalError):
            raise AuthorityLedgerConflict(
                "authority identifier claim persistence conflict"
            ) from None

    def insert_or_verify_decision(
        self, decision: IssuerDecision
    ) -> AuthorityInsertResult[IssuerDecision]:
        payload = _payload_json(decision)
        try:
            with self._sessions.begin() as session:
                bundle = self._required_bundle(session, decision.authority_bundle_id)
                if (
                    bundle.bundle_content_hash != decision.authority_bundle_content_hash
                    or bundle.provider_security_identity_id
                    != decision.provider_security_identity_id
                    or bundle.proposed_issuer_id != decision.proposed_issuer_id
                    or bundle.collision_scan_hash != decision.collision_scan_hash
                ):
                    raise AuthorityLedgerConflict(
                        "issuer decision does not match exact authority bundle"
                    )
                if (
                    decision.decision_state == IssuerMachineDecisionState.READY_FOR_MANUAL_REVIEW
                    and not bundle_satisfies_review_ready_foundation(bundle)
                ):
                    raise AuthorityLedgerConflict(
                        "review-ready decision requires complete decisive bundle"
                    )
                if decision.supersedes_decision_id is not None:
                    predecessor = session.get(
                        IssuerDecisionRow,
                        decision.supersedes_decision_id,
                    )
                    if predecessor is None:
                        raise AuthorityLedgerConflict("issuer decision predecessor does not exist")
                    if predecessor.authority_bundle_id != decision.authority_bundle_id:
                        raise AuthorityLedgerConflict("issuer decision chain cannot change bundle")
                existing = session.get(
                    IssuerDecisionRow,
                    decision.issuer_decision_id,
                )
                if existing is not None:
                    return AuthorityInsertResult(
                        _verify_payload(existing.payload_json, payload, decision),
                        False,
                    )
                session.add(self._decision_row(decision, payload))
            return AuthorityInsertResult(decision, True)
        except AuthorityLedgerError:
            raise
        except (IntegrityError, OperationalError):
            raise AuthorityLedgerConflict("issuer decision persistence conflict") from None

    def list_identifier_claims(
        self,
        *,
        identifier_kind: str,
        normalized_identifier_value: str,
    ) -> list[AuthorityIdentifierClaim]:
        with self._sessions() as session:
            rows = session.scalars(
                select(AuthorityIdentifierClaimRow)
                .where(
                    AuthorityIdentifierClaimRow.identifier_kind == identifier_kind,
                    AuthorityIdentifierClaimRow.normalized_identifier_value
                    == normalized_identifier_value,
                )
                .order_by(AuthorityIdentifierClaimRow.authority_identifier_claim_id)
            ).all()
            return [
                AuthorityIdentifierClaim.model_validate_json(row.payload_json, strict=False)
                for row in rows
            ]

    @staticmethod
    def _required_policy(
        session: Session,
        policy_id: str,
    ) -> AuthoritySourcePolicy:
        row = session.get(AuthoritySourcePolicyRow, policy_id)
        if row is None:
            raise AuthorityLedgerConflict("authority source policy does not exist")
        return AuthoritySourcePolicy.model_validate_json(row.payload_json, strict=False)

    @staticmethod
    def _required_evidence(
        session: Session,
        evidence_id: str,
    ) -> AuthorityEvidence:
        row = session.get(AuthorityEvidenceRow, evidence_id)
        if row is None:
            raise AuthorityLedgerConflict("authority evidence does not exist")
        return AuthorityEvidence.model_validate_json(row.payload_json, strict=False)

    @staticmethod
    def _required_application(
        session: Session,
        application_id: str,
    ) -> AuthorityEvidenceApplication:
        row = session.get(AuthorityEvidenceApplicationRow, application_id)
        if row is None:
            raise AuthorityLedgerConflict("authority evidence application does not exist")
        return AuthorityEvidenceApplication.model_validate_json(row.payload_json, strict=False)

    @staticmethod
    def _required_bundle(session: Session, bundle_id: str) -> AuthorityBundle:
        row = session.get(AuthorityBundleRow, bundle_id)
        if row is None:
            raise AuthorityLedgerConflict("authority bundle does not exist")
        return AuthorityBundle.model_validate_json(row.payload_json, strict=False)

    @staticmethod
    def _validate_evidence_policy(
        policy: AuthoritySourcePolicy,
        evidence: AuthorityEvidence,
    ) -> None:
        maximum = policy.maximum_weight_for(
            evidence.authority_scope,
            evidence.subject_role,
        )
        explicitly_listed = any(
            rule.authority_scope == evidence.authority_scope
            and rule.subject_role == evidence.subject_role
            for rule in policy.scope_role_weights
        )
        expected_taint = (
            policy.permanent_fixture_test_taint
            or evidence.lineage_ancestor_tainted
            or evidence.origin_data_mode.value == "TEST_ONLY"
        )
        exact = (
            explicitly_listed
            and evidence.authority_source_identifier == policy.source_namespace
            and evidence.authority_classification == policy.authority_classification
            and evidence.source_document_kind in policy.allowed_document_kinds
            and evidence.parser_contract_version in policy.admitted_parser_contract_versions
            and evidence.origin_adapter_class in policy.admitted_adapter_contract_versions
            and evidence.origin_data_mode in policy.allowed_origin_data_modes
            and evidence.policy_maximum_issuer_authority_weight == maximum
            and evidence.access_disposition == policy.required_access_disposition
            and evidence.license_disposition == policy.required_license_disposition
            and evidence.lineage_tainted == expected_taint
            and any(
                evidence.authority_source_locator.startswith(root)
                for root in policy.credential_free_locator_roots
            )
        )
        if not exact:
            raise AuthorityLedgerConflict("authority evidence does not match exact source policy")

    @staticmethod
    def _required_provider_identity(
        session: Session,
        provider_security_identity_id: str,
    ) -> ProviderSecurityIdentityRow:
        row = session.get(
            ProviderSecurityIdentityRow,
            provider_security_identity_id,
        )
        if row is None:
            raise AuthorityLedgerConflict("provider security identity does not exist")
        if row.identity_state != ProviderIdentityState.ACTIVE.value:
            raise AuthorityLedgerConflict("authority candidate requires active provider identity")
        return row

    @classmethod
    def _validate_provider_observations(
        cls,
        session: Session,
        *,
        provider_security_identity_id: str,
        observation_ids: tuple[str, ...],
    ) -> None:
        cls._required_provider_identity(session, provider_security_identity_id)
        for observation_id in observation_ids:
            observation = session.get(
                ProviderSecurityMasterObservationRow,
                observation_id,
            )
            if observation is None:
                raise AuthorityLedgerConflict(
                    "authority lineage provider observation does not exist"
                )
            if observation.provider_security_identity_id != provider_security_identity_id:
                raise AuthorityLedgerConflict("provider observation is bound to another identity")

    @classmethod
    def _validate_application_dependencies(
        cls,
        session: Session,
        application: AuthorityEvidenceApplication,
        evidence: AuthorityEvidence,
        policy: AuthoritySourcePolicy,
    ) -> None:
        if (
            application.evidence_content_hash != evidence.evidence_content_hash
            or application.authority_source_policy_id != evidence.authority_source_policy_id
            or application.authority_scope != evidence.authority_scope
            or application.policy_maximum_issuer_authority_weight
            != evidence.policy_maximum_issuer_authority_weight
            or application.authority_source_policy_content_hash != policy.policy_content_hash
            or application.lineage_tainted != evidence.lineage_tainted
        ):
            raise AuthorityLedgerConflict(
                "evidence application does not match exact evidence/policy"
            )
        evidence_observation = session.scalar(
            select(AuthorityEvidenceObservationRow).where(
                AuthorityEvidenceObservationRow.evidence_id == application.evidence_id
            )
        )
        if evidence_observation is None:
            raise AuthorityLedgerConflict("evidence application requires retrieval observation")
        cls._validate_provider_observations(
            session,
            provider_security_identity_id=(application.provider_security_identity_id),
            observation_ids=application.provider_observation_ids,
        )

    @classmethod
    def _validate_bundle_dependencies(
        cls,
        session: Session,
        bundle: AuthorityBundle,
    ) -> None:
        cls._validate_provider_observations(
            session,
            provider_security_identity_id=bundle.provider_security_identity_id,
            observation_ids=bundle.provider_observation_ids,
        )
        bundle_observations = set(bundle.provider_observation_ids)
        for member in bundle.evidence_application_members:
            application = cls._required_application(
                session,
                member.evidence_application_id,
            )
            exact = (
                application.application_content_hash == member.application_content_hash
                and application.evidence_id == member.evidence_id
                and application.evidence_content_hash == member.evidence_content_hash
                and application.authority_source_policy_id == member.authority_source_policy_id
                and application.authority_source_policy_content_hash
                == member.authority_source_policy_content_hash
                and application.provider_security_identity_id
                == bundle.provider_security_identity_id
                and application.proposed_issuer_id == bundle.proposed_issuer_id
                and application.candidate_fingerprint == bundle.candidate_fingerprint
                and application.authority_scope == member.authority_scope
                and application.application_status == member.application_status
                and application.effective_issuer_authority_weight
                == member.effective_issuer_authority_weight
            )
            if not exact:
                raise AuthorityLedgerConflict(
                    "bundle member does not match exact evidence application"
                )
            if not set(application.provider_observation_ids).issubset(bundle_observations):
                raise AuthorityLedgerConflict(
                    "bundle omits provider lineage used by an application"
                )

    @classmethod
    def _verify_stored_bundle(
        cls,
        session: Session,
        row: AuthorityBundleRow,
        payload: str,
        bundle: AuthorityBundle,
    ) -> None:
        _verify_payload(row.payload_json, payload, bundle)
        application_rows = session.scalars(
            select(AuthorityBundleEvidenceApplicationRow)
            .where(
                AuthorityBundleEvidenceApplicationRow.authority_bundle_id
                == bundle.authority_bundle_id
            )
            .order_by(AuthorityBundleEvidenceApplicationRow.member_ordinal)
        ).all()
        scope_rows = session.scalars(
            select(AuthorityBundleScopeResultRow)
            .where(AuthorityBundleScopeResultRow.authority_bundle_id == bundle.authority_bundle_id)
            .order_by(AuthorityBundleScopeResultRow.authority_scope)
        ).all()
        observation_rows = session.scalars(
            select(AuthorityBundleProviderObservationRow)
            .where(
                AuthorityBundleProviderObservationRow.authority_bundle_id
                == bundle.authority_bundle_id
            )
            .order_by(AuthorityBundleProviderObservationRow.member_ordinal)
        ).all()
        if tuple(row.evidence_application_id for row in application_rows) != tuple(
            member.evidence_application_id for member in bundle.evidence_application_members
        ):
            raise AuthorityLedgerConflict("stored bundle application membership differs")
        if tuple(row.authority_scope for row in scope_rows) != tuple(
            result.authority_scope.value for result in bundle.required_scope_results
        ):
            raise AuthorityLedgerConflict("stored bundle scope membership differs")
        if tuple(row.provider_observation_id for row in observation_rows) != (
            bundle.provider_observation_ids
        ):
            raise AuthorityLedgerConflict("stored bundle provider lineage differs")

    @staticmethod
    def _source_policy_row(
        policy: AuthoritySourcePolicy,
        payload: str,
    ) -> AuthoritySourcePolicyRow:
        return AuthoritySourcePolicyRow(
            authority_source_policy_id=policy.authority_source_policy_id,
            contract_version=policy.contract_version,
            policy_content_hash=policy.policy_content_hash,
            source_namespace=policy.source_namespace,
            field_owner=policy.field_owner,
            authority_classification=policy.authority_classification.value,
            allowed_document_kinds_json=_payload_json(list(policy.allowed_document_kinds)),
            credential_free_locator_roots_json=_payload_json(
                list(policy.credential_free_locator_roots)
            ),
            allowed_authority_scopes_json=_payload_json(list(policy.allowed_authority_scopes)),
            allowed_subject_roles_json=_payload_json(list(policy.allowed_subject_roles)),
            scope_role_weights_json=_payload_json(list(policy.scope_role_weights)),
            maximum_issuer_authority_weight=(policy.maximum_issuer_authority_weight.value),
            ingestion_mode=policy.ingestion_mode.value,
            admitted_adapter_contract_versions_json=_payload_json(
                list(policy.admitted_adapter_contract_versions)
            ),
            admitted_parser_contract_versions_json=_payload_json(
                list(policy.admitted_parser_contract_versions)
            ),
            production_authority_eligible=int(policy.production_authority_eligible),
            required_access_disposition=policy.required_access_disposition.value,
            required_license_disposition=policy.required_license_disposition.value,
            allowed_origin_data_modes_json=_payload_json(list(policy.allowed_origin_data_modes)),
            permanent_fixture_test_taint=int(policy.permanent_fixture_test_taint),
            predecessor_policy_id=policy.predecessor_policy_id,
            policy_effective_at=(
                None
                if policy.policy_effective_at is None
                else utc_to_string(policy.policy_effective_at)
            ),
            registered_at=utc_to_string(policy.registered_at),
            payload_json=payload,
        )

    @staticmethod
    def _evidence_row(
        evidence: AuthorityEvidence,
        payload: str,
    ) -> AuthorityEvidenceRow:
        return AuthorityEvidenceRow(
            evidence_id=evidence.evidence_id,
            contract_version=evidence.contract_version,
            evidence_content_hash=evidence.evidence_content_hash,
            evidence_provenance_hash=evidence.evidence_provenance_hash,
            authority_source_policy_id=evidence.authority_source_policy_id,
            authority_source_identifier=evidence.authority_source_identifier,
            authority_classification=evidence.authority_classification.value,
            authority_source_locator=evidence.authority_source_locator,
            authority_document_reference=evidence.authority_document_reference,
            source_document_kind=evidence.source_document_kind,
            authority_external_key=evidence.authority_external_key,
            authority_source_document_id=evidence.authority_source_document_id,
            raw_content_hash=evidence.raw_content_hash,
            parser_contract_version=evidence.parser_contract_version,
            evidence_kind=evidence.evidence_kind.value,
            authority_scope=evidence.authority_scope.value,
            subject_role=evidence.subject_role.value,
            policy_maximum_issuer_authority_weight=(
                evidence.policy_maximum_issuer_authority_weight.value
            ),
            claim_field=evidence.claim_field,
            raw_claim_value_json=_payload_json(evidence.raw_claim_value),
            normalized_claim_value_json=_payload_json(evidence.normalized_claim_value),
            authority_published_at=(
                None
                if evidence.authority_published_at is None
                else utc_to_string(evidence.authority_published_at)
            ),
            authority_accepted_at=(
                None
                if evidence.authority_accepted_at is None
                else utc_to_string(evidence.authority_accepted_at)
            ),
            authority_as_of_date=evidence.authority_as_of_date,
            authority_effective_at=(
                None
                if evidence.authority_effective_at is None
                else utc_to_string(evidence.authority_effective_at)
            ),
            authority_effective_date=evidence.authority_effective_date,
            authority_time_missing_reasons_json=_payload_json(
                evidence.authority_time_missing_reasons
            ),
            access_disposition=evidence.access_disposition.value,
            license_disposition=evidence.license_disposition.value,
            origin_data_mode=evidence.origin_data_mode.value,
            origin_adapter_class=evidence.origin_adapter_class,
            origin_source_system=evidence.origin_source_system,
            lineage_tainted=int(evidence.lineage_tainted),
            lineage_ancestor_tainted=int(evidence.lineage_ancestor_tainted),
            lineage_ancestor_hashes_json=_payload_json(list(evidence.lineage_ancestor_hashes)),
            payload_json=payload,
        )

    @staticmethod
    def _observation_row(
        observation: AuthorityEvidenceObservation,
        payload: str,
    ) -> AuthorityEvidenceObservationRow:
        return AuthorityEvidenceObservationRow(
            authority_evidence_observation_id=(observation.authority_evidence_observation_id),
            contract_version=observation.contract_version,
            observation_content_hash=observation.observation_content_hash,
            evidence_id=observation.evidence_id,
            fetched_at=utc_to_string(observation.fetched_at),
            raw_content_hash=observation.raw_content_hash,
            authority_source_locator=observation.authority_source_locator,
            authority_document_reference=(observation.authority_document_reference),
            raw_storage_reference=observation.raw_storage_reference,
            retrieval_status=observation.retrieval_status.value,
            secret_free_retrieval_fingerprint=(observation.secret_free_retrieval_fingerprint),
            safe_status_code=observation.safe_status_code,
            payload_json=payload,
        )

    @staticmethod
    def _relation_row(
        relation: AuthorityEvidenceRelation,
        payload: str,
    ) -> AuthorityEvidenceRelationRow:
        return AuthorityEvidenceRelationRow(
            authority_evidence_relation_id=(relation.authority_evidence_relation_id),
            contract_version=relation.contract_version,
            relation_content_hash=relation.relation_content_hash,
            predecessor_evidence_id=relation.predecessor_evidence_id,
            successor_evidence_id=relation.successor_evidence_id,
            relation_type=relation.relation_type.value,
            authority_effective_at=(
                None
                if relation.authority_effective_at is None
                else utc_to_string(relation.authority_effective_at)
            ),
            authority_effective_date=relation.authority_effective_date,
            authority_effective_missing_reason=(
                None
                if relation.authority_effective_missing_reason is None
                else relation.authority_effective_missing_reason.value
            ),
            recorded_at=utc_to_string(relation.recorded_at),
            payload_json=payload,
        )

    @staticmethod
    def _application_row(
        application: AuthorityEvidenceApplication,
        payload: str,
    ) -> AuthorityEvidenceApplicationRow:
        return AuthorityEvidenceApplicationRow(
            evidence_application_id=application.evidence_application_id,
            contract_version=application.contract_version,
            application_content_hash=application.application_content_hash,
            evidence_id=application.evidence_id,
            evidence_content_hash=application.evidence_content_hash,
            provider_security_identity_id=(application.provider_security_identity_id),
            provider_observation_ids_json=_payload_json(list(application.provider_observation_ids)),
            proposed_issuer_id=application.proposed_issuer_id,
            candidate_fingerprint=application.candidate_fingerprint,
            authority_scope=application.authority_scope.value,
            claim_target_field=application.claim_target_field,
            authority_source_policy_id=application.authority_source_policy_id,
            authority_source_policy_content_hash=(application.authority_source_policy_content_hash),
            policy_maximum_issuer_authority_weight=(
                application.policy_maximum_issuer_authority_weight.value
            ),
            application_status=application.application_status.value,
            effective_issuer_authority_weight=(application.effective_issuer_authority_weight.value),
            reason_codes_json=_payload_json(list(application.reason_codes)),
            authority_relation_head_hash=(application.authority_relation_head_hash),
            application_rule_version=application.application_rule_version,
            production_authority_admitted=int(application.production_authority_admitted),
            lineage_tainted=int(application.lineage_tainted),
            evaluated_at=utc_to_string(application.evaluated_at),
            payload_json=payload,
        )

    @staticmethod
    def _bundle_row(bundle: AuthorityBundle, payload: str) -> AuthorityBundleRow:
        return AuthorityBundleRow(
            authority_bundle_id=bundle.authority_bundle_id,
            contract_version=bundle.contract_version,
            bundle_content_hash=bundle.bundle_content_hash,
            bundle_origin_data_mode=bundle.bundle_origin_data_mode.value,
            provider_security_identity_id=bundle.provider_security_identity_id,
            candidate_jurisdiction=bundle.candidate_jurisdiction.value,
            candidate_identifier_kind=bundle.candidate_identifier_kind.value,
            candidate_identifier_value=bundle.candidate_identifier_value,
            proposed_issuer_anchor=bundle.proposed_issuer_anchor,
            proposed_issuer_id=bundle.proposed_issuer_id,
            candidate_fingerprint=bundle.candidate_fingerprint,
            legal_jurisdiction_result=bundle.legal_jurisdiction_result.value,
            collision_scan_result=bundle.collision_scan_result.value,
            collision_claim_candidate_fingerprints_json=_payload_json(
                list(bundle.collision_claim_candidate_fingerprints)
            ),
            decision_rule_version=bundle.decision_rule_version,
            evidence_application_set_hash=(bundle.evidence_application_set_hash),
            source_policy_set_hash=bundle.source_policy_set_hash,
            provider_lineage_set_hash=bundle.provider_lineage_set_hash,
            collision_scan_hash=bundle.collision_scan_hash,
            built_at=utc_to_string(bundle.built_at),
            payload_json=payload,
        )

    @classmethod
    def _append_bundle_membership(
        cls,
        session: Session,
        bundle: AuthorityBundle,
    ) -> None:
        for ordinal, member in enumerate(bundle.evidence_application_members):
            membership = {
                "authority_bundle_id": bundle.authority_bundle_id,
                "evidence_application_id": member.evidence_application_id,
                "member_ordinal": ordinal,
                "bundle_content_hash": bundle.bundle_content_hash,
                **member.model_dump(mode="python"),
            }
            membership_hash = authority_sha256(membership)
            session.add(
                AuthorityBundleEvidenceApplicationRow(
                    authority_bundle_id=bundle.authority_bundle_id,
                    evidence_application_id=member.evidence_application_id,
                    member_ordinal=ordinal,
                    bundle_content_hash=bundle.bundle_content_hash,
                    application_content_hash=member.application_content_hash,
                    evidence_id=member.evidence_id,
                    evidence_content_hash=member.evidence_content_hash,
                    authority_source_policy_id=(member.authority_source_policy_id),
                    authority_source_policy_content_hash=(
                        member.authority_source_policy_content_hash
                    ),
                    provider_security_identity_id=(member.provider_security_identity_id),
                    proposed_issuer_id=member.proposed_issuer_id,
                    candidate_fingerprint=member.candidate_fingerprint,
                    authority_scope=member.authority_scope.value,
                    application_status=member.application_status.value,
                    effective_issuer_authority_weight=(
                        member.effective_issuer_authority_weight.value
                    ),
                    membership_content_hash=membership_hash,
                    payload_json=_payload_json(membership),
                )
            )
        for result in bundle.required_scope_results:
            scope_payload = {
                "authority_bundle_id": bundle.authority_bundle_id,
                "bundle_content_hash": bundle.bundle_content_hash,
                "provider_security_identity_id": (bundle.provider_security_identity_id),
                "proposed_issuer_id": bundle.proposed_issuer_id,
                "candidate_fingerprint": bundle.candidate_fingerprint,
                **result.model_dump(mode="python"),
            }
            session.add(
                AuthorityBundleScopeResultRow(
                    authority_bundle_id=bundle.authority_bundle_id,
                    authority_scope=result.authority_scope.value,
                    bundle_content_hash=bundle.bundle_content_hash,
                    provider_security_identity_id=(bundle.provider_security_identity_id),
                    proposed_issuer_id=bundle.proposed_issuer_id,
                    candidate_fingerprint=bundle.candidate_fingerprint,
                    scope_status=result.scope_status.value,
                    reason_codes_json=_payload_json(list(result.reason_codes)),
                    scope_result_content_hash=result.scope_result_content_hash,
                    payload_json=_payload_json(scope_payload),
                )
            )
        for ordinal, observation_id in enumerate(bundle.provider_observation_ids):
            observation_payload = {
                "authority_bundle_id": bundle.authority_bundle_id,
                "provider_observation_id": observation_id,
                "member_ordinal": ordinal,
                "bundle_content_hash": bundle.bundle_content_hash,
                "provider_security_identity_id": (bundle.provider_security_identity_id),
                "proposed_issuer_id": bundle.proposed_issuer_id,
                "candidate_fingerprint": bundle.candidate_fingerprint,
            }
            membership_hash = authority_sha256(observation_payload)
            session.add(
                AuthorityBundleProviderObservationRow(
                    **observation_payload,
                    membership_content_hash=membership_hash,
                    payload_json=_payload_json(observation_payload),
                )
            )

    @staticmethod
    def _identifier_claim_row(
        claim: AuthorityIdentifierClaim,
        payload: str,
    ) -> AuthorityIdentifierClaimRow:
        return AuthorityIdentifierClaimRow(
            authority_identifier_claim_id=claim.authority_identifier_claim_id,
            contract_version=claim.contract_version,
            claim_content_hash=claim.claim_content_hash,
            identifier_kind=claim.identifier_kind.value,
            normalized_identifier_value=claim.normalized_identifier_value,
            candidate_jurisdiction=claim.candidate_jurisdiction.value,
            proposed_issuer_id=claim.proposed_issuer_id,
            candidate_fingerprint=claim.candidate_fingerprint,
            provider_security_identity_id=claim.provider_security_identity_id,
            evidence_application_id=claim.evidence_application_id,
            application_content_hash=claim.application_content_hash,
            evidence_id=claim.evidence_id,
            evidence_content_hash=claim.evidence_content_hash,
            authority_source_policy_id=claim.authority_source_policy_id,
            authority_source_policy_content_hash=(claim.authority_source_policy_content_hash),
            claim_role=claim.claim_role.value,
            claim_scope=claim.claim_scope.value,
            recorded_at=utc_to_string(claim.recorded_at),
            payload_json=payload,
        )

    @staticmethod
    def _decision_row(
        decision: IssuerDecision,
        payload: str,
    ) -> IssuerDecisionRow:
        return IssuerDecisionRow(
            issuer_decision_id=decision.issuer_decision_id,
            contract_version=decision.contract_version,
            decision_content_hash=decision.decision_content_hash,
            decision_audit_hash=decision.decision_audit_hash,
            decision_rule_version=decision.decision_rule_version,
            authority_bundle_id=decision.authority_bundle_id,
            authority_bundle_content_hash=(decision.authority_bundle_content_hash),
            provider_security_identity_id=(decision.provider_security_identity_id),
            proposed_issuer_id=decision.proposed_issuer_id,
            decision_state=decision.decision_state.value,
            reason_codes_json=_payload_json(list(decision.reason_codes)),
            latest_revision_check_hash=decision.latest_revision_check_hash,
            freshness_policy_version=decision.freshness_policy_version,
            freshness_result=decision.freshness_result.value,
            collision_scan_hash=decision.collision_scan_hash,
            supersedes_decision_id=decision.supersedes_decision_id,
            evaluated_at=utc_to_string(decision.evaluated_at),
            payload_json=payload,
        )
