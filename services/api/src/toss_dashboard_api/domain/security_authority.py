"""C2 machine-owned Security authority evaluation over the immutable 0008 ledger."""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal, cast

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session, sessionmaker

from toss_dashboard_api.contracts import security_authority as c
from toss_dashboard_api.contracts.enums import ProviderIdentityState
from toss_dashboard_api.contracts.provider_security_master import (
    ProviderSecurityMasterObservation,
)
from toss_dashboard_api.contracts.security_authority_decision import (
    KrxIssueBasicFact,
    KrxListingLifecycleFact,
    KrxStandardCodeFact,
    NasdaqPrimaryFact,
    OpenDartCorpCodeFact,
    SecAccepted8AFact,
    SecAccepted25Fact,
    SecPeriodicCoverFact,
    SecurityAuthorityEvaluationRequest,
    SecurityCollisionResult,
)
from toss_dashboard_api.domain.security_authority_registry import (
    ADAPTER_VERSION,
    PARSER_VERSION,
    SOURCE_POLICY_SPECS,
    build_policy,
    exact_policy_for,
    registry_hash,
    scope_proof_ids,
)
from toss_dashboard_api.repositories.security_authority import (
    _C2_ENGINE_CAPABILITY,
    SecurityLedgerConflict,
    SQLiteSecurityAuthorityRepository,
)
from toss_dashboard_api.storage import security_authority_models as sm
from toss_dashboard_api.storage.models import (
    IssuerApprovalEventRow,
    IssuerAuthorityLinkHeadRow,
    IssuerAuthorityLinkRow,
    IssuerDecisionRow,
    IssuerRow,
    ProviderRawManifestRow,
    ProviderSecurityIdentityRow,
    ProviderSecurityMasterObservationRow,
    ProviderSourceVersionRow,
)

RULES_VERSION = c.RULES_VERSION
FRESHNESS_VERSION = "security-authority-freshness/2026-09-30"
PROVIDER_MAX_AGE = timedelta(hours=24)
KRX_MAX_AGE = timedelta(hours=96)
OPENDART_OBSERVATION_MAX_AGE = timedelta(hours=48)
SEC_CONTRADICTION_MAX_AGE = timedelta(hours=24)
NASDAQ_MAX_AGE = timedelta(hours=36)
FUTURE_CLOCK_SKEW = timedelta(minutes=5)

_FACT_MODEL: dict[str, tuple[str, type[Any]]] = {
    "KRX_STANDARD_CODE": ("KRX_STANDARD_CODE_RECORD", KrxStandardCodeFact),
    "KRX_ISSUE_BASIC": ("KRX_ISSUE_BASIC_RECORD", KrxIssueBasicFact),
    "KRX_LISTING_LIFECYCLE": ("KRX_LISTING_LIFECYCLE_RECORD", KrxListingLifecycleFact),
    "OPENDART_CORP_CODE": ("OPENDART_CORP_CODE_RECORD", OpenDartCorpCodeFact),
    "SEC_ACCEPTED_8A": ("SEC_FORM_8A", SecAccepted8AFact),
    "SEC_ACCEPTED_25": ("SEC_FORM_25", SecAccepted25Fact),
    "SEC_PERIODIC_COVER": ("SEC_PERIODIC_COVER", SecPeriodicCoverFact),
    "NASDAQ_PRIMARY": ("NASDAQ_SYMBOL_DIRECTORY", NasdaqPrimaryFact),
}
_COMMON_CLASS = re.compile(r"^(?:class [a-z] )?common (?:stock|shares)(?:, .*)?$", re.I)
_MANDATORY_SCOPES: dict[str, tuple[c.Scope, ...]] = {
    "KR": (
        c.Scope.SECURITY_IDENTIFIER,
        c.Scope.IDENTIFIER_PROVENANCE,
        c.Scope.INSTRUMENT_CLASS,
        c.Scope.LISTING_VENUE,
        c.Scope.LISTING_STATUS,
        c.Scope.LISTING_INTERVAL,
        c.Scope.ISSUER_SECURITY_BRIDGE,
        c.Scope.PROVIDER_SECURITY_BRIDGE,
    ),
    "US": (
        c.Scope.REGISTERED_CLASS,
        c.Scope.IDENTIFIER_PROVENANCE,
        c.Scope.INSTRUMENT_CLASS,
        c.Scope.LISTING_VENUE,
        c.Scope.LISTING_STATUS,
        c.Scope.LISTING_INTERVAL,
        c.Scope.PROVIDER_SECURITY_BRIDGE,
    ),
}


class SecurityAuthorityDecisionEngineError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True)
class SecurityAuthorityDecisionEngineResult:
    provider_id: str
    issuer_id: str | None
    security_id: str | None
    machine_state: c.MachineState
    reason_codes: tuple[str, ...]
    applications: tuple[c.EvidenceApplication, ...]
    identifier_claims: tuple[c.IdentifierClaim, ...]
    class_claims: tuple[c.ClassClaim, ...]
    listing_claims: tuple[c.ListingClaim, ...]
    scope_results: tuple[c.BundleScopeResult, ...]
    bundle: c.Bundle | None
    decision: c.Decision | None
    collision: SecurityCollisionResult
    affected_provider_ids: tuple[str, ...]
    insert_counts: tuple[tuple[str, int], ...]
    idempotent: bool


@dataclass(frozen=True)
class _IssuerSnapshot:
    issuer: IssuerRow
    link: IssuerAuthorityLinkRow
    head: IssuerAuthorityLinkHeadRow
    decision: IssuerDecisionRow
    approval: IssuerApprovalEventRow


@dataclass(frozen=True)
class _ProviderSnapshot:
    identity: ProviderSecurityIdentityRow
    row: ProviderSecurityMasterObservationRow
    observation: ProviderSecurityMasterObservation
    fetched_at: datetime
    content_hash: str


@dataclass(frozen=True)
class _EvidenceSnapshot:
    record: c.Evidence
    observation: c.EvidenceObservation | None
    accepted_observation: c.EvidenceObservation | None
    observation_conflict: bool
    current: bool
    relation_head_hash: str
    fact: Any
    parse_error: bool


@dataclass(frozen=True)
class _Draft:
    jurisdiction: str
    anchor: str
    security_id: str
    profile_hash: str
    applications: tuple[c.EvidenceApplication, ...]
    identifier_claims: tuple[c.IdentifierClaim, ...]
    class_claims: tuple[c.ClassClaim, ...]
    listing_claims: tuple[c.ListingClaim, ...]
    scopes: tuple[c.BundleScopeResult, ...]
    state: c.MachineState
    reasons: tuple[str, ...]
    freshness: str
    collision: SecurityCollisionResult
    evidence_by_id: dict[str, _EvidenceSnapshot]
    policies: tuple[c.SourcePolicy, ...]
    supersedes_decision_id: str | None


def _now() -> datetime:
    return datetime.now(UTC)


def _safe_id(prefix: str, value: Any) -> str:
    return prefix + hashlib.sha256(c.canonical_security_bytes(value)).hexdigest()


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is None or value.utcoffset() is None:
        return None
    return value.astimezone(UTC)


