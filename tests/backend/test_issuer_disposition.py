"""B2-D issuer disposition execution against the real frozen migrations."""

from __future__ import annotations

import json
from base64 import urlsafe_b64decode
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from tests.backend.reviewer_test_support import Authenticator, Clock
from tests.backend.test_authority_decision_engine import (
    CURRENT_FETCHED_AT,
    EVALUATED_AT,
    _append_corrected_iros,
    _canonical_issuer,
    _insert_canonical_issuer,
    _kr_harness,
    _kr_request,
    _us_harness,
    _us_request,
)
from tests.backend.test_reviewer_runtime import OWNER, enroll

from authority_preadmitted_ledger import seed_preadmitted_authority_snapshot
from toss_dashboard_api.contracts.authority import (
    AuthorityRetrievalStatus,
    IssuerMachineDecisionState,
    authority_sha256,
    build_authority_evidence_observation,
)
from toss_dashboard_api.contracts.base import normalized_hash
from toss_dashboard_api.contracts.enums import Jurisdiction
from toss_dashboard_api.contracts.issuer import Issuer
from toss_dashboard_api.reviewer import canonical as c
from toss_dashboard_api.reviewer import issuer_disposition as disposition_module
from toss_dashboard_api.reviewer.issuer_disposition import (
    IssuerDispositionError,
    IssuerDispositionService,
    _binding,
)
from toss_dashboard_api.reviewer.runtime import _Runtime
from toss_dashboard_api.storage.models import (
    AuthorityEvidenceObservationRow,
    IssuerApprovalChallengeConsumptionRow,
    IssuerApprovalChallengeRow,
    IssuerApprovalEventRow,
    IssuerApprovalEvidenceObservationRow,
    IssuerAuthorityLinkHeadRow,
    IssuerAuthorityLinkRow,
    IssuerDecisionRow,
    IssuerRow,
    ProviderIdentityMappingRow,
    ProviderSecurityIdentityRow,
    SecurityRow,
)


def _counts(session: Session) -> tuple[int, int, int]:
    return (
        int(session.scalar(select(func.count()).select_from(IssuerRow)) or 0),
        int(session.scalar(select(func.count()).select_from(SecurityRow)) or 0),
        int(
            session.scalar(
                select(func.count())
                .select_from(ProviderIdentityMappingRow)
                .where(ProviderIdentityMappingRow.mapping_status == "VERIFIED")
            )
            or 0
        ),
    )


def _assert_one_link_leaf(session: Session, provider_id: str) -> None:
    links = session.scalars(
        select(IssuerAuthorityLinkRow).where(
            IssuerAuthorityLinkRow.provider_security_identity_id == provider_id
        )
    ).all()
    ids = {row.issuer_authority_link_id for row in links}
    parents = Counter(row.supersedes_link_id for row in links if row.supersedes_link_id)
    assert all(count == 1 for count in parents.values())
    leaves = ids - set(parents)
    assert len(leaves) == 1
    head = session.get(IssuerAuthorityLinkHeadRow, provider_id)
    assert head is not None and head.issuer_authority_link_id in leaves
    for row in links:
        if row.approval_event_id is not None:
            assert session.get(IssuerApprovalEventRow, row.approval_event_id) is not None


def test_authenticated_kr_approval_promotes_only_issuer(database_context) -> None:
    harness = _kr_harness(database_context)
    ready = harness.engine.evaluate(_kr_request(harness))
    clock = Clock(EVALUATED_AT + timedelta(minutes=1))
    runtime = _Runtime(database_context.engine, lambda: OWNER, clock)
    authenticator = Authenticator()
    enroll(runtime, authenticator)
    service = IssuerDispositionService(runtime, harness.engine)
    with harness.sessions() as session:
        before = _counts(session)
        provider = session.get(
            ProviderSecurityIdentityRow, ready.bundle.provider_security_identity_id
        )
        provider_before = tuple(
            (column.name, getattr(provider, column.name)) for column in provider.__table__.columns
        )
    challenge = service.issue(ready.decision.issuer_decision_id, "APPROVED")
    with pytest.raises(IssuerDispositionError, match="CHALLENGE_ALREADY_ISSUED"):
        service.issue(ready.decision.issuer_decision_id, "APPROVED")
    completed = service.complete(
        challenge.challenge_id,
        authenticator.assertion(challenge.options, 9),
        structured_reason_code="VERIFIED_EXACT_AUTHORITY",
        review_note="Reviewed official issuer authority",
    )
    assert (
        service.complete(
            challenge.challenge_id,
            authenticator.assertion(challenge.options, 9),
            structured_reason_code="VERIFIED_EXACT_AUTHORITY",
            review_note="Reviewed official issuer authority",
        )
        == completed
    )
    with pytest.raises(IssuerDispositionError):
        service.complete(
            challenge.challenge_id,
            authenticator.assertion(challenge.options, 9),
            structured_reason_code="DIFFERENT_REASON",
            review_note="Reviewed official issuer authority",
        )
    with harness.sessions() as session:
        after = _counts(session)
        assert after == (before[0] + 1, before[1], before[2])
        provider = session.get(
            ProviderSecurityIdentityRow, ready.bundle.provider_security_identity_id
        )
        assert (
            tuple(
                (column.name, getattr(provider, column.name))
                for column in provider.__table__.columns
            )
            == provider_before
        )
        assert (
            session.get(IssuerApprovalEventRow, completed.approval_event_id).event_state
            == "APPROVED"
        )
        assert session.get(IssuerAuthorityLinkRow, completed.link_id).link_state == "APPROVED"
        head = session.get(IssuerAuthorityLinkHeadRow, ready.bundle.provider_security_identity_id)
        assert head.issuer_authority_link_id == completed.link_id
        assert head.security_resolution_state == "UNRESOLVED"
        membership = session.scalars(
            select(IssuerApprovalEvidenceObservationRow)
            .where(
                IssuerApprovalEvidenceObservationRow.issuer_approval_event_id
                == completed.approval_event_id
            )
            .order_by(IssuerApprovalEvidenceObservationRow.member_ordinal)
        ).all()
        evidence_ids = tuple(
            member.evidence_id for member in ready.bundle.evidence_application_members
        )
        observations = session.scalars(
            select(AuthorityEvidenceObservationRow).where(
                AuthorityEvidenceObservationRow.evidence_id.in_(evidence_ids)
            )
        ).all()
        assert membership and len(membership) == len(observations)
        assert [row.member_ordinal for row in membership] == list(range(len(membership)))
        assert {
            (row.authority_evidence_observation_id, row.observation_content_hash)
            for row in membership
        } == {
            (row.authority_evidence_observation_id, row.observation_content_hash)
            for row in observations
        }


def test_authenticated_rejection_has_no_issuer_or_link(database_context) -> None:
    harness = _kr_harness(database_context)
    ready = harness.engine.evaluate(_kr_request(harness))
    clock = Clock(EVALUATED_AT + timedelta(minutes=1))
    runtime = _Runtime(database_context.engine, lambda: OWNER, clock)
    authenticator = Authenticator()
    enroll(runtime, authenticator)
    service = IssuerDispositionService(runtime, harness.engine)
    with harness.sessions() as session:
        before = _counts(session)
    challenge = service.issue(ready.decision.issuer_decision_id, "REJECTED")
    completed = service.complete(
        challenge.challenge_id,
        authenticator.assertion(challenge.options, 9),
        structured_reason_code="OFFICIAL_REVIEW_REJECTED",
        review_note="Authority was reviewed but declined",
    )
    with harness.sessions() as session:
        assert _counts(session) == before
        assert (
            session.get(IssuerApprovalEventRow, completed.approval_event_id).event_state
            == "REJECTED"
        )
        assert completed.issuer_id is None
        assert completed.link_id is None
        assert (
            session.get(IssuerAuthorityLinkHeadRow, ready.bundle.provider_security_identity_id)
            is None
        )


