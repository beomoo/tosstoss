from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import ValidationError
from sqlalchemy import or_, select
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
    AuthorityEvidenceRelationType,
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
    proposed_issuer_anchor,
    proposed_issuer_id,
)
from toss_dashboard_api.contracts.authority_decision import (
    AuthorityBridgeResult,
    AuthorityBridgeStatus,
    IssuerAuthorityEvaluationRequest,
    build_authority_bridge_result,
)
from toss_dashboard_api.contracts.base import normalized_hash
from toss_dashboard_api.contracts.enums import MappingStatus, ProviderIdentityState
from toss_dashboard_api.contracts.issuer import Issuer
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
_KR_OPENDART_LEGAL_NAME = "KR_OPENDART_LEGAL_NAME"
_KR_IROS_JURISDICTION = "KR_IROS_JURISDICTION"
_KR_IROS_BRIDGE = "KR_IROS_BRIDGE"
_KR_IROS_LEGAL_NAME = "KR_IROS_LEGAL_NAME"
_US_SEC_CIK = "US_SEC_CIK"
_US_SEC_REGISTRANT_ROLE = "US_SEC_REGISTRANT_ROLE"
_US_SEC_BRIDGE = "US_SEC_BRIDGE"
_US_SEC_LEGAL_NAME = "US_SEC_LEGAL_NAME"
_US_SEC_LATEST_STATUS = "US_SEC_LATEST_STATUS"
_US_STATE_JURISDICTION = "US_STATE_JURISDICTION"
_US_STATE_LEGAL_NAME = "US_STATE_LEGAL_NAME"
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
    component_evidence_ids: tuple[str, ...]
    relation_types: tuple[AuthorityEvidenceRelationType, ...]


@dataclass(frozen=True)
class _EvidenceSnapshot:
    evidence: AuthorityEvidence
    policy: AuthoritySourcePolicy
    observations: tuple[AuthorityEvidenceObservation, ...]
    relation_head: _RelationHead
    relation_component_evidence: tuple[AuthorityEvidence, ...]
    relation_component_document_evidence: tuple[AuthorityEvidence, ...]


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
class _NameReconciliation:
    established: bool
    conflict: bool
    scope_status: AuthorityBundleScopeStatus
    evidence_ids: tuple[str, ...]
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class _CollisionScan:
    result: AuthorityCollisionScanResult
    candidate_fingerprints: tuple[str, ...]
    reason_codes: tuple[str, ...]
    affected_provider_ids: tuple[str, ...]


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


def _server_utc_now() -> datetime:
    return datetime.now(UTC)


