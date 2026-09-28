"""Unrouted issuer dispositions over the frozen B1 ledger and R1 verifier."""

from __future__ import annotations

import re
import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, cast

from sqlalchemy import select, update
from sqlalchemy.orm import Session, sessionmaker

from toss_dashboard_api.contracts.authority import (
    AuthorityBundle,
    AuthorityEvidence,
    IssuerDecision,
    IssuerMachineDecisionState,
    authority_sha256,
    build_issuer_decision,
    canonical_authority_json_bytes,
)
from toss_dashboard_api.contracts.authority_decision import (
    IssuerAuthorityEvaluationRequest,
    build_issuer_authority_evaluation_request,
)
from toss_dashboard_api.contracts.base import normalized_hash
from toss_dashboard_api.contracts.enums import Jurisdiction, MissingReason
from toss_dashboard_api.contracts.issuer import Issuer
from toss_dashboard_api.domain.issuer_authority import (
    IssuerAuthorityDecisionEngine,
    IssuerAuthorityDecisionEngineResult,
    latest_authority_observation,
)
from toss_dashboard_api.reviewer import canonical as c
from toss_dashboard_api.reviewer import schema as s
from toss_dashboard_api.reviewer.ledger import Ledger
from toss_dashboard_api.reviewer.runtime import _ClockSample, _Runtime, create_reviewer_service
from toss_dashboard_api.reviewer.webauthn_core import assertion_options, verify_assertion
from toss_dashboard_api.storage.models import (
    AuthorityBundleRow,
    AuthorityEvidenceObservationRow,
    AuthorityEvidenceRow,
    IssuerApprovalChallengeConsumptionRow,
    IssuerApprovalChallengeRow,
    IssuerApprovalEventRow,
    IssuerApprovalEvidenceObservationRow,
    IssuerAuthorityLinkHeadRow,
    IssuerAuthorityLinkRow,
    IssuerDecisionRow,
    IssuerRow,
    ReviewerAuthenticationEventRow,
)

_CHALLENGE_VERSION = "issuer-approval-challenge/0.1.0"
_CONSUMPTION_VERSION = "issuer-approval-challenge-consumption/0.1.0"
_APPROVAL_VERSION = "issuer-approval-event/0.1.0"
_LINK_VERSION = "issuer-authority-link/0.1.0"
_REASON_CODE = re.compile(r"[A-Z][A-Z0-9_]{0,127}\Z")


class IssuerDispositionError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class IssuerChallenge:
    challenge_id: str
    expires_at: str
    options: dict[str, Any]


@dataclass(frozen=True)
class IssuerDispositionResult:
    approval_event_id: str
    issuer_id: str | None
    link_id: str | None


@dataclass(frozen=True)
class IssuerSupersessionResult:
    superseded_event_id: str
    superseded_link_id: str
    approved_event_id: str
    approved_link_id: str
    issuer_id: str


def _json(value: Any) -> str:
    return canonical_authority_json_bytes(value).decode("utf-8")


def _id(prefix: str) -> str:
    return prefix + secrets.token_hex(32)


def _row_payload(values: dict[str, Any]) -> str:
    return _json({key: value for key, value in values.items() if key != "payload_json"})


def _binding(challenge: IssuerApprovalChallengeRow) -> dict[str, Any]:
    return {key: getattr(challenge, key) for key in c.ISSUER_CHALLENGE_FIELDS}


def _approval_audit_hash(event: dict[str, Any], memberships: list[dict[str, Any]]) -> str:
    return authority_sha256(
        {
            "issuer_approval_event_id": event["issuer_approval_event_id"],
            "authentication_event_id": event["authentication_event_id"],
            "issuer_approval_challenge_id": event["issuer_approval_challenge_id"],
            "authentication_result": event["authentication_result"],
            "authentication_policy_version": event["authentication_policy_version"],
            "credential_public_key_fingerprint": event["credential_public_key_fingerprint"],
            "authenticated_at": event["authenticated_at"],
            "recorded_at": event["recorded_at"],
            "approval_observations": memberships,
        }
    )


