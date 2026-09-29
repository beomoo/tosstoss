from __future__ import annotations

import pytest
from tests.backend.security_authority_test_support import approved_issuer, candidate, policy, record

from toss_dashboard_api.contracts import security_authority as c
from toss_dashboard_api.repositories.security_authority import (
    SecurityLedgerConflict,
    SQLiteSecurityAuthorityRepository,
)
from toss_dashboard_api.storage.database import session_factory


def test_immutable_insert_read_and_conflict(database_context) -> None:
    repo = SQLiteSecurityAuthorityRepository(session_factory(database_context.engine))
    original = policy()
    assert repo.insert_or_verify(original).inserted
    assert not repo.insert_or_verify(original).inserted
    assert repo.read(c.SourcePolicy, original.policy_id) == original
    values = original.model_dump(
        exclude={"contract_version", "content_hash", "audit_hash", "recorded_at", "parser_version"}
    )
    conflicting = record(c.SourcePolicy, **values, parser_version="test/2")
    with pytest.raises(SecurityLedgerConflict, match="IMMUTABLE"):
        repo.insert_or_verify(conflicting)


def test_repository_cannot_create_ready_or_canonical_or_human_authority(database_context) -> None:
    issuer = approved_issuer(database_context)
    with database_context.engine.begin() as connection:
        g = candidate(connection, issuer)
    repo = SQLiteSecurityAuthorityRepository(session_factory(database_context.engine))
    values = g["decision"].model_dump(
        exclude={"contract_version", "content_hash", "audit_hash", "recorded_at", "machine_state"}
    )
    ready = record(c.Decision, **values, machine_state="READY_FOR_MANUAL_REVIEW")
    with pytest.raises(SecurityLedgerConflict, match="MACHINE_ENGINE_NOT_IMPLEMENTED"):
        repo.insert_or_verify(ready)
    with pytest.raises(SecurityLedgerConflict, match="POSITIVE_RUNTIME_NOT_IMPLEMENTED"):
        repo.insert_or_verify(g["subject"])
    assert not any(
        hasattr(repo, name)
        for name in ["approve", "authenticate", "evaluate", "promote", "update_head"]
    )


def test_repository_preserves_conflicting_identifier_claims(database_context) -> None:
    issuer = approved_issuer(database_context)
    with database_context.engine.begin() as connection:
        g = candidate(connection, issuer)
    repo = SQLiteSecurityAuthorityRepository(session_factory(database_context.engine))
    original = g["identifier"]
    values = original.model_dump(
        exclude={"contract_version", "content_hash", "audit_hash", "recorded_at", "claim_id"}
    )
    duplicate = record(c.IdentifierClaim, **values, claim_id="claim_second_report")
    assert repo.insert_or_verify(duplicate).inserted
    claims = repo.identifier_claims(original.identifier_kind, original.identifier_value)
    assert len(claims) == 2
    assert {v.claim_id for v in claims} == {original.claim_id, duplicate.claim_id}


def test_repository_bundle_exact_membership_replay(database_context) -> None:
    issuer = approved_issuer(database_context)
    with database_context.engine.begin() as connection:
        g = candidate(connection, issuer)
    repo = SQLiteSecurityAuthorityRepository(session_factory(database_context.engine))
    assert not repo.insert_bundle(g["bundle"], g["members"], [], []).inserted
    with pytest.raises(SecurityLedgerConflict, match="MEMBERSHIP_HASH_MISMATCH"):
        repo.insert_bundle(g["bundle"], [], [], [])
