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
                or claim.scope != claim_application.scope.value
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
        if decision.machine_state == "READY_FOR_MANUAL_REVIEW":
            self._validate_ready_graph(
                session,
                policies,
                applications,
                claims,
                bundle,
                bundle_applications,
                scopes,
                providers,
                decision,
            )

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

    @staticmethod
    def _validate_ready_graph(
        session: Session,
        policies: Sequence[c.SourcePolicy],
        applications: Sequence[c.EvidenceApplication],
        claims: Sequence[c.IdentifierClaim | c.ClassClaim | c.ListingClaim],
        bundle: c.Bundle,
        members: Sequence[c.BundleApplication],
        scopes: Sequence[c.BundleScopeResult],
        providers: Sequence[c.BundleProviderObservation],
        decision: c.Decision,
    ) -> None:
        """Reconstruct proof at the write boundary; supplied SATISFIED flags are insufficient."""
        from toss_dashboard_api.domain.security_authority import (
            SecurityAuthorityDecisionEngine,
            _kr_family,
            _norm,
            _sec_class_identity,
            _sec_family,
        )
        from toss_dashboard_api.domain.security_authority_registry import (
            ADAPTER_VERSION,
            PARSER_VERSION,
            REQUIRED_SCOPE_PROOF,
            registry_hash,
            scope_proof_ids,
        )

        engine = SecurityAuthorityDecisionEngine.__new__(SecurityAuthorityDecisionEngine)
        provider = engine._provider_snapshot(session, decision.provider_id)
        issuer = engine._issuer_snapshot(session, decision.provider_id)
        if (
            provider is None
            or issuer is None
            or issuer.issuer.jurisdiction not in REQUIRED_SCOPE_PROOF
        ):
            raise SecurityLedgerConflict("SECURITY_READY_PREREQUISITE_MISSING")
        if provider.observation.market.value != issuer.issuer.jurisdiction:
            raise SecurityLedgerConflict("SECURITY_READY_PROVIDER_BRIDGE_MISMATCH")
        if (
            issuer.issuer.issuer_id,
            issuer.link.issuer_authority_link_id,
            issuer.link.link_content_hash,
            issuer.head.state_hash,
        ) != (
            bundle.issuer_id,
            bundle.issuer_link_id,
            bundle.issuer_link_hash,
            bundle.issuer_head_state_hash,
        ):
            raise SecurityLedgerConflict("SECURITY_READY_ISSUER_BINDING_MISMATCH")
        expected_provider = (
            decision.provider_id,
            provider.row.observation_id,
            provider.content_hash,
        )
        if (
            len(providers) != 1
            or (
                providers[0].provider_id,
                providers[0].observation_id,
                providers[0].observation_hash,
            )
            != expected_provider
        ):
            raise SecurityLedgerConflict("SECURITY_READY_PROVIDER_MEMBERSHIP_MISMATCH")
        binding = (bundle.provider_id, bundle.issuer_id, bundle.security_id)
        if any(
            (item.provider_id, item.issuer_id, item.security_id) != binding
            for item in (*applications, *members)
        ):
            raise SecurityLedgerConflict("SECURITY_READY_APPLICATION_BINDING_MISMATCH")
        app_pairs = sorted((item.application_id, item.content_hash) for item in applications)
        if len(set(app_pairs)) != len(app_pairs) or app_pairs != sorted(
            (item.application_id, item.application_hash) for item in members
        ):
            raise SecurityLedgerConflict("SECURITY_READY_APPLICATION_MEMBERSHIP_MISMATCH")
        if registry_hash(tuple(policies)) != bundle.source_policy_set_hash:
            raise SecurityLedgerConflict("SECURITY_READY_POLICY_HASH_MISMATCH")
        evidence, _, relation_conflict = engine._evidence_snapshot(session, decision.evaluated_at)
        freshness = engine._freshness_map(tuple(evidence.values()), provider, decision.evaluated_at)
        if relation_conflict or not freshness.get("__provider__", False):
            raise SecurityLedgerConflict("SECURITY_READY_CURRENTNESS_MISSING")
        for application in applications:
            snapshot = evidence.get(application.evidence_id)
            observation = None if snapshot is None else snapshot.observation
            if (
                snapshot is None
                or not snapshot.current
                or snapshot.parse_error
                or snapshot.observation_conflict
                or observation is None
                or observation.access_result != "SUCCEEDED"
                or observation.evidence_hash != application.evidence_hash
                or observation.raw_digest != snapshot.record.raw_digest
                or observation.adapter_version != ADAPTER_VERSION
                or observation.parser_version != PARSER_VERSION
                or application.relation_head_hash != snapshot.relation_head_hash
            ):
                raise SecurityLedgerConflict("SECURITY_READY_OBSERVATION_PROOF_REJECTED")
        scope_by_key = {item.scope: item for item in scopes}
        required = REQUIRED_SCOPE_PROOF[issuer.issuer.jurisdiction]
        if len(scopes) != len(required) or set(scope_by_key) != set(required):
            raise SecurityLedgerConflict("SECURITY_READY_SCOPE_COMPOSITION_MISSING")
        app_by_id = {item.application_id: item for item in applications}
        for scope, result in scope_by_key.items():
            proof = scope_proof_ids(issuer.issuer.jurisdiction, scope, tuple(applications))
            if proof is None or result.owner_application_ids != proof:
                raise SecurityLedgerConflict("SECURITY_READY_SCOPE_PROOF_MISSING")
            if any(not freshness.get(app_by_id[identity].evidence_id, False) for identity in proof):
                raise SecurityLedgerConflict("SECURITY_READY_REQUIRED_SOURCE_STALE")
        class_claims = [item for item in claims if isinstance(item, c.ClassClaim)]
        if not class_claims or any(
            item.instrument_family != "COMMON_EQUITY" for item in class_claims
        ):
            raise SecurityLedgerConflict("SECURITY_READY_CLASS_UNSUPPORTED")
        for claim in class_claims:
            application = app_by_id[claim.application_id]
            fact = evidence[application.evidence_id].fact
            expected_class: tuple[str | None, str | None, str | None, str | None]
            if application.source_namespace == "KRX_ISSUE_BASIC":
                expected_class = (None, fact.stock_kind, None, None)
            elif application.source_namespace == "SEC_ACCEPTED_8A":
                identity = _sec_class_identity(fact)
                expected_class = (
                    identity.registered_class_title,
                    None,
                    identity.class_row_id(),
                    identity.section_12_basis,
                )
            else:
                raise SecurityLedgerConflict("SECURITY_READY_CLASS_PROOF_MISMATCH")
            if (
                claim.registered_class_title,
                claim.authority_share_kind,
                claim.registered_row_id,
                claim.section_12_basis,
            ) != expected_class:
                raise SecurityLedgerConflict("SECURITY_READY_CLASS_PROOF_MISMATCH")
        for application in applications:
            fact = evidence[application.evidence_id].fact
            if (
                application.source_namespace == "KRX_ISSUE_BASIC"
                and _kr_family(fact.security_type, fact.stock_kind)
                != c.InstrumentFamily.COMMON_EQUITY
            ):
                raise SecurityLedgerConflict("SECURITY_READY_CLASS_UNSUPPORTED")
            if application.source_namespace == "SEC_ACCEPTED_8A" and (
                fact.registrant_cik != issuer.issuer.cik
                or _sec_family(fact.registered_class_title) != c.InstrumentFamily.COMMON_EQUITY
            ):
                raise SecurityLedgerConflict("SECURITY_READY_CLASS_UNSUPPORTED")
        facts = {
            application.evidence_id: evidence[application.evidence_id].fact
            for application in applications
        }
        if issuer.issuer.jurisdiction == "KR":
            standards = [
                evidence[app.evidence_id].fact
                for app in applications
                if app.source_namespace == "KRX_STANDARD_CODE"
            ]
            issues = [
                evidence[app.evidence_id].fact
                for app in applications
                if app.source_namespace == "KRX_ISSUE_BASIC"
            ]
            listings = [
                evidence[app.evidence_id].fact
                for app in applications
                if app.source_namespace == "KRX_LISTING_LIFECYCLE"
            ]
            darts = [
                evidence[app.evidence_id].fact
                for app in applications
                if app.source_namespace == "OPENDART_CORP_CODE"
            ]
            anchors = {c.kr_anchor(issuer.issuer.issuer_id, fact.isin) for fact in standards}
            if (
                any(standard.isin != provider.observation.isin for standard in standards)
                or any(
                    issue.stock_code != standard.stock_code
                    or issue.isin not in (None, standard.isin)
                    for issue in issues
                    for standard in standards
                )
                or any(
                    listing.stock_code != issue.stock_code
                    or listing.market != issue.market
                    or listing.security_type not in (None, issue.security_type)
                    or listing.stock_kind not in (None, issue.stock_kind)
                    or engine._kr_listing_status(listing, decision.evaluated_at.date()) != "ACTIVE"
                    for listing in listings
                    for issue in issues
                )
                or any(
                    dart.corp_code != issuer.issuer.corp_code or dart.stock_code != issue.stock_code
                    for dart in darts
                    for issue in issues
                )
            ):
                raise SecurityLedgerConflict("SECURITY_READY_CLASS_OR_BRIDGE_CONFLICT")
        else:
            from toss_dashboard_api.contracts.security_authority_decision import (
                NasdaqPrimaryFact,
                SecAccepted8AFact,
                SecAccepted25Fact,
                SecPeriodicCoverFact,
            )

            sec_facts = [fact for fact in facts.values() if isinstance(fact, SecAccepted8AFact)]
            anchors = {
                c.us_anchor(issuer.issuer.issuer_id, _sec_class_identity(fact))
                for fact in sec_facts
            }
            exchange_facts = [
                fact for fact in facts.values() if isinstance(fact, NasdaqPrimaryFact)
            ]
            if any(
                exchange.symbol != provider.observation.symbol
                or exchange.state != "ACTIVE"
                or exchange.test_issue
                or _norm(sec.exchange_name or "") != "nasdaq"
                or _norm(exchange.security_name) != _norm(sec.registered_class_title)
                for exchange in exchange_facts
                for sec in sec_facts
            ):
                raise SecurityLedgerConflict("SECURITY_READY_PROVIDER_BRIDGE_MISMATCH")
            for snapshot in evidence.values():
                fact = snapshot.fact
                if (
                    not snapshot.current
                    or snapshot.parse_error
                    or snapshot.accepted_observation is None
                    or not engine._production_evidence(snapshot.record)
                ):
                    continue
                for sec in sec_facts:
                    if (
                        isinstance(fact, SecAccepted25Fact)
                        and fact.registrant_cik == sec.registrant_cik
                        and _norm(fact.class_description) == _norm(sec.registered_class_title)
                        and _norm(fact.exchange_name) == _norm(sec.exchange_name or "")
                        and fact.effective_date <= decision.evaluated_at.date()
                        and (
                            fact.accepted_at > sec.accepted_at
                            or fact.effective_date >= sec.accepted_at.date()
                        )
                    ):
                        raise SecurityLedgerConflict("SECURITY_READY_NEGATIVE_AUTHORITY")
                    if (
                        isinstance(fact, SecPeriodicCoverFact)
                        and fact.registrant_cik == sec.registrant_cik
                        and fact.ticker == provider.observation.symbol
                        and (
                            _norm(fact.class_title) != _norm(sec.registered_class_title)
                            or (
                                fact.exchange_name is not None
                                and _norm(fact.exchange_name) != _norm(sec.exchange_name or "")
                            )
                        )
                    ):
                        raise SecurityLedgerConflict("SECURITY_READY_NEGATIVE_AUTHORITY")
        if (
            anchors != {bundle.proposed_anchor}
            or c.security_id_for_anchor(bundle.proposed_anchor) != bundle.security_id
        ):
            raise SecurityLedgerConflict("SECURITY_READY_CANONICAL_BINDING_MISMATCH")
        collision = engine._collision_scan(
            session,
            provider,
            bundle.security_id,
            tuple(item for item in claims if isinstance(item, c.IdentifierClaim)),
            tuple(class_claims),
            tuple(item for item in claims if isinstance(item, c.ListingClaim)),
            evidence,
            decision.evaluated_at,
        )
        if collision.result != "CLEAR" or collision.digest != bundle.collision_scan_hash:
            raise SecurityLedgerConflict("SECURITY_READY_COLLISION_PROOF_REJECTED")

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
