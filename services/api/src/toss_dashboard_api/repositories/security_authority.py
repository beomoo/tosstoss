"""Immutable storage only. C2 admission/evaluation and C3 writers are unavailable."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from toss_dashboard_api.contracts import security_authority as c
from toss_dashboard_api.storage import security_authority_models as m


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
    if isinstance(record, c.Decision) and record.machine_state == "READY_FOR_MANUAL_REVIEW":
        raise SecurityLedgerConflict("SECURITY_MACHINE_ENGINE_NOT_IMPLEMENTED")


def _insert[T: c.SecurityRecord](
    session: Session, value: T, row_type: type[Any]
) -> InsertResult[T]:
    # Revalidate even objects supplied through model_construct/model_copy.
    payload = c.canonical_security_bytes(value).decode("utf-8")
    value = type(value).model_validate_json(payload)
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