class IssuerAuthorityDecisionEngine:
    """Offline B2-B issuer-side machine evaluation over the immutable ledger.

    The only positive write surface is ``evaluate``. It accepts identity and
    evidence membership, never caller authority classifications, weights,
    bridge booleans, collision results, overrides, or READY state.
    """

    def __init__(
        self,
        sessions: sessionmaker[Session],
        *,
        clock: Callable[[], datetime] = _server_utc_now,
    ) -> None:
        self._sessions = sessions
        self._clock = clock

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
            evaluated_at = self._evaluation_time()
            result = self._evaluate_locked(session, request, evaluated_at)
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

    def _evaluation_time(self) -> datetime:
        try:
            value = self._clock()
        except Exception as error:
            raise IssuerAuthorityDecisionEngineError(
                "SERVER_CLOCK_UNAVAILABLE",
                "server-owned evaluation clock failed",
            ) from error
        if value.tzinfo is None or value.utcoffset() is None:
            raise IssuerAuthorityDecisionEngineError(
                "SERVER_CLOCK_INVALID",
                "server-owned evaluation clock must return an aware timestamp",
            )
        return value.astimezone(UTC)

    def _evaluate_locked(
        self,
        session: Session,
        request: IssuerAuthorityEvaluationRequest,
        evaluated_at: datetime,
    ) -> IssuerAuthorityDecisionEngineResult:
        provider = self._provider_snapshot(
            session,
            provider_security_identity_id=request.provider_security_identity_id,
            seed_observation_ids=request.provider_observation_ids,
        )
        relations = self._all_relations(session)
        evidence = self._discover_relevant_evidence(
            session,
            request,
            relations,
        )
        provider_observation_ids = tuple(
            observation.observation_id for observation in provider.observations
        )
        assessments = tuple(
            self._assess_evidence(
                snapshot,
                request,
                evaluated_at,
                provider_observation_ids,
            )
            for snapshot in evidence
        )

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
            provider_observation_ids=provider_observation_ids,
            candidate_jurisdiction=request.candidate_jurisdiction,
            candidate_identifier_kind=request.candidate_identifier_kind,
            candidate_identifier_value=request.candidate_identifier_value,
            applications=applications,
            required_scope_results=path.scope_results,
            legal_jurisdiction_result=path.legal_jurisdiction_result,
            collision_scan_result=collision.result,
            collision_claim_candidate_fingerprints=collision.candidate_fingerprints,
            built_at=evaluated_at,
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
            evaluated_at=evaluated_at,
            supersedes_decision_id=(
                None if predecessor is None else predecessor.issuer_decision_id
            ),
        )
        if predecessor is not None and self._same_decision_semantics(predecessor, decision):
            decision = predecessor
            decision_inserted = False
        else:
            decision, decision_inserted = self._insert_engine_decision(session, decision)
        session.flush()
        self._invalidate_impacted_ready_leaves(
            session,
            collision=collision,
            evaluated_provider_id=request.provider_security_identity_id,
            evaluated_at=evaluated_at,
        )

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
        *,
        provider_security_identity_id: str,
        seed_observation_ids: tuple[str, ...],
    ) -> _ProviderSnapshot:
        row = session.get(
            ProviderSecurityIdentityRow,
            provider_security_identity_id,
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
        for observation_id in seed_observation_ids:
            stored = session.get(ProviderSecurityMasterObservationRow, observation_id)
            if stored is None:
                raise IssuerAuthorityDecisionEngineError(
                    "PROVIDER_OBSERVATION_MISSING",
                    "seed CP3-C1 provider observation does not exist",
                )
            if stored.provider_security_identity_id != provider_security_identity_id:
                raise IssuerAuthorityDecisionEngineError(
                    "PROVIDER_OBSERVATION_SUBJECT_MISMATCH",
                    "provider observation belongs to another provider identity",
                )
            if stored.source_version_id != row.latest_source_version_id:
                reasons.add("PROVIDER_SEED_OBSERVATION_NOT_CURRENT")

        current_rows = session.scalars(
            select(ProviderSecurityMasterObservationRow)
            .where(
                ProviderSecurityMasterObservationRow.provider_security_identity_id
                == provider_security_identity_id,
                ProviderSecurityMasterObservationRow.source_version_id
                == row.latest_source_version_id,
            )
            .order_by(ProviderSecurityMasterObservationRow.observation_id)
        ).all()
        if not current_rows:
            reasons.add("PROVIDER_CURRENT_OBSERVATION_MISSING")
        observations: list[ProviderSecurityMasterObservation] = []
        for stored in current_rows:
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
        if len({observation.symbol for observation in observations}) > 1:
            reasons.add("PROVIDER_CURRENT_SYMBOL_AMBIGUITY")
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

    def _discover_relevant_evidence(
        self,
        session: Session,
        request: IssuerAuthorityEvaluationRequest,
        relations: tuple[AuthorityEvidenceRelation, ...],
    ) -> tuple[_EvidenceSnapshot, ...]:
        """Treat caller memberships as seeds and discover complete current state."""

        rows = session.scalars(
            select(AuthorityEvidenceRow).order_by(AuthorityEvidenceRow.evidence_id)
        ).all()
        snapshots: dict[str, _EvidenceSnapshot] = {}
        facts: dict[str, _MatrixFact] = {}
        for row in rows:
            try:
                snapshot = self._evidence_snapshot(session, row.evidence_id, relations)
            except ValidationError as error:
                raise IssuerAuthorityDecisionEngineError(
                    "STORED_EVIDENCE_CONTRACT_INVALID",
                    "stored authority evidence failed its immutable contract",
                ) from error
            snapshots[row.evidence_id] = snapshot
            facts[row.evidence_id] = self._matrix_fact(snapshot, request)

        missing_seeds = set(request.evidence_ids) - set(snapshots)
        if missing_seeds:
            raise IssuerAuthorityDecisionEngineError(
                "AUTHORITY_EVIDENCE_MISSING",
                "seed immutable authority evidence does not exist",
            )

        candidate_fingerprint = authority_candidate_fingerprint(
            jurisdiction=request.candidate_jurisdiction,
            identifier_kind=request.candidate_identifier_kind,
            identifier_value=request.candidate_identifier_value,
        )
        relevant: set[str] = set(request.evidence_ids)

        for evidence_id, fact in facts.items():
            value = snapshots[evidence_id].evidence.normalized_claim_value
            if request.candidate_jurisdiction.value == "KR":
                direct = (
                    (fact.kind == _KR_CORP_CODE and value == request.candidate_identifier_value)
                    or (
                        fact.kind == _KR_OVERVIEW_BRIDGE
                        and isinstance(value, dict)
                        and value.get("corp_code") == request.candidate_identifier_value
                    )
                    or (
                        fact.kind == _KR_OPENDART_LEGAL_NAME
                        and snapshots[evidence_id].evidence.authority_document_reference
                        == f"company-overview:{request.candidate_identifier_value}"
                    )
                )
            else:
                direct = (
                    fact.kind == _US_SEC_CIK and value == request.candidate_identifier_value
                ) or (
                    fact.kind
                    in {
                        _US_SEC_REGISTRANT_ROLE,
                        _US_SEC_BRIDGE,
                        _US_SEC_LATEST_STATUS,
                    }
                    and isinstance(value, dict)
                    and value.get("registrant_cik") == request.candidate_identifier_value
                )
            if direct:
                relevant.add(evidence_id)

        application_rows = session.scalars(
            select(AuthorityEvidenceApplicationRow).where(
                AuthorityEvidenceApplicationRow.candidate_fingerprint == candidate_fingerprint
            )
        ).all()
        relevant.update(row.evidence_id for row in application_rows)

        if request.candidate_jurisdiction.value == "KR":
            registration_references = {
                value["jurir_no"]
                for evidence_id in tuple(relevant)
                if facts[evidence_id].kind == _KR_OVERVIEW_BRIDGE
                and isinstance(
                    (value := snapshots[evidence_id].evidence.normalized_claim_value),
                    dict,
                )
                and isinstance(value.get("jurir_no"), str)
            }
            for evidence_id, fact in facts.items():
                value = snapshots[evidence_id].evidence.normalized_claim_value
                reference = (
                    value.get("corporate_registration_reference")
                    if fact.kind == _KR_IROS_JURISDICTION and isinstance(value, dict)
                    else value
                    if fact.kind == _KR_IROS_BRIDGE
                    else None
                )
                if reference in registration_references:
                    relevant.add(evidence_id)

            overview_document_ids = {
                snapshots[evidence_id].evidence.authority_source_document_id
                for evidence_id in relevant
                if facts[evidence_id].kind == _KR_OVERVIEW_BRIDGE
            }
            iros_document_ids = {
                snapshots[evidence_id].evidence.authority_source_document_id
                for evidence_id in relevant
                if facts[evidence_id].kind in {_KR_IROS_JURISDICTION, _KR_IROS_BRIDGE}
            }
            for evidence_id, fact in facts.items():
                document_id = snapshots[evidence_id].evidence.authority_source_document_id
                if (
                    fact.kind == _KR_OPENDART_LEGAL_NAME and document_id in overview_document_ids
                ) or (fact.kind == _KR_IROS_LEGAL_NAME and document_id in iros_document_ids):
                    relevant.add(evidence_id)
        else:
            state_keys = {
                (value["formation_state"], value["state_entity_number"])
                for evidence_id in tuple(relevant)
                if facts[evidence_id].kind == _US_SEC_BRIDGE
                and isinstance(
                    (value := snapshots[evidence_id].evidence.normalized_claim_value),
                    dict,
                )
                and isinstance(value.get("formation_state"), str)
                and isinstance(value.get("state_entity_number"), str)
            }
            for evidence_id, fact in facts.items():
                value = snapshots[evidence_id].evidence.normalized_claim_value
                if fact.kind != _US_STATE_JURISDICTION or not isinstance(value, dict):
                    continue
                if (value.get("formation_state"), value.get("state_entity_number")) in state_keys:
                    relevant.add(evidence_id)

            sec_document_ids = {
                snapshots[evidence_id].evidence.authority_source_document_id
                for evidence_id in relevant
                if facts[evidence_id].kind in {_US_SEC_CIK, _US_SEC_REGISTRANT_ROLE, _US_SEC_BRIDGE}
            }
            state_document_ids = {
                snapshots[evidence_id].evidence.authority_source_document_id
                for evidence_id in relevant
                if facts[evidence_id].kind == _US_STATE_JURISDICTION
            }
            for evidence_id, fact in facts.items():
                document_id = snapshots[evidence_id].evidence.authority_source_document_id
                if (fact.kind == _US_SEC_LEGAL_NAME and document_id in sec_document_ids) or (
                    fact.kind == _US_STATE_LEGAL_NAME and document_id in state_document_ids
                ):
                    relevant.add(evidence_id)

        selected = []
        seed_ids = set(request.evidence_ids)
        for evidence_id in sorted(relevant):
            snapshot = snapshots[evidence_id]
            if (
                evidence_id in seed_ids
                or snapshot.relation_head.current
                or snapshot.relation_head.conflict
            ):
                selected.append(snapshot)
        return tuple(selected)

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
        relation_head = self._relation_head(evidence_id, relations)
        component_rows = session.scalars(
            select(AuthorityEvidenceRow)
            .where(AuthorityEvidenceRow.evidence_id.in_(relation_head.component_evidence_ids))
            .order_by(AuthorityEvidenceRow.evidence_id)
        ).all()
        if len(component_rows) != len(relation_head.component_evidence_ids):
            raise IssuerAuthorityDecisionEngineError(
                "AUTHORITY_RELATION_DEPENDENCY_MISSING",
                "authority relation component references missing immutable evidence",
            )
        component_evidence = tuple(
            AuthorityEvidence.model_validate_json(row.payload_json, strict=False)
            for row in component_rows
        )
        component_document_ids = {item.authority_source_document_id for item in component_evidence}
        document_rows = session.scalars(
            select(AuthorityEvidenceRow)
            .where(AuthorityEvidenceRow.authority_source_document_id.in_(component_document_ids))
            .order_by(AuthorityEvidenceRow.evidence_id)
        ).all()
        return _EvidenceSnapshot(
            evidence=evidence,
            policy=policy,
            observations=observations,
            relation_head=relation_head,
            relation_component_evidence=component_evidence,
            relation_component_document_evidence=tuple(
                AuthorityEvidence.model_validate_json(row.payload_json, strict=False)
                for row in document_rows
            ),
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
            component_evidence_ids=tuple(sorted(component)),
            relation_types=tuple(
                sorted(
                    {relation.relation_type for relation in edges},
                    key=lambda item: item.value,
                )
            ),
        )

    def _assess_evidence(
        self,
        snapshot: _EvidenceSnapshot,
        request: IssuerAuthorityEvaluationRequest,
        evaluated_at: datetime,
        provider_observation_ids: tuple[str, ...],
    ) -> _AssessedEvidence:
        fact = self._matrix_fact(snapshot, request)
        freshness = self._freshness(snapshot, evaluated_at, fact.current_check)
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
                provider_observation_ids=provider_observation_ids,
                candidate_jurisdiction=request.candidate_jurisdiction,
                candidate_identifier_kind=request.candidate_identifier_kind,
                candidate_identifier_value=request.candidate_identifier_value,
                claim_target_field=fact.target_field,
                requested_status=status,
                requested_effective_weight=weight,
                reason_codes=_sorted(reasons or {"EVIDENCE_UNUSABLE"}),
                authority_relation_head_hash=snapshot.relation_head.content_hash,
                evaluated_at=evaluated_at,
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
            source == "OPENDART_COMPANY_OVERVIEW"
            and document == "COMPANY_OVERVIEW_JSON_V1"
            and evidence.authority_scope == AuthorityScope.LEGAL_NAME
            and field == "company.corp_name"
        ):
            exact = (
                isinstance(normalized, str)
                and bool(normalized)
                and evidence.authority_document_reference
                == f"company-overview:{request.candidate_identifier_value}"
                and evidence.authority_external_key == evidence.authority_document_reference
            )
            return fact(
                _KR_OPENDART_LEGAL_NAME,
                "issuer.legal_name",
                AuthorityEvidenceApplicationStatus.APPLIED_SUPPORTING,
                AuthorityWeight.SUPPORTING,
                exact,
                True,
                "EXACT_OPENDART_LEGAL_NAME",
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
        if (
            source == "KR_SUPREME_COURT_IROS"
            and document == "VERIFIED_CORPORATE_REGISTRY_EXTRACT_V1"
            and evidence.authority_scope == AuthorityScope.LEGAL_NAME
            and field == "registry.legal_name"
        ):
            exact = (
                isinstance(normalized, str)
                and bool(normalized)
                and evidence.authority_external_key == evidence.authority_document_reference
            )
            return fact(
                _KR_IROS_LEGAL_NAME,
                "issuer.legal_name",
                AuthorityEvidenceApplicationStatus.APPLIED_DECISIVE,
                AuthorityWeight.DECISIVE,
                exact,
                True,
                "EXACT_IROS_LEGAL_NAME",
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
                document == "SEC_ACCEPTED_ISSUER_FILING_JSON_V1"
                and evidence.authority_scope == AuthorityScope.LEGAL_NAME
                and field == "filing.legal_name"
            ):
                exact = (
                    isinstance(normalized, str)
                    and bool(normalized)
                    and _SEC_ACCESSION_PATTERN.fullmatch(evidence.authority_document_reference)
                    is not None
                    and evidence.authority_external_key == evidence.authority_document_reference
                )
                return fact(
                    _US_SEC_LEGAL_NAME,
                    "issuer.legal_name",
                    AuthorityEvidenceApplicationStatus.APPLIED_SUPPORTING,
                    AuthorityWeight.SUPPORTING,
                    exact,
                    False,
                    "EXACT_SEC_ACCEPTED_FILING_LEGAL_NAME",
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
        if (
            source.startswith("US_STATE_REGISTRY_")
            and document == "VERIFIED_DOMESTIC_ENTITY_RECORD_V1"
            and evidence.authority_scope == AuthorityScope.LEGAL_NAME
            and field == "registry.legal_name"
        ):
            state = source.removeprefix("US_STATE_REGISTRY_")
            exact = (
                state == "DE"
                and isinstance(normalized, str)
                and bool(normalized)
                and evidence.authority_external_key == evidence.authority_document_reference
            )
            return fact(
                _US_STATE_LEGAL_NAME,
                "issuer.legal_name",
                AuthorityEvidenceApplicationStatus.APPLIED_DECISIVE,
                AuthorityWeight.DECISIVE,
                exact,
                True,
                "EXACT_US_STATE_LEGAL_NAME",
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

    @staticmethod
    def _co_current_values(
        items: tuple[_AssessedEvidence, ...],
    ) -> tuple[str, ...]:
        values = {
            authority_sha256(item.snapshot.evidence.normalized_claim_value)
            for item in items
            if item.snapshot.relation_head.current
            and not item.snapshot.relation_head.conflict
            and any(
                observation.retrieval_status == AuthorityRetrievalStatus.SUCCEEDED
                for observation in item.snapshot.observations
            )
        }
        return _sorted(values)

    @staticmethod
    def _legal_name_value(item: _AssessedEvidence) -> str | None:
        value = item.snapshot.evidence.normalized_claim_value
        if not isinstance(value, str) or not value:
            return None
        # Authority claim validation already preserves NFC. Reapplying NFC here
        # makes the only engine-side normalization explicit: no case folding,
        # punctuation stripping, suffix removal, whitespace collapsing, or fuzzy match.
        return unicodedata.normalize("NFC", value)

    @classmethod
    def _same_admitted_document_contract(
        cls,
        *,
        policy: AuthoritySourcePolicy,
        name_evidence: AuthorityEvidence,
        evidence: AuthorityEvidence,
    ) -> bool:
        return (
            is_exact_server_owned_production_policy(policy)
            and policy.production_authority_eligible
            and not policy.permanent_fixture_test_taint
            and evidence.authority_source_policy_id == policy.authority_source_policy_id
            and evidence.authority_source_policy_id == name_evidence.authority_source_policy_id
            and evidence.authority_source_identifier == policy.source_namespace
            and evidence.authority_source_identifier == name_evidence.authority_source_identifier
            and evidence.authority_classification == policy.authority_classification
            and evidence.authority_source_document_id == name_evidence.authority_source_document_id
            and evidence.authority_document_reference == name_evidence.authority_document_reference
            and evidence.authority_external_key == name_evidence.authority_external_key
            and evidence.authority_external_key == evidence.authority_document_reference
            and evidence.source_document_kind == name_evidence.source_document_kind
            and evidence.source_document_kind in policy.allowed_document_kinds
            and evidence.parser_contract_version in policy.admitted_parser_contract_versions
            and evidence.origin_adapter_class in policy.admitted_adapter_contract_versions
            and evidence.access_disposition == policy.required_access_disposition
            and evidence.license_disposition == policy.required_license_disposition
            and evidence.origin_data_mode in policy.allowed_origin_data_modes
            and any(
                evidence.authority_source_locator.startswith(root)
                for root in policy.credential_free_locator_roots
            )
            and not evidence.lineage_tainted
            and not evidence.lineage_ancestor_tainted
            and evidence.evidence_kind
            in {AuthorityEvidenceKind.ASSERTION, AuthorityEvidenceKind.CORRECTION}
            and evidence.policy_maximum_issuer_authority_weight
            == policy.maximum_weight_for(evidence.authority_scope, evidence.subject_role)
            and evidence.raw_claim_value == evidence.normalized_claim_value
        )

    @classmethod
    def _exact_registry_name_contract(
        cls,
        *,
        item: _AssessedEvidence,
        evidence: AuthorityEvidence,
        jurisdiction_prefix: str,
    ) -> bool:
        policy = item.snapshot.policy
        current = item.snapshot.evidence
        expected = (
            (
                "KR_SUPREME_COURT_IROS",
                "VERIFIED_CORPORATE_REGISTRY_EXTRACT_V1",
                AuthoritySubjectRole.KOREAN_REGISTERED_LEGAL_ENTITY,
            )
            if jurisdiction_prefix == "KR"
            else (
                current.authority_source_identifier,
                "VERIFIED_DOMESTIC_ENTITY_RECORD_V1",
                AuthoritySubjectRole.US_STATE_REGISTERED_LEGAL_ENTITY,
            )
        )
        source, document_kind, role = expected
        return (
            cls._same_admitted_document_contract(
                policy=policy,
                name_evidence=evidence,
                evidence=evidence,
            )
            and evidence.authority_source_identifier == source
            and (jurisdiction_prefix == "KR" or source.startswith("US_STATE_REGISTRY_"))
            and evidence.source_document_kind == document_kind
            and evidence.authority_scope == AuthorityScope.LEGAL_NAME
            and evidence.subject_role == role
            and evidence.claim_field == "registry.legal_name"
            and evidence.policy_maximum_issuer_authority_weight == AuthorityWeight.DECISIVE
            and isinstance(evidence.normalized_claim_value, str)
            and bool(evidence.normalized_claim_value)
            and evidence.authority_external_key == evidence.authority_document_reference
        )

    @classmethod
    def _registry_name_subject_key(
        cls,
        item: _AssessedEvidence,
        name_evidence: AuthorityEvidence,
        *,
        jurisdiction_prefix: str,
    ) -> tuple[str, ...] | None:
        if not cls._exact_registry_name_contract(
            item=item,
            evidence=name_evidence,
            jurisdiction_prefix=jurisdiction_prefix,
        ):
            return None
        policy = item.snapshot.policy
        document_evidence = tuple(
            evidence
            for evidence in item.snapshot.relation_component_document_evidence
            if evidence.authority_source_document_id == name_evidence.authority_source_document_id
        )
        if jurisdiction_prefix == "KR":
            bridge_candidates = tuple(
                evidence
                for evidence in document_evidence
                if evidence.authority_scope == AuthorityScope.LEGAL_ENTITY_BRIDGE
                and evidence.claim_field == "registry.corporate_registration_reference"
            )
            jurisdiction_candidates = tuple(
                evidence
                for evidence in document_evidence
                if evidence.authority_scope == AuthorityScope.LEGAL_JURISDICTION
                and evidence.claim_field == "registry.legal_entity_status"
            )
            if not bridge_candidates or not jurisdiction_candidates:
                return None
            bridge_values: set[str] = set()
            for evidence in bridge_candidates:
                value = evidence.normalized_claim_value
                if not (
                    cls._same_admitted_document_contract(
                        policy=policy,
                        name_evidence=name_evidence,
                        evidence=evidence,
                    )
                    and evidence.subject_role == AuthoritySubjectRole.KOREAN_REGISTERED_LEGAL_ENTITY
                    and evidence.policy_maximum_issuer_authority_weight == AuthorityWeight.DECISIVE
                    and isinstance(value, str)
                    and _KR_REGISTRATION_PATTERN.fullmatch(value) is not None
                ):
                    return None
                bridge_values.add(value)
            jurisdiction_values: set[str] = set()
            for evidence in jurisdiction_candidates:
                value = _exact_dict(
                    evidence.normalized_claim_value,
                    {
                        "corporate_registration_reference",
                        "entity_kind",
                        "jurisdiction",
                        "verification_reference",
                    },
                )
                if not (
                    cls._same_admitted_document_contract(
                        policy=policy,
                        name_evidence=name_evidence,
                        evidence=evidence,
                    )
                    and evidence.subject_role == AuthoritySubjectRole.KOREAN_REGISTERED_LEGAL_ENTITY
                    and evidence.policy_maximum_issuer_authority_weight == AuthorityWeight.DECISIVE
                    and value is not None
                    and value["jurisdiction"] == "KR"
                    and value["entity_kind"] == "DOMESTIC_CORPORATION"
                    and isinstance(value["corporate_registration_reference"], str)
                    and _KR_REGISTRATION_PATTERN.fullmatch(
                        value["corporate_registration_reference"]
                    )
                    is not None
                    and value["verification_reference"] == evidence.authority_document_reference
                ):
                    return None
                jurisdiction_values.add(value["corporate_registration_reference"])
            if (
                len(bridge_values) != 1
                or len(jurisdiction_values) != 1
                or bridge_values != jurisdiction_values
            ):
                return None
            return ("KR", "KR_SUPREME_COURT_IROS", next(iter(bridge_values)))

        state = name_evidence.authority_source_identifier.removeprefix("US_STATE_REGISTRY_")
        jurisdiction_candidates = tuple(
            evidence
            for evidence in document_evidence
            if evidence.authority_scope == AuthorityScope.LEGAL_JURISDICTION
            and evidence.claim_field == "registry.legal_entity_status"
        )
        if not jurisdiction_candidates:
            return None
        entity_values: set[str] = set()
        for evidence in jurisdiction_candidates:
            value = _exact_dict(
                evidence.normalized_claim_value,
                {
                    "formation_state",
                    "jurisdiction",
                    "record_kind",
                    "state_entity_number",
                    "status",
                    "verification_reference",
                },
            )
            if not (
                cls._same_admitted_document_contract(
                    policy=policy,
                    name_evidence=name_evidence,
                    evidence=evidence,
                )
                and evidence.subject_role == AuthoritySubjectRole.US_STATE_REGISTERED_LEGAL_ENTITY
                and evidence.policy_maximum_issuer_authority_weight == AuthorityWeight.DECISIVE
                and value is not None
                and state == "DE"
                and value["formation_state"] == state
                and value["jurisdiction"] == "US"
                and value["record_kind"] == "DOMESTIC_FORMATION"
                and value["status"] == "ACTIVE"
                and isinstance(value["state_entity_number"], str)
                and _US_STATE_ENTITY_PATTERN.fullmatch(value["state_entity_number"]) is not None
                and value["verification_reference"] == evidence.authority_document_reference
            ):
                return None
            entity_values.add(value["state_entity_number"])
        if len(entity_values) != 1:
            return None
        return (
            "US",
            name_evidence.authority_source_identifier,
            state,
            next(iter(entity_values)),
        )

    @classmethod
    def _supporting_name_subject_key(
        cls,
        item: _AssessedEvidence,
        *,
        jurisdiction_prefix: str,
    ) -> tuple[str, ...] | None:
        evidence = item.snapshot.evidence
        policy = item.snapshot.policy
        document_evidence = tuple(
            candidate
            for candidate in item.snapshot.relation_component_document_evidence
            if candidate.authority_source_document_id == evidence.authority_source_document_id
        )
        if jurisdiction_prefix == "KR":
            if not (
                cls._same_admitted_document_contract(
                    policy=policy,
                    name_evidence=evidence,
                    evidence=evidence,
                )
                and evidence.authority_source_identifier == "OPENDART_COMPANY_OVERVIEW"
                and evidence.source_document_kind == "COMPANY_OVERVIEW_JSON_V1"
                and evidence.authority_scope == AuthorityScope.LEGAL_NAME
                and evidence.subject_role == AuthoritySubjectRole.DART_DISCLOSURE_FILER
                and evidence.claim_field == "company.corp_name"
                and evidence.policy_maximum_issuer_authority_weight == AuthorityWeight.SUPPORTING
            ):
                return None
            bridge_candidates = tuple(
                candidate
                for candidate in document_evidence
                if candidate.authority_scope == AuthorityScope.LEGAL_ENTITY_BRIDGE
                and candidate.claim_field == "company.identity_bridge"
            )
            if not bridge_candidates:
                return None
            subjects: set[str] = set()
            for candidate in bridge_candidates:
                value = _exact_dict(
                    candidate.normalized_claim_value,
                    {"corp_code", "jurir_no", "stock_code"},
                )
                if not (
                    cls._same_admitted_document_contract(
                        policy=policy,
                        name_evidence=evidence,
                        evidence=candidate,
                    )
                    and candidate.subject_role == AuthoritySubjectRole.DART_DISCLOSURE_FILER
                    and candidate.policy_maximum_issuer_authority_weight
                    == AuthorityWeight.SUPPORTING
                    and value is not None
                    and isinstance(value["corp_code"], str)
                    and re.fullmatch(r"[0-9]{8}", value["corp_code"]) is not None
                    and isinstance(value["jurir_no"], str)
                    and _KR_REGISTRATION_PATTERN.fullmatch(value["jurir_no"]) is not None
                    and isinstance(value["stock_code"], str)
                    and _KR_STOCK_CODE_PATTERN.fullmatch(value["stock_code"]) is not None
                    and evidence.authority_document_reference
                    == f"company-overview:{value['corp_code']}"
                ):
                    return None
                subjects.add(value["jurir_no"])
            if len(subjects) != 1:
                return None
            return ("KR", "KR_SUPREME_COURT_IROS", next(iter(subjects)))

        if not (
            cls._same_admitted_document_contract(
                policy=policy,
                name_evidence=evidence,
                evidence=evidence,
            )
            and evidence.authority_source_identifier == "SEC_EDGAR_ACCEPTED_FILING"
            and evidence.source_document_kind == "SEC_ACCEPTED_ISSUER_FILING_JSON_V1"
            and evidence.authority_scope == AuthorityScope.LEGAL_NAME
            and evidence.subject_role == AuthoritySubjectRole.SEC_REGISTRANT
            and evidence.claim_field == "filing.legal_name"
            and evidence.policy_maximum_issuer_authority_weight == AuthorityWeight.SUPPORTING
            and _SEC_ACCESSION_PATTERN.fullmatch(evidence.authority_document_reference) is not None
        ):
            return None
        cik_values: set[str] = set()
        role_values: set[tuple[str, str]] = set()
        bridge_values: set[tuple[str, str, str]] = set()
        for candidate in document_evidence:
            relevant_field = (candidate.authority_scope, candidate.claim_field) in {
                (AuthorityScope.ISSUER_REGULATORY_ID, "filing.registrant_cik"),
                (AuthorityScope.REGISTRANT_ROLE, "filing.registrant_role"),
                (AuthorityScope.LEGAL_ENTITY_BRIDGE, "filing.legal_entity_bridge"),
            }
            if not cls._same_admitted_document_contract(
                policy=policy,
                name_evidence=evidence,
                evidence=candidate,
            ):
                if relevant_field:
                    return None
                continue
            value = candidate.normalized_claim_value
            if (
                candidate.authority_scope == AuthorityScope.ISSUER_REGULATORY_ID
                and candidate.claim_field == "filing.registrant_cik"
            ):
                if not (
                    candidate.subject_role == AuthoritySubjectRole.SEC_REGISTRANT
                    and candidate.policy_maximum_issuer_authority_weight == AuthorityWeight.DECISIVE
                    and isinstance(value, str)
                    and re.fullmatch(r"[0-9]{10}", value) is not None
                ):
                    return None
                cik_values.add(value)
            elif (
                candidate.authority_scope == AuthorityScope.REGISTRANT_ROLE
                and candidate.claim_field == "filing.registrant_role"
            ):
                role = _exact_dict(value, {"accepted_accession", "registrant_cik", "role"})
                if not (
                    candidate.subject_role == AuthoritySubjectRole.SEC_REGISTRANT
                    and candidate.policy_maximum_issuer_authority_weight == AuthorityWeight.DECISIVE
                    and role is not None
                    and role["accepted_accession"] == evidence.authority_document_reference
                    and role["role"] == "ISSUER_REGISTRANT"
                    and isinstance(role["registrant_cik"], str)
                ):
                    return None
                role_values.add((role["accepted_accession"], role["registrant_cik"]))
            elif (
                candidate.authority_scope == AuthorityScope.LEGAL_ENTITY_BRIDGE
                and candidate.claim_field == "filing.legal_entity_bridge"
            ):
                bridge = _exact_dict(
                    value,
                    {
                        "accepted_accession",
                        "formation_state",
                        "provider_symbol",
                        "registrant_cik",
                        "state_entity_number",
                    },
                )
                if not (
                    candidate.subject_role == AuthoritySubjectRole.SEC_REGISTRANT
                    and candidate.policy_maximum_issuer_authority_weight
                    == AuthorityWeight.SUPPORTING
                    and bridge is not None
                    and bridge["accepted_accession"] == evidence.authority_document_reference
                    and isinstance(bridge["formation_state"], str)
                    and re.fullmatch(r"[A-Z]{2}", bridge["formation_state"]) is not None
                    and isinstance(bridge["state_entity_number"], str)
                    and _US_STATE_ENTITY_PATTERN.fullmatch(bridge["state_entity_number"])
                    is not None
                    and isinstance(bridge["registrant_cik"], str)
                    and isinstance(bridge["provider_symbol"], str)
                    and bool(bridge["provider_symbol"])
                ):
                    return None
                bridge_values.add(
                    (
                        bridge["formation_state"],
                        bridge["state_entity_number"],
                        bridge["registrant_cik"],
                    )
                )
        if len(cik_values) != 1 or len(role_values) != 1 or len(bridge_values) != 1:
            return None
        cik = next(iter(cik_values))
        accession, role_cik = next(iter(role_values))
        formation_state, state_entity_number, bridge_cik = next(iter(bridge_values))
        if (
            accession != evidence.authority_document_reference
            or len({cik, role_cik, bridge_cik}) != 1
        ):
            return None
        return (
            "US",
            f"US_STATE_REGISTRY_{formation_state}",
            formation_state,
            state_entity_number,
        )

    @classmethod
    def _official_name_history_names(
        cls,
        decisive_item: _AssessedEvidence,
        *,
        jurisdiction_prefix: str,
    ) -> frozenset[str] | None:
        head = decisive_item.snapshot.relation_head
        current = decisive_item.snapshot.evidence
        current_subject = cls._registry_name_subject_key(
            decisive_item,
            current,
            jurisdiction_prefix=jurisdiction_prefix,
        )
        if current_subject is None:
            return None
        if not head.relation_types:
            return frozenset()
        if (
            head.conflict
            or not head.current
            or AuthorityEvidenceRelationType.REVOKES in head.relation_types
            or not set(head.relation_types).issubset(
                {
                    AuthorityEvidenceRelationType.CORRECTS,
                    AuthorityEvidenceRelationType.SUPERSEDES,
                }
            )
        ):
            return None
        history_names: set[str] = set()
        for member in decisive_item.snapshot.relation_component_evidence:
            subject = cls._registry_name_subject_key(
                decisive_item,
                member,
                jurisdiction_prefix=jurisdiction_prefix,
            )
            if subject is None or subject != current_subject:
                return None
            if not isinstance(member.normalized_claim_value, str):
                return None
            name = unicodedata.normalize("NFC", member.normalized_claim_value)
            if member.evidence_id != current.evidence_id:
                history_names.add(name)
        return frozenset(history_names)

    @classmethod
    def _name_reconciliation(
        cls,
        supporting_items: tuple[_AssessedEvidence, ...],
        decisive_items: tuple[_AssessedEvidence, ...],
        *,
        jurisdiction_prefix: str,
    ) -> _NameReconciliation:
        reasons: set[str] = set()
        if not supporting_items:
            reasons.add(f"MISSING_{jurisdiction_prefix}_SUPPORTING_LEGAL_NAME")
        if not decisive_items:
            reasons.add(f"MISSING_{jurisdiction_prefix}_DECISIVE_LEGAL_NAME")
        if not supporting_items or not decisive_items:
            return _NameReconciliation(
                established=False,
                conflict=False,
                scope_status=AuthorityBundleScopeStatus.MISSING,
                evidence_ids=(),
                reason_codes=_sorted(reasons),
            )

        supporting_current = tuple(item for item in supporting_items if item.structurally_usable)
        decisive_current = tuple(item for item in decisive_items if item.structurally_usable)
        if not supporting_current or not decisive_current:
            reasons.add(f"{jurisdiction_prefix}_LEGAL_NAME_FACT_UNUSABLE")
            return _NameReconciliation(
                established=False,
                conflict=any(
                    item.snapshot.relation_head.conflict
                    for item in supporting_items + decisive_items
                ),
                scope_status=AuthorityBundleScopeStatus.UNUSABLE,
                evidence_ids=(),
                reason_codes=_sorted(reasons),
            )

        supporting_names = tuple(cls._legal_name_value(item) for item in supporting_current)
        decisive_names = {
            value for item in decisive_current if (value := cls._legal_name_value(item)) is not None
        }
        if any(value is None for value in supporting_names) or len(decisive_names) != 1:
            reasons.add(f"{jurisdiction_prefix}_CO_CURRENT_LEGAL_NAME_CONFLICT")
            return _NameReconciliation(
                established=False,
                conflict=True,
                scope_status=AuthorityBundleScopeStatus.CONFLICT,
                evidence_ids=(),
                reason_codes=_sorted(reasons),
            )

        decisive_name = next(iter(decisive_names))
        decisive_subjects = {
            subject
            for item in decisive_current
            if (
                subject := cls._registry_name_subject_key(
                    item,
                    item.snapshot.evidence,
                    jurisdiction_prefix=jurisdiction_prefix,
                )
            )
            is not None
        }
        if len(decisive_subjects) != 1 or len(decisive_subjects) != len(
            {
                cls._registry_name_subject_key(
                    item,
                    item.snapshot.evidence,
                    jurisdiction_prefix=jurisdiction_prefix,
                )
                for item in decisive_current
            }
        ):
            reasons.add(f"{jurisdiction_prefix}_LEGAL_NAME_SUBJECT_BINDING_FAILED")
            return _NameReconciliation(
                established=False,
                conflict=True,
                scope_status=AuthorityBundleScopeStatus.CONFLICT,
                evidence_ids=(),
                reason_codes=_sorted(reasons),
            )
        decisive_subject = next(iter(decisive_subjects))
        if any(
            cls._supporting_name_subject_key(
                item,
                jurisdiction_prefix=jurisdiction_prefix,
            )
            != decisive_subject
            for item in supporting_current
        ):
            reasons.add(f"{jurisdiction_prefix}_LEGAL_NAME_SUBJECT_BINDING_FAILED")
            return _NameReconciliation(
                established=False,
                conflict=True,
                scope_status=AuthorityBundleScopeStatus.CONFLICT,
                evidence_ids=(),
                reason_codes=_sorted(reasons),
            )

        history_results = tuple(
            cls._official_name_history_names(
                item,
                jurisdiction_prefix=jurisdiction_prefix,
            )
            for item in decisive_current
        )
        if any(result is None for result in history_results):
            reasons.add(f"{jurisdiction_prefix}_LEGAL_NAME_HISTORY_SUBJECT_BINDING_FAILED")
            return _NameReconciliation(
                established=False,
                conflict=True,
                scope_status=AuthorityBundleScopeStatus.CONFLICT,
                evidence_ids=(),
                reason_codes=_sorted(reasons),
            )
        official_history_names = frozenset(
            name for result in history_results if result is not None for name in result
        )
        unexplained_names = {
            supporting_name
            for supporting_name in supporting_names
            if supporting_name is not None
            and supporting_name != decisive_name
            and supporting_name not in official_history_names
        }
        if unexplained_names:
            if len(set(supporting_names)) > 1:
                reasons.add(f"{jurisdiction_prefix}_CO_CURRENT_LEGAL_NAME_CONFLICT")
            reasons.add(f"{jurisdiction_prefix}_OFFICIAL_LEGAL_NAME_CONFLICT")
            return _NameReconciliation(
                established=False,
                conflict=True,
                scope_status=AuthorityBundleScopeStatus.CONFLICT,
                evidence_ids=(),
                reason_codes=_sorted(reasons),
            )
        explained_by_history = any(
            supporting_name != decisive_name for supporting_name in supporting_names
        )

        all_current = supporting_current + decisive_current
        if any(
            item.fact.current_check and item.freshness != AuthorityFreshnessResult.CURRENT
            for item in all_current
        ):
            reasons.add(f"{jurisdiction_prefix}_LEGAL_NAME_CURRENT_CHECK_NOT_CURRENT")
            return _NameReconciliation(
                established=False,
                conflict=False,
                scope_status=AuthorityBundleScopeStatus.STALE,
                evidence_ids=(),
                reason_codes=_sorted(reasons),
            )
        if not all(item.positively_applied for item in all_current):
            reasons.add(f"{jurisdiction_prefix}_LEGAL_NAME_APPLICATION_UNUSABLE")
            return _NameReconciliation(
                established=False,
                conflict=False,
                scope_status=AuthorityBundleScopeStatus.UNUSABLE,
                evidence_ids=(),
                reason_codes=_sorted(reasons),
            )

        reasons.add(
            f"{jurisdiction_prefix}_LEGAL_NAME_OFFICIAL_HISTORY_RECONCILED"
            if explained_by_history
            else f"{jurisdiction_prefix}_LEGAL_NAME_EXACT_MATCH"
        )
        return _NameReconciliation(
            established=True,
            conflict=False,
            scope_status=AuthorityBundleScopeStatus.SATISFIED,
            evidence_ids=_sorted(tuple(item.snapshot.evidence.evidence_id for item in all_current)),
            reason_codes=_sorted(reasons),
        )

    @staticmethod
    def _us_bridge_identity_values(
        items: tuple[_AssessedEvidence, ...],
    ) -> tuple[str, ...]:
        values: set[str] = set()
        for item in items:
            if not item.structurally_usable:
                continue
            value = item.snapshot.evidence.normalized_claim_value
            if not isinstance(value, dict):
                continue
            values.add(
                authority_sha256(
                    {
                        "registrant_cik": value.get("registrant_cik"),
                        "formation_state": value.get("formation_state"),
                        "state_entity_number": value.get("state_entity_number"),
                    }
                )
            )
        return _sorted(values)

    @staticmethod
    def _us_provider_symbol_history_reconciled(
        items: tuple[_AssessedEvidence, ...],
        provider_symbols: tuple[str, ...],
    ) -> bool:
        current = tuple(item for item in items if item.structurally_usable)
        symbols = {
            value.get("provider_symbol")
            for item in current
            if isinstance((value := item.snapshot.evidence.normalized_claim_value), dict)
        }
        if len(symbols) <= 1:
            return True
        accepted = tuple((item.snapshot.evidence.authority_accepted_at, item) for item in current)
        if any(accepted_at is None for accepted_at, _ in accepted):
            return False
        latest_at = max(accepted_at for accepted_at, _ in accepted if accepted_at is not None)
        latest_symbols = {
            value.get("provider_symbol")
            for accepted_at, item in accepted
            if accepted_at == latest_at
            and isinstance((value := item.snapshot.evidence.normalized_claim_value), dict)
        }
        return len(latest_symbols) == 1 and bool(latest_symbols.intersection(provider_symbols))

    @staticmethod
    def _us_filing_groups_complete(
        required: dict[str, tuple[_AssessedEvidence, ...]],
    ) -> bool:
        expected = {
            _US_SEC_CIK,
            _US_SEC_REGISTRANT_ROLE,
            _US_SEC_BRIDGE,
            _US_SEC_LEGAL_NAME,
        }
        groups: dict[str, set[str]] = {}
        for kind in expected:
            for item in required[kind]:
                if (
                    not item.fact.exact_shape
                    or item.snapshot.relation_head.conflict
                    or not item.snapshot.observations
                ):
                    continue
                groups.setdefault(item.snapshot.evidence.authority_source_document_id, set()).add(
                    kind
                )
        return bool(groups) and all(kinds == expected for kinds in groups.values())

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
            _KR_OPENDART_LEGAL_NAME: self._by_kind(assessments, _KR_OPENDART_LEGAL_NAME),
            _KR_IROS_JURISDICTION: self._by_kind(assessments, _KR_IROS_JURISDICTION),
            _KR_IROS_BRIDGE: self._by_kind(assessments, _KR_IROS_BRIDGE),
            _KR_IROS_LEGAL_NAME: self._by_kind(assessments, _KR_IROS_LEGAL_NAME),
        }
        reasons: set[str] = set(provider.reason_codes)
        reasons.update(self._assessment_reason_codes(assessments))
        for kind, items in required.items():
            if not items:
                reasons.add(f"MISSING_{kind}")
        structural = all(
            any(item.structurally_usable for item in items) for items in required.values()
        )
        name_reconciliation = self._name_reconciliation(
            required[_KR_OPENDART_LEGAL_NAME],
            required[_KR_IROS_LEGAL_NAME],
            jurisdiction_prefix="KR",
        )
        reasons.update(name_reconciliation.reason_codes)
        name_compatible = name_reconciliation.scope_status in {
            AuthorityBundleScopeStatus.SATISFIED,
            AuthorityBundleScopeStatus.STALE,
        }
        co_current_conflict = (
            any(
                len(self._co_current_values(required[kind])) > 1
                for kind in (
                    _KR_OVERVIEW_BRIDGE,
                    _KR_IROS_JURISDICTION,
                    _KR_IROS_BRIDGE,
                )
            )
            or name_reconciliation.conflict
        )
        recognized_current_unusable = any(
            item.snapshot.relation_head.current
            and bool(item.snapshot.observations)
            and item.freshness == AuthorityFreshnessResult.CURRENT
            and not item.positively_applied
            for items in required.values()
            for item in items
        )
        if co_current_conflict:
            reasons.add("KR_CO_CURRENT_AUTHORITY_CONFLICT")
        if recognized_current_unusable:
            reasons.add("KR_CURRENT_AUTHORITY_FACT_UNUSABLE")
        relation_safety = any(
            item.snapshot.relation_head.reason_codes for item in assessments if item.fact.kind
        )
        matched_evidence: set[str] = set()
        bridge_match = False
        coherent_paths: set[str] = set()
        if structural and provider.safe:
            for overview in required[_KR_OVERVIEW_BRIDGE]:
                for jurisdiction in required[_KR_IROS_JURISDICTION]:
                    for registry_bridge in required[_KR_IROS_BRIDGE]:
                        for overview_name in required[_KR_OPENDART_LEGAL_NAME]:
                            for registry_name in required[_KR_IROS_LEGAL_NAME]:
                                path_items = (
                                    overview,
                                    jurisdiction,
                                    registry_bridge,
                                    overview_name,
                                    registry_name,
                                )
                                if not all(item.structurally_usable for item in path_items):
                                    continue
                                overview_value = overview.snapshot.evidence.normalized_claim_value
                                jurisdiction_value = (
                                    jurisdiction.snapshot.evidence.normalized_claim_value
                                )
                                registration = (
                                    registry_bridge.snapshot.evidence.normalized_claim_value
                                )
                                exact = (
                                    name_compatible
                                    and isinstance(overview_value, dict)
                                    and isinstance(jurisdiction_value, dict)
                                    and overview_value.get("jurir_no") == registration
                                    and jurisdiction_value.get("corporate_registration_reference")
                                    == registration
                                    and jurisdiction.snapshot.evidence.authority_source_document_id
                                    == (
                                        registry_bridge.snapshot.evidence.authority_source_document_id
                                    )
                                    == registry_name.snapshot.evidence.authority_source_document_id
                                    and overview.snapshot.evidence.authority_source_document_id
                                    == overview_name.snapshot.evidence.authority_source_document_id
                                    and overview_value.get("stock_code") in provider.symbols
                                )
                                if exact:
                                    bridge_match = True
                                    coherent_paths.add(
                                        authority_sha256(
                                            {
                                                "registration_reference": registration,
                                                "provider_stock_code": overview_value.get(
                                                    "stock_code"
                                                ),
                                                "registry_document_id": (
                                                    jurisdiction.snapshot.evidence.authority_source_document_id
                                                ),
                                                "legal_name": self._legal_name_value(registry_name),
                                            }
                                        )
                                    )
                                    matched_evidence.update(
                                        item.snapshot.evidence.evidence_id for item in path_items
                                    )
            if not bridge_match:
                reasons.add("KR_EXACT_REGISTRY_PROVIDER_BRIDGE_MISMATCH")
            if len(coherent_paths) > 1:
                co_current_conflict = True
                reasons.add("KR_MULTIPLE_COHERENT_CURRENT_PATHS")
        elif not provider.safe:
            reasons.add("PROVIDER_LINEAGE_NOT_EXACT_BRIDGE_ELIGIBLE")

        core_structural = structural and bridge_match and provider.safe and name_compatible
        current_items = tuple(
            item
            for kind in (
                _KR_OVERVIEW_BRIDGE,
                _KR_OPENDART_LEGAL_NAME,
                _KR_IROS_JURISDICTION,
                _KR_IROS_BRIDGE,
                _KR_IROS_LEGAL_NAME,
            )
            for item in required[kind]
            if item.structurally_usable
        )
        freshness = self._aggregate_freshness(current_items)
        positive = (
            core_structural
            and not co_current_conflict
            and not recognized_current_unusable
            and name_reconciliation.established
            and freshness == AuthorityFreshnessResult.CURRENT
            and all(any(item.positively_applied for item in items) for items in required.values())
        )
        if freshness != AuthorityFreshnessResult.CURRENT:
            reasons.add(f"KR_REQUIRED_CURRENT_CHECK_{freshness.value}")
        if bridge_match:
            reasons.add("KR_EXACT_NON_NAME_PROVIDER_BRIDGE_ESTABLISHED")

        safety = (
            relation_safety
            or co_current_conflict
            or recognized_current_unusable
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
            provider_observation_ids=tuple(
                observation.observation_id for observation in provider.observations
            ),
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
            self._scope_result(
                AuthorityScope.LEGAL_NAME,
                required[_KR_OPENDART_LEGAL_NAME] + required[_KR_IROS_LEGAL_NAME],
                "KR_OFFICIAL_LEGAL_NAME_RECONCILED",
                forced_status=name_reconciliation.scope_status,
                extra_reasons=name_reconciliation.reason_codes,
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
            _US_SEC_LEGAL_NAME: self._by_kind(assessments, _US_SEC_LEGAL_NAME),
            _US_SEC_LATEST_STATUS: self._by_kind(assessments, _US_SEC_LATEST_STATUS),
            _US_STATE_JURISDICTION: self._by_kind(assessments, _US_STATE_JURISDICTION),
            _US_STATE_LEGAL_NAME: self._by_kind(assessments, _US_STATE_LEGAL_NAME),
        }
        reasons: set[str] = set(provider.reason_codes)
        reasons.update(self._assessment_reason_codes(assessments))
        core_kinds = (
            _US_SEC_CIK,
            _US_SEC_REGISTRANT_ROLE,
            _US_SEC_BRIDGE,
            _US_SEC_LEGAL_NAME,
            _US_STATE_JURISDICTION,
            _US_STATE_LEGAL_NAME,
        )
        for kind in core_kinds:
            if not required[kind]:
                reasons.add(f"MISSING_{kind}")
        if not required[_US_SEC_LATEST_STATUS]:
            reasons.add("US_CURRENT_STATUS_CHECK_MISSING")
        structural = all(
            any(item.structurally_usable for item in required[kind]) for kind in core_kinds
        )
        name_reconciliation = self._name_reconciliation(
            required[_US_SEC_LEGAL_NAME],
            required[_US_STATE_LEGAL_NAME],
            jurisdiction_prefix="US",
        )
        reasons.update(name_reconciliation.reason_codes)
        name_compatible = name_reconciliation.scope_status in {
            AuthorityBundleScopeStatus.SATISFIED,
            AuthorityBundleScopeStatus.STALE,
        }
        bridge_identity_conflict = (
            len(self._us_bridge_identity_values(required[_US_SEC_BRIDGE])) > 1
        )
        provider_symbol_history_reconciled = self._us_provider_symbol_history_reconciled(
            required[_US_SEC_BRIDGE], provider.symbols
        )
        filing_groups_complete = self._us_filing_groups_complete(required)
        co_current_conflict = any(
            len(self._co_current_values(required[kind])) > 1
            for kind in (
                _US_SEC_LATEST_STATUS,
                _US_STATE_JURISDICTION,
            )
        ) or any(
            (
                name_reconciliation.conflict,
                bridge_identity_conflict,
                not provider_symbol_history_reconciled,
                not filing_groups_complete,
            )
        )
        if bridge_identity_conflict:
            reasons.add("US_SEC_BRIDGE_IDENTITY_CONFLICT")
        if not provider_symbol_history_reconciled:
            reasons.add("US_PROVIDER_SYMBOL_HISTORY_UNRECONCILED")
        if not filing_groups_complete:
            reasons.add("US_ACCEPTED_FILING_FACT_SET_INCOMPLETE")
        recognized_current_unusable = any(
            item.snapshot.relation_head.current
            and bool(item.snapshot.observations)
            and item.freshness == AuthorityFreshnessResult.CURRENT
            and not item.positively_applied
            for items in required.values()
            for item in items
        )
        if co_current_conflict:
            reasons.add("US_CO_CURRENT_AUTHORITY_CONFLICT")
        if recognized_current_unusable:
            reasons.add("US_CURRENT_AUTHORITY_FACT_UNUSABLE")
        relation_safety = any(
            item.snapshot.relation_head.reason_codes for item in assessments if item.fact.kind
        )
        matched_evidence: set[str] = set()
        bridge_match = False
        coherent_paths: set[str] = set()
        if structural and provider.safe:
            for cik in required[_US_SEC_CIK]:
                for role in required[_US_SEC_REGISTRANT_ROLE]:
                    for bridge_item in required[_US_SEC_BRIDGE]:
                        for state in required[_US_STATE_JURISDICTION]:
                            for sec_name in required[_US_SEC_LEGAL_NAME]:
                                for state_name in required[_US_STATE_LEGAL_NAME]:
                                    path_items = (
                                        cik,
                                        role,
                                        bridge_item,
                                        sec_name,
                                        state,
                                        state_name,
                                    )
                                    if not all(item.structurally_usable for item in path_items):
                                        continue
                                    role_value = role.snapshot.evidence.normalized_claim_value
                                    bridge_value = (
                                        bridge_item.snapshot.evidence.normalized_claim_value
                                    )
                                    state_value = state.snapshot.evidence.normalized_claim_value
                                    same_filing = (
                                        len(
                                            {
                                                cik.snapshot.evidence.authority_source_document_id,
                                                role.snapshot.evidence.authority_source_document_id,
                                                bridge_item.snapshot.evidence.authority_source_document_id,
                                                sec_name.snapshot.evidence.authority_source_document_id,
                                            }
                                        )
                                        == 1
                                    )
                                    same_state_record = (
                                        state.snapshot.evidence.authority_source_document_id
                                        == state_name.snapshot.evidence.authority_source_document_id
                                    )
                                    exact = (
                                        name_compatible
                                        and filing_groups_complete
                                        and provider_symbol_history_reconciled
                                        and same_filing
                                        and same_state_record
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
                                        coherent_paths.add(
                                            authority_sha256(
                                                {
                                                    "registrant_cik": bridge_value.get(
                                                        "registrant_cik"
                                                    ),
                                                    "formation_state": bridge_value.get(
                                                        "formation_state"
                                                    ),
                                                    "state_entity_number": bridge_value.get(
                                                        "state_entity_number"
                                                    ),
                                                    "provider_symbol": bridge_value.get(
                                                        "provider_symbol"
                                                    ),
                                                    "legal_name": self._legal_name_value(
                                                        state_name
                                                    ),
                                                }
                                            )
                                        )
                                        matched_evidence.update(
                                            item.snapshot.evidence.evidence_id
                                            for item in path_items
                                        )
            if not bridge_match:
                reasons.add("US_EXACT_STATE_SEC_PROVIDER_BRIDGE_MISMATCH")
            if len(coherent_paths) > 1:
                co_current_conflict = True
                reasons.add("US_MULTIPLE_COHERENT_CURRENT_PATHS")
        elif not provider.safe:
            reasons.add("PROVIDER_LINEAGE_NOT_EXACT_BRIDGE_ELIGIBLE")

        latest_structural = any(
            item.structurally_usable for item in required[_US_SEC_LATEST_STATUS]
        )
        current_items = tuple(
            item
            for kind in (
                _US_SEC_LATEST_STATUS,
                _US_STATE_JURISDICTION,
                _US_STATE_LEGAL_NAME,
            )
            for item in required[kind]
            if item.structurally_usable
        )
        freshness = (
            self._aggregate_freshness(current_items)
            if latest_structural
            else AuthorityFreshnessResult.UNAVAILABLE
        )
        core_structural = structural and bridge_match and provider.safe and name_compatible
        positive = (
            core_structural
            and not co_current_conflict
            and not recognized_current_unusable
            and name_reconciliation.established
            and filing_groups_complete
            and provider_symbol_history_reconciled
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
            or co_current_conflict
            or recognized_current_unusable
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
            provider_observation_ids=tuple(
                observation.observation_id for observation in provider.observations
            ),
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
            self._scope_result(
                AuthorityScope.LEGAL_NAME,
                required[_US_SEC_LEGAL_NAME] + required[_US_STATE_LEGAL_NAME],
                "US_OFFICIAL_LEGAL_NAME_RECONCILED",
                forced_status=name_reconciliation.scope_status,
                extra_reasons=name_reconciliation.reason_codes,
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
        affected_provider_ids: set[str] = set()
        current_claims: list[AuthorityIdentifierClaim] = []
        conflicting_claim_heads: list[AuthorityIdentifierClaim] = []
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
                conflicting_claim_heads.append(claim)
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
                not in {
                    AuthorityEvidenceApplicationStatus.APPLIED_DECISIVE,
                    AuthorityEvidenceApplicationStatus.APPLIED_SUPPORTING,
                }
                or application.effective_issuer_authority_weight == AuthorityWeight.ZERO
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
        affected_provider_ids.update(
            claim.provider_security_identity_id for claim in same_identifier
        )
        for claim in conflicting_claim_heads:
            if (
                claim.identifier_kind == request.candidate_identifier_kind
                and claim.normalized_identifier_value == request.candidate_identifier_value
            ) or claim.provider_security_identity_id == request.provider_security_identity_id:
                reasons.add("CLAIM_RELATION_HEAD_CONFLICT")
                affected_provider_ids.add(claim.provider_security_identity_id)
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
        affected_provider_ids.update(
            application.provider_security_identity_id
            for application, _ in same_identifier_applications
        )
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
        if same_provider:
            affected_provider_ids.add(request.provider_security_identity_id)
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

        bridge_groups: dict[tuple[str, str, str], list[AuthorityEvidenceApplication]] = {}
        for application, evidence in current_applications:
            if application.authority_scope not in {
                AuthorityScope.LEGAL_ENTITY_BRIDGE,
                AuthorityScope.LEGAL_JURISDICTION,
            }:
                continue
            key = (
                application.authority_scope.value,
                evidence.authority_source_identifier,
                authority_sha256(evidence.normalized_claim_value),
            )
            bridge_groups.setdefault(key, []).append(application)
        for applications in bridge_groups.values():
            candidate_count = len(
                {application.candidate_fingerprint for application in applications}
            )
            provider_count = len(
                {application.provider_security_identity_id for application in applications}
            )
            if candidate_count > 1 or provider_count > 1:
                reasons.add("GLOBAL_BRIDGE_JURISDICTION_COLLISION")
                affected_provider_ids.update(
                    application.provider_security_identity_id for application in applications
                )

        anchor = proposed_issuer_anchor(
            request.candidate_jurisdiction,
            request.candidate_identifier_kind,
            request.candidate_identifier_value,
        )
        expected_issuer_id = proposed_issuer_id(anchor)
        identifier_predicate = (
            IssuerRow.corp_code == request.candidate_identifier_value
            if request.candidate_identifier_kind == AuthorityIdentifierKind.DART_CORP_CODE
            else IssuerRow.cik == request.candidate_identifier_value
        )
        canonical_rows = session.scalars(
            select(IssuerRow)
            .where(or_(IssuerRow.issuer_id == expected_issuer_id, identifier_predicate))
            .order_by(IssuerRow.issuer_id)
        ).all()
        if len(canonical_rows) > 1:
            reasons.add("MULTIPLE_CANONICAL_SUBJECTS_COMPETE")
        for canonical in canonical_rows:
            identifier_matches = (
                canonical.corp_code == request.candidate_identifier_value
                if request.candidate_identifier_kind == AuthorityIdentifierKind.DART_CORP_CODE
                else canonical.cik == request.candidate_identifier_value
            )
            relational_exact = (
                canonical.issuer_id == expected_issuer_id
                and canonical.jurisdiction == request.candidate_jurisdiction.value
                and identifier_matches
            )
            payload_exact = False
            try:
                issuer = Issuer.model_validate_json(canonical.payload_json, strict=False)
                payload_exact = (
                    issuer.issuer_id == canonical.issuer_id
                    and issuer.jurisdiction.value == canonical.jurisdiction
                    and issuer.corp_code == canonical.corp_code
                    and issuer.cik == canonical.cik
                    and issuer.normalized_content_hash == canonical.normalized_content_hash
                    and normalized_hash(issuer) == issuer.normalized_content_hash
                )
            except ValidationError:
                payload_exact = False
            if not relational_exact or not payload_exact:
                reasons.add("EXISTING_CANONICAL_IDENTIFIER_CONFLICT")
                reasons.add("EXISTING_CANONICAL_SUBJECT_INCONSISTENT")

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
        if reasons:
            affected_provider_ids.add(request.provider_security_identity_id)
        return _CollisionScan(
            result=(
                AuthorityCollisionScanResult.CONFLICT
                if reasons
                else AuthorityCollisionScanResult.CLEAR
            ),
            candidate_fingerprints=fingerprints,
            reason_codes=_sorted(reasons or {"GLOBAL_COLLISION_SCAN_CLEAR"}),
            affected_provider_ids=_sorted(affected_provider_ids),
        )

    def _invalidate_impacted_ready_leaves(
        self,
        session: Session,
        *,
        collision: _CollisionScan,
        evaluated_provider_id: str,
        evaluated_at: datetime,
    ) -> None:
        """Append safety successors for every other READY subject in one writer lock."""

        if collision.result != AuthorityCollisionScanResult.CONFLICT:
            return
        for provider_id in collision.affected_provider_ids:
            if provider_id == evaluated_provider_id:
                continue
            predecessor = self._decision_leaf(session, provider_id)
            if (
                predecessor is None
                or predecessor.decision_state != IssuerMachineDecisionState.READY_FOR_MANUAL_REVIEW
            ):
                continue
            old_bundle = SQLiteAuthorityLedgerRepository._required_bundle(
                session,
                predecessor.authority_bundle_id,
            )
            applications: list[AuthorityEvidenceApplication] = []
            provider_observation_ids = set(old_bundle.provider_observation_ids)
            for member in old_bundle.evidence_application_members:
                application = SQLiteAuthorityLedgerRepository._required_application(
                    session,
                    member.evidence_application_id,
                )
                if application.application_content_hash != member.application_content_hash:
                    raise AuthorityLedgerConflict(
                        "impacted READY bundle application content changed"
                    )
                applications.append(application)
                provider_observation_ids.update(application.provider_observation_ids)

            provider_row = session.get(ProviderSecurityIdentityRow, provider_id)
            if provider_row is None:
                raise AuthorityLedgerConflict("impacted READY provider subject no longer exists")
            current_observation_ids = session.scalars(
                select(ProviderSecurityMasterObservationRow.observation_id).where(
                    ProviderSecurityMasterObservationRow.provider_security_identity_id
                    == provider_id,
                    ProviderSecurityMasterObservationRow.source_version_id
                    == provider_row.latest_source_version_id,
                )
            ).all()
            provider_observation_ids.update(current_observation_ids)

            safety_bundle = build_production_authority_bundle(
                provider_security_identity_id=provider_id,
                provider_observation_ids=_sorted(provider_observation_ids),
                candidate_jurisdiction=old_bundle.candidate_jurisdiction,
                candidate_identifier_kind=old_bundle.candidate_identifier_kind,
                candidate_identifier_value=old_bundle.candidate_identifier_value,
                applications=applications,
                required_scope_results=old_bundle.required_scope_results,
                legal_jurisdiction_result=old_bundle.legal_jurisdiction_result,
                collision_scan_result=AuthorityCollisionScanResult.CONFLICT,
                collision_claim_candidate_fingerprints=collision.candidate_fingerprints,
                built_at=evaluated_at,
            )
            safety_bundle, _ = self._insert_or_reuse_bundle(session, safety_bundle)
            latest_revision_check_hash = authority_sha256(
                {
                    "invalidated_predecessor_decision_id": predecessor.issuer_decision_id,
                    "collision_scan_hash": safety_bundle.collision_scan_hash,
                    "collision_reason_codes": collision.reason_codes,
                    "invalidation_rule": "impacted-ready-collision/0.1.0",
                }
            )
            safety_decision = build_issuer_decision(
                bundle=safety_bundle,
                decision_state=IssuerMachineDecisionState.REVIEW_REQUIRED,
                reason_codes=_sorted(
                    set(collision.reason_codes)
                    | {
                        "IMPACTED_READY_INVALIDATED_IN_COLLISION_TRANSACTION",
                        "MACHINE_STATE_REVIEW_REQUIRED",
                    }
                ),
                latest_revision_check_hash=latest_revision_check_hash,
                freshness_policy_version=FRESHNESS_POLICY_VERSION,
                freshness_result=predecessor.freshness_result,
                collision_scan_hash=safety_bundle.collision_scan_hash,
                evaluated_at=evaluated_at,
                supersedes_decision_id=predecessor.issuer_decision_id,
            )
            self._insert_engine_decision(session, safety_decision)
            session.flush()

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
        reloaded_provider = self._provider_snapshot(
            session,
            provider_security_identity_id=request.provider_security_identity_id,
            seed_observation_ids=request.provider_observation_ids,
        )
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
