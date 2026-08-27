from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session, sessionmaker

from toss_dashboard_api.authority_source_registry import (
    SOURCE_POLICY_REGISTRY_VERSION,
    is_exact_server_owned_production_policy,
)
from toss_dashboard_api.contracts.authority import (
    AuthorityBundle,
    AuthorityBundleScopeResult,
    AuthorityBundleScopeStatus,
    AuthorityCollisionScanResult,
    AuthorityEvidence,
    AuthorityEvidenceApplication,
    AuthorityEvidenceApplicationStatus,
    AuthorityEvidenceKind,
    AuthorityEvidenceObservation,
    AuthorityEvidenceRelation,
    AuthorityFreshnessResult,
    AuthorityIdentifierClaim,
    AuthorityIdentifierKind,
    AuthorityLegalJurisdictionResult,
    AuthorityRetrievalStatus,
    AuthorityScope,
    AuthoritySourcePolicy,
    AuthoritySubjectRole,
    AuthorityWeight,
    IssuerDecision,
    IssuerMachineDecisionState,
    authority_candidate_fingerprint,
    authority_sha256,
    build_authority_bundle_scope_result,
    build_authority_evidence_application,
    build_authority_identifier_claim,
    build_issuer_decision,
    build_production_authority_bundle,
    bundle_satisfies_review_ready_foundation,
)
from toss_dashboard_api.contracts.authority_decision import (
    AuthorityBridgeResult,
    AuthorityBridgeStatus,
    IssuerAuthorityEvaluationRequest,
    build_authority_bridge_result,
)
from toss_dashboard_api.contracts.enums import MappingStatus, ProviderIdentityState
from toss_dashboard_api.contracts.provider_security_master import (
    ProviderSecurityMasterObservation,
)
from toss_dashboard_api.repositories.authority import (
    AuthorityLedgerConflict,
    SQLiteAuthorityLedgerRepository,
)
from toss_dashboard_api.storage.models import (
    AuthorityBundleRow,
    AuthorityEvidenceApplicationRow,
    AuthorityEvidenceObservationRow,
    AuthorityEvidenceRelationRow,
    AuthorityEvidenceRow,
    AuthorityIdentifierClaimRow,
    AuthoritySourcePolicyRow,
    IssuerDecisionRow,
    IssuerRow,
    ProviderSecurityIdentityRow,
    ProviderSecurityMasterObservationRow,
)

FRESHNESS_POLICY_VERSION = "conservative-approval-freshness/0.1.0"
FRESHNESS_LIMIT = timedelta(hours=24)
FUTURE_CLOCK_SKEW_LIMIT = timedelta(minutes=5)

_SYNTHETIC_IDENTIFIERS = {"90000001", "9999999998", "9999999999"}
_SEC_ACCESSION_PATTERN = re.compile(r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$")
_KR_REGISTRATION_PATTERN = re.compile(r"^[0-9]{13}$")
_KR_STOCK_CODE_PATTERN = re.compile(r"^[0-9]{6}$")
_US_STATE_ENTITY_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9-]{1,63}$")

_KR_CORP_CODE = "KR_CORP_CODE"
_KR_OVERVIEW_BRIDGE = "KR_OVERVIEW_BRIDGE"
_KR_IROS_JURISDICTION = "KR_IROS_JURISDICTION"
_KR_IROS_BRIDGE = "KR_IROS_BRIDGE"
_US_SEC_CIK = "US_SEC_CIK"
_US_SEC_REGISTRANT_ROLE = "US_SEC_REGISTRANT_ROLE"
_US_SEC_BRIDGE = "US_SEC_BRIDGE"
_US_SEC_LATEST_STATUS = "US_SEC_LATEST_STATUS"
_US_STATE_JURISDICTION = "US_STATE_JURISDICTION"
_PROVENANCE_ONLY = "PROVENANCE_ONLY"


class IssuerAuthorityDecisionEngineError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True)
class IssuerAuthorityDecisionEngineResult:
    applications: tuple[AuthorityEvidenceApplication, ...]
    identifier_claims: tuple[AuthorityIdentifierClaim, ...]
    bridge_result: AuthorityBridgeResult
    bundle: AuthorityBundle
    decision: IssuerDecision
    inserted_application_count: int
    inserted_claim_count: int
    bundle_inserted: bool
    decision_inserted: bool


@dataclass(frozen=True)
class _ProviderSnapshot:
    row: ProviderSecurityIdentityRow
    observations: tuple[ProviderSecurityMasterObservation, ...]
    reason_codes: tuple[str, ...]

    @property
    def safe(self) -> bool:
        return not self.reason_codes

    @property
    def symbols(self) -> tuple[str, ...]:
        return tuple(sorted({observation.symbol for observation in self.observations}))


@dataclass(frozen=True)
class _RelationHead:
    content_hash: str
    current: bool
    conflict: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class _EvidenceSnapshot:
    evidence: AuthorityEvidence
    policy: AuthoritySourcePolicy
    observations: tuple[AuthorityEvidenceObservation, ...]
    relation_head: _RelationHead


@dataclass(frozen=True)
class _MatrixFact:
    kind: str | None
    target_field: str
    requested_status: AuthorityEvidenceApplicationStatus
    requested_weight: AuthorityWeight
    reason_codes: tuple[str, ...]
    exact_shape: bool
    current_check: bool


@dataclass(frozen=True)
class _AssessedEvidence:
    snapshot: _EvidenceSnapshot
    fact: _MatrixFact
    freshness: AuthorityFreshnessResult
    application: AuthorityEvidenceApplication | None

    @property
    def structurally_usable(self) -> bool:
        return (
            self.fact.kind is not None
            and self.fact.exact_shape
            and self.snapshot.relation_head.current
            and not self.snapshot.relation_head.conflict
            and bool(self.snapshot.observations)
        )

    @property
    def positively_applied(self) -> bool:
        return self.application is not None and self.application.application_status in {
            AuthorityEvidenceApplicationStatus.APPLIED_DECISIVE,
            AuthorityEvidenceApplicationStatus.APPLIED_SUPPORTING,
        }


@dataclass(frozen=True)
class _PathEvaluation:
    bridge: AuthorityBridgeResult
    scope_results: tuple[AuthorityBundleScopeResult, ...]
    legal_jurisdiction_result: AuthorityLegalJurisdictionResult
    freshness_result: AuthorityFreshnessResult
    structural_complete: bool
    positive_complete: bool
    safety_event: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class _CollisionScan:
    result: AuthorityCollisionScanResult
    candidate_fingerprints: tuple[str, ...]
    reason_codes: tuple[str, ...]


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise IssuerAuthorityDecisionEngineError(
            "INVALID_STORED_TIMESTAMP", "stored authority timestamp is not timezone aware"
        )
    return parsed.astimezone(UTC)


def _payload(value: Any) -> str:
    from toss_dashboard_api.contracts.authority import canonical_authority_json_bytes

    return canonical_authority_json_bytes(value).decode("utf-8")


def _sorted(values: set[str] | list[str] | tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted(set(values), key=lambda item: item.encode("utf-8")))


def _exact_dict(value: Any, keys: set[str]) -> dict[str, Any] | None:
    if not isinstance(value, dict) or set(value) != keys:
        return None
    return value