def _parse_time(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return _as_utc(parsed)


def _fresh_clock(value: datetime | None, at: datetime, maximum_age: timedelta) -> bool:
    source_time = _as_utc(value)
    if source_time is None or source_time > at + FUTURE_CLOCK_SKEW:
        return False
    return at - source_time <= maximum_age


def _norm(value: str) -> str:
    return " ".join(value.split()).casefold()


def _periodic_cover_cross_check(
    fact: SecPeriodicCoverFact,
    registrant_cik: str | None,
    class_title: str,
    ticker: str,
    exchange_name: str | None,
) -> tuple[tuple[c.Scope, str], ...] | None:
    """Return current cover conflicts, or None when class/ticker is unrelated."""
    same_class = _norm(fact.class_title) == _norm(class_title)
    same_ticker = fact.ticker == ticker
    if fact.registrant_cik != registrant_cik or not (same_class or same_ticker):
        return None
    conflicts = []
    if not same_class:
        conflicts.append((c.Scope.REGISTERED_CLASS, "SEC_PERIODIC_CLASS_CONTRADICTION"))
    if fact.ticker is not None and not same_ticker:
        conflicts.append((c.Scope.LISTING_VENUE, "SEC_PERIODIC_TICKER_CONTRADICTION"))
    if fact.exchange_name is not None and _norm(fact.exchange_name) != _norm(exchange_name or ""):
        conflicts.append((c.Scope.LISTING_VENUE, "SEC_PERIODIC_VENUE_CONTRADICTION"))
    return tuple(conflicts)


def _sec_family(title: str) -> c.InstrumentFamily:
    if _COMMON_CLASS.fullmatch(_norm(title)):
        return c.InstrumentFamily.COMMON_EQUITY
    return c.InstrumentFamily.UNKNOWN


def _kr_family(security_type: str, stock_kind: str) -> c.InstrumentFamily:
    return (
        c.InstrumentFamily.COMMON_EQUITY
        if (security_type, stock_kind) == ("STOCK", "COMMON_EQUITY")
        else c.InstrumentFamily.UNKNOWN
    )


def _fact_subject(fact: Any) -> str | None:
    if isinstance(fact, KrxStandardCodeFact | KrxIssueBasicFact | KrxListingLifecycleFact):
        return f"KRX_ISSUE:{fact.stock_code}"
    if isinstance(fact, OpenDartCorpCodeFact):
        return f"OPENDART_ISSUER:{fact.corp_code}"
    if isinstance(fact, SecAccepted8AFact):
        return "SEC_8A:" + c.security_hash(
            (
                fact.registrant_cik,
                fact.registered_class_title,
                fact.section_12_basis,
                fact.official_class_discriminator,
                fact.exchange_name,
            )
        )
    if isinstance(fact, SecAccepted25Fact):
        return "SEC_25:" + c.security_hash(
            (fact.registrant_cik, fact.class_description, fact.exchange_name)
        )
    if isinstance(fact, SecPeriodicCoverFact):
        return "SEC_PERIODIC:" + c.security_hash((fact.registrant_cik, fact.class_title))
    if isinstance(fact, NasdaqPrimaryFact):
        return f"NASDAQ_ISSUE:{fact.symbol}"
    return None


def _sec_class_identity(fact: SecAccepted8AFact) -> c.RegisteredClassIdentity:
    return c.RegisteredClassIdentity(
        verified_registrant_cik=fact.registrant_cik,
        accepted_accession=fact.accepted_accession,
        filing_document_digest=fact.filing_document_digest,
        filing_form="8-A",
        registered_class_title=fact.registered_class_title,
        section_12_basis=fact.section_12_basis,
        official_class_discriminator=fact.official_class_discriminator,
        registered_exchange_text=fact.exchange_name,
    )


def _effective_removals(
    sec: SecAccepted8AFact,
    evidence: Sequence[_EvidenceSnapshot],
    at: datetime,
) -> tuple[_EvidenceSnapshot, ...]:
    return tuple(
        item
        for item in evidence
        if item.current
        and not item.parse_error
        and item.accepted_observation is not None
        and item.record.origin_mode == "PRODUCTION_AUTHORITY"
        and not item.record.fixture_taint
        and not item.record.test_taint
        and isinstance(item.fact, SecAccepted25Fact)
        and item.fact.registrant_cik == sec.registrant_cik
        and _norm(item.fact.class_description) == _norm(sec.registered_class_title)
        and _norm(item.fact.exchange_name) == _norm(sec.exchange_name or "")
        and item.fact.effective_date <= at.date()
        and (
            item.fact.accepted_at > sec.accepted_at
            or item.fact.effective_date >= sec.accepted_at.date()
        )
    )


class SecurityAuthorityDecisionEngine:
    """Only ``evaluate`` writes machine decisions; callers supply no authority fields."""

    def __init__(
        self,
        sessions: sessionmaker[Session],
        *,
        clock: Callable[[], datetime] = _now,
    ) -> None:
        self._sessions = sessions
        self._clock = clock
        self._repository = SQLiteSecurityAuthorityRepository(sessions)

    def evaluate(
        self, request: SecurityAuthorityEvaluationRequest
    ) -> SecurityAuthorityDecisionEngineResult:
        session = self._sessions()
        try:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            at = self._evaluation_time()
            result = self.evaluate_locked(session, request, evaluated_at=at)
            session.commit()
            return result
        except SecurityAuthorityDecisionEngineError:
            session.rollback()
            raise
        except SecurityLedgerConflict as error:
            session.rollback()
            raise SecurityAuthorityDecisionEngineError(
                "IMMUTABLE_LEDGER_CONFLICT", str(error)
            ) from None
        except (IntegrityError, OperationalError) as error:
            session.rollback()
            raise SecurityAuthorityDecisionEngineError(
                "TRANSACTION_REVALIDATION_CONFLICT",
                "Security ledger changed or rejected a relational invariant",
            ) from error
        finally:
            session.close()

    def evaluate_locked(
        self,
        session: Session,
        request: SecurityAuthorityEvaluationRequest,
        *,
        evaluated_at: datetime,
    ) -> SecurityAuthorityDecisionEngineResult:
        at = _as_utc(evaluated_at)
        if at is None:
            raise SecurityAuthorityDecisionEngineError("SERVER_CLOCK_INVALID", "UTC clock required")
        provider = self._provider_snapshot(session, request.provider_id)
        if provider is None:
            return self._negative_successor(
                session, request.provider_id, "STALE", "PROVIDER_OBSERVATION_MISSING", at
            )
        issuer = self._issuer_snapshot(session, request.provider_id)
        if issuer is None:
            return self._negative_successor(
                session,
                request.provider_id,
                "REVIEW_REQUIRED",
                "ISSUER_AUTHORITY_NO_LONGER_APPROVED",
                at,
            )
        if issuer.issuer.jurisdiction not in _MANDATORY_SCOPES:
            return self._negative_successor(
                session,
                request.provider_id,
                "UNRESOLVED",
                "UNSUPPORTED_LEGAL_JURISDICTION",
                at,
            )

        evidence, _, relation_conflict = self._evidence_snapshot(session, at)
        policies = tuple(build_policy(spec, recorded_at=at) for spec in SOURCE_POLICY_SPECS)
        draft = self._draft(session, provider, issuer, evidence, policies, at, relation_conflict)
        if draft is None:
            return self._negative_successor(
                session,
                request.provider_id,
                "REVIEW_REQUIRED" if relation_conflict else "UNRESOLVED",
                "EVIDENCE_RELATION_CONFLICT"
                if relation_conflict
                else "SECURITY_ANCHOR_UNAVAILABLE",
                at,
            )
        result = self._persist(session, provider, issuer, draft, at)
        if result.collision.result == "CONFLICT":
            for affected_id in result.affected_provider_ids:
                if affected_id != request.provider_id:
                    self._negative_successor(
                        session,
                        affected_id,
                        "REVIEW_REQUIRED",
                        "GLOBAL_LISTING_COLLISION",
                        at,
                        collision=result.collision,
                    )
        return result

    def _evaluation_time(self) -> datetime:
        try:
            value = self._clock()
        except Exception as error:
            raise SecurityAuthorityDecisionEngineError(
                "SERVER_CLOCK_UNAVAILABLE", "server-owned evaluation clock failed"
            ) from error
        result = _as_utc(value)
        if result is None:
            raise SecurityAuthorityDecisionEngineError("SERVER_CLOCK_INVALID", "UTC clock required")
        return result

    def _negative_successor(
        self,
        session: Session,
        provider_id: str,
        state: c.MachineState,
        reason: str,
        at: datetime,
        *,
        collision: SecurityCollisionResult | None = None,
    ) -> SecurityAuthorityDecisionEngineResult:
        """Record prerequisite loss against captured historical authority."""
        prior = self._current_decision_leaf(session, provider_id)
        if prior is None:
            return self._empty(
                provider_id,
                "UNRESOLVED",
                "APPROVED_ISSUER_HEAD_MISSING"
                if reason == "ISSUER_AUTHORITY_NO_LONGER_APPROVED"
                else reason,
            )
        stored_bundle = session.get(sm.SecurityBundleRow, prior.bundle_id)
        if stored_bundle is None:
            raise SecurityLedgerConflict("SECURITY_DECISION_BUNDLE_MISSING_OR_CHANGED")
        historical = c.Bundle.model_validate_json(stored_bundle.payload_json)
        prior_scopes = session.scalars(
            select(sm.SecurityBundleScopeResultRow).where(
                sm.SecurityBundleScopeResultRow.bundle_id == historical.bundle_id
            )
        ).all()
        scope_values = sorted((row.scope, "MISSING", (reason,), ()) for row in prior_scopes)
        if collision is None:
            current_identity = session.get(ProviderSecurityIdentityRow, provider_id)
            current_head = session.get(IssuerAuthorityLinkHeadRow, provider_id)
            collision = SecurityCollisionResult(
                result="CLEAR",
                reason_codes=(),
                affected_provider_ids=(),
                digest=c.security_hash(
                    {
                        "prerequisite_loss": reason,
                        "provider": None
                        if current_identity is None
                        else (
                            current_identity.identity_state,
                            current_identity.latest_source_version_id,
                        ),
                        "issuer_head": None
                        if current_head is None
                        else (
                            current_head.issuer_authority_link_id,
                            current_head.link_state,
                            current_head.state_hash,
                        ),
                    }
                ),
            )
        # APPROVED and the head hash here describe the captured historical B link.
        # Current approval is explicitly unavailable, so no READY can use this bundle.
        fields = historical.model_dump(mode="python")
        for name in ("content_hash", "audit_hash", "bundle_id", "recorded_at"):
            fields.pop(name)
        fields["membership_hash"] = c.security_hash(
            {"applications": [], "scopes": scope_values, "providers": []}
        )
        fields["collision_scan_hash"] = collision.digest
        bundle = c.seal_security_record(
            c.Bundle, **fields, bundle_id=_safe_id("sec_bundle_", fields), recorded_at=at
        )
        scopes = tuple(
            c.seal_security_record(
                c.BundleScopeResult,
                contract_version="security-authority-bundle-scope-result/0.1.0",
                bundle_id=bundle.bundle_id,
                bundle_hash=bundle.content_hash,
                scope=scope,
                result=result,
                reason_codes=reasons,
                owner_application_ids=ids,
                recorded_at=at,
            )
            for scope, result, reasons, ids in scope_values
        )
        freshness = "STALE" if state == "STALE" else "UNKNOWN"
        idempotent = (
            prior.bundle_hash == bundle.content_hash
            and prior.machine_state == state
            and prior.reason_codes == (reason,)
            and prior.freshness_result == freshness
            and prior.collision_result == collision.result
        )
        decision = (
            prior
            if idempotent
            else c.seal_security_record(
                c.Decision,
                contract_version="security-decision/0.1.0",
                decision_id=_safe_id(
                    "sec_decision_",
                    (provider_id, bundle.content_hash, state, reason, prior.decision_id),
                ),
                provider_id=provider_id,
                issuer_id=historical.issuer_id,
                security_id=historical.security_id,
                bundle_id=bundle.bundle_id,
                bundle_hash=bundle.content_hash,
                issuer_link_id=historical.issuer_link_id,
                issuer_link_hash=historical.issuer_link_hash,
                issuer_link_state="APPROVED",
                issuer_head_state_hash=historical.issuer_head_state_hash,
                machine_state=state,
                reason_codes=(reason,),
                freshness_result=freshness,
                collision_result=collision.result,
                supersedes_decision_id=prior.decision_id,
                evaluated_at=at,
                recorded_at=at,
            )
        )
        counts = (
            {}
            if idempotent
            else self._repository.insert_machine_evaluation(
                session,
                capability=_C2_ENGINE_CAPABILITY,
                policies=(),
                applications=(),
                claims=(),
                bundle=bundle,
                bundle_applications=(),
                scopes=scopes,
                providers=(),
                decision=decision,
            )
        )
        return SecurityAuthorityDecisionEngineResult(
            provider_id=provider_id,
            issuer_id=historical.issuer_id,
            security_id=historical.security_id,
            machine_state=state,
            reason_codes=decision.reason_codes,
            applications=(),
            identifier_claims=(),
            class_claims=(),
            listing_claims=(),
            scope_results=scopes,
            bundle=bundle,
            decision=decision,
            collision=collision,
            affected_provider_ids=collision.affected_provider_ids,
            insert_counts=tuple(sorted((key, value) for key, value in counts.items() if value)),
            idempotent=idempotent,
        )

    @staticmethod
    def _empty(
        provider_id: str,
        state: c.MachineState,
        reason: str,
        *,
        issuer_id: str | None = None,
    ) -> SecurityAuthorityDecisionEngineResult:
        collision = SecurityCollisionResult(
            result="CLEAR",
            reason_codes=(),
            affected_provider_ids=(),
            digest=c.security_hash({"result": "CLEAR", "providers": []}),
        )
        return SecurityAuthorityDecisionEngineResult(
            provider_id=provider_id,
            issuer_id=issuer_id,
            security_id=None,
            machine_state=state,
            reason_codes=(reason,),
            applications=(),
            identifier_claims=(),
            class_claims=(),
            listing_claims=(),
            scope_results=(),
            bundle=None,
            decision=None,
            collision=collision,
            affected_provider_ids=(),
            insert_counts=(),
            idempotent=False,
        )

    @staticmethod
    def _provider_snapshot(session: Session, provider_id: str) -> _ProviderSnapshot | None:
        identity = session.get(ProviderSecurityIdentityRow, provider_id)
        if identity is None or identity.identity_state != ProviderIdentityState.ACTIVE.value:
            return None
        source = session.get(ProviderSourceVersionRow, identity.latest_source_version_id)
        if source is None:
            return None
        raw = session.get(ProviderRawManifestRow, source.raw_response_id)
        fetched_at = None if raw is None else _parse_time(raw.fetched_at)
        rows = session.scalars(
            select(ProviderSecurityMasterObservationRow).where(
                ProviderSecurityMasterObservationRow.provider_security_identity_id == provider_id,
                ProviderSecurityMasterObservationRow.source_version_id
                == identity.latest_source_version_id,
            )
        ).all()
        if len(rows) != 1 or fetched_at is None:
            return None
        row = rows[0]
        try:
            observation = ProviderSecurityMasterObservation.model_validate_json(row.payload_json)
        except ValidationError:
            return None
        if (
            observation.provider_security_identity_id != provider_id
            or not observation.eligible_for_mapping
            or observation.collision_identity_ids
            or observation.staging_state.value != "ELIGIBLE_FOR_MAPPING"
            or observation.identity_state_after is None
            or observation.identity_state_after.value != ProviderIdentityState.ACTIVE.value
        ):
            return None
        return _ProviderSnapshot(
            identity=identity,
            row=row,
            observation=observation,
            fetched_at=fetched_at,
            content_hash=c.security_hash(observation.model_dump(mode="python")),
        )

    @staticmethod
    def _issuer_snapshot(session: Session, provider_id: str) -> _IssuerSnapshot | None:
        head = session.get(IssuerAuthorityLinkHeadRow, provider_id)
        if (
            head is None
            or head.link_state != "APPROVED"
            or head.security_resolution_state != "UNRESOLVED"
        ):
            return None
        link = session.get(IssuerAuthorityLinkRow, head.issuer_authority_link_id)
        if (
            link is None
            or link.provider_security_identity_id != provider_id
            or link.link_state != "APPROVED"
            or link.security_resolution_state != "UNRESOLVED"
        ):
            return None
        issuer = session.get(IssuerRow, link.issuer_id)
        decision = session.get(IssuerDecisionRow, link.issuer_decision_id)
        approval = session.get(IssuerApprovalEventRow, link.approval_event_id)
        if (
            issuer is None
            or decision is None
            or decision.decision_state != "READY_FOR_MANUAL_REVIEW"
            or approval is None
            or approval.event_state != "APPROVED"
            or head.issuer_authority_link_id != link.issuer_authority_link_id
            or head.state_hash == ""
            or link.link_content_hash == ""
        ):
            return None
        return _IssuerSnapshot(
            issuer=issuer, link=link, head=head, decision=decision, approval=approval
        )

    @staticmethod
    def _evidence_snapshot(
        session: Session, at: datetime
    ) -> tuple[dict[str, _EvidenceSnapshot], str, bool]:
        rows = session.scalars(select(sm.SecurityEvidenceRow)).all()
        evidence_by_id = {
            row.evidence_id: c.Evidence.model_validate_json(row.payload_json) for row in rows
        }
        relation_rows = session.scalars(select(sm.SecurityEvidenceRelationRow)).all()
        relations = [
            c.EvidenceRelation.model_validate_json(row.payload_json) for row in relation_rows
        ]
        outgoing: dict[str, list[c.EvidenceRelation]] = defaultdict(list)
        incoming: dict[str, list[c.EvidenceRelation]] = defaultdict(list)
        relation_conflict = False
        for relation in relations:
            prior = evidence_by_id.get(relation.prior_evidence_id)
            successor = evidence_by_id.get(relation.successor_evidence_id)
            if (
                prior is None
                or successor is None
                or prior.content_hash != relation.prior_evidence_hash
                or successor.content_hash != relation.successor_evidence_hash
                or prior.source_namespace != successor.source_namespace
                or prior.document_kind != successor.document_kind
                or prior.subject_role != successor.subject_role
                or prior.exact_subject != successor.exact_subject
                or prior.origin_mode != successor.origin_mode
                or prior.fixture_taint != successor.fixture_taint
                or prior.test_taint != successor.test_taint
            ):
                relation_conflict = True
                continue
            outgoing[relation.prior_evidence_id].append(relation)
            incoming[relation.successor_evidence_id].append(relation)
        if any(len(items) > 1 for items in outgoing.values()) or any(
            len(items) > 1 for items in incoming.values()
        ):
            relation_conflict = True
        color: dict[str, int] = {}

        def visit(evidence_id: str) -> None:
            nonlocal relation_conflict
            state = color.get(evidence_id, 0)
            if state == 1:
                relation_conflict = True
                return
            if state == 2:
                return
            color[evidence_id] = 1
            for relation in outgoing.get(evidence_id, ()):
                visit(relation.successor_evidence_id)
            color[evidence_id] = 2

        for evidence_id in evidence_by_id:
            visit(evidence_id)
        current_ids = set(evidence_by_id).difference(outgoing)
        obs_rows = session.scalars(select(sm.SecurityEvidenceObservationRow)).all()
        observations: dict[str, list[c.EvidenceObservation]] = defaultdict(list)
        for row in obs_rows:
            observations[row.evidence_id].append(
                c.EvidenceObservation.model_validate_json(row.payload_json)
            )
        relation_head_hash = c.security_hash(
            {
                "heads": sorted(
                    (evidence_id, evidence_by_id[evidence_id].content_hash)
                    for evidence_id in current_ids
                ),
                "relations": sorted((item.relation_id, item.content_hash) for item in relations),
                "conflict": relation_conflict,
            }
        )
        snapshots: dict[str, _EvidenceSnapshot] = {}
        for evidence_id, record in evidence_by_id.items():
            candidates = observations.get(evidence_id, [])
            latest: c.EvidenceObservation | None = None
            observation_conflict = False
            if candidates:
                latest_time = max(item.retrieved_at for item in candidates)
                latest_rows = [item for item in candidates if item.retrieved_at == latest_time]
                hashes = {item.content_hash for item in latest_rows}
                observation_conflict = len(hashes) > 1
                latest = min(latest_rows, key=lambda item: item.observation_id)
                if latest.access_result != "SUCCEEDED" or latest.raw_digest != record.raw_digest:
                    observation_conflict = True
            accepted = [
                item
                for item in candidates
                if item.access_result == "SUCCEEDED"
                and item.evidence_hash == record.content_hash
                and item.raw_digest == record.raw_digest
                and item.adapter_version == ADAPTER_VERSION
                and item.parser_version == PARSER_VERSION
            ]
            accepted_observation = max(
                accepted, key=lambda item: (item.retrieved_at, item.observation_id), default=None
            )
            fact: Any | None = None
            parse_error = False
            expected = _FACT_MODEL.get(record.source_namespace)
            if expected is not None:
                expected_document, model = expected
                if record.document_kind != expected_document:
                    parse_error = True
                else:
                    try:
                        fact = model.model_validate_json(record.fact_value)
                    except (ValidationError, ValueError):
                        parse_error = True
                    if fact is not None and record.exact_subject != _fact_subject(fact):
                        parse_error = True
            snapshots[evidence_id] = _EvidenceSnapshot(
                record=record,
                observation=latest,
                accepted_observation=accepted_observation,
                observation_conflict=observation_conflict,
                current=evidence_id in current_ids,
                relation_head_hash=relation_head_hash,
                fact=fact,
                parse_error=parse_error,
            )
        if at.utcoffset() is None:
            relation_conflict = True
        return snapshots, relation_head_hash, relation_conflict

    def _draft(
        self,
        session: Session,
        provider: _ProviderSnapshot,
        issuer: _IssuerSnapshot,
        evidence: dict[str, _EvidenceSnapshot],
        policies: tuple[c.SourcePolicy, ...],
        at: datetime,
        relation_conflict: bool,
    ) -> _Draft | None:
        facts = tuple(
            snapshot
            for snapshot in evidence.values()
            if snapshot.current
            and snapshot.fact is not None
            and not snapshot.parse_error
            and self._production_evidence(snapshot.record)
        )
        if issuer.issuer.jurisdiction == "KR":
            return self._draft_kr(
                session, provider, issuer, evidence, facts, policies, at, relation_conflict
            )
        if issuer.issuer.jurisdiction == "US":
            return self._draft_us(
                session, provider, issuer, evidence, facts, policies, at, relation_conflict
            )
        return None

    @staticmethod
    def _production_evidence(evidence: c.Evidence) -> bool:
        return (
            evidence.origin_mode == "PRODUCTION_AUTHORITY"
            and evidence.fixture_taint == 0
            and evidence.test_taint == 0
        )

    @staticmethod
    def _snapshot_namespace(
        facts: Sequence[_EvidenceSnapshot], namespace: str, kind: type[Any]
    ) -> tuple[_EvidenceSnapshot, ...]:
        return tuple(
            snapshot
            for snapshot in facts
            if snapshot.record.source_namespace == namespace and isinstance(snapshot.fact, kind)
        )

    def _draft_kr(
        self,
        session: Session,
        provider: _ProviderSnapshot,
        issuer: _IssuerSnapshot,
        evidence: dict[str, _EvidenceSnapshot],
        facts: Sequence[_EvidenceSnapshot],
        policies: tuple[c.SourcePolicy, ...],
        at: datetime,
        relation_conflict: bool,
    ) -> _Draft | None:
        standards = self._snapshot_namespace(facts, "KRX_STANDARD_CODE", KrxStandardCodeFact)
        issues = self._snapshot_namespace(facts, "KRX_ISSUE_BASIC", KrxIssueBasicFact)
        darts = self._snapshot_namespace(facts, "OPENDART_CORP_CODE", OpenDartCorpCodeFact)
        dart_rows = tuple(
            item
            for item in darts
            if item.fact.corp_code == issuer.issuer.corp_code
            and self._has_owner(item, c.Scope.ISSUER_SECURITY_BRIDGE)
        )
        dart_dates = [item.fact.modify_date for item in dart_rows]
        latest_dart_date = max(dart_dates) if dart_dates else None
        latest_dart = tuple(item for item in dart_rows if item.fact.modify_date == latest_dart_date)
        dart_semantics = {
            c.security_hash(item.fact.model_dump(mode="python")) for item in latest_dart
        }
        dart_ambiguous = len(dart_semantics) > 1
        dart = min(latest_dart, key=lambda item: item.record.evidence_id) if latest_dart else None

        standard_rows = [
            item for item in standards if self._has_owner(item, c.Scope.SECURITY_IDENTIFIER)
        ]
        candidate_pool: list[tuple[_EvidenceSnapshot, KrxStandardCodeFact]] = []
        for item in standard_rows:
            fact = item.fact
            try:
                c.kr_anchor(issuer.issuer.issuer_id, fact.isin)
            except ValueError:
                continue
            if any(row.fact.stock_code == fact.stock_code for row in issues):
                candidate_pool.append((item, fact))
        dart_candidates = (
            [
                candidate
                for candidate in candidate_pool
                if candidate[1].stock_code == dart.fact.stock_code
            ]
            if dart is not None and not dart_ambiguous
            else []
        )
        if dart_candidates:
            dart_isins = {fact.isin for _, fact in dart_candidates}
            if len(dart_isins) > 1:
                if provider.observation.isin is None:
                    return None
                candidates = [
                    candidate
                    for candidate in dart_candidates
                    if candidate[1].isin == provider.observation.isin
                ]
                if not candidates:
                    return None
            else:
                candidates = dart_candidates
        else:
            if provider.observation.isin is None:
                return None
            candidates = [
                candidate
                for candidate in candidate_pool
                if candidate[1].isin == provider.observation.isin
            ]
        candidate_stock_codes = {fact.stock_code for _, fact in candidates}
        if len(candidate_stock_codes) != 1:
            return None
        candidate_isins = {fact.isin for _, fact in candidates}
        if len(candidate_isins) != 1:
            return None
        isin = next(iter(candidate_isins))
        standard, standard_fact = min(
            candidates,
            key=lambda item: item[0].record.evidence_id,
        )
        standard_semantics = {
            (item.fact.stock_code, item.fact.isin)
            for item in standard_rows
            if item.fact.stock_code == standard_fact.stock_code
        }
        standard_conflict = len(standard_semantics) > 1
        anchor = c.kr_anchor(issuer.issuer.issuer_id, isin)
        security_id = c.security_id_for_anchor(anchor)
        matching_issues = tuple(
            item
            for item in issues
            if item.fact.stock_code == standard_fact.stock_code
            or (item.fact.isin is not None and item.fact.isin == isin)
        )
        issue_semantics = {
            c.security_hash(item.fact.model_dump(mode="python")) for item in matching_issues
        }
        ambiguous_issue = len(issue_semantics) > 1
        issue = (
            min(matching_issues, key=lambda item: item.record.evidence_id)
            if matching_issues
            else None
        )
        listing_rows = self._snapshot_namespace(
            facts, "KRX_LISTING_LIFECYCLE", KrxListingLifecycleFact
        )
        listing_rows = tuple(
            item for item in listing_rows if item.fact.stock_code == standard_fact.stock_code
        )
        matching_listings = tuple(
            item for item in listing_rows if self._has_owner(item, c.Scope.LISTING_STATUS)
        )
        listing_semantics = {
            c.security_hash(item.fact.model_dump(mode="python")) for item in matching_listings
        }
        listing_ambiguous = len(listing_semantics) > 1
        lifecycle = (
            min(matching_listings, key=lambda item: item.record.evidence_id)
            if matching_listings
            else None
        )
        current_issue = cast(KrxIssueBasicFact, issue.fact) if issue is not None else None
        current_listing = (
            cast(KrxListingLifecycleFact, lifecycle.fact) if lifecycle is not None else None
        )
        family = (
            _kr_family(current_issue.security_type, current_issue.stock_kind)
            if current_issue is not None
            else c.InstrumentFamily.UNKNOWN
        )
        app_evidence = tuple(
            item
            for item in facts
            if self._relevant_kr(
                item, issuer.issuer, provider.observation, standard_fact, current_issue
            )
        )
        applications = self._applications(app_evidence, policies, provider, issuer, security_id, at)
        app_map = {(app.evidence_id, app.scope): app for app in applications}
        identifier_claims: list[c.IdentifierClaim] = []
        class_claims: list[c.ClassClaim] = []
        listing_claims: list[c.ListingClaim] = []

        standard_app = app_map.get((standard.record.evidence_id, c.Scope.SECURITY_IDENTIFIER))
        if standard_app is not None and standard_app.status == "ADMITTED":
            identifier_claims.append(
                self._identifier_claim(
                    standard_app,
                    "KRX_ISIN",
                    isin,
                    None if current_issue is None else current_issue.listing_date,
                    at,
                )
            )
        if issue is not None and current_issue is not None:
            issue_app = app_map.get((issue.record.evidence_id, c.Scope.INSTRUMENT_CLASS))
            if issue_app is not None and issue_app.status == "ADMITTED":
                class_claims.append(
                    self._class_claim(
                        issue_app,
                        family,
                        None,
                        current_issue.stock_kind,
                        None,
                        None,
                        at,
                    )
                )
            for scope in (c.Scope.LISTING_VENUE, c.Scope.LISTING_INTERVAL):
                issue_listing_app = app_map.get((issue.record.evidence_id, scope))
                if issue_listing_app is not None and issue_listing_app.status == "ADMITTED":
                    listing_claims.append(
                        self._listing_claim(
                            issue_listing_app,
                            current_issue.market,
                            current_issue.market,
                            current_issue.ticker,
                            "ACTIVE",
                            current_issue.listing_date,
                            None,
                            at,
                        )
                    )
        if lifecycle is not None and current_listing is not None:
            for scope in (c.Scope.LISTING_STATUS, c.Scope.LISTING_INTERVAL, c.Scope.LISTING_VENUE):
                listing_app = app_map.get((lifecycle.record.evidence_id, scope))
                if listing_app is not None and listing_app.status == "ADMITTED":
                    status = self._kr_listing_status(current_listing, at.date())
                    listing_claims.append(
                        self._listing_claim(
                            listing_app,
                            current_listing.market,
                            current_listing.market,
                            current_listing.ticker,
                            status,
                            current_listing.listing_date,
                            None
                            if current_listing.delisting_date is None
                            else current_listing.delisting_date,
                            at,
                        )
                    )

        states: dict[c.Scope, tuple[str, str | None]] = {}
        if standard_conflict:
            self._set_scope(
                states,
                c.Scope.SECURITY_IDENTIFIER,
                "CONFLICT",
                "KRX_STANDARD_CODE_CONTRADICTION",
            )
        else:
            self._set_scope(
                states,
                c.Scope.SECURITY_IDENTIFIER,
                "SATISFIED" if standard is not None else "MISSING",
                None if standard else "KRX_ISIN_MISSING",
            )
        self._set_scope(
            states,
            c.Scope.IDENTIFIER_PROVENANCE,
            "SATISFIED" if standard is not None else "MISSING",
            None if standard else "KRX_IDENTIFIER_PROVENANCE_MISSING",
        )
        if ambiguous_issue:
            self._set_scope(states, c.Scope.INSTRUMENT_CLASS, "CONFLICT", "KRX_ISSUE_AMBIGUOUS")
        elif current_issue is None:
            self._set_scope(states, c.Scope.INSTRUMENT_CLASS, "MISSING", "KRX_ISSUE_BASIC_MISSING")
        elif family != c.InstrumentFamily.COMMON_EQUITY:
            self._set_scope(
                states, c.Scope.INSTRUMENT_CLASS, "UNSUPPORTED", "KRX_SHARE_KIND_UNSUPPORTED"
            )
        else:
            self._set_scope(states, c.Scope.INSTRUMENT_CLASS, "SATISFIED")
        if (
            current_issue is not None
            and current_listing is not None
            and (
                (
                    current_listing.security_type is not None
                    and current_listing.security_type != current_issue.security_type
                )
                or (
                    current_listing.stock_kind is not None
                    and current_listing.stock_kind != current_issue.stock_kind
                )
            )
        ):
            self._set_scope(
                states, c.Scope.INSTRUMENT_CLASS, "CONFLICT", "KRX_CLASS_TYPE_CONTRADICTION"
            )
        if current_issue is None or current_listing is None:
            self._set_scope(states, c.Scope.LISTING_VENUE, "MISSING", "KRX_LISTING_VENUE_MISSING")
        elif current_issue.market != current_listing.market:
            self._set_scope(
                states, c.Scope.LISTING_VENUE, "CONFLICT", "KRX_LISTING_VENUE_CONTRADICTION"
            )
        else:
            self._set_scope(states, c.Scope.LISTING_VENUE, "SATISFIED")
        if listing_ambiguous:
            self._set_scope(states, c.Scope.LISTING_STATUS, "CONFLICT", "KRX_LISTING_CONTRADICTION")
        elif current_listing is None:
            self._set_scope(
                states, c.Scope.LISTING_STATUS, "MISSING", "KRX_LISTING_LIFECYCLE_MISSING"
            )
        elif self._kr_listing_status(current_listing, at.date()) != "ACTIVE":
            self._set_scope(states, c.Scope.LISTING_STATUS, "CONFLICT", "KRX_NOT_CURRENTLY_LISTED")
        else:
            self._set_scope(states, c.Scope.LISTING_STATUS, "SATISFIED")
        if current_listing is None or current_listing.listing_date is None:
            self._set_scope(states, c.Scope.LISTING_INTERVAL, "MISSING", "KRX_LISTING_DATE_MISSING")
        elif current_listing.listing_date > at.date():
            self._set_scope(
                states, c.Scope.LISTING_INTERVAL, "UNSUPPORTED", "KRX_LISTING_NOT_EFFECTIVE"
            )
        else:
            self._set_scope(states, c.Scope.LISTING_INTERVAL, "SATISFIED")
        dart_match = (
            dart is not None
            and not dart_ambiguous
            and issuer.issuer.corp_code == dart.fact.corp_code
            and current_issue is not None
            and dart.fact.stock_code == current_issue.stock_code
        )
        if dart_ambiguous or (dart is not None and not dart_match):
            self._set_scope(
                states, c.Scope.ISSUER_SECURITY_BRIDGE, "CONFLICT", "OPENDART_BRIDGE_MISMATCH"
            )
        elif dart_match:
            self._set_scope(states, c.Scope.ISSUER_SECURITY_BRIDGE, "SATISFIED")
        else:
            self._set_scope(
                states, c.Scope.ISSUER_SECURITY_BRIDGE, "MISSING", "OPENDART_BRIDGE_MISSING"
            )
        provider_match = (
            provider.observation.market.value == "KR"
            and provider.observation.isin == isin
            and current_issue is not None
            and current_issue.isin in (None, isin)
        )
        if provider.observation.isin is not None and not provider_match:
            self._set_scope(
                states, c.Scope.PROVIDER_SECURITY_BRIDGE, "CONFLICT", "PROVIDER_ISIN_MISMATCH"
            )
        elif provider_match:
            self._set_scope(states, c.Scope.PROVIDER_SECURITY_BRIDGE, "SATISFIED")
        else:
            self._set_scope(
                states, c.Scope.PROVIDER_SECURITY_BRIDGE, "MISSING", "PROVIDER_ISIN_MISSING"
            )

        freshness = self._freshness_map(tuple(evidence.values()), provider, at)
        self._apply_scope_freshness(states, applications, freshness)
        reasons = {reason for _, reason in states.values() if reason is not None}
        if standard_conflict or ambiguous_issue or listing_ambiguous or dart_ambiguous:
            reasons.add("AUTHORITY_CONTRADICTION")
        if issuer.issuer.jurisdiction != "KR":
            reasons.add("UNSUPPORTED_LEGAL_JURISDICTION")
            for scope in _MANDATORY_SCOPES["KR"]:
                self._set_scope(states, scope, "UNSUPPORTED", "UNSUPPORTED_LEGAL_JURISDICTION")
        scope_results = self._scope_records(
            _MANDATORY_SCOPES["KR"], states, applications, provider, issuer, security_id, at
        )
        collision = self._collision_scan(
            session,
            provider,
            security_id,
            identifier_claims,
            class_claims,
            listing_claims,
            evidence,
            at,
        )
        reasons.update(collision.reason_codes)
        if relation_conflict:
            reasons.add("EVIDENCE_RELATION_CONFLICT")
        if any(item.parse_error for item in app_evidence):
            reasons.add("EVIDENCE_OBSERVATION_CONFLICT")
        freshness_result = self._freshness_result(states)
        prior = self._current_decision_leaf(
            session, provider.identity.provider_security_identity_id
        )
        state = self._machine_state(states, collision, relation_conflict, prior)
        if state == "REVIEW_REQUIRED":
            reasons.add("SAFETY_REVIEW_REQUIRED")
        profile_hash = c.security_hash(
            {
                "security_id": security_id,
                "anchor": anchor,
                "instrument_family": family.value,
                "identifier": isin,
                "venue": None if current_issue is None else current_issue.market,
                "ticker": None if current_issue is None else current_issue.ticker,
                "listing_date": None if current_listing is None else current_listing.listing_date,
                "class_claims": sorted(item.content_hash for item in class_claims),
                "listing_claims": sorted(item.content_hash for item in listing_claims),
            }
        )
        return _Draft(
            jurisdiction="KR",
            anchor=anchor,
            security_id=security_id,
            profile_hash=profile_hash,
            applications=applications,
            identifier_claims=tuple(identifier_claims),
            class_claims=tuple(class_claims),
            listing_claims=tuple(listing_claims),
            scopes=scope_results,
            state=state,
            reasons=tuple(sorted(reasons)),
            freshness=freshness_result,
            collision=collision,
            evidence_by_id=evidence,
            policies=policies,
            supersedes_decision_id=None if prior is None else prior.decision_id,
        )

    def _draft_us(
        self,
        session: Session,
        provider: _ProviderSnapshot,
        issuer: _IssuerSnapshot,
        evidence: dict[str, _EvidenceSnapshot],
        facts: Sequence[_EvidenceSnapshot],
        policies: tuple[c.SourcePolicy, ...],
        at: datetime,
        relation_conflict: bool,
    ) -> _Draft | None:
        if issuer.issuer.cik is None:
            return None
        sec_rows = self._snapshot_namespace(facts, "SEC_ACCEPTED_8A", SecAccepted8AFact)
        sec_rows = tuple(
            item
            for item in sec_rows
            if item.fact.registrant_cik == issuer.issuer.cik
            and self._has_owner(item, c.Scope.REGISTERED_CLASS)
        )
        if not sec_rows:
            return None
        nasdaq_rows = self._snapshot_namespace(facts, "NASDAQ_PRIMARY", NasdaqPrimaryFact)
        same_symbol = tuple(
            item for item in nasdaq_rows if item.fact.symbol == provider.observation.symbol
        )
        matching_class = tuple(
            item
            for item in sec_rows
            if item.fact.exchange_name is not None
            and _norm(item.fact.exchange_name) == "nasdaq"
            and any(
                _norm(exchange.fact.security_name) == _norm(item.fact.registered_class_title)
                for exchange in same_symbol
            )
        )
        selected_rows = matching_class or sec_rows
        row_identities: dict[str, tuple[_EvidenceSnapshot, c.RegisteredClassIdentity]] = {}
        for item in selected_rows:
            fact = item.fact
            identity = _sec_class_identity(fact)
            row_identities[identity.class_row_id()] = (item, identity)
        if len(row_identities) != 1:
            return None
        sec, class_identity = next(iter(row_identities.values()))
        anchor = c.us_anchor(issuer.issuer.issuer_id, class_identity)
        security_id = c.security_id_for_anchor(anchor)
        sec25_rows = self._snapshot_namespace(facts, "SEC_ACCEPTED_25", SecAccepted25Fact)
        sec25_rows = tuple(
            item
            for item in sec25_rows
            if item.fact.registrant_cik == issuer.issuer.cik
            and item.accepted_observation is not None
            and _norm(item.fact.exchange_name)
            == _norm(class_identity.registered_exchange_text or "")
            and _norm(item.fact.class_description) == _norm(class_identity.registered_class_title)
        )
        effective_form25 = _effective_removals(sec.fact, tuple(evidence.values()), at)
        cover_rows = self._snapshot_namespace(facts, "SEC_PERIODIC_COVER", SecPeriodicCoverFact)
        cover_rows = tuple(
            item
            for item in cover_rows
            if item.fact.registrant_cik == issuer.issuer.cik
            and item.accepted_observation is not None
        )
        relevant_nasdaq = tuple(
            item
            for item in same_symbol
            if any(
                self._has_owner(item, scope)
                for scope in (c.Scope.LISTING_STATUS, c.Scope.LISTING_VENUE)
            )
        )
        nasdaq_signatures = {
            c.security_hash(item.fact.model_dump(mode="python")) for item in relevant_nasdaq
        }
        nasdaq_ambiguous = len(nasdaq_signatures) > 1
        active_rows = tuple(item for item in relevant_nasdaq if item.fact.state == "ACTIVE")
        active_matching = tuple(
            item
            for item in active_rows
            if _norm(item.fact.security_name) == _norm(class_identity.registered_class_title)
        )
        nasdaq = (
            min(active_matching or active_rows, key=lambda item: item.record.evidence_id)
            if (active_matching or active_rows)
            else None
        )
        family = _sec_family(class_identity.registered_class_title)
        app_evidence = tuple(
            item
            for item in facts
            if self._relevant_us(item, issuer.issuer, provider.observation, class_identity)
        )
        applications = self._applications(app_evidence, policies, provider, issuer, security_id, at)
        app_map = {(app.evidence_id, app.scope): app for app in applications}
        identifier_claims: list[c.IdentifierClaim] = []
        class_claims: list[c.ClassClaim] = []
        listing_claims: list[c.ListingClaim] = []
        class_app = app_map.get((sec.record.evidence_id, c.Scope.REGISTERED_CLASS))
        if class_app is not None and class_app.status == "ADMITTED":
            class_claims.append(
                self._class_claim(
                    class_app,
                    family,
                    class_identity.registered_class_title,
                    None,
                    class_identity.class_row_id(),
                    class_identity.section_12_basis,
                    at,
                )
            )
        if nasdaq is not None and not effective_form25:
            for scope in (c.Scope.LISTING_VENUE, c.Scope.LISTING_STATUS, c.Scope.LISTING_INTERVAL):
                listing_app = app_map.get((nasdaq.record.evidence_id, scope))
                if listing_app is not None and listing_app.status == "ADMITTED":
                    listing_claims.append(
                        self._listing_claim(
                            listing_app,
                            "NASDAQ",
                            "US",
                            nasdaq.fact.symbol,
                            "ACTIVE",
                            nasdaq.fact.listing_date,
                            None,
                            at,
                        )
                    )

        states: dict[c.Scope, tuple[str, str | None]] = {}
        class_title_agrees = nasdaq is not None and _norm(nasdaq.fact.security_name) == _norm(
            class_identity.registered_class_title
        )
        self._set_scope(states, c.Scope.REGISTERED_CLASS, "SATISFIED")
        self._set_scope(states, c.Scope.IDENTIFIER_PROVENANCE, "SATISFIED")
        if family != c.InstrumentFamily.COMMON_EQUITY:
            self._set_scope(
                states, c.Scope.INSTRUMENT_CLASS, "UNSUPPORTED", "SEC_CLASS_UNSUPPORTED"
            )
        elif nasdaq is not None and not class_title_agrees:
            self._set_scope(
                states, c.Scope.INSTRUMENT_CLASS, "CONFLICT", "SEC_NASDAQ_CLASS_TITLE_MISMATCH"
            )
        else:
            self._set_scope(states, c.Scope.INSTRUMENT_CLASS, "SATISFIED")
        exact_exchange = (
            class_identity.registered_exchange_text is not None
            and _norm(class_identity.registered_exchange_text) == "nasdaq"
        )
        if nasdaq_ambiguous:
            self._set_scope(states, c.Scope.LISTING_VENUE, "CONFLICT", "NASDAQ_ISSUE_AMBIGUOUS")
        elif nasdaq is None:
            self._set_scope(
                states, c.Scope.LISTING_VENUE, "MISSING", "NASDAQ_PRIMARY_AUTHORITY_MISSING"
            )
        elif not exact_exchange:
            self._set_scope(states, c.Scope.LISTING_VENUE, "CONFLICT", "SEC_EXCHANGE_MISMATCH")
        else:
            self._set_scope(states, c.Scope.LISTING_VENUE, "SATISFIED")
        for cover in cover_rows:
            for scope, reason in (
                _periodic_cover_cross_check(
                    cover.fact,
                    issuer.issuer.cik,
                    class_identity.registered_class_title,
                    provider.observation.symbol,
                    class_identity.registered_exchange_text,
                )
                or ()
            ):
                self._set_scope(states, scope, "CONFLICT", reason)
        # Compare accepted/effective chronology without using retrieval time as filing authority.
        later_nasdaq_event = any(
            item.fact.state in ("ISSUE_DELETION", "ISSUE_SUSPENSION")
            and item.fact.file_creation_time
            > (nasdaq.fact.file_creation_time if nasdaq else datetime.min.replace(tzinfo=UTC))
            for item in relevant_nasdaq
        )
        later_nasdaq_event_reasons = {
            "NASDAQ_ISSUE_DELETION"
            if item.fact.state == "ISSUE_DELETION"
            else "NASDAQ_ISSUE_SUSPENSION"
            for item in relevant_nasdaq
            if item.fact.state in ("ISSUE_DELETION", "ISSUE_SUSPENSION")
            and item.fact.file_creation_time
            > (nasdaq.fact.file_creation_time if nasdaq else datetime.min.replace(tzinfo=UTC))
        }
        if effective_form25 or later_nasdaq_event:
            listing_conflict_reason = (
                "SEC_FORM_25_EFFECTIVE"
                if effective_form25
                else sorted(later_nasdaq_event_reasons)[0]
            )
            self._set_scope(
                states,
                c.Scope.LISTING_STATUS,
                "CONFLICT",
                listing_conflict_reason,
            )
        elif nasdaq is None:
            self._set_scope(
                states, c.Scope.LISTING_STATUS, "MISSING", "NASDAQ_CURRENT_STATUS_MISSING"
            )
        elif nasdaq.fact.test_issue or nasdaq.fact.state != "ACTIVE":
            self._set_scope(
                states, c.Scope.LISTING_STATUS, "CONFLICT", "NASDAQ_NOT_CURRENTLY_LISTED"
            )
        else:
            self._set_scope(states, c.Scope.LISTING_STATUS, "SATISFIED")
        if nasdaq is None:
            self._set_scope(
                states, c.Scope.LISTING_INTERVAL, "MISSING", "NASDAQ_LISTING_INTERVAL_MISSING"
            )
        elif nasdaq.fact.listing_date is not None and nasdaq.fact.listing_date > at.date():
            self._set_scope(
                states, c.Scope.LISTING_INTERVAL, "UNSUPPORTED", "NASDAQ_LISTING_NOT_EFFECTIVE"
            )
        else:
            self._set_scope(states, c.Scope.LISTING_INTERVAL, "SATISFIED")
        provider_matches = (
            provider.observation.market.value == "US"
            and nasdaq is not None
            and provider.observation.symbol == nasdaq.fact.symbol
        )
        if nasdaq is not None and not provider_matches:
            self._set_scope(
                states,
                c.Scope.PROVIDER_SECURITY_BRIDGE,
                "CONFLICT",
                "PROVIDER_TICKER_MARKET_MISMATCH",
            )
        elif provider_matches:
            self._set_scope(states, c.Scope.PROVIDER_SECURITY_BRIDGE, "SATISFIED")
        else:
            self._set_scope(
                states,
                c.Scope.PROVIDER_SECURITY_BRIDGE,
                "MISSING",
                "PROVIDER_TICKER_BRIDGE_MISSING",
            )

        freshness = self._freshness_map(tuple(evidence.values()), provider, at)
        self._apply_scope_freshness(states, applications, freshness)
        reasons = {reason for _, reason in states.values() if reason is not None}
        if sec25_rows and effective_form25:
            reasons.add("SEC_FORM_25_EFFECTIVE")
        reasons.update(later_nasdaq_event_reasons)
        scope_results = self._scope_records(
            _MANDATORY_SCOPES["US"], states, applications, provider, issuer, security_id, at
        )
        collision = self._collision_scan(
            session,
            provider,
            security_id,
            identifier_claims,
            class_claims,
            listing_claims,
            evidence,
            at,
        )
        reasons.update(collision.reason_codes)
        source_conflict = (
            nasdaq_ambiguous or bool(effective_form25) or later_nasdaq_event or relation_conflict
        )
        if relation_conflict:
            reasons.add("EVIDENCE_RELATION_CONFLICT")
        if any(item.parse_error for item in app_evidence):
            reasons.add("EVIDENCE_OBSERVATION_CONFLICT")
        freshness_result = self._freshness_result(states)
        prior = self._current_decision_leaf(
            session, provider.identity.provider_security_identity_id
        )
        state = self._machine_state(states, collision, source_conflict, prior)
        if state == "REVIEW_REQUIRED":
            reasons.add("SAFETY_REVIEW_REQUIRED")
        registered_value = (
            f"{class_identity.verified_registrant_cik}/{class_identity.accepted_accession}/"
            f"{class_identity.class_row_id()}"
        )
        profile_hash = c.security_hash(
            {
                "security_id": security_id,
                "anchor": anchor,
                "instrument_family": family.value,
                "registered_class_title": class_identity.registered_class_title,
                "registered_row_id": class_identity.class_row_id(),
                "identifier": registered_value,
                "venue": "NASDAQ" if nasdaq is not None else None,
                "market": "US",
                "ticker": None if nasdaq is None else nasdaq.fact.symbol,
                "listing_date": None if nasdaq is None else nasdaq.fact.listing_date,
                "class_claims": sorted(item.content_hash for item in class_claims),
                "listing_claims": sorted(item.content_hash for item in listing_claims),
            }
        )
        return _Draft(
            jurisdiction="US",
            anchor=anchor,
            security_id=security_id,
            profile_hash=profile_hash,
            applications=applications,
            identifier_claims=tuple(identifier_claims),
            class_claims=tuple(class_claims),
            listing_claims=tuple(listing_claims),
            scopes=scope_results,
            state=state,
            reasons=tuple(sorted(reasons)),
            freshness=freshness_result,
            collision=collision,
            evidence_by_id=evidence,
            policies=policies,
            supersedes_decision_id=None if prior is None else prior.decision_id,
        )

    def _persist(
        self,
        session: Session,
        provider: _ProviderSnapshot,
        issuer: _IssuerSnapshot,
        draft: _Draft,
        at: datetime,
    ) -> SecurityAuthorityDecisionEngineResult:
        """Revalidate and atomically append one immutable machine-evaluation graph."""
        provider_id = provider.identity.provider_security_identity_id
        current_provider = self._provider_snapshot(session, provider_id)
        if (
            current_provider is None
            or current_provider.row.observation_id != provider.row.observation_id
            or current_provider.content_hash != provider.content_hash
            or current_provider.fetched_at != provider.fetched_at
        ):
            raise SecurityAuthorityDecisionEngineError(
                "PROVIDER_OBSERVATION_CHANGED", "provider observation changed during evaluation"
            )

        current_issuer = self._issuer_snapshot(session, provider_id)
        if (
            current_issuer is None
            or current_issuer.issuer.issuer_id != issuer.issuer.issuer_id
            or current_issuer.link.issuer_authority_link_id != issuer.link.issuer_authority_link_id
            or current_issuer.link.link_content_hash != issuer.link.link_content_hash
            or current_issuer.head.state_hash != issuer.head.state_hash
        ):
            raise SecurityAuthorityDecisionEngineError(
                "ISSUER_AUTHORITY_CHANGED", "approved issuer head changed during evaluation"
            )

        latest_evidence, _, relation_conflict = self._evidence_snapshot(session, at)

        def evidence_signature(items: dict[str, _EvidenceSnapshot]) -> tuple[Any, ...]:
            return tuple(
                (
                    evidence_id,
                    item.record.content_hash,
                    item.current,
                    item.relation_head_hash,
                    None if item.observation is None else item.observation.observation_id,
                    None
                    if item.observation is None
                    else c.security_hash(item.observation.model_dump(mode="python")),
                    item.parse_error,
                )
                for evidence_id, item in sorted(items.items())
            )

        if evidence_signature(latest_evidence) != evidence_signature(
            draft.evidence_by_id
        ) or relation_conflict != ("EVIDENCE_RELATION_CONFLICT" in draft.reasons):
            raise SecurityAuthorityDecisionEngineError(
                "EVIDENCE_AUTHORITY_CHANGED",
                "evidence or correction heads changed during evaluation",
            )

        prior = self._current_decision_leaf(session, provider_id)
        prior_id = None if prior is None else prior.decision_id
        if prior_id != draft.supersedes_decision_id:
            raise SecurityAuthorityDecisionEngineError(
                "SECURITY_DECISION_LEAF_CHANGED", "decision chain leaf changed during evaluation"
            )
        collision = self._collision_scan(
            session,
            current_provider,
            draft.security_id,
            draft.identifier_claims,
            draft.class_claims,
            draft.listing_claims,
            latest_evidence,
            at,
        )
        if collision != draft.collision:
            raise SecurityAuthorityDecisionEngineError(
                "SECURITY_COLLISION_STATE_CHANGED",
                "global collision state changed during evaluation",
            )

        policies: list[c.SourcePolicy] = []
        for policy in draft.policies:
            stored_row = session.get(sm.SecuritySourcePolicyRow, policy.policy_id)
            if stored_row is None:
                policies.append(policy)
                continue
            stored = c.SourcePolicy.model_validate_json(stored_row.payload_json)
            if stored.content_hash != policy.content_hash:
                raise SecurityLedgerConflict("SECURITY_SOURCE_POLICY_REGISTRY_DRIFT")
            policies.append(stored)
        policy_set = tuple(sorted(policies, key=lambda item: item.policy_id))
        policy_set_hash = registry_hash(policy_set)

        app_membership = tuple(
            sorted((item.application_id, item.content_hash) for item in draft.applications)
        )
        scope_values = tuple(
            sorted(
                (
                    item.scope.value,
                    item.result,
                    item.reason_codes,
                    item.owner_application_ids,
                )
                for item in draft.scopes
            )
        )
        provider_membership = (
            (
                provider.observation.observation_id,
                provider.content_hash,
            ),
        )
        membership_hash = c.security_hash(
            {
                "applications": app_membership,
                "scopes": scope_values,
                "providers": provider_membership,
            }
        )
        bundle_seed = {
            "provider_id": provider_id,
            "issuer_id": issuer.issuer.issuer_id,
            "security_id": draft.security_id,
            "issuer_link_id": issuer.link.issuer_authority_link_id,
            "issuer_link_hash": issuer.link.link_content_hash,
            "issuer_head_state_hash": issuer.head.state_hash,
            "proposed_anchor": draft.anchor,
            "profile_hash": draft.profile_hash,
            "membership_hash": membership_hash,
            "source_policy_set_hash": policy_set_hash,
            "rules_version": RULES_VERSION,
            "freshness_version": FRESHNESS_VERSION,
            "collision_scan_hash": collision.digest,
        }
        bundle = c.seal_security_record(
            c.Bundle,
            contract_version="security-authority-bundle/0.1.0",
            bundle_id=_safe_id("sec_bundle_", bundle_seed),
            provider_id=provider_id,
            issuer_id=issuer.issuer.issuer_id,
            security_id=draft.security_id,
            issuer_link_id=issuer.link.issuer_authority_link_id,
            issuer_link_hash=issuer.link.link_content_hash,
            issuer_link_state="APPROVED",
            issuer_head_state_hash=issuer.head.state_hash,
            proposed_anchor=draft.anchor,
            profile_hash=draft.profile_hash,
            rules_version=RULES_VERSION,
            freshness_version=FRESHNESS_VERSION,
            source_policy_set_hash=policy_set_hash,
            collision_scan_hash=collision.digest,
            membership_hash=membership_hash,
            recorded_at=at,
        )
        bundle_applications = tuple(
            c.seal_security_record(
                c.BundleApplication,
                contract_version="security-authority-bundle/0.1.0",
                provider_id=provider_id,
                issuer_id=issuer.issuer.issuer_id,
                security_id=draft.security_id,
                bundle_id=bundle.bundle_id,
                bundle_hash=bundle.content_hash,
                application_id=application.application_id,
                application_hash=application.content_hash,
                member_ordinal=ordinal,
                recorded_at=at,
            )
            for ordinal, application in enumerate(
                sorted(draft.applications, key=lambda item: item.application_id)
            )
        )
        scopes = tuple(
            c.seal_security_record(
                c.BundleScopeResult,
                contract_version="security-authority-bundle-scope-result/0.1.0",
                bundle_id=bundle.bundle_id,
                bundle_hash=bundle.content_hash,
                scope=scope,
                result=result,
                reason_codes=reason_codes,
                owner_application_ids=owner_ids,
                recorded_at=at,
            )
            for scope, result, reason_codes, owner_ids in sorted(
                scope_values, key=lambda item: item[0]
            )
        )
        providers = (
            c.seal_security_record(
                c.BundleProviderObservation,
                contract_version="security-authority-bundle/0.1.0",
                bundle_id=bundle.bundle_id,
                bundle_hash=bundle.content_hash,
                provider_id=provider_id,
                observation_id=provider.observation.observation_id,
                observation_hash=provider.content_hash,
                member_ordinal=0,
                recorded_at=at,
            ),
        )
        decision = c.seal_security_record(
            c.Decision,
            contract_version="security-decision/0.1.0",
            decision_id=_safe_id(
                "sec_decision_",
                (
                    provider_id,
                    bundle.bundle_id,
                    draft.state,
                    draft.reasons,
                    prior_id,
                ),
            ),
            provider_id=provider_id,
            issuer_id=issuer.issuer.issuer_id,
            security_id=draft.security_id,
            bundle_id=bundle.bundle_id,
            bundle_hash=bundle.content_hash,
            issuer_link_id=issuer.link.issuer_authority_link_id,
            issuer_link_hash=issuer.link.link_content_hash,
            issuer_link_state="APPROVED",
            issuer_head_state_hash=issuer.head.state_hash,
            machine_state=draft.state,
            reason_codes=draft.reasons,
            freshness_result=draft.freshness,
            collision_result=collision.result,
            supersedes_decision_id=prior_id,
            evaluated_at=at,
            recorded_at=at,
        )

        if prior is not None and (
            prior.bundle_id == bundle.bundle_id
            and prior.bundle_hash == bundle.content_hash
            and prior.machine_state == decision.machine_state
            and prior.reason_codes == decision.reason_codes
            and prior.freshness_result == decision.freshness_result
            and prior.collision_result == decision.collision_result
        ):
            existing_bundle = session.get(sm.SecurityBundleRow, bundle.bundle_id)
            if (
                existing_bundle is None
                or c.Bundle.model_validate_json(existing_bundle.payload_json).content_hash
                != bundle.content_hash
            ):
                raise SecurityLedgerConflict("SECURITY_DECISION_BUNDLE_MISSING_OR_CHANGED")
            return SecurityAuthorityDecisionEngineResult(
                provider_id=provider_id,
                issuer_id=issuer.issuer.issuer_id,
                security_id=draft.security_id,
                machine_state=prior.machine_state,
                reason_codes=prior.reason_codes,
                applications=draft.applications,
                identifier_claims=draft.identifier_claims,
                class_claims=draft.class_claims,
                listing_claims=draft.listing_claims,
                scope_results=scopes,
                bundle=bundle,
                decision=prior,
                collision=collision,
                affected_provider_ids=collision.affected_provider_ids,
                insert_counts=(),
                idempotent=True,
            )

        counts = self._repository.insert_machine_evaluation(
            session,
            capability=_C2_ENGINE_CAPABILITY,
            policies=policy_set,
            applications=draft.applications,
            claims=(
                *draft.identifier_claims,
                *draft.class_claims,
                *draft.listing_claims,
            ),
            bundle=bundle,
            bundle_applications=bundle_applications,
            scopes=scopes,
            providers=providers,
            decision=decision,
        )
        inserted = tuple(sorted((key, value) for key, value in counts.items() if value))
        return SecurityAuthorityDecisionEngineResult(
            provider_id=provider_id,
            issuer_id=issuer.issuer.issuer_id,
            security_id=draft.security_id,
            machine_state=decision.machine_state,
            reason_codes=decision.reason_codes,
            applications=draft.applications,
            identifier_claims=draft.identifier_claims,
            class_claims=draft.class_claims,
            listing_claims=draft.listing_claims,
            scope_results=scopes,
            bundle=bundle,
            decision=decision,
            collision=collision,
            affected_provider_ids=collision.affected_provider_ids,
            insert_counts=inserted,
            idempotent=not inserted,
        )

    @staticmethod
    def _has_owner(snapshot: _EvidenceSnapshot, scope: c.Scope) -> bool:
        if not SecurityAuthorityDecisionEngine._production_evidence(snapshot.record):
            return False
        spec = exact_policy_for(
            snapshot.record.source_namespace,
            snapshot.record.document_kind,
            scope,
            snapshot.record.subject_role,
        )
        return spec is not None and spec.weight == 3

    @staticmethod
    def _relevant_kr(
        snapshot: _EvidenceSnapshot,
        issuer: IssuerRow,
        provider: ProviderSecurityMasterObservation,
        standard: KrxStandardCodeFact,
        issue: KrxIssueBasicFact | None,
    ) -> bool:
        fact = snapshot.fact
        if isinstance(fact, KrxStandardCodeFact):
            return fact.stock_code == standard.stock_code or fact.isin == standard.isin
        if isinstance(fact, KrxIssueBasicFact):
            return fact.stock_code == standard.stock_code or fact.isin == standard.isin
        if isinstance(fact, KrxListingLifecycleFact):
            return fact.stock_code == standard.stock_code
        if isinstance(fact, OpenDartCorpCodeFact):
            return fact.corp_code == issuer.corp_code or (
                issue is not None and fact.stock_code == issue.stock_code
            )
        return False

    @staticmethod
    def _relevant_us(
        snapshot: _EvidenceSnapshot,
        issuer: IssuerRow,
        provider: ProviderSecurityMasterObservation,
        identity: c.RegisteredClassIdentity,
    ) -> bool:
        fact = snapshot.fact
        if isinstance(fact, SecAccepted8AFact):
            return (
                fact.registrant_cik == issuer.cik
                and fact.accepted_accession == identity.accepted_accession
            )
        if isinstance(fact, SecAccepted25Fact):
            return fact.registrant_cik == issuer.cik
        if isinstance(fact, SecPeriodicCoverFact):
            return (
                _periodic_cover_cross_check(
                    fact,
                    issuer.cik,
                    identity.registered_class_title,
                    provider.symbol,
                    identity.registered_exchange_text,
                )
                is not None
            )
        if isinstance(fact, NasdaqPrimaryFact):
            return fact.symbol == provider.symbol
        return False

    @staticmethod
    def _applications(
        snapshots: Sequence[_EvidenceSnapshot],
        policies: Sequence[c.SourcePolicy],
        provider: _ProviderSnapshot,
        issuer: _IssuerSnapshot,
        security_id: str,
        at: datetime,
    ) -> tuple[c.EvidenceApplication, ...]:
        policy_by_key = {
            (item.source_namespace, item.document_kind, item.scope, item.subject_role): item
            for item in policies
        }
        applications: list[c.EvidenceApplication] = []
        claim_targets = {
            c.Scope.SECURITY_IDENTIFIER: "security.identifier",
            c.Scope.IDENTIFIER_PROVENANCE: "security.identifier.provenance",
            c.Scope.INSTRUMENT_CLASS: "security.instrument_class",
            c.Scope.REGISTERED_CLASS: "security.registered_class",
            c.Scope.LISTING_VENUE: "listing.venue",
            c.Scope.LISTING_STATUS: "listing.status",
            c.Scope.LISTING_INTERVAL: "listing.interval",
            c.Scope.ISSUER_SECURITY_BRIDGE: "issuer.security.bridge",
            c.Scope.PROVIDER_SECURITY_BRIDGE: "provider.security.bridge",
        }
        for snapshot in snapshots:
            record = snapshot.record
            expected = _FACT_MODEL.get(record.source_namespace)
            if (
                expected is None
                or record.document_kind != expected[0]
                or snapshot.fact is None
                or snapshot.parse_error
                or snapshot.observation_conflict
                or snapshot.observation is None
                or snapshot.observation.access_result != "SUCCEEDED"
                or snapshot.observation.evidence_hash != record.content_hash
                or snapshot.observation.raw_digest != record.raw_digest
                or snapshot.observation.adapter_version != ADAPTER_VERSION
                or snapshot.observation.parser_version != PARSER_VERSION
            ):
                continue
            for scope in c.Scope:
                spec = exact_policy_for(
                    record.source_namespace, record.document_kind, scope, record.subject_role
                )
                if spec is None:
                    continue
                policy = policy_by_key.get(
                    (record.source_namespace, record.document_kind, scope, record.subject_role)
                )
                if policy is None:
                    continue
                application_id = _safe_id(
                    "sec_app_",
                    (
                        record.evidence_id,
                        policy.policy_id,
                        provider.identity.provider_security_identity_id,
                        issuer.issuer.issuer_id,
                        security_id,
                        snapshot.relation_head_hash,
                    ),
                )
                applications.append(
                    c.seal_security_record(
                        c.EvidenceApplication,
                        contract_version="security-authority-evidence-application/0.1.0",
                        application_id=application_id,
                        provider_id=provider.identity.provider_security_identity_id,
                        issuer_id=issuer.issuer.issuer_id,
                        security_id=security_id,
                        evidence_id=record.evidence_id,
                        evidence_hash=record.content_hash,
                        policy_id=policy.policy_id,
                        policy_hash=policy.content_hash,
                        source_namespace=record.source_namespace,
                        document_kind=record.document_kind,
                        scope=scope,
                        subject_role=record.subject_role,
                        requested_weight=spec.weight,
                        claim_target=claim_targets[scope],
                        relation_head_hash=snapshot.relation_head_hash,
                        status="ADMITTED" if spec.weight == 3 else "SUPPORT_ONLY",
                        fixture_taint=record.fixture_taint,
                        test_taint=record.test_taint,
                        recorded_at=at,
                    )
                )
        return tuple(sorted(applications, key=lambda item: item.application_id))

    @staticmethod
    def _identifier_claim(
        application: c.EvidenceApplication,
        identifier_kind: str,
        identifier_value: str,
        valid_from: date | None,
        at: datetime,
    ) -> c.IdentifierClaim:
        return c.seal_security_record(
            c.IdentifierClaim,
            contract_version="security-identifier-claim/0.1.0",
            claim_id=_safe_id(
                "sec_idclaim_",
                (application.application_id, identifier_kind, identifier_value, valid_from),
            ),
            provider_id=application.provider_id,
            issuer_id=application.issuer_id,
            security_id=application.security_id,
            application_id=application.application_id,
            application_hash=application.content_hash,
            application_status="ADMITTED",
            scope="SECURITY_IDENTIFIER",
            identifier_kind=identifier_kind,
            identifier_value=identifier_value,
            valid_from=valid_from,
            valid_to=None,
            interval_missing_reason="NOT_SUPPLIED_BY_AUTHORITY",
            recorded_at=at,
        )

    @staticmethod
    def _class_claim(
        application: c.EvidenceApplication,
        family: c.InstrumentFamily,
        title: str | None,
        share_kind: str | None,
        row_id: str | None,
        section_12_basis: str | None,
        at: datetime,
    ) -> c.ClassClaim:
        return c.seal_security_record(
            c.ClassClaim,
            contract_version="security-class-claim/0.1.0",
            claim_id=_safe_id(
                "sec_classclaim_",
                (
                    application.application_id,
                    family.value,
                    title,
                    share_kind,
                    row_id,
                    section_12_basis,
                ),
            ),
            provider_id=application.provider_id,
            issuer_id=application.issuer_id,
            security_id=application.security_id,
            application_id=application.application_id,
            application_hash=application.content_hash,
            application_status="ADMITTED",
            scope=application.scope.value,
            instrument_family=family,
            registered_class_title=title,
            authority_share_kind=share_kind,
            registered_row_id=row_id,
            section_12_basis=section_12_basis,
            missing_reason="NOT_SUPPLIED_BY_AUTHORITY"
            if family == c.InstrumentFamily.UNKNOWN
            else None,
            recorded_at=at,
        )

    @staticmethod
    def _listing_claim(
        application: c.EvidenceApplication,
        venue: str,
        market: str,
        ticker: str,
        status: str,
        valid_from: date | None,
        valid_to: date | None,
        at: datetime,
    ) -> c.ListingClaim:
        return c.seal_security_record(
            c.ListingClaim,
            contract_version="security-listing-claim/0.1.0",
            claim_id=_safe_id(
                "sec_listingclaim_",
                (application.application_id, venue, market, ticker, status, valid_from, valid_to),
            ),
            provider_id=application.provider_id,
            issuer_id=application.issuer_id,
            security_id=application.security_id,
            application_id=application.application_id,
            application_hash=application.content_hash,
            application_status="ADMITTED",
            scope=application.scope.value,
            venue=venue,
            market=market,
            ticker=ticker,
            listing_status=status,
            valid_from=valid_from,
            valid_to=valid_to,
            interval_missing_reason=(
                "NOT_SUPPLIED_BY_AUTHORITY" if valid_from is None or valid_to is None else None
            ),
            recorded_at=at,
        )

    @staticmethod
    def _kr_listing_status(fact: KrxListingLifecycleFact, today: date) -> str:
        if fact.status == "DELISTED" or (
            fact.delisting_date is not None and fact.delisting_date <= today
        ):
            return "DELISTED"
        if fact.status == "SUSPENDED":
            return "SUSPENDED"
        return fact.status

    @staticmethod
    def _set_scope(
        states: dict[c.Scope, tuple[str, str | None]],
        scope: c.Scope,
        result: str,
        reason: str | None = None,
    ) -> None:
        priority = {"MISSING": 0, "UNSUPPORTED": 1, "STALE": 2, "CONFLICT": 3, "SATISFIED": -1}
        current = states.get(scope)
        if current is None or priority[result] > priority[current[0]]:
            states[scope] = (result, reason)

    @staticmethod
    def _scope_records(
        mandatory: Sequence[c.Scope],
        states: dict[c.Scope, tuple[str, str | None]],
        applications: Sequence[c.EvidenceApplication],
        provider: _ProviderSnapshot,
        issuer: _IssuerSnapshot,
        security_id: str,
        at: datetime,
    ) -> tuple[c.BundleScopeResult, ...]:
        app_ids_by_scope: dict[c.Scope, tuple[str, ...]] = {}
        for scope in mandatory:
            app_ids_by_scope[scope] = (
                scope_proof_ids(issuer.issuer.jurisdiction, scope, tuple(applications)) or ()
            )
        return tuple(
            c.seal_security_record(
                c.BundleScopeResult,
                contract_version="security-authority-bundle-scope-result/0.1.0",
                bundle_id="sec_bundle_pending",
                bundle_hash=c.security_hash("pending-bundle-membership"),
                scope=scope,
                result=states.get(scope, ("MISSING", None))[0],
                reason_codes=()
                if states.get(scope, ("MISSING", None))[1] is None
                else (states[scope][1],),
                owner_application_ids=app_ids_by_scope[scope],
                recorded_at=at,
            )
            for scope in sorted(mandatory, key=lambda item: item.value)
        )

    @staticmethod
    def _freshness_map(
        snapshots: Sequence[_EvidenceSnapshot], provider: _ProviderSnapshot, at: datetime
    ) -> dict[str, bool]:
        krx_latest: dict[tuple[str, str], datetime] = {}
        for snapshot in snapshots:
            obs = snapshot.observation
            if (
                obs is not None
                and snapshot.current
                and not snapshot.parse_error
                and SecurityAuthorityDecisionEngine._production_evidence(snapshot.record)
                and snapshot.record.source_namespace in ("KRX_STANDARD_CODE", "KRX_ISSUE_BASIC")
                and obs.source_as_of is not None
            ):
                key = (snapshot.record.source_namespace, snapshot.record.exact_subject)
                krx_latest[key] = max(krx_latest.get(key, obs.source_as_of), obs.source_as_of)
        result: dict[str, bool] = {}
        for snapshot in snapshots:
            record = snapshot.record
            obs = snapshot.observation
            fresh = False
            if (
                obs is not None
                and obs.access_result == "SUCCEEDED"
                and not snapshot.parse_error
                and not snapshot.observation_conflict
            ):
                namespace = record.source_namespace
                if namespace in ("KRX_STANDARD_CODE", "KRX_ISSUE_BASIC"):
                    fresh = (
                        obs.source_as_of is not None
                        and obs.source_as_of == krx_latest.get((namespace, record.exact_subject))
                        and _fresh_clock(obs.source_as_of, at, KRX_MAX_AGE)
                    )
                elif namespace == "KRX_LISTING_LIFECYCLE":
                    fresh = _fresh_clock(obs.retrieved_at, at, KRX_MAX_AGE)
                elif namespace == "OPENDART_CORP_CODE":
                    fresh = _fresh_clock(obs.retrieved_at, at, OPENDART_OBSERVATION_MAX_AGE)
                elif namespace == "SEC_ACCEPTED_8A":
                    fresh = _fresh_clock(obs.source_as_of, at, SEC_CONTRADICTION_MAX_AGE)
                elif namespace in ("SEC_ACCEPTED_25", "SEC_PERIODIC_COVER"):
                    fresh = True
                elif namespace == "NASDAQ_PRIMARY" and isinstance(snapshot.fact, NasdaqPrimaryFact):
                    fresh = _fresh_clock(snapshot.fact.file_creation_time, at, NASDAQ_MAX_AGE)
            result[record.evidence_id] = fresh
        result["__provider__"] = _fresh_clock(provider.fetched_at, at, PROVIDER_MAX_AGE)
        return result

    @staticmethod
    def _apply_scope_freshness(
        states: dict[c.Scope, tuple[str, str | None]],
        applications: Sequence[c.EvidenceApplication],
        freshness: dict[str, bool],
    ) -> None:
        for scope, (current, _) in tuple(states.items()):
            jurisdiction = "KR" if c.Scope.SECURITY_IDENTIFIER in states else "US"
            proof_ids = scope_proof_ids(jurisdiction, scope, tuple(applications))
            if proof_ids is None:
                if current == "SATISFIED":
                    states[scope] = ("MISSING", "REQUIRED_APPLICATION_PROOF_MISSING")
                continue
            relevant = [app for app in applications if app.application_id in proof_ids]
            stale = any(not freshness.get(app.evidence_id, False) for app in relevant)
            if scope == c.Scope.PROVIDER_SECURITY_BRIDGE:
                stale = stale or not freshness.get("__provider__", False)
            if stale and current != "CONFLICT":
                states[scope] = ("STALE", "REQUIRED_SOURCE_FRESHNESS_NOT_ESTABLISHED")

    @staticmethod
    def _freshness_result(states: dict[c.Scope, tuple[str, str | None]]) -> str:
        values = tuple(result for result, _ in states.values())
        if "STALE" in values:
            return "STALE"
        if values and all(value == "SATISFIED" for value in values):
            return "FRESH"
        return "UNKNOWN"

    @staticmethod
    def _current_decision_leaf(session: Session, provider_id: str) -> c.Decision | None:
        rows = session.scalars(
            select(sm.SecurityDecisionRow).where(sm.SecurityDecisionRow.provider_id == provider_id)
        ).all()
        if not rows:
            return None
        superseded = {row.supersedes_decision_id for row in rows if row.supersedes_decision_id}
        leaves = [row for row in rows if row.decision_id not in superseded]
        if len(leaves) != 1:
            raise SecurityAuthorityDecisionEngineError(
                "SECURITY_DECISION_CHAIN_FORK", "provider decision chain must have one leaf"
            )
        return c.Decision.model_validate_json(leaves[0].payload_json)

    @staticmethod
    def _machine_state(
        states: dict[c.Scope, tuple[str, str | None]],
        collision: SecurityCollisionResult,
        source_conflict: bool,
        prior: c.Decision | None,
    ) -> c.MachineState:
        outcomes = tuple(result for result, _ in states.values())
        if collision.result == "CONFLICT" or source_conflict or "CONFLICT" in outcomes:
            return "REVIEW_REQUIRED"
        if "STALE" in outcomes:
            return "STALE"
        if outcomes and all(result == "SATISFIED" for result in outcomes):
            return "READY_FOR_MANUAL_REVIEW"
        if (
            prior is not None
            and prior.machine_state == "READY_FOR_MANUAL_REVIEW"
            and "UNSUPPORTED" in outcomes
        ):
            return "REVIEW_REQUIRED"
        return "UNRESOLVED"

    @staticmethod
    def _intervals_overlap(left: Any, right: Any, today: date) -> bool:
        left_start = left.valid_from or date.min
        right_start = right.valid_from or date.min
        left_end = left.valid_to or date.max
        right_end = right.valid_to or date.max
        if left_start > today and right_start > today:
            return False
        return max(left_start, right_start) <= min(left_end, right_end)

    def _collision_scan(
        self,
        session: Session,
        provider: _ProviderSnapshot,
        security_id: str,
        proposed_identifiers: Sequence[c.IdentifierClaim],
        proposed_classes: Sequence[c.ClassClaim],
        proposed_listings: Sequence[c.ListingClaim],
        evidence: dict[str, _EvidenceSnapshot],
        at: datetime,
    ) -> SecurityCollisionResult:
        current_evidence = {
            evidence_id
            for evidence_id, snapshot in evidence.items()
            if (
                snapshot.current
                and not snapshot.parse_error
                and self._production_evidence(snapshot.record)
            )
        }

        def has_current_application(application_id: str) -> bool:
            application = session.get(sm.SecurityEvidenceApplicationRow, application_id)
            return (
                application is not None
                and application.evidence_id in current_evidence
                and application.status == "ADMITTED"
                and application.fixture_taint == 0
                and application.test_taint == 0
            )

        existing: list[c.IdentifierClaim | c.ClassClaim | c.ListingClaim] = []
        for identifier_row in session.scalars(select(sm.SecurityIdentifierClaimRow)).all():
            try:
                identifier_claim = c.IdentifierClaim.model_validate_json(
                    identifier_row.payload_json
                )
            except ValidationError:
                continue
            if has_current_application(identifier_claim.application_id):
                existing.append(identifier_claim)
        for class_row in session.scalars(select(sm.SecurityClassClaimRow)).all():
            try:
                class_claim = c.ClassClaim.model_validate_json(class_row.payload_json)
            except ValidationError:
                continue
            if has_current_application(class_claim.application_id):
                existing.append(class_claim)
        for listing_row in session.scalars(select(sm.SecurityListingClaimRow)).all():
            try:
                listing_claim = c.ListingClaim.model_validate_json(listing_row.payload_json)
            except ValidationError:
                continue
            if has_current_application(listing_claim.application_id):
                existing.append(listing_claim)

        by_id: dict[str, c.IdentifierClaim | c.ClassClaim | c.ListingClaim] = {}
        for candidate_claim in (
            *existing,
            *proposed_identifiers,
            *proposed_classes,
            *proposed_listings,
        ):
            by_id[candidate_claim.claim_id] = candidate_claim
        claims = tuple(by_id[key] for key in sorted(by_id))
        reasons: set[str] = set()
        affected: set[str] = set()
        today = at.date()
        identifiers: dict[tuple[str, str], list[c.IdentifierClaim]] = defaultdict(list)
        provider_security: dict[str, set[str]] = defaultdict(set)
        classes: dict[tuple[str, str], list[c.ClassClaim]] = defaultdict(list)
        listings: dict[tuple[str, str], list[c.ListingClaim]] = defaultdict(list)

        for claim in claims:
            provider_security[claim.provider_id].add(claim.security_id)
            if isinstance(claim, c.IdentifierClaim):
                active = (claim.valid_from is None or claim.valid_from <= today) and (
                    claim.valid_to is None or claim.valid_to >= today
                )
                if active:
                    identifiers[(claim.identifier_kind, claim.identifier_value)].append(claim)
            elif isinstance(claim, c.ClassClaim):
                classes[(claim.provider_id, claim.security_id)].append(claim)
            else:
                listings[(claim.provider_id, claim.security_id)].append(claim)

        for identifier_values in identifiers.values():
            if len({claim.security_id for claim in identifier_values}) > 1:
                reasons.add("AUTHORITATIVE_IDENTIFIER_COLLISION")
                affected.update(claim.provider_id for claim in identifier_values)
        for provider_id, security_ids in provider_security.items():
            if len(security_ids) > 1:
                reasons.add("PROVIDER_SECURITY_COLLISION")
                affected.add(provider_id)
        for key, class_values in classes.items():
            semantics = {
                (
                    claim.instrument_family,
                    claim.registered_class_title,
                    claim.authority_share_kind,
                )
                for claim in class_values
            }
            if len(semantics) > 1:
                reasons.add("CURRENT_CLASS_CLAIM_CONFLICT")
                affected.add(key[0])
        for key, listing_values in listings.items():
            for index, left in enumerate(listing_values):
                for right in listing_values[index + 1 :]:
                    if self._intervals_overlap(left, right, today) and (
                        left.venue,
                        left.market,
                        left.ticker,
                        left.listing_status,
                    ) != (
                        right.venue,
                        right.market,
                        right.ticker,
                        right.listing_status,
                    ):
                        reasons.add("CURRENT_LISTING_CLAIM_CONFLICT")
                        affected.add(key[0])

        active_listings: dict[tuple[str, str], list[Any]] = defaultdict(list)
        removed_securities = {
            claim.security_id
            for claim in claims
            if isinstance(claim, c.ClassClaim)
            for item in evidence.values()
            if isinstance(item.fact, SecAccepted8AFact)
            and _sec_class_identity(item.fact).class_row_id() == claim.registered_row_id
            and _effective_removals(item.fact, tuple(evidence.values()), at)
        }
        for claim in claims:
            if (
                isinstance(claim, c.ListingClaim)
                and claim.listing_status == "ACTIVE"
                and claim.security_id not in removed_securities
            ):
                active_listings[(claim.venue, claim.ticker)].append(claim)
        for listing_values in active_listings.values():
            for index, left in enumerate(listing_values):
                for right in listing_values[index + 1 :]:
                    if left.security_id != right.security_id and self._intervals_overlap(
                        left, right, today
                    ):
                        reasons.add("GLOBAL_ACTIVE_LISTING_COLLISION")
                        affected.update((left.provider_id, right.provider_id))

        # Inspect unevaluated providers as well: insertion order cannot choose a winner.
        # The B head proves issuer identity; the accepted SEC row proves class identity.
        # No Nasdaq CIK, company-name inference or ticker-derived Security ID is used.
        prospective: dict[tuple[str, str], list[tuple[str, str, date | None]]] = defaultdict(list)
        for identity in session.scalars(select(ProviderSecurityIdentityRow)).all():
            candidate_provider = self._provider_snapshot(
                session, identity.provider_security_identity_id
            )
            candidate_issuer = self._issuer_snapshot(
                session, identity.provider_security_identity_id
            )
            if (
                candidate_provider is None
                or candidate_issuer is None
                or candidate_issuer.issuer.jurisdiction != "US"
            ):
                continue
            for sec in evidence.values():
                if (
                    not sec.current
                    or sec.parse_error
                    or not self._production_evidence(sec.record)
                    or not isinstance(sec.fact, SecAccepted8AFact)
                    or sec.fact.registrant_cik != candidate_issuer.issuer.cik
                    or _norm(sec.fact.exchange_name or "") != "nasdaq"
                ):
                    continue
                if _effective_removals(sec.fact, tuple(evidence.values()), at):
                    continue
                for exchange in evidence.values():
                    if (
                        not exchange.current
                        or exchange.parse_error
                        or not self._production_evidence(exchange.record)
                        or not isinstance(exchange.fact, NasdaqPrimaryFact)
                        or exchange.fact.symbol != candidate_provider.observation.symbol
                        or exchange.fact.state != "ACTIVE"
                        or exchange.fact.test_issue
                        or _norm(exchange.fact.security_name)
                        != _norm(sec.fact.registered_class_title)
                    ):
                        continue
                    class_identity = _sec_class_identity(sec.fact)
                    candidate_id = c.security_id_for_anchor(
                        c.us_anchor(candidate_issuer.issuer.issuer_id, class_identity)
                    )
                    policies = tuple(
                        build_policy(spec, recorded_at=at) for spec in SOURCE_POLICY_SPECS
                    )
                    apps = self._applications(
                        (sec, exchange),
                        policies,
                        candidate_provider,
                        candidate_issuer,
                        candidate_id,
                        at,
                    )
                    fresh = self._freshness_map((sec, exchange), candidate_provider, at)
                    if (
                        scope_proof_ids("US", c.Scope.REGISTERED_CLASS, apps) is None
                        or scope_proof_ids("US", c.Scope.LISTING_STATUS, apps) is None
                        or not all(fresh.values())
                    ):
                        continue
                    prospective[("NASDAQ", exchange.fact.symbol)].append(
                        (
                            identity.provider_security_identity_id,
                            candidate_id,
                            exchange.fact.listing_date,
                        )
                    )
        for values in prospective.values():
            if len({item[1] for item in values}) > 1:
                reasons.add("GLOBAL_ACTIVE_LISTING_COLLISION")
                affected.update(item[0] for item in values)

        candidate_isins = {
            proposed_identifier.identifier_value
            for proposed_identifier in proposed_identifiers
            if proposed_identifier.identifier_kind == "KRX_ISIN"
        }
        for isin in candidate_isins:
            stock_codes = {
                snapshot.fact.stock_code
                for snapshot in evidence.values()
                if (
                    snapshot.current
                    and not snapshot.parse_error
                    and self._production_evidence(snapshot.record)
                    and isinstance(snapshot.fact, KrxStandardCodeFact)
                    and snapshot.fact.isin == isin
                )
            }
            if len(stock_codes) > 1:
                reasons.add("DUPLICATE_ACTIVE_ISIN_AUTHORITY")
                affected.add(provider.identity.provider_security_identity_id)
            for provider_row in session.scalars(select(ProviderSecurityMasterObservationRow)).all():
                try:
                    observation = ProviderSecurityMasterObservation.model_validate_json(
                        provider_row.payload_json
                    )
                except ValidationError:
                    continue
                if (
                    observation.isin == isin
                    and observation.provider_security_identity_id is not None
                ):
                    affected.add(observation.provider_security_identity_id)

        affected_ids = tuple(sorted(affected))
        reason_codes = tuple(sorted(reasons))
        result: Literal["CLEAR", "CONFLICT"] = "CONFLICT" if reason_codes else "CLEAR"
        digest = c.security_hash(
            {
                "result": result,
                "reasons": reason_codes,
                "affected_provider_ids": affected_ids,
                "claims": sorted((claim.claim_id, claim.content_hash) for claim in claims),
                "prospective_listings": sorted(
                    (key, sorted(values)) for key, values in prospective.items()
                ),
                "removed_securities": sorted(removed_securities),
            }
        )
        return SecurityCollisionResult(
            result=result,
            reason_codes=reason_codes,
            affected_provider_ids=affected_ids,
            digest=digest,
        )