def test_assertion_for_other_disposition_cannot_authorize_approval(database_context) -> None:
    harness = _kr_harness(database_context)
    ready = harness.engine.evaluate(_kr_request(harness))
    clock = Clock(EVALUATED_AT + timedelta(minutes=1))
    runtime = _Runtime(database_context.engine, lambda: OWNER, clock)
    authenticator = Authenticator()
    enroll(runtime, authenticator)
    service = IssuerDispositionService(runtime, harness.engine)
    approve = service.issue(ready.decision.issuer_decision_id, "APPROVED")
    reject = service.issue(ready.decision.issuer_decision_id, "REJECTED")
    with pytest.raises(IssuerDispositionError):
        service.complete(
            approve.challenge_id,
            authenticator.assertion(reject.options, 9),
            structured_reason_code="WRONG_DISPOSITION",
            review_note="Must not approve",
        )
    with harness.sessions() as session:
        consumption = session.scalar(
            select(IssuerApprovalChallengeConsumptionRow).where(
                IssuerApprovalChallengeConsumptionRow.issuer_approval_challenge_id
                == approve.challenge_id
            )
        )
        assert consumption.terminal_result == "BINDING_MISMATCH"
        assert session.scalar(select(func.count()).select_from(IssuerApprovalEventRow)) == 0


def test_supersession_cas_failure_keeps_only_authentication_audit(
    database_context, monkeypatch
) -> None:
    harness = _kr_harness(database_context)
    first = harness.engine.evaluate(_kr_request(harness))
    clock = Clock(EVALUATED_AT + timedelta(minutes=1))
    runtime = _Runtime(database_context.engine, lambda: OWNER, clock)
    authenticator = Authenticator()
    enroll(runtime, authenticator)
    service = IssuerDispositionService(runtime, harness.engine)
    first_challenge = service.issue(first.decision.issuer_decision_id, "APPROVED")
    initial = service.complete(
        first_challenge.challenge_id,
        authenticator.assertion(first_challenge.options, 9),
        structured_reason_code="VERIFIED_EXACT_AUTHORITY",
        review_note="Original issuer approved",
    )
    corrected = _append_corrected_iros(harness, suffix="fault-b2d")
    corrected_ids = (
        *(
            item.evidence_id
            for key, item in harness.evidence.items()
            if key not in {"iros_jurisdiction", "iros_bridge", "iros_name"}
        ),
        *(item.evidence_id for item in corrected),
    )
    harness.clock.value = EVALUATED_AT + timedelta(minutes=2)
    successor = harness.engine.evaluate(_kr_request(harness, evidence_ids=corrected_ids))
    clock.value = EVALUATED_AT + timedelta(minutes=3)
    old_challenge, new_challenge = service.issue_supersession(successor.decision.issuer_decision_id)

    def fail_cas(*_args):
        raise IssuerDispositionError("INJECTED_CAS_CONFLICT")

    monkeypatch.setattr(service, "_cas_head", fail_cas)
    with pytest.raises(IssuerDispositionError, match="INJECTED_CAS_CONFLICT"):
        service.complete_supersession(
            old_challenge.challenge_id,
            authenticator.assertion(old_challenge.options, 10),
            new_challenge.challenge_id,
            authenticator.assertion(new_challenge.options, 11),
            supersession_reason_code="OFFICIAL_CORRECTION",
            supersession_note="Old authority superseded",
            approval_reason_code="VERIFIED_SUCCESSOR",
            approval_note="Successor authority approved",
        )
    with harness.sessions() as session:
        assert session.scalar(select(func.count()).select_from(IssuerApprovalEventRow)) == 1
        assert session.scalar(select(func.count()).select_from(IssuerAuthorityLinkRow)) == 1
        assert (
            session.scalar(select(func.count()).select_from(IssuerApprovalChallengeConsumptionRow))
            == 3
        )
        head = session.get(IssuerAuthorityLinkHeadRow, first.bundle.provider_security_identity_id)
        assert head.issuer_authority_link_id == initial.link_id


def test_revocation_appends_history_and_moves_head(database_context) -> None:
    harness = _kr_harness(database_context)
    ready = harness.engine.evaluate(_kr_request(harness))
    clock = Clock(EVALUATED_AT + timedelta(minutes=1))
    runtime = _Runtime(database_context.engine, lambda: OWNER, clock)
    authenticator = Authenticator()
    enroll(runtime, authenticator)
    service = IssuerDispositionService(runtime, harness.engine)
    approved_challenge = service.issue(ready.decision.issuer_decision_id, "APPROVED")
    approved = service.complete(
        approved_challenge.challenge_id,
        authenticator.assertion(approved_challenge.options, 9),
        structured_reason_code="VERIFIED_EXACT_AUTHORITY",
        review_note="Approved original issuer",
    )
    clock.value += timedelta(seconds=1)
    revocation_challenge = service.issue_revocation(ready.bundle.provider_security_identity_id)
    revoked = service.complete(
        revocation_challenge.challenge_id,
        authenticator.assertion(revocation_challenge.options, 10),
        structured_reason_code="HUMAN_REVOCATION",
        review_note="Revoked current issuer authority",
    )
    with harness.sessions() as session:
        assert (
            session.get(IssuerApprovalEventRow, approved.approval_event_id).event_state
            == "APPROVED"
        )
        assert session.get(IssuerAuthorityLinkRow, approved.link_id).link_state == "APPROVED"
        new_event = session.get(IssuerApprovalEventRow, revoked.approval_event_id)
        new_link = session.get(IssuerAuthorityLinkRow, revoked.link_id)
        head = session.get(IssuerAuthorityLinkHeadRow, ready.bundle.provider_security_identity_id)
        assert new_event.event_state == "REVOKED"
        assert new_event.predecessor_approval_event_id == approved.approval_event_id
        assert new_link.link_state == "REVOKED"
        assert new_link.supersedes_link_id == approved.link_id
        assert head.issuer_authority_link_id == revoked.link_id
        assert head.link_state == "REVOKED"


