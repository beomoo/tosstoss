"""Immutable Security ledger with a capability-gated C2 machine write path."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from toss_dashboard_api.contracts import security_authority as c
from toss_dashboard_api.storage import security_authority_models as m

_C2_ENGINE_CAPABILITY = object()


class SecurityLedgerConflict(RuntimeError):
    pass


@dataclass(frozen=True)
class InsertResult[T: c.SecurityRecord]:
    value: T
    inserted: bool


# Positive authority objects intentionally have no public persistence route.
_ROWS: dict[type[c.SecurityRecord], type[Any]] = {
    c.SourcePolicy: m.SecuritySourcePolicyRow,
    c.Evidence: m.SecurityEvidenceRow,
    c.EvidenceObservation: m.SecurityEvidenceObservationRow,
    c.EvidenceRelation: m.SecurityEvidenceRelationRow,
    c.EvidenceApplication: m.SecurityEvidenceApplicationRow,
    c.IdentifierClaim: m.SecurityIdentifierClaimRow,
    c.ClassClaim: m.SecurityClassClaimRow,
    c.ListingClaim: m.SecurityListingClaimRow,
    c.Decision: m.SecurityDecisionRow,
}
_BUNDLE_ROWS: dict[type[c.SecurityRecord], type[Any]] = {
    c.Bundle: m.SecurityBundleRow,
    c.BundleApplication: m.SecurityBundleApplicationRow,
    c.BundleScopeResult: m.SecurityBundleScopeResultRow,
    c.BundleProviderObservation: m.SecurityBundleProviderObservationRow,
}


def _guard(record: c.SecurityRecord) -> None:
    if isinstance(record, c.SourcePolicy) and record.production_eligible:
        raise SecurityLedgerConflict("SECURITY_PRODUCTION_ADMISSION_NOT_IMPLEMENTED")
    if isinstance(record, c.Evidence) and record.origin_mode != "TEST_ONLY":
        raise SecurityLedgerConflict("SECURITY_PRODUCTION_ADMISSION_NOT_IMPLEMENTED")
    if isinstance(record, c.EvidenceApplication) and not (
        record.fixture_taint or record.test_taint
    ):
        raise SecurityLedgerConflict("SECURITY_ENGINE_APPLICATION_REQUIRED")
    if isinstance(record, c.Decision) and record.machine_state == "READY_FOR_MANUAL_REVIEW":
        raise SecurityLedgerConflict("SECURITY_MACHINE_ENGINE_NOT_IMPLEMENTED")


def _insert[T: c.SecurityRecord](
    session: Session, value: T, row_type: type[Any], *, engine_owned: bool = False
) -> InsertResult[T]:
    # Revalidate even objects supplied through model_construct/model_copy.
    payload = c.canonical_security_bytes(value).decode("utf-8")
    value = type(value).model_validate_json(payload)
    if not engine_owned:
        _guard(value)
    identity = tuple(getattr(value, col.name) for col in row_type.__table__.primary_key)
    existing = session.get(row_type, identity)
    if existing is not None:
        if existing.payload_json != payload:
            raise SecurityLedgerConflict("IMMUTABLE_SECURITY_OBJECT_CONFLICT")
        return InsertResult(value, False)
    data = c.strict_security_json(payload)
    for name in type(value).model_fields:
        if isinstance(data[name], list):
            data[name] = c.canonical_security_bytes(data[name]).decode("utf-8")
    session.add(row_type(**data, payload_json=payload))
    session.flush()
    return InsertResult(value, True)


def _insert_engine_record[T: c.SecurityRecord](
    session: Session, value: T, row_type: type[Any]
) -> InsertResult[T]:
    """Reuse a semantically identical immutable row despite a newer audit clock."""
    payload = c.canonical_security_bytes(value).decode("utf-8")
    value = type(value).model_validate_json(payload)
    identity = tuple(getattr(value, col.name) for col in row_type.__table__.primary_key)
    existing = session.get(row_type, identity)
    if existing is None:
        return _insert(session, value, row_type, engine_owned=True)
    stored = type(value).model_validate_json(existing.payload_json)
    if (
        stored.content_hash != value.content_hash
        or stored.semantic_payload() != value.semantic_payload()
    ):
        raise SecurityLedgerConflict("IMMUTABLE_SECURITY_OBJECT_CONFLICT")
    return InsertResult(stored, False)


class SQLiteSecurityAuthorityRepository:
    """No authentication, canonical subject, approval, link or head writer."""

    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self._sessions = sessions

    def insert_or_verify[T: c.SecurityRecord](self, value: T) -> InsertResult[T]:
        row_type = _ROWS.get(type(value))
        if row_type is None:
            raise SecurityLedgerConflict("SECURITY_POSITIVE_RUNTIME_NOT_IMPLEMENTED")
        with self._sessions.begin() as session:
            return _insert(session, value, row_type)

    def read[T: c.SecurityRecord](self, kind: type[T], identity: str | tuple[str, ...]) -> T:
        row_type = {**_ROWS, **_BUNDLE_ROWS}.get(kind)
        if row_type is None:
            raise SecurityLedgerConflict("UNSUPPORTED_SECURITY_READ")
        with self._sessions() as session:
            row = session.get(row_type, identity)
            if row is None:
                raise SecurityLedgerConflict("SECURITY_OBJECT_MISSING")
            return kind.model_validate_json(row.payload_json)

    def insert_bundle(
        self,
        bundle: c.Bundle,
        applications: Sequence[c.BundleApplication],
        scopes: Sequence[c.BundleScopeResult],
        providers: Sequence[c.BundleProviderObservation],
    ) -> InsertResult[c.Bundle]:
        members: tuple[
            c.BundleApplication | c.BundleScopeResult | c.BundleProviderObservation, ...
        ] = (*applications, *scopes, *providers)
        for member in members:
            if member.bundle_id != bundle.bundle_id or member.bundle_hash != bundle.content_hash:
                raise SecurityLedgerConflict("SECURITY_BUNDLE_MEMBERSHIP_MISMATCH")
        actual = c.security_hash(
            {
                "applications": sorted(
                    (v.application_id, v.application_hash) for v in applications
                ),
                "scopes": sorted(
                    (v.scope.value, v.result, v.reason_codes, v.owner_application_ids)
                    for v in scopes
                ),
                "providers": sorted((v.observation_id, v.observation_hash) for v in providers),
            }
        )
        if actual != bundle.membership_hash:
            raise SecurityLedgerConflict("SECURITY_BUNDLE_MEMBERSHIP_HASH_MISMATCH")
        with self._sessions.begin() as session:
            result = _insert(session, bundle, m.SecurityBundleRow)
            for member in members:
                _insert(session, member, _BUNDLE_ROWS[type(member)])
        return result

    def insert_machine_evaluation(
        self,
        session: Session,
        *,
        capability: object,
        policies: Sequence[c.SourcePolicy],
        applications: Sequence[c.EvidenceApplication],
        claims: Sequence[c.IdentifierClaim | c.ClassClaim | c.ListingClaim],
        bundle: c.Bundle,
        bundle_applications: Sequence[c.BundleApplication],
        scopes: Sequence[c.BundleScopeResult],
        providers: Sequence[c.BundleProviderObservation],
        decision: c.Decision,
    ) -> dict[str, int]:
        """Persist one fully evaluated graph inside the C2 writer transaction."""
        if capability is not _C2_ENGINE_CAPABILITY:
            raise SecurityLedgerConflict("SECURITY_ENGINE_CAPABILITY_REQUIRED")
        from toss_dashboard_api.domain.security_authority_registry import (
            build_policy,
            exact_policy_for,
        )

        policy_by_id: dict[str, c.SourcePolicy] = {}
        counts: dict[str, int] = {}

        def append(value: c.SecurityRecord, row_type: type[Any], label: str) -> None:
            result = _insert_engine_record(session, value, row_type)
            counts[label] = counts.get(label, 0) + int(result.inserted)

        for policy in policies:
            spec = exact_policy_for(
                policy.source_namespace,
                policy.document_kind,
                policy.scope,
                policy.subject_role,
            )
            if spec is None or policy != build_policy(spec, recorded_at=policy.recorded_at):
                raise SecurityLedgerConflict("SECURITY_SOURCE_POLICY_NOT_SERVER_OWNED")
            append(policy, m.SecuritySourcePolicyRow, "policies")
            policy_by_id[policy.policy_id] = policy

        application_by_id: dict[str, c.EvidenceApplication] = {}
        for application in applications:
            application_policy = policy_by_id.get(application.policy_id)
            evidence = session.get(m.SecurityEvidenceRow, application.evidence_id)
            if (
                application_policy is None
                or application.policy_hash != application_policy.content_hash
                or application.source_namespace != application_policy.source_namespace
                or application.document_kind != application_policy.document_kind
                or application.scope != application_policy.scope
                or application.subject_role != application_policy.subject_role
                or application.requested_weight > application_policy.max_weight
                or application.fixture_taint
                or application.test_taint
                or application.status
                != ("ADMITTED" if application_policy.max_weight == 3 else "SUPPORT_ONLY")
                or evidence is None
                or evidence.content_hash != application.evidence_hash
                or evidence.source_namespace != application_policy.source_namespace
                or evidence.document_kind != application_policy.document_kind
                or evidence.subject_role != application_policy.subject_role
                or evidence.origin_mode != "PRODUCTION_AUTHORITY"
                or evidence.fixture_taint
                or evidence.test_taint
            ):
                raise SecurityLedgerConflict("SECURITY_APPLICATION_PROVENANCE_REJECTED")
            append(application, m.SecurityEvidenceApplicationRow, "applications")
            application_by_id[application.application_id] = application

        for claim in claims:
            claim_application = application_by_id.get(claim.application_id)
            if (
                claim_application is None
                or claim.application_hash != claim_application.content_hash
                or claim_application.status != "ADMITTED"
                or claim.application_status != "ADMITTED"
                or (claim.provider_id, claim.issuer_id, claim.security_id)
                != (
                    claim_application.provider_id,
                    claim_application.issuer_id,
                    claim_application.security_id,
                )
            ):
                raise SecurityLedgerConflict("SECURITY_CLAIM_APPLICATION_MISMATCH")
            row_type = {
                c.IdentifierClaim: m.SecurityIdentifierClaimRow,
                c.ClassClaim: m.SecurityClassClaimRow,
                c.ListingClaim: m.SecurityListingClaimRow,
            }[type(claim)]
            append(claim, row_type, "claims")

        members: tuple[
            c.BundleApplication | c.BundleScopeResult | c.BundleProviderObservation, ...
        ] = (*bundle_applications, *scopes, *providers)
        if any(
            member.bundle_id != bundle.bundle_id or member.bundle_hash != bundle.content_hash
            for member in members
        ):
            raise SecurityLedgerConflict("SECURITY_BUNDLE_MEMBERSHIP_MISMATCH")
        membership_hash = c.security_hash(
            {
                "applications": sorted(
                    (value.application_id, value.application_hash) for value in bundle_applications
                ),
                "scopes": sorted(
                    (
                        value.scope.value,
                        value.result,
                        value.reason_codes,
                        value.owner_application_ids,
                    )
                    for value in scopes
                ),
                "providers": sorted(
                    (value.observation_id, value.observation_hash) for value in providers
                ),
            }
        )
        if membership_hash != bundle.membership_hash:
            raise SecurityLedgerConflict("SECURITY_BUNDLE_MEMBERSHIP_HASH_MISMATCH")
        if (
            decision.bundle_id != bundle.bundle_id
            or decision.bundle_hash != bundle.content_hash
            or (decision.provider_id, decision.issuer_id, decision.security_id)
            != (bundle.provider_id, bundle.issuer_id, bundle.security_id)
            or decision.issuer_link_id != bundle.issuer_link_id
            or decision.issuer_link_hash != bundle.issuer_link_hash
            or decision.issuer_head_state_hash != bundle.issuer_head_state_hash
        ):
            raise SecurityLedgerConflict("SECURITY_DECISION_BUNDLE_MISMATCH")
        if decision.machine_state == "READY_FOR_MANUAL_REVIEW" and (
            decision.freshness_result != "FRESH"
            or decision.collision_result != "CLEAR"
            or not scopes
            or any(scope.result != "SATISFIED" for scope in scopes)
            or not providers
            or any(application.status == "REJECTED" for application in applications)
        ):
            raise SecurityLedgerConflict("SECURITY_READY_PREDICATES_NOT_SATISFIED")

        append(bundle, m.SecurityBundleRow, "bundles")
        for application_member in bundle_applications:
            append(application_member, m.SecurityBundleApplicationRow, "bundle_members")
        for scope_result in scopes:
            append(scope_result, m.SecurityBundleScopeResultRow, "bundle_members")
        for provider_observation in providers:
            append(
                provider_observation,
                m.SecurityBundleProviderObservationRow,
                "bundle_members",
            )
        append(decision, m.SecurityDecisionRow, "decisions")
        return counts

    def identifier_claims(self, kind: str, value: str) -> tuple[c.IdentifierClaim, ...]:
        """Return every matching claim, including contradictions; never pick a winner."""
        with self._sessions() as session:
            rows = session.scalars(
                select(m.SecurityIdentifierClaimRow)
                .where(
                    m.SecurityIdentifierClaimRow.identifier_kind == kind,
                    m.SecurityIdentifierClaimRow.identifier_value == value,
                )
                .order_by(m.SecurityIdentifierClaimRow.claim_id)
            ).all()
            return tuple(c.IdentifierClaim.model_validate_json(row.payload_json) for row in rows)