class IssuerAuthorityDecisionEngine:
    """Offline B2-B issuer-side machine evaluation over the immutable ledger.

    The only positive write surface is ``evaluate``. It accepts identity and
    evidence membership, never caller authority classifications, weights,
    bridge booleans, collision results, overrides, or READY state.
    """

    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self._sessions = sessions

    def evaluate(
        self, request: IssuerAuthorityEvaluationRequest
    ) -> IssuerAuthorityDecisionEngineResult:
        if request.candidate_identifier_value in _SYNTHETIC_IDENTIFIERS:
            raise IssuerAuthorityDecisionEngineError(
                "SYNTHETIC_IDENTIFIER_PROHIBITED",
                "fixture/synthetic authority identifier cannot enter production evaluation",
            )
        session = self._sessions()
        try:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            result = self._evaluate_locked(session, request)
            session.commit()
            return result
        except IssuerAuthorityDecisionEngineError:
            session.rollback()
            raise
        except AuthorityLedgerConflict as error:
            session.rollback()
            raise IssuerAuthorityDecisionEngineError(
                "IMMUTABLE_LEDGER_CONFLICT", str(error)
            ) from None
        except (IntegrityError, OperationalError) as error:
            session.rollback()
            raise IssuerAuthorityDecisionEngineError(
                "TRANSACTION_REVALIDATION_CONFLICT",
                "SQLite ledger state changed or failed an exact integrity constraint",
            ) from error
        finally:
            session.close()

    def _evaluate_locked(
        self,
        session: Session,
        request: IssuerAuthorityEvaluationRequest,
    ) -> IssuerAuthorityDecisionEngineResult:
        provider = self._provider_snapshot(session, request)
        relations = self._all_relations(session)
        evidence = tuple(
            self._evidence_snapshot(session, evidence_id, relations)
            for evidence_id in request.evidence_ids
        )
        assessments = tuple(self._assess_evidence(snapshot, request) for snapshot in evidence)

        inserted_applications = 0
        persisted_assessments: list[_AssessedEvidence] = []
        for assessment in assessments:
            application = assessment.application
            if application is None:
                persisted_assessments.append(assessment)
                continue
            persisted, inserted = self._insert_or_reuse_application(session, application)
            inserted_applications += int(inserted)
            persisted_assessments.append(
                _AssessedEvidence(
                    snapshot=assessment.snapshot,
                    fact=assessment.fact,
                    freshness=assessment.freshness,
                    application=persisted,
                )
            )
        assessments = tuple(persisted_assessments)
        session.flush()

        claims = self._identifier_claims(request, assessments)
        persisted_claims: list[AuthorityIdentifierClaim] = []
        inserted_claims = 0
        for claim in claims:
            persisted_claim, inserted = self._insert_or_reuse_claim(session, claim)
            persisted_claims.append(persisted_claim)
            inserted_claims += int(inserted)
        session.flush()

        collision = self._collision_scan(session, request, provider, relations)
        path = self._path_evaluation(request, provider, assessments)
        applications = tuple(
            sorted(
                (
                    assessment.application
                    for assessment in assessments
                    if assessment.positively_applied and assessment.application is not None
                ),
                key=lambda application: application.evidence_application_id,
            )
        )
        bundle = build_production_authority_bundle(
            provider_security_identity_id=request.provider_security_identity_id,
            provider_observation_ids=request.provider_observation_ids,
            candidate_jurisdiction=request.candidate_jurisdiction,
            candidate_identifier_kind=request.candidate_identifier_kind,
            candidate_identifier_value=request.candidate_identifier_value,
            applications=applications,
            required_scope_results=path.scope_results,
            legal_jurisdiction_result=path.legal_jurisdiction_result,
            collision_scan_result=collision.result,
            collision_claim_candidate_fingerprints=collision.candidate_fingerprints,
            built_at=request.evaluated_at,
        )
        bundle, bundle_inserted = self._insert_or_reuse_bundle(session, bundle)
        session.flush()

        predecessor = self._decision_leaf(session, request.provider_security_identity_id)
        state = self._decision_state(path, collision, predecessor is not None)
        latest_hash = self._latest_revision_check_hash(request, assessments, path)
        reasons = _sorted(
            set(path.reason_codes) | set(collision.reason_codes) | {f"MACHINE_STATE_{state.value}"}
        )
        if state == IssuerMachineDecisionState.READY_FOR_MANUAL_REVIEW:
            self._revalidate_ready_locked(
                session,
                request=request,
                provider=provider,
                assessments=assessments,
                path=path,
                collision=collision,
                bundle=bundle,
            )
        decision = build_issuer_decision(
            bundle=bundle,
            decision_state=state,
            reason_codes=reasons,
            latest_revision_check_hash=latest_hash,
            freshness_policy_version=FRESHNESS_POLICY_VERSION,
            freshness_result=path.freshness_result,
            collision_scan_hash=bundle.collision_scan_hash,
            evaluated_at=request.evaluated_at,
            supersedes_decision_id=(
                None if predecessor is None else predecessor.issuer_decision_id
            ),
        )
        if predecessor is not None and self._same_decision_semantics(predecessor, decision):
            decision = predecessor
            decision_inserted = False
        else:
            decision, decision_inserted = self._insert_engine_decision(session, decision)

        return IssuerAuthorityDecisionEngineResult(
            applications=tuple(
                assessment.application
                for assessment in assessments
                if assessment.application is not None
            ),
            identifier_claims=tuple(persisted_claims),
            bridge_result=path.bridge,
            bundle=bundle,
            decision=decision,
            inserted_application_count=inserted_applications,
            inserted_claim_count=inserted_claims,
            bundle_inserted=bundle_inserted,
            decision_inserted=decision_inserted,
        )

    @staticmethod
    def _provider_snapshot(
        session: Session,
        request: IssuerAuthorityEvaluationRequest,
    ) -> _ProviderSnapshot:
        row = session.get(
            ProviderSecurityIdentityRow,
            request.provider_security_identity_id,
        )
        if row is None:
            raise IssuerAuthorityDecisionEngineError(
                "PROVIDER_IDENTITY_MISSING", "provider authority subject does not exist"
            )
        reasons: set[str] = set()
        if row.identity_state != ProviderIdentityState.ACTIVE.value:
            reasons.add("PROVIDER_IDENTITY_NOT_ACTIVE")
        if row.mapping_status != MappingStatus.UNRESOLVED.value:
            reasons.add("PROVIDER_MAPPING_STATE_NOT_UNRESOLVED")
        observations: list[ProviderSecurityMasterObservation] = []
        for observation_id in request.provider_observation_ids:
            stored = session.get(ProviderSecurityMasterObservationRow, observation_id)
            if stored is None:
                raise IssuerAuthorityDecisionEngineError(
                    "PROVIDER_OBSERVATION_MISSING",
                    "exact CP3-C1 provider observation does not exist",
                )
            if stored.provider_security_identity_id != request.provider_security_identity_id:
                raise IssuerAuthorityDecisionEngineError(
                    "PROVIDER_OBSERVATION_SUBJECT_MISMATCH",
                    "provider observation belongs to another provider identity",
                )
            try:
                observation = ProviderSecurityMasterObservation.model_validate_json(
                    stored.payload_json, strict=False
                )
            except ValidationError:
                reasons.add("PROVIDER_OBSERVATION_CONTRACT_INVALID")
                continue
            exact_row = (
                observation.observation_id == stored.observation_id
                and observation.source_version_id == stored.source_version_id
                and observation.provider_security_identity_id
                == stored.provider_security_identity_id
                and observation.provider.value == stored.provider
                and observation.market.value == stored.market
                and observation.symbol == stored.symbol
                and observation.staging_state.value == stored.staging_state
                and observation.reconciliation_outcome.value == stored.reconciliation_outcome
                and int(observation.eligible_for_mapping) == stored.eligible_for_mapping
            )
            if not exact_row:
                reasons.add("PROVIDER_OBSERVATION_ROW_PAYLOAD_MISMATCH")
            if (
                not observation.eligible_for_mapping
                or observation.identity_state_after != ProviderIdentityState.ACTIVE
                or observation.collision_identity_ids
            ):
                reasons.add("PROVIDER_OBSERVATION_NOT_BRIDGE_ELIGIBLE")
            observations.append(observation)
        if not any(
            observation.source_version_id == row.latest_source_version_id
            for observation in observations
        ):
            reasons.add("PROVIDER_OBSERVATION_NOT_CURRENT")
        return _ProviderSnapshot(
            row=row,
            observations=tuple(sorted(observations, key=lambda item: item.observation_id)),
            reason_codes=_sorted(reasons),
        )

    @staticmethod
    def _all_relations(session: Session) -> tuple[AuthorityEvidenceRelation, ...]:
        rows = session.scalars(
            select(AuthorityEvidenceRelationRow).order_by(
                AuthorityEvidenceRelationRow.authority_evidence_relation_id
            )
        ).all()
        return tuple(
            AuthorityEvidenceRelation.model_validate_json(row.payload_json, strict=False)
            for row in rows
        )

    def _evidence_snapshot(
        self,
        session: Session,
        evidence_id: str,
        relations: tuple[AuthorityEvidenceRelation, ...],
    ) -> _EvidenceSnapshot:
        row = session.get(AuthorityEvidenceRow, evidence_id)
        if row is None:
            raise IssuerAuthorityDecisionEngineError(
                "AUTHORITY_EVIDENCE_MISSING", "selected immutable evidence does not exist"
            )
        evidence = AuthorityEvidence.model_validate_json(row.payload_json, strict=False)
        policy_row = session.get(AuthoritySourcePolicyRow, evidence.authority_source_policy_id)
        if policy_row is None:
            raise IssuerAuthorityDecisionEngineError(
                "AUTHORITY_SOURCE_POLICY_MISSING", "selected evidence policy does not exist"
            )
        policy = AuthoritySourcePolicy.model_validate_json(policy_row.payload_json, strict=False)
        observation_rows = session.scalars(
            select(AuthorityEvidenceObservationRow)
            .where(AuthorityEvidenceObservationRow.evidence_id == evidence_id)
            .order_by(
                AuthorityEvidenceObservationRow.fetched_at,
                AuthorityEvidenceObservationRow.authority_evidence_observation_id,
            )
        ).all()
        observations = tuple(
            AuthorityEvidenceObservation.model_validate_json(row.payload_json, strict=False)
            for row in observation_rows
        )
        return _EvidenceSnapshot(
            evidence=evidence,
            policy=policy,
            observations=observations,
            relation_head=self._relation_head(evidence_id, relations),
        )

    @staticmethod
    def _relation_head(
        evidence_id: str,
        relations: tuple[AuthorityEvidenceRelation, ...],
    ) -> _RelationHead:
        adjacent: dict[str, set[str]] = {}
        for relation in relations:
            adjacent.setdefault(relation.predecessor_evidence_id, set()).add(
                relation.successor_evidence_id
            )
            adjacent.setdefault(relation.successor_evidence_id, set()).add(
                relation.predecessor_evidence_id
            )
        component = {evidence_id}
        pending = [evidence_id]
        while pending:
            current = pending.pop()
            for neighbor in adjacent.get(current, set()):
                if neighbor not in component:
                    component.add(neighbor)
                    pending.append(neighbor)
        edges = tuple(
            relation
            for relation in relations
            if relation.predecessor_evidence_id in component
            and relation.successor_evidence_id in component
        )
        outgoing: dict[str, list[AuthorityEvidenceRelation]] = {}
        incoming: dict[str, list[AuthorityEvidenceRelation]] = {}
        for relation in edges:
            outgoing.setdefault(relation.predecessor_evidence_id, []).append(relation)
            incoming.setdefault(relation.successor_evidence_id, []).append(relation)
        reasons: set[str] = set()
        if any(len(items) != 1 for items in outgoing.values()):
            reasons.add("AUTHORITY_RELATION_FORK")
        if any(len(items) != 1 for items in incoming.values()):
            reasons.add("AUTHORITY_RELATION_MERGE_AMBIGUITY")
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node: str) -> None:
            if node in visiting:
                reasons.add("AUTHORITY_RELATION_CYCLE")
                return
            if node in visited:
                return
            visiting.add(node)
            for relation in outgoing.get(node, []):
                visit(relation.successor_evidence_id)
            visiting.remove(node)
            visited.add(node)

        for node in component:
            visit(node)
        leaves = tuple(sorted(component - set(outgoing)))
        if len(leaves) != 1:
            reasons.add("AUTHORITY_RELATION_HEAD_AMBIGUOUS")
        is_current = len(leaves) == 1 and leaves[0] == evidence_id and not reasons
        if not is_current and not reasons:
            reasons.add("AUTHORITY_EVIDENCE_NOT_CURRENT_HEAD")
        content_hash = authority_sha256(
            {
                "component_evidence_ids": tuple(sorted(component)),
                "relation_content_hashes": tuple(
                    sorted(relation.relation_content_hash for relation in edges)
                ),
                "current_head_evidence_ids": leaves,
            }
        )
        return _RelationHead(
            content_hash=content_hash,
            current=is_current,
            conflict=bool(reasons - {"AUTHORITY_EVIDENCE_NOT_CURRENT_HEAD"}),
            reason_codes=_sorted(reasons),
        )

    def _assess_evidence(
        self,
        snapshot: _EvidenceSnapshot,
        request: IssuerAuthorityEvaluationRequest,
    ) -> _AssessedEvidence:
        fact = self._matrix_fact(snapshot, request)
        freshness = self._freshness(snapshot, request.evaluated_at, fact.current_check)
        reasons = set(fact.reason_codes) | set(snapshot.relation_head.reason_codes)
        status = fact.requested_status
        weight = fact.requested_weight
        if not is_exact_server_owned_production_policy(snapshot.policy):
            status = AuthorityEvidenceApplicationStatus.REJECTED_SOURCE_POLICY
            weight = AuthorityWeight.ZERO
            reasons.add("SOURCE_POLICY_NOT_EXACT_SERVER_REGISTRY_ENTRY")
        elif not fact.exact_shape:
            status = AuthorityEvidenceApplicationStatus.REJECTED_UNUSABLE
            weight = AuthorityWeight.ZERO
        elif snapshot.relation_head.conflict or not snapshot.relation_head.current:
            status = AuthorityEvidenceApplicationStatus.REJECTED_CONFLICT
            weight = AuthorityWeight.ZERO
        elif not snapshot.observations or not any(
            observation.retrieval_status == AuthorityRetrievalStatus.SUCCEEDED
            for observation in snapshot.observations
        ):
            status = AuthorityEvidenceApplicationStatus.REJECTED_UNVERIFIABLE
            weight = AuthorityWeight.ZERO
            reasons.add("AUTHORITY_RETRIEVAL_NOT_VERIFIED")
        elif freshness != AuthorityFreshnessResult.CURRENT and fact.current_check:
            status = AuthorityEvidenceApplicationStatus.REJECTED_STALE
            weight = AuthorityWeight.ZERO
            reasons.add(f"CURRENT_CHECK_{freshness.value}")
        elif snapshot.evidence.evidence_kind == AuthorityEvidenceKind.REVOCATION:
            status = AuthorityEvidenceApplicationStatus.REJECTED_CONFLICT
            weight = AuthorityWeight.ZERO
            reasons.add("AUTHORITY_EVIDENCE_REVOKED")
        if fact.kind is None and status not in {
            AuthorityEvidenceApplicationStatus.PROVENANCE_ONLY,
            AuthorityEvidenceApplicationStatus.REJECTED_SOURCE_POLICY,
        }:
            status = AuthorityEvidenceApplicationStatus.REJECTED_UNUSABLE
            weight = AuthorityWeight.ZERO
        application = None
        if snapshot.observations:
            application = build_authority_evidence_application(
                policy=snapshot.policy,
                evidence=snapshot.evidence,
                provider_security_identity_id=request.provider_security_identity_id,
                provider_observation_ids=request.provider_observation_ids,
                candidate_jurisdiction=request.candidate_jurisdiction,
                candidate_identifier_kind=request.candidate_identifier_kind,
                candidate_identifier_value=request.candidate_identifier_value,
                claim_target_field=fact.target_field,
                requested_status=status,
                requested_effective_weight=weight,
                reason_codes=_sorted(reasons or {"EVIDENCE_UNUSABLE"}),
                authority_relation_head_hash=snapshot.relation_head.content_hash,
                evaluated_at=request.evaluated_at,
            )
        return _AssessedEvidence(
            snapshot=snapshot,
            fact=fact,
            freshness=freshness,
            application=application,
        )

    @staticmethod
    def _freshness(
        snapshot: _EvidenceSnapshot,
        evaluated_at: datetime,
        current_check: bool,
    ) -> AuthorityFreshnessResult:
        if not current_check:
            return AuthorityFreshnessResult.CURRENT
        if not snapshot.observations:
            return AuthorityFreshnessResult.UNAVAILABLE
        latest = max(
            snapshot.observations,
            key=lambda item: (item.fetched_at, item.authority_evidence_observation_id),
        )
        if latest.retrieval_status != AuthorityRetrievalStatus.SUCCEEDED:
            return AuthorityFreshnessResult.UNAVAILABLE
        if latest.fetched_at - evaluated_at > FUTURE_CLOCK_SKEW_LIMIT:
            return AuthorityFreshnessResult.UNAVAILABLE
        if evaluated_at - latest.fetched_at > FRESHNESS_LIMIT:
            return AuthorityFreshnessResult.STALE
        return AuthorityFreshnessResult.CURRENT

    def _matrix_fact(
        self,
        snapshot: _EvidenceSnapshot,
        request: IssuerAuthorityEvaluationRequest,
    ) -> _MatrixFact:
        evidence = snapshot.evidence
        source = evidence.authority_source_identifier
        document = evidence.source_document_kind
        field = evidence.claim_field
        normalized = evidence.normalized_claim_value
        raw_exact = evidence.raw_claim_value == normalized
        common = (
            evidence.evidence_kind
            in {AuthorityEvidenceKind.ASSERTION, AuthorityEvidenceKind.CORRECTION}
            and raw_exact
        )

        def fact(
            kind: str | None,
            target: str,
            status: AuthorityEvidenceApplicationStatus,
            weight: AuthorityWeight,
            exact: bool,
            current: bool,
            *reasons: str,
        ) -> _MatrixFact:
            return _MatrixFact(
                kind=kind,
                target_field=target,
                requested_status=status,
                requested_weight=weight,
                reason_codes=_sorted(set(reasons) or {"EXACT_ENGINE_MATRIX_MATCH"}),
                exact_shape=exact and common,
                current_check=current,
            )

        if (
            source == "OPENDART_CORP_CODE"
            and document == "CORP_CODE_XML_V1"
            and evidence.authority_scope == AuthorityScope.ISSUER_REGULATORY_ID
            and field == "corp_list.corp.corp_code"
        ):
            exact = (
                isinstance(normalized, str)
                and normalized == request.candidate_identifier_value
                and evidence.authority_document_reference == f"corp-code:{normalized}"
                and evidence.authority_external_key == f"corp-code:{normalized}"
            )
            return fact(
                _KR_CORP_CODE,
                "issuer.corp_code",
                AuthorityEvidenceApplicationStatus.APPLIED_DECISIVE,
                AuthorityWeight.DECISIVE,
                exact,
                False,
                "EXACT_OPENDART_CORP_CODE",
            )
        if (
            source == "OPENDART_COMPANY_OVERVIEW"
            and document == "COMPANY_OVERVIEW_JSON_V1"
            and evidence.authority_scope == AuthorityScope.LEGAL_ENTITY_BRIDGE
            and field == "company.identity_bridge"
        ):
            value = _exact_dict(normalized, {"corp_code", "jurir_no", "stock_code"})
            exact = (
                value is not None
                and value["corp_code"] == request.candidate_identifier_value
                and isinstance(value["jurir_no"], str)
                and _KR_REGISTRATION_PATTERN.fullmatch(value["jurir_no"]) is not None
                and isinstance(value["stock_code"], str)
                and _KR_STOCK_CODE_PATTERN.fullmatch(value["stock_code"]) is not None
                and evidence.authority_document_reference
                == f"company-overview:{request.candidate_identifier_value}"
                and evidence.authority_external_key
                == f"company-overview:{request.candidate_identifier_value}"
            )
            return fact(
                _KR_OVERVIEW_BRIDGE,
                "issuer.authority_bridge",
                AuthorityEvidenceApplicationStatus.APPLIED_SUPPORTING,
                AuthorityWeight.SUPPORTING,
                exact,
                True,
                "EXACT_OPENDART_JURIR_PROVIDER_BRIDGE",
            )
        if (
            source == "KR_SUPREME_COURT_IROS"
            and document == "VERIFIED_CORPORATE_REGISTRY_EXTRACT_V1"
            and evidence.authority_scope == AuthorityScope.LEGAL_JURISDICTION
            and field == "registry.legal_entity_status"
        ):
            value = _exact_dict(
                normalized,
                {
                    "corporate_registration_reference",
                    "entity_kind",
                    "jurisdiction",
                    "verification_reference",
                },
            )
            exact = (
                value is not None
                and value["jurisdiction"] == "KR"
                and value["entity_kind"] == "DOMESTIC_CORPORATION"
                and isinstance(value["corporate_registration_reference"], str)
                and _KR_REGISTRATION_PATTERN.fullmatch(value["corporate_registration_reference"])
                is not None
                and value["verification_reference"] == evidence.authority_document_reference
                and evidence.authority_external_key == evidence.authority_document_reference
            )
            return fact(
                _KR_IROS_JURISDICTION,
                "issuer.jurisdiction",
                AuthorityEvidenceApplicationStatus.APPLIED_DECISIVE,
                AuthorityWeight.DECISIVE,
                exact,
                True,
                "EXACT_IROS_DOMESTIC_JURISDICTION",
            )
        if (
            source == "KR_SUPREME_COURT_IROS"
            and document == "VERIFIED_CORPORATE_REGISTRY_EXTRACT_V1"
            and evidence.authority_scope == AuthorityScope.LEGAL_ENTITY_BRIDGE
            and field == "registry.corporate_registration_reference"
        ):
            exact = (
                isinstance(normalized, str)
                and _KR_REGISTRATION_PATTERN.fullmatch(normalized) is not None
                and evidence.authority_external_key == evidence.authority_document_reference
            )
            return fact(
                _KR_IROS_BRIDGE,
                "issuer.authority_bridge",
                AuthorityEvidenceApplicationStatus.APPLIED_DECISIVE,
                AuthorityWeight.DECISIVE,
                exact,
                True,
                "EXACT_IROS_REGISTRATION_REFERENCE",
            )
        if source == "SEC_EDGAR_ACCEPTED_FILING":
            if (
                document == "SEC_ACCEPTED_ISSUER_FILING_JSON_V1"
                and evidence.authority_scope == AuthorityScope.ISSUER_REGULATORY_ID
                and field == "filing.registrant_cik"
            ):
                exact = (
                    isinstance(normalized, str)
                    and normalized == request.candidate_identifier_value
                    and _SEC_ACCESSION_PATTERN.fullmatch(evidence.authority_document_reference)
                    is not None
                    and evidence.authority_external_key == evidence.authority_document_reference
                )
                return fact(
                    _US_SEC_CIK,
                    "issuer.cik",
                    AuthorityEvidenceApplicationStatus.APPLIED_DECISIVE,
                    AuthorityWeight.DECISIVE,
                    exact,
                    False,
                    "EXACT_SEC_REGISTRANT_CIK",
                )
            if (
                document == "SEC_ACCEPTED_ISSUER_FILING_JSON_V1"
                and evidence.authority_scope == AuthorityScope.REGISTRANT_ROLE
                and field == "filing.registrant_role"
            ):
                value = _exact_dict(normalized, {"accepted_accession", "registrant_cik", "role"})
                exact = (
                    value is not None
                    and value["registrant_cik"] == request.candidate_identifier_value
                    and value["role"] == "ISSUER_REGISTRANT"
                    and value["accepted_accession"] == evidence.authority_document_reference
                    and _SEC_ACCESSION_PATTERN.fullmatch(value["accepted_accession"]) is not None
                    and evidence.authority_external_key == evidence.authority_document_reference
                )
                return fact(
                    _US_SEC_REGISTRANT_ROLE,
                    "issuer.registrant_role",
                    AuthorityEvidenceApplicationStatus.APPLIED_DECISIVE,
                    AuthorityWeight.DECISIVE,
                    exact,
                    False,
                    "EXACT_SEC_ISSUER_REGISTRANT_ROLE",
                )
            if (
                document == "SEC_ACCEPTED_ISSUER_FILING_JSON_V1"
                and evidence.authority_scope == AuthorityScope.LEGAL_ENTITY_BRIDGE
                and field == "filing.legal_entity_bridge"
            ):
                value = _exact_dict(
                    normalized,
                    {
                        "accepted_accession",
                        "formation_state",
                        "provider_symbol",
                        "registrant_cik",
                        "state_entity_number",
                    },
                )
                exact = (
                    value is not None
                    and value["registrant_cik"] == request.candidate_identifier_value
                    and value["accepted_accession"] == evidence.authority_document_reference
                    and _SEC_ACCESSION_PATTERN.fullmatch(value["accepted_accession"]) is not None
                    and isinstance(value["formation_state"], str)
                    and re.fullmatch(r"[A-Z]{2}", value["formation_state"]) is not None
                    and isinstance(value["provider_symbol"], str)
                    and bool(value["provider_symbol"])
                    and isinstance(value["state_entity_number"], str)
                    and _US_STATE_ENTITY_PATTERN.fullmatch(value["state_entity_number"]) is not None
                    and evidence.authority_external_key == evidence.authority_document_reference
                )
                return fact(
                    _US_SEC_BRIDGE,
                    "issuer.authority_bridge",
                    AuthorityEvidenceApplicationStatus.APPLIED_SUPPORTING,
                    AuthorityWeight.SUPPORTING,
                    exact,
                    False,
                    "EXACT_SEC_STATE_PROVIDER_BRIDGE",
                )
            if (
                document == "SEC_REGISTRANT_LATEST_STATUS_JSON_V1"
                and evidence.authority_scope == AuthorityScope.REGISTRANT_ROLE
                and field == "registrant.latest_filing_status"
            ):
                value = _exact_dict(normalized, {"latest_accession", "registrant_cik", "status"})
                exact = (
                    value is not None
                    and value["registrant_cik"] == request.candidate_identifier_value
                    and value["status"] == "CURRENT"
                    and value["latest_accession"] == evidence.authority_document_reference
                    and _SEC_ACCESSION_PATTERN.fullmatch(value["latest_accession"]) is not None
                    and evidence.authority_external_key == evidence.authority_document_reference
                )
                return fact(
                    _US_SEC_LATEST_STATUS,
                    "issuer.latest_authority_status",
                    AuthorityEvidenceApplicationStatus.APPLIED_DECISIVE,
                    AuthorityWeight.DECISIVE,
                    exact,
                    True,
                    "EXACT_SEC_LATEST_STATUS_CHECK",
                )
        if (
            source.startswith("US_STATE_REGISTRY_")
            and document == "VERIFIED_DOMESTIC_ENTITY_RECORD_V1"
            and evidence.authority_scope == AuthorityScope.LEGAL_JURISDICTION
            and field == "registry.legal_entity_status"
        ):
            value = _exact_dict(
                normalized,
                {
                    "formation_state",
                    "jurisdiction",
                    "record_kind",
                    "state_entity_number",
                    "status",
                    "verification_reference",
                },
            )
            state = source.removeprefix("US_STATE_REGISTRY_")
            exact = (
                value is not None
                and state == "DE"
                and value["formation_state"] == state
                and value["jurisdiction"] == "US"
                and value["record_kind"] == "DOMESTIC_FORMATION"
                and value["status"] == "ACTIVE"
                and isinstance(value["state_entity_number"], str)
                and _US_STATE_ENTITY_PATTERN.fullmatch(value["state_entity_number"]) is not None
                and value["verification_reference"] == evidence.authority_document_reference
                and evidence.authority_external_key == evidence.authority_document_reference
            )
            return fact(
                _US_STATE_JURISDICTION,
                "issuer.jurisdiction",
                AuthorityEvidenceApplicationStatus.APPLIED_DECISIVE,
                AuthorityWeight.DECISIVE,
                exact,
                True,
                "EXACT_US_STATE_DOMESTIC_JURISDICTION",
            )
        if source == "SEC_EDGAR_LOGIN_PROVENANCE":
            exact = (
                document == "SEC_SUBMISSION_PROVENANCE_JSON_V1"
                and evidence.authority_scope == AuthorityScope.SUBMISSION_PROVENANCE
                and evidence.subject_role
                in {AuthoritySubjectRole.SEC_LOGIN_CIK, AuthoritySubjectRole.SEC_FILING_AGENT}
                and field in {"submission.login_cik", "submission.provenance_cik"}
                and evidence.evidence_kind == AuthorityEvidenceKind.PROVENANCE_ONLY
                and raw_exact
            )
            return _MatrixFact(
                kind=_PROVENANCE_ONLY,
                target_field="issuer.submission_provenance",
                requested_status=AuthorityEvidenceApplicationStatus.PROVENANCE_ONLY,
                requested_weight=AuthorityWeight.ZERO,
                reason_codes=("SEC_LOGIN_AGENT_PROVENANCE_ZERO_AUTHORITY",),
                exact_shape=exact,
                current_check=False,
            )
        return fact(
            None,
            "issuer.authority_unusable",
            AuthorityEvidenceApplicationStatus.REJECTED_SOURCE_POLICY,
            AuthorityWeight.ZERO,
            False,
            False,
            "SOURCE_SCOPE_ROLE_DOCUMENT_NOT_IN_ENGINE_MATRIX",
        )

    @staticmethod
    def _by_kind(
        assessments: tuple[_AssessedEvidence, ...], kind: str
    ) -> tuple[_AssessedEvidence, ...]:
        return tuple(item for item in assessments if item.fact.kind == kind)

    def _path_evaluation(
        self,
        request: IssuerAuthorityEvaluationRequest,
        provider: _ProviderSnapshot,
        assessments: tuple[_AssessedEvidence, ...],
    ) -> _PathEvaluation:
        if request.candidate_jurisdiction.value == "KR":
            return self._kr_path(request, provider, assessments)
        return self._us_path(request, provider, assessments)

    def _kr_path(
        self,
        request: IssuerAuthorityEvaluationRequest,
        provider: _ProviderSnapshot,
        assessments: tuple[_AssessedEvidence, ...],
    ) -> _PathEvaluation:
        required = {
            _KR_CORP_CODE: self._by_kind(assessments, _KR_CORP_CODE),
            _KR_OVERVIEW_BRIDGE: self._by_kind(assessments, _KR_OVERVIEW_BRIDGE),
            _KR_IROS_JURISDICTION: self._by_kind(assessments, _KR_IROS_JURISDICTION),
            _KR_IROS_BRIDGE: self._by_kind(assessments, _KR_IROS_BRIDGE),
        }
        reasons: set[str] = set(provider.reason_codes)
        reasons.update(self._assessment_reason_codes(assessments))
        for kind, items in required.items():
            if not items:
                reasons.add(f"MISSING_{kind}")
        structural = all(
            any(item.structurally_usable for item in items) for items in required.values()
        )
        relation_safety = any(
            item.snapshot.relation_head.reason_codes for item in assessments if item.fact.kind
        )
        matched_evidence: set[str] = set()
        bridge_match = False
        if structural and provider.safe:
            for overview in required[_KR_OVERVIEW_BRIDGE]:
                for jurisdiction in required[_KR_IROS_JURISDICTION]:
                    for registry_bridge in required[_KR_IROS_BRIDGE]:
                        if not all(
                            item.structurally_usable
                            for item in (overview, jurisdiction, registry_bridge)
                        ):
                            continue
                        overview_value = overview.snapshot.evidence.normalized_claim_value
                        jurisdiction_value = jurisdiction.snapshot.evidence.normalized_claim_value
                        registration = registry_bridge.snapshot.evidence.normalized_claim_value
                        exact = (
                            isinstance(overview_value, dict)
                            and isinstance(jurisdiction_value, dict)
                            and overview_value.get("jurir_no") == registration
                            and jurisdiction_value.get("corporate_registration_reference")
                            == registration
                            and jurisdiction.snapshot.evidence.authority_source_document_id
                            == registry_bridge.snapshot.evidence.authority_source_document_id
                            and overview_value.get("stock_code") in provider.symbols
                        )
                        if exact:
                            bridge_match = True
                            matched_evidence.update(
                                {
                                    overview.snapshot.evidence.evidence_id,
                                    jurisdiction.snapshot.evidence.evidence_id,
                                    registry_bridge.snapshot.evidence.evidence_id,
                                }
                            )
            if not bridge_match:
                reasons.add("KR_EXACT_REGISTRY_PROVIDER_BRIDGE_MISMATCH")
        elif not provider.safe:
            reasons.add("PROVIDER_LINEAGE_NOT_EXACT_BRIDGE_ELIGIBLE")

        core_structural = structural and bridge_match and provider.safe
        current_items = tuple(
            item
            for kind in (
                _KR_OVERVIEW_BRIDGE,
                _KR_IROS_JURISDICTION,
                _KR_IROS_BRIDGE,
            )
            for item in required[kind]
            if item.structurally_usable
        )
        freshness = self._aggregate_freshness(current_items)
        positive = (
            core_structural
            and freshness == AuthorityFreshnessResult.CURRENT
            and all(any(item.positively_applied for item in items) for items in required.values())
        )
        if freshness != AuthorityFreshnessResult.CURRENT:
            reasons.add(f"KR_REQUIRED_CURRENT_CHECK_{freshness.value}")
        if bridge_match:
            reasons.add("KR_EXACT_NON_NAME_PROVIDER_BRIDGE_ESTABLISHED")

        safety = (
            relation_safety
            or (structural and not bridge_match and provider.safe)
            or bool(provider.reason_codes)
        )
        bridge_status = self._bridge_status(
            positive=positive,
            structural=core_structural,
            freshness=freshness,
            safety=safety,
        )
        bridge = build_authority_bridge_result(
            candidate_jurisdiction=request.candidate_jurisdiction,
            candidate_identifier_kind=request.candidate_identifier_kind,
            candidate_identifier_value=request.candidate_identifier_value,
            bridge_status=bridge_status,
            authority_evidence_ids=_sorted(matched_evidence),
            provider_observation_ids=request.provider_observation_ids,
            reason_codes=_sorted(reasons or {"KR_AUTHORITY_PATH_UNRESOLVED"}),
        )
        scope_results = (
            self._scope_result(
                AuthorityScope.ISSUER_REGULATORY_ID,
                required[_KR_CORP_CODE],
                "KR_CORP_CODE_AUTHORITY",
            ),
            self._scope_result(
                AuthorityScope.LEGAL_ENTITY_BRIDGE,
                required[_KR_OVERVIEW_BRIDGE] + required[_KR_IROS_BRIDGE],
                "KR_EXACT_LEGAL_ENTITY_BRIDGE",
                forced_status=self._bridge_scope_status(bridge_status),
                extra_reasons=bridge.reason_codes,
            ),
            self._scope_result(
                AuthorityScope.LEGAL_JURISDICTION,
                required[_KR_IROS_JURISDICTION],
                "KR_IROS_JURISDICTION",
            ),
        )
        legal = (
            AuthorityLegalJurisdictionResult.ESTABLISHED
            if any(item.positively_applied for item in required[_KR_IROS_JURISDICTION])
            else AuthorityLegalJurisdictionResult.UNRESOLVED
        )
        for scope_result in scope_results:
            reasons.update(scope_result.reason_codes)
        return _PathEvaluation(
            bridge=bridge,
            scope_results=tuple(sorted(scope_results, key=lambda item: item.authority_scope.value)),
            legal_jurisdiction_result=legal,
            freshness_result=freshness,
            structural_complete=core_structural,
            positive_complete=positive,
            safety_event=safety,
            reason_codes=_sorted(reasons or {"KR_AUTHORITY_PATH_UNRESOLVED"}),
        )

    def _us_path(
        self,
        request: IssuerAuthorityEvaluationRequest,
        provider: _ProviderSnapshot,
        assessments: tuple[_AssessedEvidence, ...],
    ) -> _PathEvaluation:
        required = {
            _US_SEC_CIK: self._by_kind(assessments, _US_SEC_CIK),
            _US_SEC_REGISTRANT_ROLE: self._by_kind(assessments, _US_SEC_REGISTRANT_ROLE),
            _US_SEC_BRIDGE: self._by_kind(assessments, _US_SEC_BRIDGE),
            _US_SEC_LATEST_STATUS: self._by_kind(assessments, _US_SEC_LATEST_STATUS),
            _US_STATE_JURISDICTION: self._by_kind(assessments, _US_STATE_JURISDICTION),
        }
        reasons: set[str] = set(provider.reason_codes)
        reasons.update(self._assessment_reason_codes(assessments))
        core_kinds = (
            _US_SEC_CIK,
            _US_SEC_REGISTRANT_ROLE,
            _US_SEC_BRIDGE,
            _US_STATE_JURISDICTION,
        )
        for kind in core_kinds:
            if not required[kind]:
                reasons.add(f"MISSING_{kind}")
        if not required[_US_SEC_LATEST_STATUS]:
            reasons.add("US_CURRENT_STATUS_CHECK_MISSING")
        structural = all(
            any(item.structurally_usable for item in required[kind]) for kind in core_kinds
        )
        relation_safety = any(
            item.snapshot.relation_head.reason_codes for item in assessments if item.fact.kind
        )
        matched_evidence: set[str] = set()
        bridge_match = False
        if structural and provider.safe:
            for cik in required[_US_SEC_CIK]:
                for role in required[_US_SEC_REGISTRANT_ROLE]:
                    for bridge_item in required[_US_SEC_BRIDGE]:
                        for state in required[_US_STATE_JURISDICTION]:
                            if not all(
                                item.structurally_usable for item in (cik, role, bridge_item, state)
                            ):
                                continue
                            role_value = role.snapshot.evidence.normalized_claim_value
                            bridge_value = bridge_item.snapshot.evidence.normalized_claim_value
                            state_value = state.snapshot.evidence.normalized_claim_value
                            same_filing = (
                                len(
                                    {
                                        cik.snapshot.evidence.authority_source_document_id,
                                        role.snapshot.evidence.authority_source_document_id,
                                        bridge_item.snapshot.evidence.authority_source_document_id,
                                    }
                                )
                                == 1
                            )
                            exact = (
                                same_filing
                                and isinstance(role_value, dict)
                                and isinstance(bridge_value, dict)
                                and isinstance(state_value, dict)
                                and role_value.get("accepted_accession")
                                == bridge_value.get("accepted_accession")
                                and bridge_value.get("formation_state")
                                == state_value.get("formation_state")
                                and bridge_value.get("state_entity_number")
                                == state_value.get("state_entity_number")
                                and bridge_value.get("provider_symbol") in provider.symbols
                            )
                            if exact:
                                bridge_match = True
                                matched_evidence.update(
                                    item.snapshot.evidence.evidence_id
                                    for item in (cik, role, bridge_item, state)
                                )
            if not bridge_match:
                reasons.add("US_EXACT_STATE_SEC_PROVIDER_BRIDGE_MISMATCH")
        elif not provider.safe:
            reasons.add("PROVIDER_LINEAGE_NOT_EXACT_BRIDGE_ELIGIBLE")

        latest_structural = any(
            item.structurally_usable for item in required[_US_SEC_LATEST_STATUS]
        )
        current_items = tuple(
            item
            for kind in (_US_SEC_LATEST_STATUS, _US_STATE_JURISDICTION)
            for item in required[kind]
            if item.structurally_usable
        )
        freshness = (
            self._aggregate_freshness(current_items)
            if latest_structural
            else AuthorityFreshnessResult.UNAVAILABLE
        )
        core_structural = structural and bridge_match and provider.safe
        positive = (
            core_structural
            and latest_structural
            and freshness == AuthorityFreshnessResult.CURRENT
            and all(any(item.positively_applied for item in required[kind]) for kind in required)
        )
        if freshness != AuthorityFreshnessResult.CURRENT:
            reasons.add(f"US_REQUIRED_CURRENT_CHECK_{freshness.value}")
        if bridge_match:
            reasons.add("US_EXACT_NON_NAME_PROVIDER_BRIDGE_ESTABLISHED")
        safety = (
            relation_safety
            or (structural and not bridge_match and provider.safe)
            or bool(provider.reason_codes)
        )
        bridge_status = self._bridge_status(
            positive=positive,
            structural=core_structural,
            freshness=freshness,
            safety=safety,
        )
        bridge = build_authority_bridge_result(
            candidate_jurisdiction=request.candidate_jurisdiction,
            candidate_identifier_kind=request.candidate_identifier_kind,
            candidate_identifier_value=request.candidate_identifier_value,
            bridge_status=bridge_status,
            authority_evidence_ids=_sorted(matched_evidence),
            provider_observation_ids=request.provider_observation_ids,
            reason_codes=_sorted(reasons or {"US_AUTHORITY_PATH_UNRESOLVED"}),
        )
        scope_results = (
            self._scope_result(
                AuthorityScope.ISSUER_REGULATORY_ID,
                required[_US_SEC_CIK],
                "US_SEC_REGISTRANT_CIK_AUTHORITY",
            ),
            self._scope_result(
                AuthorityScope.LEGAL_ENTITY_BRIDGE,
                required[_US_SEC_BRIDGE],
                "US_EXACT_LEGAL_ENTITY_BRIDGE",
                forced_status=self._bridge_scope_status(bridge_status),
                extra_reasons=bridge.reason_codes,
            ),
            self._scope_result(
                AuthorityScope.LEGAL_JURISDICTION,
                required[_US_STATE_JURISDICTION],
                "US_STATE_FORMATION_JURISDICTION",
            ),
            self._scope_result(
                AuthorityScope.REGISTRANT_ROLE,
                required[_US_SEC_REGISTRANT_ROLE] + required[_US_SEC_LATEST_STATUS],
                "US_ACCEPTED_ISSUER_REGISTRANT_ROLE",
            ),
        )
        legal = (
            AuthorityLegalJurisdictionResult.ESTABLISHED
            if any(item.positively_applied for item in required[_US_STATE_JURISDICTION])
            else AuthorityLegalJurisdictionResult.UNRESOLVED
        )
        for scope_result in scope_results:
            reasons.update(scope_result.reason_codes)
        return _PathEvaluation(
            bridge=bridge,
            scope_results=tuple(sorted(scope_results, key=lambda item: item.authority_scope.value)),
            legal_jurisdiction_result=legal,
            freshness_result=freshness,
            structural_complete=core_structural,
            positive_complete=positive,
            safety_event=safety,
            reason_codes=_sorted(reasons or {"US_AUTHORITY_PATH_UNRESOLVED"}),
        )

    @staticmethod
    def _aggregate_freshness(
        items: tuple[_AssessedEvidence, ...],
    ) -> AuthorityFreshnessResult:
        results = {item.freshness for item in items if item.fact.current_check}
        if AuthorityFreshnessResult.UNAVAILABLE in results:
            return AuthorityFreshnessResult.UNAVAILABLE
        if AuthorityFreshnessResult.STALE in results:
            return AuthorityFreshnessResult.STALE
        return AuthorityFreshnessResult.CURRENT

    @staticmethod
    def _assessment_reason_codes(
        assessments: tuple[_AssessedEvidence, ...],
    ) -> set[str]:
        reasons: set[str] = set()
        for assessment in assessments:
            reasons.update(assessment.snapshot.relation_head.reason_codes)
            if assessment.application is None:
                reasons.update(assessment.fact.reason_codes)
            elif not assessment.positively_applied:
                reasons.update(assessment.application.reason_codes)
        return reasons

    @staticmethod
    def _bridge_status(
        *,
        positive: bool,
        structural: bool,
        freshness: AuthorityFreshnessResult,
        safety: bool,
    ) -> AuthorityBridgeStatus:
        if positive:
            return AuthorityBridgeStatus.ESTABLISHED
        if safety:
            return AuthorityBridgeStatus.CONFLICT
        if structural and freshness != AuthorityFreshnessResult.CURRENT:
            return AuthorityBridgeStatus.STALE
        return AuthorityBridgeStatus.MISSING

    @staticmethod
    def _bridge_scope_status(status: AuthorityBridgeStatus) -> AuthorityBundleScopeStatus:
        return {
            AuthorityBridgeStatus.ESTABLISHED: AuthorityBundleScopeStatus.SATISFIED,
            AuthorityBridgeStatus.MISSING: AuthorityBundleScopeStatus.MISSING,
            AuthorityBridgeStatus.CONFLICT: AuthorityBundleScopeStatus.CONFLICT,
            AuthorityBridgeStatus.STALE: AuthorityBundleScopeStatus.STALE,
            AuthorityBridgeStatus.UNUSABLE: AuthorityBundleScopeStatus.UNUSABLE,
        }[status]

    @staticmethod
    def _scope_result(
        scope: AuthorityScope,
        items: tuple[_AssessedEvidence, ...],
        satisfied_reason: str,
        *,
        forced_status: AuthorityBundleScopeStatus | None = None,
        extra_reasons: tuple[str, ...] = (),
    ) -> AuthorityBundleScopeResult:
        if forced_status is not None:
            status = forced_status
        elif any(item.positively_applied for item in items):
            status = AuthorityBundleScopeStatus.SATISFIED
        elif any(item.snapshot.relation_head.reason_codes for item in items):
            status = AuthorityBundleScopeStatus.CONFLICT
        elif any(
            item.fact.current_check and item.freshness != AuthorityFreshnessResult.CURRENT
            for item in items
        ):
            status = AuthorityBundleScopeStatus.STALE
        elif items:
            status = AuthorityBundleScopeStatus.UNUSABLE
        else:
            status = AuthorityBundleScopeStatus.MISSING
        reasons = {
            (
                satisfied_reason
                if status == AuthorityBundleScopeStatus.SATISFIED
                else f"{scope.value}_{status.value}"
            )
        }
        if status != AuthorityBundleScopeStatus.SATISFIED:
            reasons.update(extra_reasons)
        return build_authority_bundle_scope_result(
            authority_scope=scope,
            scope_status=status,
            reason_codes=_sorted(reasons),
        )

    def _identifier_claims(
        self,
        request: IssuerAuthorityEvaluationRequest,
        assessments: tuple[_AssessedEvidence, ...],
    ) -> tuple[AuthorityIdentifierClaim, ...]:
        claims: list[AuthorityIdentifierClaim] = []
        for assessment in assessments:
            application = assessment.application
            if (
                application is None
                or not assessment.positively_applied
                or assessment.snapshot.evidence.authority_scope
                != AuthorityScope.ISSUER_REGULATORY_ID
                or application.effective_issuer_authority_weight != AuthorityWeight.DECISIVE
            ):
                continue
            claims.append(
                build_authority_identifier_claim(
                    identifier_kind=request.candidate_identifier_kind,
                    normalized_identifier_value=request.candidate_identifier_value,
                    candidate_jurisdiction=request.candidate_jurisdiction,
                    provider_security_identity_id=request.provider_security_identity_id,
                    application=application,
                    evidence=assessment.snapshot.evidence,
                    policy=assessment.snapshot.policy,
                    claim_role=assessment.snapshot.evidence.subject_role,
                    recorded_at=application.evaluated_at,
                )
            )
        return tuple(sorted(claims, key=lambda item: item.authority_identifier_claim_id))

    def _collision_scan(
        self,
        session: Session,
        request: IssuerAuthorityEvaluationRequest,
        provider: _ProviderSnapshot,
        relations: tuple[AuthorityEvidenceRelation, ...],
    ) -> _CollisionScan:
        reasons: set[str] = set(provider.reason_codes)
        current_claims: list[AuthorityIdentifierClaim] = []
        claim_rows = session.scalars(
            select(AuthorityIdentifierClaimRow).order_by(
                AuthorityIdentifierClaimRow.authority_identifier_claim_id
            )
        ).all()
        for claim_row in claim_rows:
            claim = AuthorityIdentifierClaim.model_validate_json(
                claim_row.payload_json, strict=False
            )
            head = self._relation_head(claim.evidence_id, relations)
            if head.conflict:
                reasons.add("CLAIM_RELATION_HEAD_CONFLICT")
            if head.current and not head.conflict:
                current_claims.append(claim)
        current_applications: list[tuple[AuthorityEvidenceApplication, AuthorityEvidence]] = []
        application_rows = session.scalars(
            select(AuthorityEvidenceApplicationRow).order_by(
                AuthorityEvidenceApplicationRow.evidence_application_id
            )
        ).all()
        for application_row in application_rows:
            try:
                application = AuthorityEvidenceApplication.model_validate_json(
                    application_row.payload_json, strict=False
                )
            except ValidationError as error:
                raise IssuerAuthorityDecisionEngineError(
                    "STORED_APPLICATION_CONTRACT_INVALID",
                    "stored authority application failed its immutable contract",
                ) from error
            if (
                application.application_status
                != AuthorityEvidenceApplicationStatus.APPLIED_DECISIVE
                or application.effective_issuer_authority_weight != AuthorityWeight.DECISIVE
                or application.authority_scope != AuthorityScope.ISSUER_REGULATORY_ID
                or application.claim_target_field not in {"issuer.corp_code", "issuer.cik"}
                or not application.production_authority_admitted
                or application.lineage_tainted
            ):
                continue
            evidence_row = session.get(AuthorityEvidenceRow, application.evidence_id)
            policy_row = session.get(
                AuthoritySourcePolicyRow, application.authority_source_policy_id
            )
            if evidence_row is None or policy_row is None:
                raise IssuerAuthorityDecisionEngineError(
                    "STORED_APPLICATION_DEPENDENCY_MISSING",
                    "positive authority application lost an immutable dependency",
                )
            evidence = AuthorityEvidence.model_validate_json(
                evidence_row.payload_json, strict=False
            )
            policy = AuthoritySourcePolicy.model_validate_json(
                policy_row.payload_json, strict=False
            )
            head = self._relation_head(evidence.evidence_id, relations)
            if not head.current or head.conflict:
                continue
            if application.authority_relation_head_hash != head.content_hash:
                # A predecessor relation may have been appended after this application.
                # The immutable application remains history but is not a current path.
                continue
            if not is_exact_server_owned_production_policy(policy):
                reasons.add("CURRENT_APPLICATION_SOURCE_POLICY_INVALID")
                continue
            current_applications.append((application, evidence))
        same_identifier = [
            claim
            for claim in current_claims
            if claim.identifier_kind == request.candidate_identifier_kind
            and claim.normalized_identifier_value == request.candidate_identifier_value
        ]
        if len({claim.candidate_fingerprint for claim in same_identifier}) > 1:
            reasons.add("IDENTIFIER_CANDIDATE_FINGERPRINT_COLLISION")
        if len({claim.provider_security_identity_id for claim in same_identifier}) > 1:
            reasons.add("IDENTIFIER_PROVIDER_SUBJECT_COLLISION")
        expected_target = (
            "issuer.corp_code"
            if request.candidate_identifier_kind == AuthorityIdentifierKind.DART_CORP_CODE
            else "issuer.cik"
        )
        same_identifier_applications = [
            (application, evidence)
            for application, evidence in current_applications
            if application.claim_target_field == expected_target
            and evidence.normalized_claim_value == request.candidate_identifier_value
        ]
        if (
            len(
                {
                    application.candidate_fingerprint
                    for application, _ in same_identifier_applications
                }
            )
            > 1
        ):
            reasons.add("APPLICATION_IDENTIFIER_CANDIDATE_COLLISION")
        if (
            len(
                {
                    application.provider_security_identity_id
                    for application, _ in same_identifier_applications
                }
            )
            > 1
        ):
            reasons.add("APPLICATION_IDENTIFIER_PROVIDER_COLLISION")
        same_provider = [
            claim
            for claim in current_claims
            if claim.provider_security_identity_id == request.provider_security_identity_id
        ]
        if (
            len(
                {
                    (claim.identifier_kind.value, claim.normalized_identifier_value)
                    for claim in same_provider
                }
            )
            > 1
        ):
            reasons.add("PROVIDER_CONTRADICTORY_ISSUER_CANDIDATES")
        same_provider_applications = [
            application
            for application, _ in current_applications
            if application.provider_security_identity_id == request.provider_security_identity_id
        ]
        if (
            len({application.candidate_fingerprint for application in same_provider_applications})
            > 1
        ):
            reasons.add("APPLICATION_PROVIDER_CANDIDATE_COLLISION")
        canonical = session.scalar(
            select(IssuerRow).where(
                IssuerRow.corp_code == request.candidate_identifier_value
                if request.candidate_identifier_kind == AuthorityIdentifierKind.DART_CORP_CODE
                else IssuerRow.cik == request.candidate_identifier_value
            )
        )
        if canonical is not None:
            reasons.add("EXISTING_CANONICAL_IDENTIFIER_CONFLICT")
        fingerprints = _sorted(
            {claim.candidate_fingerprint for claim in same_identifier}
            | {application.candidate_fingerprint for application, _ in same_identifier_applications}
            | {
                authority_candidate_fingerprint(
                    jurisdiction=request.candidate_jurisdiction,
                    identifier_kind=request.candidate_identifier_kind,
                    identifier_value=request.candidate_identifier_value,
                )
            }
        )
        return _CollisionScan(
            result=(
                AuthorityCollisionScanResult.CONFLICT
                if reasons
                else AuthorityCollisionScanResult.CLEAR
            ),
            candidate_fingerprints=fingerprints,
            reason_codes=_sorted(reasons or {"GLOBAL_COLLISION_SCAN_CLEAR"}),
        )

    @staticmethod
    def _decision_state(
        path: _PathEvaluation,
        collision: _CollisionScan,
        has_predecessor: bool,
    ) -> IssuerMachineDecisionState:
        safety = path.safety_event or collision.result == AuthorityCollisionScanResult.CONFLICT
        if safety:
            return (
                IssuerMachineDecisionState.REVIEW_REQUIRED
                if has_predecessor
                else IssuerMachineDecisionState.UNRESOLVED
            )
        if path.structural_complete and path.freshness_result != AuthorityFreshnessResult.CURRENT:
            return IssuerMachineDecisionState.STALE
        if path.positive_complete:
            return IssuerMachineDecisionState.READY_FOR_MANUAL_REVIEW
        return IssuerMachineDecisionState.UNRESOLVED

    @staticmethod
    def _latest_revision_check_hash(
        request: IssuerAuthorityEvaluationRequest,
        assessments: tuple[_AssessedEvidence, ...],
        path: _PathEvaluation,
    ) -> str:
        checks = []
        for assessment in assessments:
            latest_status = None
            if assessment.snapshot.observations:
                latest = max(
                    assessment.snapshot.observations,
                    key=lambda item: (
                        item.fetched_at,
                        item.authority_evidence_observation_id,
                    ),
                )
                latest_status = {
                    "raw_content_hash": latest.raw_content_hash,
                    "retrieval_status": latest.retrieval_status,
                    "safe_status_code": latest.safe_status_code,
                }
            checks.append(
                {
                    "evidence_id": assessment.snapshot.evidence.evidence_id,
                    "relation_head_hash": assessment.snapshot.relation_head.content_hash,
                    "relation_current": assessment.snapshot.relation_head.current,
                    "current_check": assessment.fact.current_check,
                    "freshness_result": assessment.freshness,
                    "latest_retrieval_semantics": latest_status,
                }
            )
        return authority_sha256(
            {
                "source_policy_registry_version": SOURCE_POLICY_REGISTRY_VERSION,
                "freshness_policy_version": FRESHNESS_POLICY_VERSION,
                "candidate_fingerprint": authority_candidate_fingerprint(
                    jurisdiction=request.candidate_jurisdiction,
                    identifier_kind=request.candidate_identifier_kind,
                    identifier_value=request.candidate_identifier_value,
                ),
                "checks": tuple(sorted(checks, key=lambda item: item["evidence_id"])),
                "aggregate_freshness_result": path.freshness_result,
            }
        )

    def _revalidate_ready_locked(
        self,
        session: Session,
        *,
        request: IssuerAuthorityEvaluationRequest,
        provider: _ProviderSnapshot,
        assessments: tuple[_AssessedEvidence, ...],
        path: _PathEvaluation,
        collision: _CollisionScan,
        bundle: AuthorityBundle,
    ) -> None:
        reloaded_provider = self._provider_snapshot(session, request)
        if reloaded_provider.reason_codes or reloaded_provider.symbols != provider.symbols:
            raise IssuerAuthorityDecisionEngineError(
                "READY_PROVIDER_REVALIDATION_FAILED",
                "provider subject changed before READY persistence",
            )
        current_relations = self._all_relations(session)
        for assessment in assessments:
            current = self._relation_head(
                assessment.snapshot.evidence.evidence_id,
                current_relations,
            )
            if current != assessment.snapshot.relation_head:
                raise IssuerAuthorityDecisionEngineError(
                    "READY_RELATION_HEAD_REVALIDATION_FAILED",
                    "authority correction/revocation head changed before READY persistence",
                )
            if not is_exact_server_owned_production_policy(assessment.snapshot.policy):
                raise IssuerAuthorityDecisionEngineError(
                    "READY_SOURCE_POLICY_REVALIDATION_FAILED",
                    "source policy is not the exact server-owned registry entry",
                )
        rescanned = self._collision_scan(session, request, reloaded_provider, current_relations)
        if rescanned != collision or rescanned.result != AuthorityCollisionScanResult.CLEAR:
            raise IssuerAuthorityDecisionEngineError(
                "READY_COLLISION_REVALIDATION_FAILED",
                "global identifier/provider collision state changed before READY persistence",
            )
        if (
            not path.positive_complete
            or path.bridge.bridge_status != AuthorityBridgeStatus.ESTABLISHED
            or path.freshness_result != AuthorityFreshnessResult.CURRENT
            or not bundle_satisfies_review_ready_foundation(bundle)
        ):
            raise IssuerAuthorityDecisionEngineError(
                "READY_POSITIVE_GATE_REVALIDATION_FAILED",
                "complete source, bridge, jurisdiction, freshness, and collision gate failed",
            )

    @staticmethod
    def _decision_leaf(session: Session, provider_id: str) -> IssuerDecision | None:
        rows = session.scalars(
            select(IssuerDecisionRow)
            .where(IssuerDecisionRow.provider_security_identity_id == provider_id)
            .order_by(IssuerDecisionRow.issuer_decision_id)
        ).all()
        child_ids = {
            row.supersedes_decision_id for row in rows if row.supersedes_decision_id is not None
        }
        leaves = [row for row in rows if row.issuer_decision_id not in child_ids]
        if len(leaves) > 1:
            raise IssuerAuthorityDecisionEngineError(
                "DECISION_CHAIN_AMBIGUOUS",
                "provider authority subject has more than one current decision leaf",
            )
        if not leaves:
            return None
        return IssuerDecision.model_validate_json(leaves[0].payload_json, strict=False)

    @staticmethod
    def _same_decision_semantics(
        predecessor: IssuerDecision,
        candidate: IssuerDecision,
    ) -> bool:
        candidate_without_new_parent = candidate.model_copy(
            update={"supersedes_decision_id": predecessor.supersedes_decision_id}
        )
        return (
            predecessor.authority_bundle_id == candidate.authority_bundle_id
            and predecessor.decision_state == candidate.decision_state
            and predecessor.reason_codes == candidate.reason_codes
            and predecessor.latest_revision_check_hash == candidate.latest_revision_check_hash
            and predecessor.freshness_result == candidate.freshness_result
            and predecessor.collision_scan_hash == candidate.collision_scan_hash
            and candidate_without_new_parent.supersedes_decision_id
            == predecessor.supersedes_decision_id
        )

    @staticmethod
    def _insert_or_reuse_application(
        session: Session,
        application: AuthorityEvidenceApplication,
    ) -> tuple[AuthorityEvidenceApplication, bool]:
        existing = session.get(
            AuthorityEvidenceApplicationRow,
            application.evidence_application_id,
        )
        if existing is not None:
            stored = AuthorityEvidenceApplication.model_validate_json(
                existing.payload_json, strict=False
            )
            if stored.application_content_hash != application.application_content_hash:
                raise AuthorityLedgerConflict(
                    "engine application semantic identity has conflicting immutable content"
                )
            return stored, False
        evidence = SQLiteAuthorityLedgerRepository._required_evidence(
            session, application.evidence_id
        )
        policy = SQLiteAuthorityLedgerRepository._required_policy(
            session, application.authority_source_policy_id
        )
        SQLiteAuthorityLedgerRepository._validate_application_dependencies(
            session, application, evidence, policy
        )
        session.add(
            SQLiteAuthorityLedgerRepository._application_row(application, _payload(application))
        )
        return application, True

    @staticmethod
    def _insert_or_reuse_claim(
        session: Session,
        claim: AuthorityIdentifierClaim,
    ) -> tuple[AuthorityIdentifierClaim, bool]:
        existing = session.get(
            AuthorityIdentifierClaimRow,
            claim.authority_identifier_claim_id,
        )
        if existing is not None:
            stored = AuthorityIdentifierClaim.model_validate_json(
                existing.payload_json, strict=False
            )
            if stored.claim_content_hash != claim.claim_content_hash:
                raise AuthorityLedgerConflict(
                    "engine identifier claim has conflicting immutable content"
                )
            return stored, False
        application = SQLiteAuthorityLedgerRepository._required_application(
            session, claim.evidence_application_id
        )
        if (
            application.application_content_hash != claim.application_content_hash
            or application.evidence_id != claim.evidence_id
            or application.candidate_fingerprint != claim.candidate_fingerprint
            or application.provider_security_identity_id != claim.provider_security_identity_id
        ):
            raise AuthorityLedgerConflict("engine identifier claim/application mismatch")
        session.add(SQLiteAuthorityLedgerRepository._identifier_claim_row(claim, _payload(claim)))
        return claim, True

    @staticmethod
    def _insert_or_reuse_bundle(
        session: Session,
        bundle: AuthorityBundle,
    ) -> tuple[AuthorityBundle, bool]:
        existing = session.get(AuthorityBundleRow, bundle.authority_bundle_id)
        if existing is not None:
            stored = AuthorityBundle.model_validate_json(existing.payload_json, strict=False)
            if stored.bundle_content_hash != bundle.bundle_content_hash:
                raise AuthorityLedgerConflict(
                    "engine bundle semantic identity has conflicting immutable content"
                )
            SQLiteAuthorityLedgerRepository._verify_stored_bundle(
                session, existing, existing.payload_json, stored
            )
            return stored, False
        SQLiteAuthorityLedgerRepository._validate_bundle_dependencies(session, bundle)
        session.add(SQLiteAuthorityLedgerRepository._bundle_row(bundle, _payload(bundle)))
        session.flush()
        SQLiteAuthorityLedgerRepository._append_bundle_membership(session, bundle)
        return bundle, True

    @staticmethod
    def _insert_engine_decision(
        session: Session,
        decision: IssuerDecision,
    ) -> tuple[IssuerDecision, bool]:
        existing = session.get(IssuerDecisionRow, decision.issuer_decision_id)
        if existing is not None:
            stored = IssuerDecision.model_validate_json(existing.payload_json, strict=False)
            if stored.decision_content_hash != decision.decision_content_hash:
                raise AuthorityLedgerConflict(
                    "engine decision semantic identity has conflicting immutable content"
                )
            return stored, False
        bundle = SQLiteAuthorityLedgerRepository._required_bundle(
            session, decision.authority_bundle_id
        )
        if (
            bundle.bundle_content_hash != decision.authority_bundle_content_hash
            or bundle.provider_security_identity_id != decision.provider_security_identity_id
            or bundle.proposed_issuer_id != decision.proposed_issuer_id
            or bundle.collision_scan_hash != decision.collision_scan_hash
        ):
            raise AuthorityLedgerConflict("engine decision does not match exact bundle")
        if decision.supersedes_decision_id is not None:
            predecessor = session.get(IssuerDecisionRow, decision.supersedes_decision_id)
            if predecessor is None:
                raise AuthorityLedgerConflict("engine decision predecessor is missing")
            if predecessor.provider_security_identity_id != decision.provider_security_identity_id:
                raise AuthorityLedgerConflict(
                    "engine decision predecessor belongs to another provider subject"
                )
        session.add(SQLiteAuthorityLedgerRepository._decision_row(decision, _payload(decision)))
        session.flush()
        return decision, True