def test_supersession_uses_two_authentications_and_one_head_transition(database_context) -> None:
    harness = _kr_harness(database_context)
    first = harness.engine.evaluate(_kr_request(harness))
    clock = Clock(EVALUATED_AT + timedelta(minutes=1))
    runtime = _Runtime(database_context.engine, lambda: OWNER, clock)
    authenticator = Authenticator()
    enroll(runtime, authenticator)
    service = IssuerDispositionService(runtime, harness.engine)
    first_challenge = service.issue(first.decision.issuer_decision_id, "APPROVED")
    initial = service.complete(
        first_challenge.challenge_id,
        authenticator.assertion(first_challenge.options, 9),
        structured_reason_code="VERIFIED_EXACT_AUTHORITY",
        review_note="Original issuer approved",
    )
    corrected = _append_corrected_iros(harness, suffix="b2d")
    corrected_ids = (
        *(
            item.evidence_id
            for key, item in harness.evidence.items()
            if key not in {"iros_jurisdiction", "iros_bridge", "iros_name"}
        ),
        *(item.evidence_id for item in corrected),
    )
    harness.clock.value = EVALUATED_AT + timedelta(minutes=2)
    successor = harness.engine.evaluate(_kr_request(harness, evidence_ids=corrected_ids))
    assert successor.decision.issuer_decision_id != first.decision.issuer_decision_id
    assert successor.decision.decision_state.value == "READY_FOR_MANUAL_REVIEW"
    clock.value = EVALUATED_AT + timedelta(minutes=3)
    old_challenge, new_challenge = service.issue_supersession(successor.decision.issuer_decision_id)
    result = service.complete_supersession(
        old_challenge.challenge_id,
        authenticator.assertion(old_challenge.options, 10),
        new_challenge.challenge_id,
        authenticator.assertion(new_challenge.options, 11),
        supersession_reason_code="OFFICIAL_CORRECTION",
        supersession_note="Old authority superseded",
        approval_reason_code="VERIFIED_SUCCESSOR",
        approval_note="Successor authority approved",
    )
    assert (
        service.complete_supersession(
            old_challenge.challenge_id,
            authenticator.assertion(old_challenge.options, 10),
            new_challenge.challenge_id,
            authenticator.assertion(new_challenge.options, 11),
            supersession_reason_code="OFFICIAL_CORRECTION",
            supersession_note="Old authority superseded",
            approval_reason_code="VERIFIED_SUCCESSOR",
            approval_note="Successor authority approved",
        )
        == result
    )
    with harness.sessions() as session:
        assert (
            session.get(IssuerApprovalEventRow, result.superseded_event_id).event_state
            == "SUPERSEDED"
        )
        assert (
            session.get(IssuerApprovalEventRow, result.approved_event_id).event_state == "APPROVED"
        )
        assert (
            session.get(IssuerAuthorityLinkRow, result.superseded_link_id).supersedes_link_id
            == initial.link_id
        )
        assert (
            session.get(IssuerAuthorityLinkRow, result.approved_link_id).supersedes_link_id
            == result.superseded_link_id
        )
        head = session.get(IssuerAuthorityLinkHeadRow, first.bundle.provider_security_identity_id)
        assert head.issuer_authority_link_id == result.approved_link_id


def test_one_authentication_cannot_supersede_current_approval(database_context) -> None:
    harness = _kr_harness(database_context)
    first = harness.engine.evaluate(_kr_request(harness))
    clock = Clock(EVALUATED_AT + timedelta(minutes=1))
    runtime = _Runtime(database_context.engine, lambda: OWNER, clock)
    authenticator = Authenticator()
    enroll(runtime, authenticator)
    service = IssuerDispositionService(runtime, harness.engine)
    first_challenge = service.issue(first.decision.issuer_decision_id, "APPROVED")
    initial = service.complete(
        first_challenge.challenge_id,
        authenticator.assertion(first_challenge.options, 9),
        structured_reason_code="VERIFIED_EXACT_AUTHORITY",
        review_note="Original issuer approved",
    )
    corrected = _append_corrected_iros(harness, suffix="b2d-single-auth")
    corrected_ids = (
        *(
            item.evidence_id
            for key, item in harness.evidence.items()
            if key not in {"iros_jurisdiction", "iros_bridge", "iros_name"}
        ),
        *(item.evidence_id for item in corrected),
    )
    harness.clock.value = EVALUATED_AT + timedelta(minutes=2)
    successor = harness.engine.evaluate(_kr_request(harness, evidence_ids=corrected_ids))
    clock.value = EVALUATED_AT + timedelta(minutes=3)
    old_challenge, new_challenge = service.issue_supersession(successor.decision.issuer_decision_id)
    with pytest.raises(IssuerDispositionError, match="PAIRED_SUPERSESSION_REQUIRED"):
        service.complete(
            old_challenge.challenge_id,
            authenticator.assertion(old_challenge.options, 10),
            structured_reason_code="OFFICIAL_CORRECTION",
            review_note="One authenticator assertion",
        )
    with harness.sessions() as session:
        assert session.get(IssuerApprovalChallengeRow, new_challenge.challenge_id)
        assert session.scalar(select(func.count()).select_from(IssuerApprovalEventRow)) == 1
        assert session.scalar(select(func.count()).select_from(IssuerAuthorityLinkRow)) == 1
        head = session.get(IssuerAuthorityLinkHeadRow, first.bundle.provider_security_identity_id)
        assert head.issuer_authority_link_id == initial.link_id
        assert head.link_state == "APPROVED"


def test_late_official_correction_suspends_current_approval(database_context) -> None:
    harness = _kr_harness(database_context)
    ready = harness.engine.evaluate(_kr_request(harness))
    clock = Clock(EVALUATED_AT + timedelta(minutes=1))
    runtime = _Runtime(database_context.engine, lambda: OWNER, clock)
    authenticator = Authenticator()
    enroll(runtime, authenticator)
    service = IssuerDispositionService(runtime, harness.engine)
    challenge = service.issue(ready.decision.issuer_decision_id, "APPROVED")
    approved = service.complete(
        challenge.challenge_id,
        authenticator.assertion(challenge.options, 9),
        structured_reason_code="VERIFIED_EXACT_AUTHORITY",
        review_note="Approved original authority",
    )
    _append_corrected_iros(harness, suffix="late-b2d")
    harness.clock.value = EVALUATED_AT + timedelta(minutes=2)
    clock.value = EVALUATED_AT + timedelta(minutes=2)
    safety_link_id = service.revalidate_current_link(ready.bundle.provider_security_identity_id)
    with harness.sessions() as session:
        old_event = session.get(IssuerApprovalEventRow, approved.approval_event_id)
        old_link = session.get(IssuerAuthorityLinkRow, approved.link_id)
        safety = session.get(IssuerAuthorityLinkRow, safety_link_id)
        head = session.get(IssuerAuthorityLinkHeadRow, ready.bundle.provider_security_identity_id)
        assert old_event.event_state == "APPROVED"
        assert old_link.link_state == "APPROVED"
        assert safety.link_state == "REVIEW_REQUIRED"
        assert safety.approval_event_id is None
        assert safety.machine_trigger_decision_id is not None
        assert safety.supersedes_link_id == approved.link_id
        assert head.issuer_authority_link_id == safety_link_id
        assert head.link_state == "REVIEW_REQUIRED"


def test_authenticated_us_approval_uses_registrant_cik(database_context) -> None:
    harness = _us_harness(database_context)
    ready = harness.engine.evaluate(_us_request(harness))
    clock = Clock(EVALUATED_AT + timedelta(minutes=1))
    runtime = _Runtime(database_context.engine, lambda: OWNER, clock)
    authenticator = Authenticator()
    enroll(runtime, authenticator)
    service = IssuerDispositionService(runtime, harness.engine)
    challenge = service.issue(ready.decision.issuer_decision_id, "APPROVED")
    completed = service.complete(
        challenge.challenge_id,
        authenticator.assertion(challenge.options, 9),
        structured_reason_code="VERIFIED_REGISTRANT",
        review_note="Reviewed SEC registrant and state authority",
    )
    with harness.sessions() as session:
        issuer = session.get(IssuerRow, completed.issuer_id)
        assert issuer.jurisdiction == "US"
        assert issuer.cik == ready.bundle.candidate_identifier_value
        assert issuer.corp_code is None
        head = session.get(IssuerAuthorityLinkHeadRow, ready.bundle.provider_security_identity_id)
        assert head.link_state == "APPROVED"


