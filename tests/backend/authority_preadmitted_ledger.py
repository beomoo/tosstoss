"""White-box test seeding for an already admitted immutable authority ledger.

This module deliberately lives under ``tests/``.  Production code must never
import it.  It does not model or bypass a runtime ingestion ceremony; it only
lets decision-algorithm tests start from state that an independently trusted
future ingestion component would already have admitted.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session, sessionmaker

from toss_dashboard_api.contracts.authority import (
    AuthorityEvidence,
    AuthorityEvidenceObservation,
    AuthorityEvidenceRelation,
    AuthoritySourcePolicy,
    canonical_authority_json_bytes,
)
from toss_dashboard_api.repositories.authority import SQLiteAuthorityLedgerRepository
from toss_dashboard_api.storage.models import (
    AuthorityEvidenceObservationRow,
    AuthorityEvidenceRelationRow,
    AuthorityEvidenceRow,
    AuthoritySourcePolicyRow,
)


def _payload(value: object) -> str:
    return canonical_authority_json_bytes(value).decode("utf-8")


def _assert_same(stored_payload: str, value: object) -> None:
    if stored_payload != _payload(value):
        raise AssertionError("test pre-admitted identity has conflicting immutable content")


def seed_preadmitted_authority_snapshot(
    sessions: sessionmaker[Session],
    *,
    policies: Sequence[AuthoritySourcePolicy] = (),
    evidence: Sequence[AuthorityEvidence] = (),
    observations: Sequence[AuthorityEvidenceObservation] = (),
    relations: Sequence[AuthorityEvidenceRelation] = (),
) -> None:
    """Seed immutable rows without creating a production admission API."""

    with sessions.begin() as session:
        for policy in policies:
            existing = session.get(
                AuthoritySourcePolicyRow,
                policy.authority_source_policy_id,
            )
            if existing is not None:
                _assert_same(existing.payload_json, policy)
                continue
            session.add(
                SQLiteAuthorityLedgerRepository._source_policy_row(
                    policy,
                    _payload(policy),
                )
            )
        session.flush()

        for item in evidence:
            existing = session.get(AuthorityEvidenceRow, item.evidence_id)
            if existing is not None:
                _assert_same(existing.payload_json, item)
                continue
            if (
                session.get(
                    AuthoritySourcePolicyRow,
                    item.authority_source_policy_id,
                )
                is None
            ):
                raise AssertionError("pre-admitted evidence policy is missing")
            session.add(
                SQLiteAuthorityLedgerRepository._evidence_row(
                    item,
                    _payload(item),
                )
            )
        session.flush()

        for observation in observations:
            existing = session.get(
                AuthorityEvidenceObservationRow,
                observation.authority_evidence_observation_id,
            )
            if existing is not None:
                _assert_same(existing.payload_json, observation)
                continue
            if session.get(AuthorityEvidenceRow, observation.evidence_id) is None:
                raise AssertionError("pre-admitted observation evidence is missing")
            session.add(
                SQLiteAuthorityLedgerRepository._observation_row(
                    observation,
                    _payload(observation),
                )
            )
        session.flush()

        for relation in relations:
            existing = session.get(
                AuthorityEvidenceRelationRow,
                relation.authority_evidence_relation_id,
            )
            if existing is not None:
                _assert_same(existing.payload_json, relation)
                continue
            if any(
                session.get(AuthorityEvidenceRow, evidence_id) is None
                for evidence_id in (
                    relation.predecessor_evidence_id,
                    relation.successor_evidence_id,
                )
            ):
                raise AssertionError("pre-admitted relation endpoint is missing")
            session.add(
                SQLiteAuthorityLedgerRepository._relation_row(
                    relation,
                    _payload(relation),
                )
            )