class IssuerDispositionService:
    """Trusted backend entry point; caller supplies only intent and assertion bytes."""

    def __init__(self, runtime: _Runtime, decision_engine: IssuerAuthorityDecisionEngine) -> None:
        self._runtime = runtime
        self._decisions = decision_engine

    @staticmethod
    def _decision(
        session: Session, decision_id: str
    ) -> tuple[IssuerDecisionRow, AuthorityBundleRow]:
        decision = session.get(IssuerDecisionRow, decision_id)
        if decision is None:
            raise IssuerDispositionError("UNKNOWN_DECISION")
        bundle = session.get(AuthorityBundleRow, decision.authority_bundle_id)
        if bundle is None:
            raise IssuerDispositionError("AUTHORITY_BUNDLE_MISSING")
        parsed_decision = IssuerDecision.model_validate_json(decision.payload_json, strict=False)
        parsed_bundle = AuthorityBundle.model_validate_json(bundle.payload_json, strict=False)
        if (
            parsed_decision.issuer_decision_id != decision.issuer_decision_id
            or parsed_decision.decision_content_hash != decision.decision_content_hash
            or parsed_bundle.authority_bundle_id != bundle.authority_bundle_id
            or parsed_bundle.bundle_content_hash != bundle.bundle_content_hash
            or decision.authority_bundle_content_hash != bundle.bundle_content_hash
            or decision.provider_security_identity_id != bundle.provider_security_identity_id
            or decision.proposed_issuer_id != bundle.proposed_issuer_id
        ):
            raise IssuerDispositionError("AUTHORITY_CONTENT_MISMATCH")
        return decision, bundle

    @staticmethod
    def _current_leaf(session: Session, decision: IssuerDecisionRow) -> None:
        successors = session.scalars(
            select(IssuerDecisionRow).where(
                IssuerDecisionRow.supersedes_decision_id == decision.issuer_decision_id
            )
        ).all()
        if successors:
            raise IssuerDispositionError("DECISION_NOT_CURRENT")

    def issue(self, decision_id: str, disposition: str) -> IssuerChallenge:
        if disposition not in {"APPROVED", "REJECTED"} or type(decision_id) is not str:
            raise IssuerDispositionError("INVALID_DISPOSITION_INTENT")
        with self._runtime._transaction() as (connection, ledger, _owner):
            with Session(bind=connection) as session:
                if ledger.principal is None or not ledger.active:
                    raise IssuerDispositionError("NO_ACTIVE_STEWARD_CREDENTIAL")
                decision, bundle = self._decision(session, decision_id)
                self._current_leaf(session, decision)
                if (
                    decision.decision_state
                    != IssuerMachineDecisionState.READY_FOR_MANUAL_REVIEW.value
                ):
                    raise IssuerDispositionError("DECISION_NOT_REVIEW_READY")
                return self._new_challenge(session, ledger, decision, bundle, disposition)

    def _new_challenge(
        self,
        session: Session,
        ledger: Any,
        decision: IssuerDecisionRow,
        bundle: AuthorityBundleRow,
        disposition: str,
        *,
        predecessor_approval_event_id: str | None = None,
        predecessor_link_id: str | None = None,
        successor_decision_id: str | None = None,
    ) -> IssuerChallenge:
        now = _ClockSample.take(self._runtime._clock).stored
        challenge_id = _id("iach_")
        values: dict[str, Any] = {
            "issuer_approval_challenge_id": challenge_id,
            "contract_version": _CHALLENGE_VERSION,
            "challenge_digest": "",
            "challenge_binding_hash": "",
            "reviewer_principal_id": ledger.principal["reviewer_principal_id"],
            "reviewer_role": c.ROLE,
            "principal_content_hash": ledger.principal["principal_content_hash"],
            "issuer_decision_id": decision.issuer_decision_id,
            "authority_bundle_id": bundle.authority_bundle_id,
            "expected_decision_content_hash": decision.decision_content_hash,
            "expected_bundle_content_hash": bundle.bundle_content_hash,
            "provider_security_identity_id": bundle.provider_security_identity_id,
            "proposed_issuer_id": bundle.proposed_issuer_id,
            "requested_disposition": disposition,
            "predecessor_approval_event_id": predecessor_approval_event_id,
            "predecessor_link_id": predecessor_link_id,
            "successor_decision_id": successor_decision_id,
            "rp_id": c.RP_ID,
            "allowed_origin": c.ORIGIN,
            "user_verification_required": 1,
            "authentication_policy_version": c.POLICY,
            "issued_at": c.utc_text(now),
            "expires_at": c.utc_text(now + timedelta(minutes=5)),
        }
        raw = secrets.token_bytes(32)
        values["challenge_digest"] = c.digest(raw)
        challenge = IssuerApprovalChallengeRow(**values, payload_json="{}")
        values["challenge_binding_hash"] = c.row_hash(
            _binding(challenge), c.ISSUER_CHALLENGE_FIELDS
        )
        if (
            session.scalar(
                select(IssuerApprovalChallengeRow.issuer_approval_challenge_id).where(
                    IssuerApprovalChallengeRow.issuer_decision_id == decision.issuer_decision_id,
                    IssuerApprovalChallengeRow.requested_disposition == disposition,
                    IssuerApprovalChallengeRow.reviewer_principal_id
                    == values["reviewer_principal_id"],
                    IssuerApprovalChallengeRow.issued_at == values["issued_at"],
                    IssuerApprovalChallengeRow.expires_at == values["expires_at"],
                    IssuerApprovalChallengeRow.predecessor_approval_event_id
                    == predecessor_approval_event_id,
                    IssuerApprovalChallengeRow.predecessor_link_id == predecessor_link_id,
                    IssuerApprovalChallengeRow.successor_decision_id == successor_decision_id,
                )
            )
            is not None
        ):
            raise IssuerDispositionError("CHALLENGE_ALREADY_ISSUED")
        values["payload_json"] = _row_payload(values)
        session.add(IssuerApprovalChallengeRow(**values))
        session.flush()
        options = assertion_options(raw, tuple(sorted(ledger.active)), 300_000)
        return IssuerChallenge(challenge_id, values["expires_at"], options)

    @staticmethod
    def _verify_approval_audit(session: Session, event: IssuerApprovalEventRow) -> None:
        rows = session.scalars(
            select(IssuerApprovalEvidenceObservationRow)
            .where(
                IssuerApprovalEvidenceObservationRow.issuer_approval_event_id
                == event.issuer_approval_event_id
            )
            .order_by(IssuerApprovalEvidenceObservationRow.member_ordinal)
        ).all()
        memberships: list[dict[str, Any]] = []
        for row in rows:
            member = {
                "issuer_approval_event_id": row.issuer_approval_event_id,
                "authority_evidence_observation_id": row.authority_evidence_observation_id,
                "member_ordinal": row.member_ordinal,
                "observation_content_hash": row.observation_content_hash,
            }
            if row.membership_content_hash != authority_sha256(member):
                raise IssuerDispositionError("APPROVAL_OBSERVATION_AUDIT_CONFLICT")
            memberships.append({**member, "membership_content_hash": row.membership_content_hash})
        audit_fields = (
            "issuer_approval_event_id",
            "authentication_event_id",
            "issuer_approval_challenge_id",
            "authentication_result",
            "authentication_policy_version",
            "credential_public_key_fingerprint",
            "authenticated_at",
            "recorded_at",
        )
        if event.approval_event_audit_hash != _approval_audit_hash(
            {field: getattr(event, field) for field in audit_fields}, memberships
        ):
            raise IssuerDispositionError("APPROVAL_EVENT_AUDIT_CONFLICT")

    @staticmethod
    def _current_approved(
        session: Session, provider_id: str
    ) -> tuple[IssuerAuthorityLinkHeadRow, IssuerAuthorityLinkRow, IssuerApprovalEventRow]:
        head = session.get(IssuerAuthorityLinkHeadRow, provider_id)
        if head is None or head.link_state != "APPROVED":
            raise IssuerDispositionError("CURRENT_APPROVAL_REQUIRED")
        link = session.get(IssuerAuthorityLinkRow, head.issuer_authority_link_id)
        if (
            link is None
            or link.link_state != "APPROVED"
            or link.provider_security_identity_id != provider_id
        ):
            raise IssuerDispositionError("LINK_HEAD_BINDING_MISMATCH")
        event = session.get(IssuerApprovalEventRow, link.approval_event_id)
        if (
            event is None
            or event.event_state != "APPROVED"
            or event.provider_security_identity_id != provider_id
        ):
            raise IssuerDispositionError("APPROVAL_LINK_BINDING_MISMATCH")
        IssuerDispositionService._verify_approval_audit(session, event)
        return head, link, event

    def issue_revocation(self, provider_id: str) -> IssuerChallenge:
        if type(provider_id) is not str:
            raise IssuerDispositionError("INVALID_PROVIDER_INTENT")
        with self._runtime._transaction() as (connection, ledger, _owner):
            with Session(bind=connection) as session:
                _head, link, event = self._current_approved(session, provider_id)
                decision, bundle = self._decision(session, event.issuer_decision_id)
                return self._new_challenge(
                    session,
                    ledger,
                    decision,
                    bundle,
                    "REVOKED",
                    predecessor_approval_event_id=event.issuer_approval_event_id,
                    predecessor_link_id=link.issuer_authority_link_id,
                )

    def issue_supersession(
        self, successor_decision_id: str
    ) -> tuple[IssuerChallenge, IssuerChallenge]:
        if type(successor_decision_id) is not str:
            raise IssuerDispositionError("INVALID_SUCCESSOR_INTENT")
        with self._runtime._transaction() as (connection, ledger, _owner):
            with Session(bind=connection) as session:
                successor, successor_bundle = self._decision(session, successor_decision_id)
                self._current_leaf(session, successor)
                if (
                    successor.decision_state
                    != IssuerMachineDecisionState.READY_FOR_MANUAL_REVIEW.value
                ):
                    raise IssuerDispositionError("SUCCESSOR_NOT_REVIEW_READY")
                _head, old_link, old_event = self._current_approved(
                    session, successor.provider_security_identity_id
                )
                old_decision, old_bundle = self._decision(session, old_event.issuer_decision_id)
                if (
                    successor.issuer_decision_id == old_decision.issuer_decision_id
                    or successor.provider_security_identity_id
                    != old_link.provider_security_identity_id
                    or successor.supersedes_decision_id is None
                ):
                    raise IssuerDispositionError("SUCCESSOR_LINEAGE_MISMATCH")
                ancestor_id: str | None = successor.supersedes_decision_id
                visited: set[str] = set()
                while ancestor_id != old_decision.issuer_decision_id:
                    if ancestor_id is None or ancestor_id in visited:
                        raise IssuerDispositionError("SUCCESSOR_LINEAGE_MISMATCH")
                    visited.add(ancestor_id)
                    ancestor = session.get(IssuerDecisionRow, ancestor_id)
                    if (
                        ancestor is None
                        or ancestor.provider_security_identity_id
                        != successor.provider_security_identity_id
                    ):
                        raise IssuerDispositionError("SUCCESSOR_LINEAGE_MISMATCH")
                    ancestor_id = ancestor.supersedes_decision_id
                references = {
                    "predecessor_approval_event_id": old_event.issuer_approval_event_id,
                    "predecessor_link_id": old_link.issuer_authority_link_id,
                    "successor_decision_id": successor_decision_id,
                }
                old_challenge = self._new_challenge(
                    session, ledger, old_decision, old_bundle, "SUPERSEDED", **references
                )
                new_challenge = self._new_challenge(
                    session, ledger, successor, successor_bundle, "APPROVED", **references
                )
                return old_challenge, new_challenge

    def complete(
        self,
        challenge_id: str,
        assertion: Any,
        *,
        structured_reason_code: str,
        review_note: str,
    ) -> IssuerDispositionResult:
        if (
            type(challenge_id) is not str
            or type(structured_reason_code) is not str
            or type(review_note) is not str
        ):
            raise IssuerDispositionError("INVALID_COMPLETION_INTENT")
        if not _REASON_CODE.fullmatch(structured_reason_code) or not review_note.strip():
            raise IssuerDispositionError("REASON_REQUIRED")
        business_error: IssuerDispositionError | None = None
        result: IssuerDispositionResult | None = None
        with self._runtime._transaction() as (connection, ledger, _owner):
            with Session(bind=connection) as session:
                prior = self._completed_event(
                    session, challenge_id, structured_reason_code, review_note
                )
                if prior is not None:
                    event, link = prior
                    if event.event_state == "SUPERSEDED":
                        raise IssuerDispositionError("PAIRED_SUPERSESSION_REQUIRED")
                    return IssuerDispositionResult(
                        event.issuer_approval_event_id,
                        None if event.event_state == "REJECTED" else event.proposed_issuer_id,
                        None if link is None else link.issuer_authority_link_id,
                    )
                challenge, authentication, recorded_at, business_error = self._consume(
                    session, connection, ledger, challenge_id, assertion
                )
                if authentication is not None:
                    try:
                        if challenge.requested_disposition in {"APPROVED", "REJECTED"}:
                            current = self._revalidate_locked(session, challenge)
                            with session.begin_nested():
                                result = self._execute_initial(
                                    session,
                                    challenge,
                                    authentication,
                                    current.bundle,
                                    structured_reason_code,
                                    review_note,
                                    recorded_at,
                                )
                        elif challenge.requested_disposition == "REVOKED":
                            with session.begin_nested():
                                result = self._execute_revocation(
                                    session,
                                    challenge,
                                    authentication,
                                    structured_reason_code,
                                    review_note,
                                    recorded_at,
                                )
                        else:
                            raise IssuerDispositionError("PAIRED_SUPERSESSION_REQUIRED")
                    except IssuerDispositionError as error:
                        business_error = error
        if business_error is not None:
            raise business_error
        assert result is not None
        return result

    def _consume(
        self,
        session: Session,
        connection: Any,
        ledger: Any,
        challenge_id: str,
        assertion: Any,
    ) -> tuple[
        IssuerApprovalChallengeRow,
        dict[str, Any] | None,
        str,
        IssuerDispositionError | None,
    ]:
        challenge = session.get(IssuerApprovalChallengeRow, challenge_id)
        if challenge is None:
            raise IssuerDispositionError("UNKNOWN_CHALLENGE")
        if (
            session.scalar(
                select(IssuerApprovalChallengeConsumptionRow).where(
                    IssuerApprovalChallengeConsumptionRow.issuer_approval_challenge_id
                    == challenge_id
                )
            )
            is not None
        ):
            raise IssuerDispositionError("CHALLENGE_ALREADY_CONSUMED")
        if (
            ledger.principal is None
            or challenge.challenge_binding_hash
            != c.row_hash(_binding(challenge), c.ISSUER_CHALLENGE_FIELDS)
            or challenge.reviewer_principal_id != ledger.principal["reviewer_principal_id"]
            or challenge.principal_content_hash != ledger.principal["principal_content_hash"]
            or challenge.reviewer_role != c.ROLE
            or challenge.authentication_policy_version != c.POLICY
            or challenge.rp_id != c.RP_ID
            or challenge.allowed_origin != c.ORIGIN
            or challenge.user_verification_required != 1
        ):
            raise IssuerDispositionError("CHALLENGE_BINDING_MISMATCH")
        clock = _ClockSample.take(self._runtime._clock)
        clock.check_sql(
            connection, {"issued_at": challenge.issued_at, "expires_at": challenge.expires_at}
        )
        expired = clock.raw >= c.parse_utc(challenge.expires_at)
        facts = (
            None
            if expired
            else verify_assertion(assertion, challenge.challenge_digest, ledger.allowed())
        )
        if facts is not None:
            facts.flags["replay_rejected"] = 1
        if expired:
            terminal = "EXPIRED"
            safe_code = "CHALLENGE_EXPIRED"
        else:
            assert facts is not None
            terminal = facts.terminal_result
            safe_code = facts.safe_code
        if terminal == "COUNTER_REJECTED":
            terminal = "REPLAY_REJECTED"
        if terminal == "USER_PRESENCE_ABSENT":
            terminal = "FAILED_CLOSED"
        consumption_id = _id("iacc_")
        consumed_at = c.utc_text(clock.stored)
        consumption: dict[str, Any] = {
            "challenge_consumption_id": consumption_id,
            "contract_version": _CONSUMPTION_VERSION,
            "issuer_approval_challenge_id": challenge_id,
            "terminal_result": terminal,
            "safe_result_code": safe_code,
            "consumed_at": consumed_at,
        }
        consumption["consumption_content_hash"] = authority_sha256(consumption)
        consumption["payload_json"] = _row_payload(consumption)
        session.add(IssuerApprovalChallengeConsumptionRow(**consumption))
        session.flush()
        if terminal != "SUCCEEDED" or facts is None or facts.credential_id not in ledger.active:
            return challenge, None, consumed_at, IssuerDispositionError(safe_code)
        credential = ledger.active[facts.credential_id][0]
        previous_count = ledger.counters[facts.credential_id]
        auth = {
            "authentication_event_id": _id("iauth_"),
            "issuer_approval_challenge_id": challenge_id,
            "challenge_consumption_id": consumption_id,
            "reviewer_principal_id": challenge.reviewer_principal_id,
            "reviewer_role": challenge.reviewer_role,
            "webauthn_credential_id": facts.credential_id,
            "credential_id_fingerprint": credential["credential_id_fingerprint"],
            "public_key_fingerprint": credential["public_key_fingerprint"],
            "issuer_decision_id": challenge.issuer_decision_id,
            "authority_bundle_id": challenge.authority_bundle_id,
            "expected_decision_content_hash": challenge.expected_decision_content_hash,
            "expected_bundle_content_hash": challenge.expected_bundle_content_hash,
            "requested_disposition": challenge.requested_disposition,
            "authentication_result": "VERIFIED",
            "authentication_policy_version": c.POLICY,
            "rp_id": c.RP_ID,
            "exact_origin": c.ORIGIN,
            "user_presence_verified": facts.flags["user_presence_verified"],
            "user_verification_verified": facts.flags["user_verification_verified"],
            "origin_verified": facts.flags["origin_verified"],
            "rp_id_hash_verified": facts.flags["rp_id_hash_verified"],
            "signature_verified": facts.flags["signature_verified"],
            "counter_capability": credential["counter_capability"],
            "previous_sign_count": previous_count,
            "asserted_sign_count": facts.asserted_count if previous_count is not None else None,
            "counter_verified": facts.flags["counter_verified"],
            "replay_rejected": facts.flags["replay_rejected"],
            "safe_result_code": facts.safe_code,
            "authenticated_at": consumed_at,
        }
        sealed = s.sealed(s.ISSUER_AUTHENTICATION, auth)
        session.add(ReviewerAuthenticationEventRow(**sealed))
        session.flush()
        return challenge, sealed, consumed_at, None

    @staticmethod
    def _completed_event(
        session: Session, challenge_id: str, reason: str, note: str
    ) -> tuple[IssuerApprovalEventRow, IssuerAuthorityLinkRow | None] | None:
        consumption = session.scalar(
            select(IssuerApprovalChallengeConsumptionRow).where(
                IssuerApprovalChallengeConsumptionRow.issuer_approval_challenge_id == challenge_id
            )
        )
        if consumption is None:
            return None
        challenge = session.get(IssuerApprovalChallengeRow, challenge_id)
        auth = session.scalar(
            select(ReviewerAuthenticationEventRow).where(
                ReviewerAuthenticationEventRow.issuer_approval_challenge_id == challenge_id
            )
        )
        if (
            challenge is None
            or consumption.terminal_result != "SUCCEEDED"
            or auth is None
            or auth.authentication_result != "VERIFIED"
            or auth.challenge_consumption_id != consumption.challenge_consumption_id
        ):
            raise IssuerDispositionError("CHALLENGE_ALREADY_CONSUMED")
        event = session.scalar(
            select(IssuerApprovalEventRow).where(
                IssuerApprovalEventRow.authentication_event_id == auth.authentication_event_id
            )
        )
        if (
            event is None
            or event.issuer_approval_challenge_id != challenge_id
            or event.event_state != challenge.requested_disposition
            or event.structured_reason_code != reason
            or event.review_note_digest != authority_sha256(note)
            or event.decision_content_hash != challenge.expected_decision_content_hash
            or event.bundle_content_hash != challenge.expected_bundle_content_hash
            or event.provider_security_identity_id != challenge.provider_security_identity_id
            or event.proposed_issuer_id != challenge.proposed_issuer_id
        ):
            raise IssuerDispositionError("CHALLENGE_ALREADY_CONSUMED")
        links = session.scalars(
            select(IssuerAuthorityLinkRow).where(
                IssuerAuthorityLinkRow.approval_event_id == event.issuer_approval_event_id
            )
        ).all()
        if event.event_state == "REJECTED":
            if links:
                raise IssuerDispositionError("APPROVAL_LINK_BINDING_MISMATCH")
            return event, None
        if len(links) != 1 or links[0].link_state != event.event_state:
            raise IssuerDispositionError("APPROVAL_LINK_BINDING_MISMATCH")
        return event, links[0]

    def complete_supersession(
        self,
        old_challenge_id: str,
        old_assertion: Any,
        successor_challenge_id: str,
        successor_assertion: Any,
        *,
        supersession_reason_code: str,
        supersession_note: str,
        approval_reason_code: str,
        approval_note: str,
    ) -> IssuerSupersessionResult:
        if (
            type(old_challenge_id) is not str
            or type(successor_challenge_id) is not str
            or old_challenge_id == successor_challenge_id
            or any(
                type(value) is not str or not value
                for value in (
                    supersession_reason_code,
                    supersession_note,
                    approval_reason_code,
                    approval_note,
                )
            )
            or not _REASON_CODE.fullmatch(supersession_reason_code)
            or not _REASON_CODE.fullmatch(approval_reason_code)
            or not supersession_note.strip()
            or not approval_note.strip()
        ):
            raise IssuerDispositionError("INVALID_SUPERSESSION_INTENT")
        error: IssuerDispositionError | None = None
        result: IssuerSupersessionResult | None = None
        with self._runtime._transaction() as (connection, ledger, owner):
            with Session(bind=connection) as session:
                old_prior = self._completed_event(
                    session, old_challenge_id, supersession_reason_code, supersession_note
                )
                new_prior = self._completed_event(
                    session, successor_challenge_id, approval_reason_code, approval_note
                )
                if old_prior is not None or new_prior is not None:
                    if old_prior is None or new_prior is None:
                        raise IssuerDispositionError("CHALLENGE_ALREADY_CONSUMED")
                    old_event, old_link = old_prior
                    new_event, new_link = new_prior
                    if (
                        old_event.event_state != "SUPERSEDED"
                        or new_event.event_state != "APPROVED"
                        or old_link is None
                        or new_link is None
                        or old_event.successor_decision_id != new_event.issuer_decision_id
                        or new_link.supersedes_link_id != old_link.issuer_authority_link_id
                    ):
                        raise IssuerDispositionError("SUPERSESSION_REPLAY_CONFLICT")
                    return IssuerSupersessionResult(
                        old_event.issuer_approval_event_id,
                        old_link.issuer_authority_link_id,
                        new_event.issuer_approval_event_id,
                        new_link.issuer_authority_link_id,
                        new_link.issuer_id,
                    )
                old, old_auth, old_at, error = self._consume(
                    session, connection, ledger, old_challenge_id, old_assertion
                )
                if old_auth is not None:
                    refreshed = Ledger(connection, owner)
                    successor, successor_auth, successor_at, error = self._consume(
                        session,
                        connection,
                        refreshed,
                        successor_challenge_id,
                        successor_assertion,
                    )
                    if successor_auth is not None:
                        try:
                            result = self._execute_supersession(
                                session,
                                old,
                                old_auth,
                                old_at,
                                successor,
                                successor_auth,
                                successor_at,
                                supersession_reason_code,
                                supersession_note,
                                approval_reason_code,
                                approval_note,
                            )
                        except IssuerDispositionError as failure:
                            error = failure
        if error is not None:
            raise error
        assert result is not None
        return result

    def _execute_supersession(
        self,
        session: Session,
        old: IssuerApprovalChallengeRow,
        old_auth: dict[str, Any],
        old_at: str,
        successor: IssuerApprovalChallengeRow,
        successor_auth: dict[str, Any],
        successor_at: str,
        supersession_reason_code: str,
        supersession_note: str,
        approval_reason_code: str,
        approval_note: str,
    ) -> IssuerSupersessionResult:
        if (
            old.requested_disposition != "SUPERSEDED"
            or successor.requested_disposition != "APPROVED"
            or old.issuer_approval_challenge_id == successor.issuer_approval_challenge_id
            or old_auth["authentication_event_id"] == successor_auth["authentication_event_id"]
            or old_auth["challenge_consumption_id"] == successor_auth["challenge_consumption_id"]
            or old.provider_security_identity_id != successor.provider_security_identity_id
            or old.successor_decision_id != successor.issuer_decision_id
            or successor.successor_decision_id != successor.issuer_decision_id
            or old.predecessor_approval_event_id != successor.predecessor_approval_event_id
            or old.predecessor_link_id != successor.predecessor_link_id
        ):
            raise IssuerDispositionError("SUPERSESSION_AUTHORIZATION_MISMATCH")
        head, old_link, old_event = self._current_approved(
            session, old.provider_security_identity_id
        )
        if (
            old.predecessor_approval_event_id != old_event.issuer_approval_event_id
            or old.predecessor_link_id != old_link.issuer_authority_link_id
            or old.issuer_decision_id != old_event.issuer_decision_id
            or old.authority_bundle_id != old_event.authority_bundle_id
            or old.proposed_issuer_id != old_event.proposed_issuer_id
        ):
            raise IssuerDispositionError("SUPERSESSION_PREDECESSOR_CHANGED")
        current = self._revalidate_locked(session, successor)
        if current.decision.supersedes_decision_id is None:
            raise IssuerDispositionError("SUCCESSOR_LINEAGE_MISMATCH")
        with session.begin_nested():
            old_event_row = self._append_event(
                session,
                old,
                old_auth,
                supersession_reason_code,
                supersession_note,
                old_at,
                predecessor_approval_event_id=old_event.issuer_approval_event_id,
                successor_decision_id=successor.issuer_decision_id,
            )
            old_link_row = self._append_successor_link(
                session, old_link, old_event_row, "SUPERSEDED", old_at
            )
            issuer_id = self._insert_issuer(session, current.bundle)
            successor_event_row = self._append_event(
                session,
                successor,
                successor_auth,
                approval_reason_code,
                approval_note,
                successor_at,
                approval_bundle=current.bundle,
            )
            successor_link_row = self._append_successor_link(
                session, old_link_row, successor_event_row, "APPROVED", successor_at
            )
            self._cas_head(session, head, successor_link_row, successor_at)
        return IssuerSupersessionResult(
            old_event_row["issuer_approval_event_id"],
            old_link_row["issuer_authority_link_id"],
            successor_event_row["issuer_approval_event_id"],
            successor_link_row["issuer_authority_link_id"],
            issuer_id,
        )

    def _revalidate_locked(
        self, session: Session, challenge: IssuerApprovalChallengeRow
    ) -> IssuerAuthorityDecisionEngineResult:
        decision, bundle = self._decision(session, challenge.issuer_decision_id)
        if (
            decision.decision_content_hash != challenge.expected_decision_content_hash
            or bundle.bundle_content_hash != challenge.expected_bundle_content_hash
            or bundle.provider_security_identity_id != challenge.provider_security_identity_id
            or bundle.proposed_issuer_id != challenge.proposed_issuer_id
        ):
            raise IssuerDispositionError("AUTHORITY_CHANGED")
        parsed_bundle = AuthorityBundle.model_validate_json(bundle.payload_json, strict=False)
        request = self._request_from_bundle(parsed_bundle)
        approved_head = self._matching_approved_head(session, challenge)
        try:
            self._current_leaf(session, decision)
        except IssuerDispositionError:
            if approved_head is not None:
                head, old_link = approved_head
                current = self._decisions.evaluate_locked(session, request)
                self._project_safety_locked(session, head, old_link, current)
            raise
        if decision.decision_state != IssuerMachineDecisionState.READY_FOR_MANUAL_REVIEW.value:
            if approved_head is not None:
                head, old_link = approved_head
                current = self._decisions.evaluate_locked(session, request)
                self._project_safety_locked(session, head, old_link, current)
            raise IssuerDispositionError("AUTHORITY_CHANGED")
        current = self._decisions.evaluate_locked(session, request)
        if (
            current.decision.issuer_decision_id != decision.issuer_decision_id
            or current.decision.decision_content_hash != decision.decision_content_hash
            or current.bundle.authority_bundle_id != bundle.authority_bundle_id
            or current.bundle.bundle_content_hash != bundle.bundle_content_hash
            or current.decision.decision_state != IssuerMachineDecisionState.READY_FOR_MANUAL_REVIEW
        ):
            if approved_head is not None:
                head, old_link = approved_head
                self._project_safety_locked(session, head, old_link, current)
            raise IssuerDispositionError("AUTHORITY_CHANGED")
        return current

    @staticmethod
    def _matching_approved_head(
        session: Session, challenge: IssuerApprovalChallengeRow
    ) -> tuple[IssuerAuthorityLinkHeadRow, IssuerAuthorityLinkRow] | None:
        head = session.get(IssuerAuthorityLinkHeadRow, challenge.provider_security_identity_id)
        if head is None or head.link_state != "APPROVED":
            return None
        old_link = session.get(IssuerAuthorityLinkRow, head.issuer_authority_link_id)
        if old_link is None:
            raise IssuerDispositionError("LINK_HEAD_BINDING_MISMATCH")
        if old_link.issuer_decision_id != challenge.issuer_decision_id:
            return None
        return head, old_link

    @staticmethod
    def _request_from_bundle(bundle: AuthorityBundle) -> IssuerAuthorityEvaluationRequest:
        return build_issuer_authority_evaluation_request(
            provider_security_identity_id=bundle.provider_security_identity_id,
            provider_observation_ids=bundle.provider_observation_ids,
            candidate_jurisdiction=bundle.candidate_jurisdiction,
            candidate_identifier_kind=bundle.candidate_identifier_kind,
            candidate_identifier_value=bundle.candidate_identifier_value,
            evidence_ids=tuple(
                member.evidence_id for member in bundle.evidence_application_members
            ),
        )

    def revalidate_current_link(self, provider_id: str) -> str | None:
        """Project a B2-B authority loss onto an approved current issuer link."""
        if type(provider_id) is not str:
            raise IssuerDispositionError("INVALID_PROVIDER_INTENT")
        with self._runtime._transaction() as (connection, _ledger, _owner):
            with Session(bind=connection) as session:
                head = session.get(IssuerAuthorityLinkHeadRow, provider_id)
                if head is None:
                    return None
                if head.link_state == "REVIEW_REQUIRED":
                    return head.issuer_authority_link_id
                head, old_link, _event = self._current_approved(session, provider_id)
                _decision, old_bundle = self._decision(session, old_link.issuer_decision_id)
                parsed = AuthorityBundle.model_validate_json(old_bundle.payload_json, strict=False)
                current = self._decisions.evaluate_locked(
                    session, self._request_from_bundle(parsed)
                )
                return self._project_safety_locked(session, head, old_link, current)

    def evaluate_and_revalidate_affected(
        self, request: IssuerAuthorityEvaluationRequest
    ) -> IssuerAuthorityDecisionEngineResult:
        """Evaluate a new collision and project every affected approved link atomically."""
        with self._runtime._transaction() as (connection, _ledger, _owner):
            with Session(bind=connection) as session:
                result = self._decisions.evaluate_locked(session, request)
                for provider_id in result.affected_provider_ids:
                    head = session.get(IssuerAuthorityLinkHeadRow, provider_id)
                    if head is None or head.link_state != "APPROVED":
                        continue
                    head, old_link, _event = self._current_approved(session, provider_id)
                    if provider_id == request.provider_security_identity_id:
                        current = result
                    else:
                        _decision, old_bundle = self._decision(session, old_link.issuer_decision_id)
                        parsed = AuthorityBundle.model_validate_json(
                            old_bundle.payload_json, strict=False
                        )
                        current = self._decisions.evaluate_locked(
                            session, self._request_from_bundle(parsed)
                        )
                    self._project_safety_locked(session, head, old_link, current)
                return result

    def _project_safety_locked(
        self,
        session: Session,
        head: IssuerAuthorityLinkHeadRow,
        old_link: IssuerAuthorityLinkRow,
        current: IssuerAuthorityDecisionEngineResult,
    ) -> str:
        if (
            current.decision.issuer_decision_id == old_link.issuer_decision_id
            and current.bundle.authority_bundle_id == old_link.authority_bundle_id
            and current.decision.decision_state
            == IssuerMachineDecisionState.READY_FOR_MANUAL_REVIEW
        ):
            return old_link.issuer_authority_link_id
        safety_decision = current.decision
        if safety_decision.decision_state != IssuerMachineDecisionState.REVIEW_REQUIRED:
            safety_decision = build_issuer_decision(
                bundle=current.bundle,
                decision_state=IssuerMachineDecisionState.REVIEW_REQUIRED,
                reason_codes=(*current.decision.reason_codes, "POST_APPROVAL_AUTHORITY_LOST"),
                latest_revision_check_hash=current.decision.latest_revision_check_hash,
                freshness_policy_version=current.decision.freshness_policy_version,
                freshness_result=current.decision.freshness_result,
                collision_scan_hash=current.decision.collision_scan_hash,
                evaluated_at=current.decision.evaluated_at,
                supersedes_decision_id=current.decision.issuer_decision_id,
            )
            self._decisions._insert_engine_decision(session, safety_decision)
        recorded_at = c.utc_text(_ClockSample.take(self._runtime._clock).stored)
        with session.begin_nested():
            safety_link = self._append_successor_link(
                session,
                old_link,
                None,
                "REVIEW_REQUIRED",
                recorded_at,
                machine_trigger_decision_id=safety_decision.issuer_decision_id,
            )
            self._cas_head(session, head, safety_link, recorded_at)
        return cast(str, safety_link["issuer_authority_link_id"])

    def _execute_initial(
        self,
        session: Session,
        challenge: IssuerApprovalChallengeRow,
        authentication: dict[str, Any],
        bundle: AuthorityBundle,
        reason: str,
        note: str,
        recorded_at: str,
    ) -> IssuerDispositionResult:
        disposition = challenge.requested_disposition
        if disposition not in {"APPROVED", "REJECTED"}:
            raise IssuerDispositionError("INVALID_DISPOSITION_INTENT")
        prior = session.scalar(
            select(IssuerApprovalEventRow).where(
                IssuerApprovalEventRow.issuer_decision_id == challenge.issuer_decision_id,
                IssuerApprovalEventRow.predecessor_approval_event_id.is_(None),
                IssuerApprovalEventRow.event_state.in_(("APPROVED", "REJECTED")),
            )
        )
        if prior is not None:
            raise IssuerDispositionError("INITIAL_DISPOSITION_CONFLICT")
        issuer_id: str | None = None
        link_id: str | None = None
        if disposition == "APPROVED":
            issuer_id = self._insert_issuer(session, bundle)
        event = self._append_event(
            session,
            challenge,
            authentication,
            reason,
            note,
            recorded_at,
            approval_bundle=bundle if disposition == "APPROVED" else None,
        )
        if disposition == "APPROVED":
            assert issuer_id is not None
            link_id = self._append_link(session, event, issuer_id, recorded_at)
        return IssuerDispositionResult(event["issuer_approval_event_id"], issuer_id, link_id)

    def _append_event(
        self,
        session: Session,
        challenge: IssuerApprovalChallengeRow,
        authentication: dict[str, Any],
        reason: str,
        note: str,
        recorded_at: str,
        *,
        predecessor_approval_event_id: str | None = None,
        successor_decision_id: str | None = None,
        approval_bundle: AuthorityBundle | None = None,
    ) -> dict[str, Any]:
        decision, bundle_row = self._decision(session, challenge.issuer_decision_id)
        semantic = {
            "contract_version": _APPROVAL_VERSION,
            "issuer_decision_id": decision.issuer_decision_id,
            "decision_content_hash": decision.decision_content_hash,
            "authority_bundle_id": bundle_row.authority_bundle_id,
            "bundle_content_hash": bundle_row.bundle_content_hash,
            "event_state": challenge.requested_disposition,
            "reviewer_principal_id": authentication["reviewer_principal_id"],
            "reviewer_role": authentication["reviewer_role"],
            "structured_reason_code": reason,
            "review_note_digest": authority_sha256(note),
            "predecessor_approval_event_id": predecessor_approval_event_id,
            "successor_decision_id": successor_decision_id,
        }
        event_hash = authority_sha256(semantic)
        event_id = "iap_" + event_hash.removeprefix("sha256:")
        if session.get(IssuerApprovalEventRow, event_id) is not None:
            raise IssuerDispositionError("APPROVAL_EVENT_ALREADY_EXISTS")
        if challenge.requested_disposition == "APPROVED" and approval_bundle is None:
            raise IssuerDispositionError("APPROVAL_OBSERVATIONS_REQUIRED")
        memberships = (
            self._approval_observations(session, event_id, approval_bundle)
            if approval_bundle is not None
            else []
        )
        event: dict[str, Any] = {
            "issuer_approval_event_id": event_id,
            **semantic,
            "approval_event_content_hash": event_hash,
            "approval_event_audit_hash": "",
            "provider_security_identity_id": bundle_row.provider_security_identity_id,
            "proposed_issuer_id": bundle_row.proposed_issuer_id,
            "authentication_event_id": authentication["authentication_event_id"],
            "issuer_approval_challenge_id": challenge.issuer_approval_challenge_id,
            "authentication_result": "VERIFIED",
            "authentication_policy_version": c.POLICY,
            "credential_public_key_fingerprint": authentication["public_key_fingerprint"],
            "authenticated_at": authentication["authenticated_at"],
            "recorded_at": recorded_at,
        }
        event["approval_event_audit_hash"] = _approval_audit_hash(event, memberships)
        event["payload_json"] = _row_payload(event)
        session.add(IssuerApprovalEventRow(**event))
        session.flush()
        for values in memberships:
            session.add(
                IssuerApprovalEvidenceObservationRow(**values, payload_json=_row_payload(values))
            )
        session.flush()
        return event

    @staticmethod
    def _insert_issuer(session: Session, bundle: AuthorityBundle) -> str:
        name_members = {
            member.evidence_id: member
            for member in bundle.evidence_application_members
            if member.authority_scope.value == "LEGAL_NAME"
            and member.application_status.value == "APPLIED_DECISIVE"
            and member.effective_issuer_authority_weight.value == "DECISIVE"
            and member.production_authority_admitted
            and not member.lineage_tainted
        }
        evidences = session.scalars(
            select(AuthorityEvidenceRow).where(
                AuthorityEvidenceRow.evidence_id.in_(tuple(name_members))
            )
        ).all()
        names: set[str] = set()
        for evidence in evidences:
            member = name_members[evidence.evidence_id]
            if evidence.evidence_content_hash != member.evidence_content_hash:
                raise IssuerDispositionError("LEGAL_NAME_CONTENT_MISMATCH")
            parsed = AuthorityEvidence.model_validate_json(evidence.payload_json, strict=False)
            if (
                parsed.authority_scope.value != "LEGAL_NAME"
                or parsed.policy_maximum_issuer_authority_weight.value != "DECISIVE"
                or not isinstance(parsed.normalized_claim_value, str)
            ):
                raise IssuerDispositionError("LEGAL_NAME_CONTENT_MISMATCH")
            names.add(parsed.normalized_claim_value)
        if len(names) != 1:
            raise IssuerDispositionError("CANONICAL_LEGAL_NAME_AMBIGUOUS")
        name = next(iter(names))
        jurisdiction = bundle.candidate_jurisdiction
        values: dict[str, Any] = {
            "contract_version": "0.1.0",
            "missing_reasons": (
                {"cik": MissingReason.NOT_APPLICABLE}
                if jurisdiction == Jurisdiction.KR
                else {"corp_code": MissingReason.NOT_APPLICABLE}
            ),
            "issuer_id": bundle.proposed_issuer_id,
            "legal_name": name,
            "display_name": name,
            "jurisdiction": jurisdiction,
            "corp_code": bundle.candidate_identifier_value
            if jurisdiction == Jurisdiction.KR
            else None,
            "cik": bundle.candidate_identifier_value if jurisdiction == Jurisdiction.US else None,
        }
        values["normalized_content_hash"] = normalized_hash(values)
        issuer = Issuer.model_validate(values)
        existing = session.get(IssuerRow, issuer.issuer_id)
        if existing is not None:
            existing_issuer = Issuer.model_validate_json(existing.payload_json, strict=False)
            if (
                existing.jurisdiction != jurisdiction.value
                or existing.corp_code != issuer.corp_code
                or existing.cik != issuer.cik
                or existing.normalized_content_hash != issuer.normalized_content_hash
                or normalized_hash(existing_issuer) != existing.normalized_content_hash
                or existing_issuer != issuer
            ):
                raise IssuerDispositionError("CANONICAL_ISSUER_CONFLICT")
            return issuer.issuer_id
        session.add(
            IssuerRow(
                issuer_id=issuer.issuer_id,
                jurisdiction=jurisdiction.value,
                corp_code=issuer.corp_code,
                cik=issuer.cik,
                normalized_content_hash=issuer.normalized_content_hash,
                payload_json=issuer.model_dump_json(),
            )
        )
        session.flush()
        return issuer.issuer_id

    @staticmethod
    def _approval_observations(
        session: Session, event_id: str, bundle: AuthorityBundle
    ) -> list[dict[str, Any]]:
        evidence_ids = {member.evidence_id for member in bundle.evidence_application_members}
        rows = session.scalars(
            select(AuthorityEvidenceObservationRow).where(
                AuthorityEvidenceObservationRow.evidence_id.in_(evidence_ids)
            )
        ).all()
        by_evidence: dict[str, list[AuthorityEvidenceObservationRow]] = {}
        for row in rows:
            by_evidence.setdefault(row.evidence_id, []).append(row)
        selected = [
            latest_authority_observation(by_evidence[evidence_id])
            for evidence_id in sorted(evidence_ids)
            if evidence_id in by_evidence
        ]
        observations = sorted(
            (row for row in selected if row is not None),
            key=lambda row: row.authority_evidence_observation_id,
        )
        memberships: list[dict[str, Any]] = []
        for ordinal, observation in enumerate(observations):
            values = {
                "issuer_approval_event_id": event_id,
                "authority_evidence_observation_id": observation.authority_evidence_observation_id,
                "member_ordinal": ordinal,
                "observation_content_hash": observation.observation_content_hash,
            }
            values["membership_content_hash"] = authority_sha256(values)
            memberships.append(values)
        return memberships

    @staticmethod
    def _append_link(
        session: Session, event: dict[str, Any], issuer_id: str, recorded_at: str
    ) -> str:
        provider_id = event["provider_security_identity_id"]
        if session.get(IssuerAuthorityLinkHeadRow, provider_id) is not None:
            raise IssuerDispositionError("LINK_HEAD_ALREADY_EXISTS")
        semantic = {
            "contract_version": _LINK_VERSION,
            "provider_security_identity_id": provider_id,
            "issuer_id": issuer_id,
            "authority_bundle_id": event["authority_bundle_id"],
            "bundle_content_hash": event["bundle_content_hash"],
            "issuer_decision_id": event["issuer_decision_id"],
            "decision_content_hash": event["decision_content_hash"],
            "approval_event_id": event["issuer_approval_event_id"],
            "machine_trigger_decision_id": None,
            "link_state": "APPROVED",
            "security_resolution_state": "UNRESOLVED",
            "supersedes_link_id": None,
            "authority_valid_from": None,
            "authority_valid_to": None,
        }
        link_hash = authority_sha256(semantic)
        link_id = "ial_" + link_hash.removeprefix("sha256:")
        link = {
            "issuer_authority_link_id": link_id,
            **semantic,
            "link_content_hash": link_hash,
            "link_audit_hash": authority_sha256({"link_id": link_id, "recorded_at": recorded_at}),
            "recorded_at": recorded_at,
        }
        link["payload_json"] = _row_payload(link)
        session.add(IssuerAuthorityLinkRow(**link))
        session.flush()
        head = {
            "provider_security_identity_id": provider_id,
            "issuer_authority_link_id": link_id,
            "link_state": "APPROVED",
            "security_resolution_state": "UNRESOLVED",
            "previous_state_hash": None,
            "projected_at": recorded_at,
        }
        head["state_hash"] = authority_sha256(head)
        head["payload_json"] = _row_payload(head)
        session.add(IssuerAuthorityLinkHeadRow(**head))
        session.flush()
        return link_id

    def _execute_revocation(
        self,
        session: Session,
        challenge: IssuerApprovalChallengeRow,
        authentication: dict[str, Any],
        reason: str,
        note: str,
        recorded_at: str,
    ) -> IssuerDispositionResult:
        head, old_link, old_event = self._current_approved(
            session, challenge.provider_security_identity_id
        )
        if (
            challenge.predecessor_approval_event_id != old_event.issuer_approval_event_id
            or challenge.predecessor_link_id != old_link.issuer_authority_link_id
            or challenge.issuer_decision_id != old_event.issuer_decision_id
            or challenge.authority_bundle_id != old_event.authority_bundle_id
            or challenge.proposed_issuer_id != old_event.proposed_issuer_id
            or challenge.successor_decision_id is not None
        ):
            raise IssuerDispositionError("REVOCATION_PREDECESSOR_CHANGED")
        event = self._append_event(
            session,
            challenge,
            authentication,
            reason,
            note,
            recorded_at,
            predecessor_approval_event_id=old_event.issuer_approval_event_id,
        )
        link = self._append_successor_link(session, old_link, event, "REVOKED", recorded_at)
        self._cas_head(session, head, link, recorded_at)
        return IssuerDispositionResult(
            event["issuer_approval_event_id"], old_link.issuer_id, link["issuer_authority_link_id"]
        )

    @staticmethod
    def _append_successor_link(
        session: Session,
        previous: IssuerAuthorityLinkRow | dict[str, Any],
        event: dict[str, Any] | None,
        state: str,
        recorded_at: str,
        *,
        machine_trigger_decision_id: str | None = None,
    ) -> dict[str, Any]:
        def prior(name: str) -> Any:
            return previous[name] if isinstance(previous, dict) else getattr(previous, name)

        if (state == "REVIEW_REQUIRED") != (event is None):
            raise IssuerDispositionError("LINK_TRIGGER_MISMATCH")
        semantic = {
            "contract_version": _LINK_VERSION,
            "provider_security_identity_id": prior("provider_security_identity_id"),
            "issuer_id": prior("issuer_id") if event is None else event["proposed_issuer_id"],
            "authority_bundle_id": prior("authority_bundle_id")
            if event is None
            else event["authority_bundle_id"],
            "bundle_content_hash": prior("bundle_content_hash")
            if event is None
            else event["bundle_content_hash"],
            "issuer_decision_id": prior("issuer_decision_id")
            if event is None
            else event["issuer_decision_id"],
            "decision_content_hash": prior("decision_content_hash")
            if event is None
            else event["decision_content_hash"],
            "approval_event_id": None if event is None else event["issuer_approval_event_id"],
            "machine_trigger_decision_id": machine_trigger_decision_id,
            "link_state": state,
            "security_resolution_state": "UNRESOLVED",
            "supersedes_link_id": prior("issuer_authority_link_id"),
            "authority_valid_from": None,
            "authority_valid_to": None,
        }
        link_hash = authority_sha256(semantic)
        link = {
            "issuer_authority_link_id": "ial_" + link_hash.removeprefix("sha256:"),
            **semantic,
            "link_content_hash": link_hash,
            "link_audit_hash": authority_sha256(
                {"link_content_hash": link_hash, "recorded_at": recorded_at}
            ),
            "recorded_at": recorded_at,
        }
        link["payload_json"] = _row_payload(link)
        if session.get(IssuerAuthorityLinkRow, link["issuer_authority_link_id"]) is not None:
            raise IssuerDispositionError("LINK_ALREADY_EXISTS")
        session.add(IssuerAuthorityLinkRow(**link))
        session.flush()
        return link

    @staticmethod
    def _cas_head(
        session: Session,
        head: IssuerAuthorityLinkHeadRow,
        link: dict[str, Any],
        projected_at: str,
    ) -> None:
        if link["provider_security_identity_id"] != head.provider_security_identity_id:
            raise IssuerDispositionError("LINK_HEAD_PROVIDER_MISMATCH")
        new = {
            "issuer_authority_link_id": link["issuer_authority_link_id"],
            "link_state": link["link_state"],
            "security_resolution_state": "UNRESOLVED",
            "previous_state_hash": head.state_hash,
            "projected_at": projected_at,
        }
        new["state_hash"] = authority_sha256(
            {"provider_security_identity_id": head.provider_security_identity_id, **new}
        )
        new["payload_json"] = _row_payload(
            {"provider_security_identity_id": head.provider_security_identity_id, **new}
        )
        changed = session.execute(
            update(IssuerAuthorityLinkHeadRow)
            .where(
                IssuerAuthorityLinkHeadRow.provider_security_identity_id
                == head.provider_security_identity_id,
                IssuerAuthorityLinkHeadRow.state_hash == head.state_hash,
                IssuerAuthorityLinkHeadRow.issuer_authority_link_id
                == head.issuer_authority_link_id,
            )
            .values(**new)
        ).rowcount
        if changed != 1:
            raise IssuerDispositionError("LINK_HEAD_CAS_CONFLICT")


def create_issuer_disposition_service() -> IssuerDispositionService:
    """Use the canonical local reviewer runtime and its owner-checked database."""
    runtime = create_reviewer_service()
    decisions = IssuerAuthorityDecisionEngine(
        sessionmaker(runtime._engine, expire_on_commit=False), clock=runtime._clock
    )
    return IssuerDispositionService(runtime, decisions)