def test_late_staleness_appends_review_required_safety_decision(database_context) -> None:
    harness = _kr_harness(database_context)
    ready = harness.engine.evaluate(_kr_request(harness))
    clock = Clock(EVALUATED_AT + timedelta(minutes=1))
    runtime = _Runtime(database_context.engine, lambda: OWNER, clock)
    authenticator = Authenticator()
    enroll(runtime, authenticator)
    service = IssuerDispositionService(runtime, harness.engine)
    challenge = service.issue(ready.decision.issuer_decision_id, "APPROVED")
    service.complete(
        challenge.challenge_id,
        authenticator.assertion(challenge.options, 9),
        structured_reason_code="VERIFIED_EXACT_AUTHORITY",
        review_note="Approved original authority",
    )
    harness.clock.value = EVALUATED_AT + timedelta(hours=26)
    clock.value = harness.clock.value
    link_id = service.revalidate_current_link(ready.bundle.provider_security_identity_id)
    with harness.sessions() as session:
        link = session.get(IssuerAuthorityLinkRow, link_id)
        trigger = session.get(IssuerDecisionRow, link.machine_trigger_decision_id)
        assert link.link_state == "REVIEW_REQUIRED"
        assert trigger.decision_state == "REVIEW_REQUIRED"
        assert trigger.supersedes_decision_id is not None


def test_approval_and_rejection_compete_for_one_initial_disposition(database_context) -> None:
    harness = _kr_harness(database_context)
    ready = harness.engine.evaluate(_kr_request(harness))
    clock = Clock(EVALUATED_AT + timedelta(minutes=1))
    runtime = _Runtime(database_context.engine, lambda: OWNER, clock)
    authenticator = Authenticator()
    enroll(runtime, authenticator, registration_count=0, assertion_count=0)
    service = IssuerDispositionService(runtime, harness.engine)
    approve = service.issue(ready.decision.issuer_decision_id, "APPROVED")
    reject = service.issue(ready.decision.issuer_decision_id, "REJECTED")
    gate = Barrier(2)

    def attempt(challenge, reason: str):
        assertion = authenticator.assertion(challenge.options, 0)
        gate.wait()
        try:
            return service.complete(
                challenge.challenge_id,
                assertion,
                structured_reason_code=reason,
                review_note="Concurrent human disposition",
            )
        except IssuerDispositionError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(attempt, approve, "APPROVE"),
            pool.submit(attempt, reject, "REJECT"),
        ]
        outcomes = [future.result() for future in futures]
    assert sum(not isinstance(item, str) for item in outcomes) == 1
    assert sum(item == "INITIAL_DISPOSITION_CONFLICT" for item in outcomes) == 1
    with harness.sessions() as session:
        events = session.scalars(select(IssuerApprovalEventRow)).all()
        assert len(events) == 1
        assert (
            session.scalar(select(func.count()).select_from(IssuerApprovalChallengeConsumptionRow))
            == 2
        )
        assert session.scalar(select(func.count()).select_from(IssuerAuthorityLinkRow)) <= 1


def test_authority_changes_after_authentication_preserve_consumption_only(database_context) -> None:
    harness = _kr_harness(database_context)
    ready = harness.engine.evaluate(_kr_request(harness))
    clock = Clock(EVALUATED_AT + timedelta(minutes=1))
    runtime = _Runtime(database_context.engine, lambda: OWNER, clock)
    authenticator = Authenticator()
    enroll(runtime, authenticator)
    service = IssuerDispositionService(runtime, harness.engine)
    challenge = service.issue(ready.decision.issuer_decision_id, "APPROVED")
    with harness.sessions() as session:
        before = _counts(session)
    _append_corrected_iros(harness, suffix="between-auth-and-approval")
    clock.value = EVALUATED_AT + timedelta(minutes=2)
    harness.clock.value = clock.value
    with pytest.raises(IssuerDispositionError, match="AUTHORITY_CHANGED"):
        service.complete(
            challenge.challenge_id,
            authenticator.assertion(challenge.options, 9),
            structured_reason_code="VERIFIED_EXACT_AUTHORITY",
            review_note="Authority changed before approval",
        )
    with harness.sessions() as session:
        assert _counts(session) == before
        consumption = session.scalar(select(IssuerApprovalChallengeConsumptionRow))
        assert consumption.terminal_result == "SUCCEEDED"
        assert session.scalar(select(func.count()).select_from(IssuerApprovalEventRow)) == 0
        assert (
            session.get(IssuerAuthorityLinkHeadRow, ready.bundle.provider_security_identity_id)
            is None
        )


def test_wrong_origin_consumes_challenge_without_approval(database_context) -> None:
    harness = _kr_harness(database_context)
    ready = harness.engine.evaluate(_kr_request(harness))
    clock = Clock(EVALUATED_AT + timedelta(minutes=1))
    runtime = _Runtime(database_context.engine, lambda: OWNER, clock)
    authenticator = Authenticator()
    enroll(runtime, authenticator)
    service = IssuerDispositionService(runtime, harness.engine)
    challenge = service.issue(ready.decision.issuer_decision_id, "APPROVED")
    invalid = authenticator.assertion(challenge.options, 9, origin="http://wrong.example")
    with pytest.raises(IssuerDispositionError):
        service.complete(
            challenge.challenge_id,
            invalid,
            structured_reason_code="VERIFIED_EXACT_AUTHORITY",
            review_note="Never approved",
        )
    with harness.sessions() as session:
        consumption = session.scalar(
            select(IssuerApprovalChallengeConsumptionRow).where(
                IssuerApprovalChallengeConsumptionRow.issuer_approval_challenge_id
                == challenge.challenge_id
            )
        )
        assert consumption is not None
        assert consumption.terminal_result != "SUCCEEDED"
        assert session.scalar(select(func.count()).select_from(IssuerApprovalEventRow)) == 0
        assert (
            session.get(IssuerAuthorityLinkHeadRow, ready.bundle.provider_security_identity_id)
            is None
        )


@pytest.mark.parametrize(
    "failure",
    ("invalid_signature", "wrong_rp", "missing_uv", "missing_up", "unknown_credential", "expired"),
)
def test_failed_webauthn_never_authorizes_disposition(
    database_context, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    harness = _kr_harness(database_context)
    ready = harness.engine.evaluate(_kr_request(harness))
    clock = Clock(EVALUATED_AT + timedelta(minutes=1))
    runtime = _Runtime(database_context.engine, lambda: OWNER, clock)
    authenticator = Authenticator()
    enroll(runtime, authenticator)
    service = IssuerDispositionService(runtime, harness.engine)
    challenge = service.issue(ready.decision.issuer_decision_id, "APPROVED")
    with harness.sessions() as session:
        initial_issuer_count = session.scalar(select(func.count()).select_from(IssuerRow))
    if failure == "wrong_rp":
        monkeypatch.setattr("tests.backend.reviewer_test_support.RP_ID", "wrong.example")
    assertion = authenticator.assertion(
        challenge.options,
        9,
        invalid=failure == "invalid_signature",
        flags=1 if failure == "missing_uv" else 4 if failure == "missing_up" else 5,
    )
    if failure == "unknown_credential":
        assertion["id"] = assertion["rawId"] = "dW5rbm93bi1jcmVkZW50aWFs"
    if failure == "expired":
        clock.value += timedelta(minutes=6)
    with pytest.raises(IssuerDispositionError):
        service.complete(
            challenge.challenge_id,
            assertion,
            structured_reason_code="VERIFIED_EXACT_AUTHORITY",
            review_note="Must not approve",
        )
    with harness.sessions() as session:
        consumption = session.scalar(select(IssuerApprovalChallengeConsumptionRow))
        assert consumption is not None
        assert consumption.terminal_result != "SUCCEEDED"
        assert session.scalar(select(func.count()).select_from(IssuerApprovalEventRow)) == 0
        assert session.scalar(select(func.count()).select_from(IssuerRow)) == initial_issuer_count
        assert session.scalar(select(func.count()).select_from(IssuerAuthorityLinkRow)) == 0


@pytest.mark.parametrize(
    "field,value",
    (
        ("requested_disposition", "REJECTED"),
        ("issuer_decision_id", "wrong_decision"),
        ("authority_bundle_id", "wrong_bundle"),
        ("expected_decision_content_hash", "sha256:" + "a" * 64),
        ("expected_bundle_content_hash", "sha256:" + "b" * 64),
        ("provider_security_identity_id", "wrong_provider"),
        ("proposed_issuer_id", "wrong_issuer"),
        ("predecessor_approval_event_id", "wrong_predecessor"),
        ("successor_decision_id", "wrong_successor"),
    ),
)
def test_challenge_binding_is_append_only(database_context, field: str, value: str) -> None:
    harness = _kr_harness(database_context)
    ready = harness.engine.evaluate(_kr_request(harness))
    clock = Clock(EVALUATED_AT + timedelta(minutes=1))
    runtime = _Runtime(database_context.engine, lambda: OWNER, clock)
    authenticator = Authenticator()
    enroll(runtime, authenticator)
    service = IssuerDispositionService(runtime, harness.engine)
    challenge = service.issue(ready.decision.issuer_decision_id, "APPROVED")
    with harness.sessions() as session:
        row = session.get(IssuerApprovalChallengeRow, challenge.challenge_id)
        setattr(row, field, value)
        with pytest.raises(IntegrityError, match="append-only"):
            session.commit()
        session.rollback()
    with harness.sessions() as session:
        assert (
            session.scalar(select(func.count()).select_from(IssuerApprovalChallengeConsumptionRow))
            == 0
        )
        assert session.scalar(select(func.count()).select_from(IssuerApprovalEventRow)) == 0
        assert (
            getattr(session.get(IssuerApprovalChallengeRow, challenge.challenge_id), field) != value
        )


def test_existing_semantic_issuer_is_reused_by_approval(database_context) -> None:
    harness = _kr_harness(database_context)
    ready = harness.engine.evaluate(_kr_request(harness))
    clock = Clock(EVALUATED_AT + timedelta(minutes=1))
    runtime = _Runtime(database_context.engine, lambda: OWNER, clock)
    authenticator = Authenticator()
    enroll(runtime, authenticator)
    service = IssuerDispositionService(runtime, harness.engine)
    with harness.sessions.begin() as session:
        existing_id = service._insert_issuer(session, ready.bundle)
    with harness.sessions() as session:
        before = session.scalar(select(func.count()).select_from(IssuerRow))
    challenge = service.issue(ready.decision.issuer_decision_id, "APPROVED")
    result = service.complete(
        challenge.challenge_id,
        authenticator.assertion(challenge.options, 9),
        structured_reason_code="VERIFIED_EXACT_AUTHORITY",
        review_note="Reusing the same issuer",
    )
    with harness.sessions() as session:
        assert result.issuer_id == existing_id
        assert session.scalar(select(func.count()).select_from(IssuerRow)) == before
        assert session.get(IssuerAuthorityLinkHeadRow, ready.bundle.provider_security_identity_id)


def test_conflicting_semantic_issuer_fails_after_authentication(database_context) -> None:
    harness = _kr_harness(database_context)
    ready = harness.engine.evaluate(_kr_request(harness))
    clock = Clock(EVALUATED_AT + timedelta(minutes=1))
    runtime = _Runtime(database_context.engine, lambda: OWNER, clock)
    authenticator = Authenticator()
    enroll(runtime, authenticator)
    service = IssuerDispositionService(runtime, harness.engine)
    candidate = _canonical_issuer(
        jurisdiction=Jurisdiction.KR,
        identifier_value=ready.bundle.candidate_identifier_value,
    )
    values = candidate.model_dump(mode="python")
    values["legal_name"] = values["display_name"] = "Deliberately conflicting legal name"
    values["normalized_content_hash"] = normalized_hash(
        {key: value for key, value in values.items() if key != "normalized_content_hash"}
    )
    conflict = Issuer.model_validate(values)
    _insert_canonical_issuer(harness.sessions, conflict)
    challenge = service.issue(ready.decision.issuer_decision_id, "APPROVED")
    with pytest.raises(IssuerDispositionError, match="CANONICAL_ISSUER_CONFLICT"):
        service.complete(
            challenge.challenge_id,
            authenticator.assertion(challenge.options, 9),
            structured_reason_code="VERIFIED_EXACT_AUTHORITY",
            review_note="Conflict must stop",
        )
    with harness.sessions() as session:
        consumption = session.scalar(select(IssuerApprovalChallengeConsumptionRow))
        assert consumption.terminal_result == "SUCCEEDED"
        assert session.scalar(select(func.count()).select_from(IssuerApprovalEventRow)) == 0
        assert (
            session.get(IssuerAuthorityLinkHeadRow, ready.bundle.provider_security_identity_id)
            is None
        )


def test_issuer_challenge_matches_frozen_gv09_and_binds_authority_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = (
        Path(__file__).resolve().parents[2]
        / "qa/PHASE_02_CP3_C2_B2_C_RUNTIME_CANONICALIZATION_GAP_CODEX_REPORT.md"
    ).read_text(encoding="utf-8")
    gv09 = source.split("### GV-09 — issuer challenge digest and binding", 1)[1]
    preimage = json.loads(gv09.split("serialized UTF-8:\n", 1)[1].splitlines()[0])
    raw = bytes.fromhex("202122232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f")
    expected_digest = "sha256:72dbb7336c76780023f83da4c355f2eeea85733b13d3477697917790c1229084"
    expected_binding = "sha256:63d824e6d016ba693c716b0d0c4b882eeeb8c2eb91d5fc65e3736ac0ef78a1ef"
    assert expected_digest in gv09 and expected_binding in gv09
    assert c.digest(raw) == expected_digest
    assert set(preimage) == set(c.ISSUER_CHALLENGE_FIELDS)
    assert c.row_hash(preimage, c.ISSUER_CHALLENGE_FIELDS) == expected_binding
    challenge = IssuerApprovalChallengeRow(
        **preimage, challenge_binding_hash=expected_binding, payload_json="{}"
    )
    assert c.row_hash(_binding(challenge), c.ISSUER_CHALLENGE_FIELDS) == expected_binding
    requested_lengths: list[int] = []

    def deterministic_raw(count: int) -> bytes:
        requested_lengths.append(count)
        assert count == 32
        return raw

    monkeypatch.setattr(disposition_module.secrets, "token_bytes", deterministic_raw)
    monkeypatch.setattr(
        disposition_module, "_id", lambda _prefix: preimage["issuer_approval_challenge_id"]
    )

    class CaptureSession:
        row: IssuerApprovalChallengeRow | None = None

        def scalar(self, _query):
            return None

        def add(self, row):
            self.row = row

        def flush(self):
            pass

    session = CaptureSession()
    runtime = SimpleNamespace(_clock=lambda: datetime(2026, 8, 28, tzinfo=UTC))
    service = IssuerDispositionService(runtime, None)
    ledger = SimpleNamespace(
        principal={
            "reviewer_principal_id": preimage["reviewer_principal_id"],
            "principal_content_hash": preimage["principal_content_hash"],
        },
        active={"AA": {}},
    )
    decision = SimpleNamespace(
        issuer_decision_id=preimage["issuer_decision_id"],
        decision_content_hash=preimage["expected_decision_content_hash"],
    )
    bundle = SimpleNamespace(
        authority_bundle_id=preimage["authority_bundle_id"],
        bundle_content_hash=preimage["expected_bundle_content_hash"],
        provider_security_identity_id=preimage["provider_security_identity_id"],
        proposed_issuer_id=preimage["proposed_issuer_id"],
    )
    issued = service._new_challenge(session, ledger, decision, bundle, "APPROVED")
    assert session.row is not None
    assert session.row.challenge_digest == expected_digest
    assert session.row.challenge_binding_hash == expected_binding
    assert raw.hex() not in session.row.payload_json
    assert urlsafe_b64decode(issued.options["challenge"] + "==") == raw
    assert requested_lengths == [32]
    for field in (
        "requested_disposition",
        "issuer_decision_id",
        "authority_bundle_id",
        "provider_security_identity_id",
        "predecessor_approval_event_id",
        "successor_decision_id",
    ):
        changed = dict(preimage)
        changed[field] = "REJECTED" if field == "requested_disposition" else "mutated"
        challenge = IssuerApprovalChallengeRow(
            **changed, challenge_binding_hash=expected_binding, payload_json="{}"
        )
        assert c.row_hash(_binding(challenge), c.ISSUER_CHALLENGE_FIELDS) != expected_binding


def _seed_later_observation(harness, evidence, fetched_at, status):
    observation = build_authority_evidence_observation(
        evidence_id=evidence.evidence_id,
        fetched_at=fetched_at,
        raw_content_hash=evidence.raw_content_hash,
        authority_source_locator=evidence.authority_source_locator,
        authority_document_reference=evidence.authority_document_reference,
        retrieval_status=status,
        secret_free_retrieval_fingerprint=authority_sha256(
            {"b2d_observation": evidence.evidence_id, "at": fetched_at}
        ),
        safe_status_code="OK" if status == AuthorityRetrievalStatus.SUCCEEDED else "UNAVAILABLE",
    )
    seed_preadmitted_authority_snapshot(harness.sessions, observations=(observation,))
    return observation


def test_approval_audit_binds_only_current_observation_and_revalidation(database_context) -> None:
    harness = _kr_harness(database_context)
    evidence = next(iter(harness.evidence.values()))
    with harness.sessions() as session:
        old_id = session.scalar(
            select(AuthorityEvidenceObservationRow.authority_evidence_observation_id).where(
                AuthorityEvidenceObservationRow.evidence_id == evidence.evidence_id
            )
        )
    newer = _seed_later_observation(
        harness,
        evidence,
        CURRENT_FETCHED_AT + timedelta(minutes=10),
        AuthorityRetrievalStatus.SUCCEEDED,
    )
    ready = harness.engine.evaluate(_kr_request(harness))
    clock = Clock(EVALUATED_AT + timedelta(minutes=1))
    runtime = _Runtime(database_context.engine, lambda: OWNER, clock)
    authenticator = Authenticator()
    enroll(runtime, authenticator)
    service = IssuerDispositionService(runtime, harness.engine)
    challenge = service.issue(ready.decision.issuer_decision_id, "APPROVED")
    approved = service.complete(
        challenge.challenge_id,
        authenticator.assertion(challenge.options, 9),
        structured_reason_code="VERIFIED_EXACT_AUTHORITY",
        review_note="Current observation",
    )
    with harness.sessions() as session:
        members = session.scalars(
            select(IssuerApprovalEvidenceObservationRow).where(
                IssuerApprovalEvidenceObservationRow.issuer_approval_event_id
                == approved.approval_event_id
            )
        ).all()
        member_ids = {row.authority_evidence_observation_id for row in members}
        assert newer.authority_evidence_observation_id in member_ids
        assert old_id not in member_ids
        event = session.get(IssuerApprovalEventRow, approved.approval_event_id)
        service._verify_approval_audit(session, event)
    clock.value += timedelta(seconds=1)
    pending = service.issue(ready.decision.issuer_decision_id, "APPROVED")
    _seed_later_observation(
        harness,
        evidence,
        EVALUATED_AT + timedelta(minutes=2),
        AuthorityRetrievalStatus.FAILED,
    )
    harness.clock.value = EVALUATED_AT + timedelta(minutes=3)
    clock.value = EVALUATED_AT + timedelta(minutes=3)
    with pytest.raises(IssuerDispositionError, match="AUTHORITY_CHANGED"):
        service.complete(
            pending.challenge_id,
            authenticator.assertion(pending.options, 10),
            structured_reason_code="VERIFIED_EXACT_AUTHORITY",
            review_note="Stale binding",
        )
    with harness.sessions() as session:
        assert session.scalar(select(func.count()).select_from(IssuerApprovalEventRow)) == 1
        assert (
            session.get(
                IssuerAuthorityLinkHeadRow, ready.bundle.provider_security_identity_id
            ).link_state
            == "REVIEW_REQUIRED"
        )


def test_approval_audit_detects_inserted_historical_membership(database_context) -> None:
    harness = _kr_harness(database_context)
    evidence = next(iter(harness.evidence.values()))
    with harness.sessions() as session:
        historical = session.scalar(
            select(AuthorityEvidenceObservationRow).where(
                AuthorityEvidenceObservationRow.evidence_id == evidence.evidence_id
            )
        )
        historical_id = historical.authority_evidence_observation_id
        historical_hash = historical.observation_content_hash
    _seed_later_observation(
        harness,
        evidence,
        CURRENT_FETCHED_AT + timedelta(minutes=10),
        AuthorityRetrievalStatus.SUCCEEDED,
    )
    ready = harness.engine.evaluate(_kr_request(harness))
    runtime = _Runtime(
        database_context.engine, lambda: OWNER, Clock(EVALUATED_AT + timedelta(minutes=1))
    )
    authenticator = Authenticator()
    enroll(runtime, authenticator)
    service = IssuerDispositionService(runtime, harness.engine)
    challenge = service.issue(ready.decision.issuer_decision_id, "APPROVED")
    approved = service.complete(
        challenge.challenge_id,
        authenticator.assertion(challenge.options, 9),
        structured_reason_code="VERIFIED_EXACT_AUTHORITY",
        review_note="Audit baseline",
    )
    with harness.sessions() as session:
        members = session.scalars(
            select(IssuerApprovalEvidenceObservationRow).where(
                IssuerApprovalEvidenceObservationRow.issuer_approval_event_id
                == approved.approval_event_id
            )
        ).all()
        assert historical_id not in {row.authority_evidence_observation_id for row in members}
        values = {
            "issuer_approval_event_id": approved.approval_event_id,
            "authority_evidence_observation_id": historical_id,
            "member_ordinal": len(members),
            "observation_content_hash": historical_hash,
        }
        session.add(
            IssuerApprovalEvidenceObservationRow(
                **values, membership_content_hash=authority_sha256(values), payload_json="{}"
            )
        )
        session.commit()
    with pytest.raises(IssuerDispositionError, match="APPROVAL_EVENT_AUDIT_CONFLICT"):
        service.revalidate_current_link(ready.bundle.provider_security_identity_id)


def _approved_context(database_context):
    harness = _kr_harness(database_context)
    ready = harness.engine.evaluate(_kr_request(harness))
    clock = Clock(EVALUATED_AT + timedelta(minutes=1))
    runtime = _Runtime(database_context.engine, lambda: OWNER, clock)
    authenticator = Authenticator()
    enroll(runtime, authenticator, registration_count=0, assertion_count=0)
    service = IssuerDispositionService(runtime, harness.engine)
    challenge = service.issue(ready.decision.issuer_decision_id, "APPROVED")
    approved = service.complete(
        challenge.challenge_id,
        authenticator.assertion(challenge.options, 0),
        structured_reason_code="VERIFIED_EXACT_AUTHORITY",
        review_note="Initial approval",
    )
    return harness, ready, clock, authenticator, service, approved


def test_two_duplicate_approvals_race_with_one_semantic_winner(database_context) -> None:
    harness = _kr_harness(database_context)
    ready = harness.engine.evaluate(_kr_request(harness))
    clock = Clock(EVALUATED_AT + timedelta(minutes=1))
    runtime = _Runtime(database_context.engine, lambda: OWNER, clock)
    authenticator = Authenticator()
    enroll(runtime, authenticator, registration_count=0, assertion_count=0)
    service = IssuerDispositionService(runtime, harness.engine)
    first = service.issue(ready.decision.issuer_decision_id, "APPROVED")
    clock.value += timedelta(seconds=1)
    second = service.issue(ready.decision.issuer_decision_id, "APPROVED")
    gate = Barrier(2)

    def attempt(challenge):
        assertion = authenticator.assertion(challenge.options, 0)
        gate.wait()
        try:
            return service.complete(
                challenge.challenge_id,
                assertion,
                structured_reason_code="VERIFIED_EXACT_AUTHORITY",
                review_note="Duplicate approval race",
            )
        except IssuerDispositionError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(attempt, challenge) for challenge in (first, second)]
        outcomes = [future.result() for future in futures]
    assert sum(not isinstance(item, str) for item in outcomes) == 1
    assert sum(item == "INITIAL_DISPOSITION_CONFLICT" for item in outcomes) == 1
    with harness.sessions() as session:
        events = session.scalars(select(IssuerApprovalEventRow)).all()
        links = session.scalars(select(IssuerAuthorityLinkRow)).all()
        head = session.get(IssuerAuthorityLinkHeadRow, ready.bundle.provider_security_identity_id)
        assert len(events) == len(links) == 1
        assert head.issuer_authority_link_id == links[0].issuer_authority_link_id
        assert links[0].approval_event_id == events[0].issuer_approval_event_id
        _assert_one_link_leaf(session, ready.bundle.provider_security_identity_id)


def test_two_concurrent_head_successors_have_one_leaf(database_context) -> None:
    harness, ready, clock, authenticator, service, approved = _approved_context(database_context)
    clock.value += timedelta(seconds=1)
    first = service.issue_revocation(ready.bundle.provider_security_identity_id)
    clock.value += timedelta(seconds=1)
    second = service.issue_revocation(ready.bundle.provider_security_identity_id)
    gate = Barrier(2)

    def attempt(challenge):
        assertion = authenticator.assertion(challenge.options, 0)
        gate.wait()
        try:
            return service.complete(
                challenge.challenge_id,
                assertion,
                structured_reason_code="HUMAN_REVOCATION",
                review_note="Head race",
            )
        except IssuerDispositionError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(attempt, challenge) for challenge in (first, second)]
        outcomes = [future.result() for future in futures]
    assert sum(not isinstance(item, str) for item in outcomes) == 1
    with harness.sessions() as session:
        events = session.scalars(select(IssuerApprovalEventRow)).all()
        links = session.scalars(select(IssuerAuthorityLinkRow)).all()
        head = session.get(IssuerAuthorityLinkHeadRow, ready.bundle.provider_security_identity_id)
        assert len(events) == len(links) == 2
        assert sum(row.supersedes_link_id == approved.link_id for row in links) == 1
        assert head.link_state == "REVOKED"
        assert head.issuer_authority_link_id == next(
            row.issuer_authority_link_id for row in links if row.link_state == "REVOKED"
        )
        _assert_one_link_leaf(session, ready.bundle.provider_security_identity_id)


def test_late_collision_moves_both_approved_provider_heads_to_review(database_context) -> None:
    first = _kr_harness(database_context, label="b2d_multi_a")
    second = _kr_harness(
        database_context,
        label="b2d_multi_b",
        corp_code="00126381",
        overview_jurir="1101110000001",
        iros_jurir="1101110000001",
        opendart_legal_name="Second Korean Corporation",
        iros_legal_name="Second Korean Corporation",
    )
    a = first.engine.evaluate(_kr_request(first))
    b = second.engine.evaluate(_kr_request(second, identifier_value="00126381"))
    assert a.decision.decision_state == IssuerMachineDecisionState.READY_FOR_MANUAL_REVIEW
    assert b.decision.decision_state == IssuerMachineDecisionState.READY_FOR_MANUAL_REVIEW
    clock = Clock(EVALUATED_AT + timedelta(minutes=1))
    runtime = _Runtime(database_context.engine, lambda: OWNER, clock)
    authenticator = Authenticator()
    enroll(runtime, authenticator, registration_count=0, assertion_count=0)
    service = IssuerDispositionService(runtime, first.engine)
    approvals = []
    for decision in (a.decision, b.decision):
        challenge = service.issue(decision.issuer_decision_id, "APPROVED")
        approvals.append(
            service.complete(
                challenge.challenge_id,
                authenticator.assertion(challenge.options, 0),
                structured_reason_code="VERIFIED_EXACT_AUTHORITY",
                review_note="Distinct provider",
            )
        )
    collision = service.evaluate_and_revalidate_affected(
        _kr_request(
            second,
            identifier_value="00126380",
            evidence_ids=tuple(item.evidence_id for item in first.evidence.values()),
        )
    )
    assert {first.provider_id, second.provider_id} <= set(collision.affected_provider_ids)
    with first.sessions() as session:
        heads = [
            session.get(IssuerAuthorityLinkHeadRow, provider_id)
            for provider_id in (first.provider_id, second.provider_id)
        ]
        assert [head.link_state for head in heads] == ["REVIEW_REQUIRED", "REVIEW_REQUIRED"]
        assert session.scalar(select(func.count()).select_from(IssuerApprovalEventRow)) == 2
        assert all(session.get(IssuerRow, approval.issuer_id) is not None for approval in approvals)
        for head, approval in zip(heads, approvals, strict=True):
            old_link = session.get(IssuerAuthorityLinkRow, approval.link_id)
            new_link = session.get(IssuerAuthorityLinkRow, head.issuer_authority_link_id)
            assert old_link.link_state == "APPROVED"
            assert new_link.link_state == "REVIEW_REQUIRED"
            assert new_link.supersedes_link_id == approval.link_id
            assert new_link.machine_trigger_decision_id is not None
            assert (
                session.get(IssuerDecisionRow, new_link.machine_trigger_decision_id).decision_state
                == "REVIEW_REQUIRED"
            )
        for provider_id in (first.provider_id, second.provider_id):
            _assert_one_link_leaf(session, provider_id)


def test_revocation_races_with_safety_head_successor(database_context) -> None:
    harness, ready, clock, authenticator, service, approved = _approved_context(database_context)
    clock.value += timedelta(seconds=1)
    revoke = service.issue_revocation(ready.bundle.provider_security_identity_id)
    _append_corrected_iros(harness, suffix="revocation-race")
    harness.clock.value = EVALUATED_AT + timedelta(minutes=2)
    clock.value = EVALUATED_AT + timedelta(minutes=2)
    assertion = authenticator.assertion(revoke.options, 0)
    gate = Barrier(2)

    def revocation():
        gate.wait()
        try:
            return service.complete(
                revoke.challenge_id,
                assertion,
                structured_reason_code="HUMAN_REVOCATION",
                review_note="Racing revocation",
            )
        except IssuerDispositionError as error:
            return error.code

    def safety():
        gate.wait()
        try:
            return service.revalidate_current_link(ready.bundle.provider_security_identity_id)
        except IssuerDispositionError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = [future.result() for future in (pool.submit(revocation), pool.submit(safety))]
    with harness.sessions() as session:
        links = session.scalars(select(IssuerAuthorityLinkRow)).all()
        events = session.scalars(select(IssuerApprovalEventRow)).all()
        head = session.get(IssuerAuthorityLinkHeadRow, ready.bundle.provider_security_identity_id)
        assert len(links) == 2
        assert len([row for row in links if row.supersedes_link_id == approved.link_id]) == 1
        assert head.issuer_authority_link_id != approved.link_id
        assert head.link_state in {"REVOKED", "REVIEW_REQUIRED"}
        assert len(events) == (2 if head.link_state == "REVOKED" else 1)
        assert sum(not isinstance(item, str) or item.startswith("ial_") for item in outcomes) == 1
        _assert_one_link_leaf(session, ready.bundle.provider_security_identity_id)


def test_supersession_pair_races_with_revocation_head_mutation(database_context) -> None:
    harness, first, clock, authenticator, service, approved = _approved_context(database_context)
    corrected = _append_corrected_iros(harness, suffix="supersession-race")
    corrected_ids = (
        *(
            item.evidence_id
            for key, item in harness.evidence.items()
            if key not in {"iros_jurisdiction", "iros_bridge", "iros_name"}
        ),
        *(item.evidence_id for item in corrected),
    )
    harness.clock.value = EVALUATED_AT + timedelta(minutes=2)
    successor = harness.engine.evaluate(_kr_request(harness, evidence_ids=corrected_ids))
    assert successor.decision.decision_state == IssuerMachineDecisionState.READY_FOR_MANUAL_REVIEW
    clock.value = EVALUATED_AT + timedelta(minutes=3)
    old_challenge, new_challenge = service.issue_supersession(successor.decision.issuer_decision_id)
    revoke = service.issue_revocation(first.bundle.provider_security_identity_id)
    old_assertion = authenticator.assertion(old_challenge.options, 0)
    new_assertion = authenticator.assertion(new_challenge.options, 0)
    revoke_assertion = authenticator.assertion(revoke.options, 0)
    gate = Barrier(2)

    def supersede():
        gate.wait()
        try:
            return service.complete_supersession(
                old_challenge.challenge_id,
                old_assertion,
                new_challenge.challenge_id,
                new_assertion,
                supersession_reason_code="OFFICIAL_CORRECTION",
                supersession_note="Old authority superseded",
                approval_reason_code="VERIFIED_SUCCESSOR",
                approval_note="Successor authority approved",
            )
        except IssuerDispositionError as error:
            return error.code

    def revocation():
        gate.wait()
        try:
            return service.complete(
                revoke.challenge_id,
                revoke_assertion,
                structured_reason_code="HUMAN_REVOCATION",
                review_note="Competing head",
            )
        except IssuerDispositionError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = [future.result() for future in (pool.submit(supersede), pool.submit(revocation))]
    assert sum(not isinstance(item, str) for item in outcomes) == 1
    with harness.sessions() as session:
        events = session.scalars(select(IssuerApprovalEventRow)).all()
        links = session.scalars(select(IssuerAuthorityLinkRow)).all()
        head = session.get(IssuerAuthorityLinkHeadRow, first.bundle.provider_security_identity_id)
        states = [row.event_state for row in events]
        assert states.count("SUPERSEDED") == states.count("APPROVED") - 1
        assert (states.count("REVOKED") == 1) != (states.count("SUPERSEDED") == 1)
        assert len(links) == len(events)
        assert sum(row.supersedes_link_id == approved.link_id for row in links) == 1
        assert (
            head.issuer_authority_link_id
            in {
                row.issuer_authority_link_id
                for row in links
                if row.supersedes_link_id == approved.link_id
            }
            or head.link_state == "APPROVED"
        )
        _assert_one_link_leaf(session, first.bundle.provider_security_identity_id)


@pytest.mark.parametrize(
    "changed_field",
    (
        "event_state",
        "issuer_decision_id",
        "authority_bundle_id",
    ),
)
def test_successful_authentication_id_cannot_cross_authority_binding(
    database_context,
    changed_field: str,
) -> None:
    harness, _ready, _clock, _authenticator, _service, approved = _approved_context(
        database_context
    )
    successor = None
    if changed_field != "event_state":
        corrected = _append_corrected_iros(harness, suffix=f"auth-reuse-{changed_field}")
        corrected_ids = (
            *(
                item.evidence_id
                for key, item in harness.evidence.items()
                if key not in {"iros_jurisdiction", "iros_bridge", "iros_name"}
            ),
            *(item.evidence_id for item in corrected),
        )
        harness.clock.value = EVALUATED_AT + timedelta(minutes=2)
        successor = harness.engine.evaluate(_kr_request(harness, evidence_ids=corrected_ids))
        assert (
            successor.decision.decision_state == IssuerMachineDecisionState.READY_FOR_MANUAL_REVIEW
        )
    with harness.sessions() as session:
        original = session.get(IssuerApprovalEventRow, approved.approval_event_id)
        values = {
            column.name: getattr(original, column.name) for column in original.__table__.columns
        }
        values["issuer_approval_event_id"] = "iap_" + "f" * 64
        values["approval_event_content_hash"] = "sha256:" + "f" * 64
        values["approval_event_audit_hash"] = "sha256:" + "e" * 64
        if changed_field == "event_state":
            values["event_state"] = "REJECTED"
        else:
            assert successor is not None
            values.update(
                issuer_decision_id=successor.decision.issuer_decision_id,
                decision_content_hash=successor.decision.decision_content_hash,
                authority_bundle_id=successor.bundle.authority_bundle_id,
                bundle_content_hash=successor.bundle.bundle_content_hash,
                proposed_issuer_id=successor.bundle.proposed_issuer_id,
            )
            assert values[changed_field] != getattr(original, changed_field)
        session.add(IssuerApprovalEventRow(**values))
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()
    with harness.sessions() as session:
        assert session.scalar(select(func.count()).select_from(IssuerApprovalEventRow)) == 1
        assert session.scalar(select(func.count()).select_from(IssuerAuthorityLinkRow)) == 1
