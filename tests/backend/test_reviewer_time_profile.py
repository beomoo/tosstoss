"""Approved immutable unfinished-operation compatibility boundary."""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from alembic import command
from sqlalchemy import Engine
from tests.backend.conftest import alembic_config
from tests.backend.reviewer_test_support import Authenticator, Clock
from tests.backend.test_reviewer_runtime import OWNER, enroll, runtime, snapshot

from toss_dashboard_api.reviewer import canonical as c
from toss_dashboard_api.reviewer import runtime as implementation
from toss_dashboard_api.reviewer import schema as s
from toss_dashboard_api.reviewer.runtime import Ceremony, _ClockSample, _Runtime
from toss_dashboard_api.storage.database import create_database_engine

__all__ = ["runtime"]


@contextmanager
def historical_setup() -> Any:
    """Construct valid pre-policy fixture rows, never bypass an execution under test."""

    def unquantized(cls: Any, source: Any) -> Any:
        raw = source()
        return cls(raw, raw)

    with (
        patch.object(_ClockSample, "take", classmethod(unquantized)),
        patch.object(implementation, "_require_time_profile", lambda _ledger: None, create=True),
    ):
        yield


@pytest.mark.parametrize("boundary,fraction", [("issued", 123900), ("expiry", 123456)])
def test_exact_reported_assertion_cannot_be_resubmitted(
    runtime: tuple[_Runtime, Engine, Clock], boundary: str, fraction: int
) -> None:
    service, engine, clock = runtime
    authorizer = Authenticator()
    enroll(service, authorizer)
    clock.value += timedelta(seconds=1, microseconds=fraction)
    with historical_setup():
        challenge = service.issue(
            "REVOKE_CREDENTIAL", target_webauthn_credential_id=authorizer.identity
        )
    assertion = authorizer.assertion(challenge.options, 8)
    original_bytes = c.canonical_json(assertion)
    before = snapshot(engine)
    clock.value = (
        clock.value + timedelta(microseconds=1)
        if boundary == "issued"
        else c.parse_utc(challenge.expires_at) - timedelta(microseconds=1)
    )
    results = []
    with patch.object(
        implementation, "verify_assertion", wraps=implementation.verify_assertion
    ) as spy:
        for moment in (clock.value, clock.value.replace(microsecond=124000)):
            clock.value = moment
            try:
                results.append(service.complete(challenge.challenge_id, assertion).result)
            except c.ReviewerError as failure:
                results.append(failure.code)
        assert results == ["R1_TIME_PROFILE_INCOMPATIBLE"] * 2
        assert spy.call_count == 0
    assert c.canonical_json(assertion) == original_bytes
    after = snapshot(engine)
    assert all(after.rows(table) == before.rows(table) for table in s.WRITE_TABLES)
    assert authorizer.identity in after.active and after.counters[authorizer.identity] == 7


@pytest.mark.parametrize(
    "operation,stage",
    [
        ("FIRST_ENROLLMENT", "registration"),
        ("FIRST_ENROLLMENT", "child"),
        ("ADD_CREDENTIAL", "authorization"),
        ("ADD_CREDENTIAL", "registration"),
        ("ADD_CREDENTIAL", "child"),
        ("REPLACE_CREDENTIAL", "authorization"),
        ("REPLACE_CREDENTIAL", "registration"),
        ("REPLACE_CREDENTIAL", "child"),
        ("REVOKE_CREDENTIAL", "authorization"),
    ],
)
def test_every_unfinished_path_blocks_all_attempts_and_entrypoints(
    runtime: tuple[_Runtime, Engine, Clock], operation: str, stage: str
) -> None:
    service, engine, clock = runtime
    old, new = Authenticator(), Authenticator()
    if operation != "FIRST_ENROLLMENT":
        enroll(service, old)
    clock.value += timedelta(seconds=1, microseconds=123900)
    intent = (
        {"target_webauthn_credential_id": old.identity}
        if operation in ("REPLACE_CREDENTIAL", "REVOKE_CREDENTIAL")
        else {}
    )
    with historical_setup():
        ceremony = service.issue(operation, **intent)
        if stage != "authorization" and operation != "FIRST_ENROLLMENT":
            result = service.complete(ceremony.challenge_id, old.assertion(ceremony.options, 8))
            assert isinstance(result, Ceremony)
            ceremony = result
        if stage == "child":
            result = service.complete(ceremony.challenge_id, new.registration(ceremony.options, 0))
            assert isinstance(result, Ceremony)
            ceremony = result
    before = snapshot(engine)
    registration = ceremony.purpose == "REGISTRATION_CREATE"
    actor = old if stage == "authorization" else new
    response = (
        actor.registration(ceremony.options, 7)
        if registration
        else actor.assertion(ceremony.options, 11)
    )
    with (
        patch.object(
            implementation, "verify_registration", wraps=implementation.verify_registration
        ) as reg,
        patch.object(
            implementation, "verify_assertion", wraps=implementation.verify_assertion
        ) as auth,
    ):
        for instance in (service, _Runtime(engine, lambda: OWNER, clock)):
            for moment in (clock.value, c.parse_utc(ceremony.expires_at) + timedelta(days=1)):
                clock.value = moment
                for wire in (response, {"different": "assertion"}, None):
                    with pytest.raises(c.ReviewerError, match="R1_TIME_PROFILE_INCOMPATIBLE"):
                        instance.complete(ceremony.challenge_id, wire)
                for kind in (
                    "FIRST_ENROLLMENT",
                    "ADD_CREDENTIAL",
                    "REPLACE_CREDENTIAL",
                    "REVOKE_CREDENTIAL",
                ):
                    target = (
                        {"target_webauthn_credential_id": old.identity}
                        if kind in ("REPLACE_CREDENTIAL", "REVOKE_CREDENTIAL")
                        else {}
                    )
                    with pytest.raises(c.ReviewerError, match="R1_TIME_PROFILE_INCOMPATIBLE"):
                        instance.issue(kind, **target)
        assert reg.call_count == auth.call_count == 0
    after = snapshot(engine)
    assert all(after.rows(t) == before.rows(t) for t in s.WRITE_TABLES)
    assert after.counters == before.counters


@pytest.mark.parametrize(
    "table,field",
    [(s.PENDING, "verified_at"), (s.CONSUMPTION, "consumed_at"), (s.CHILD, "issued_at")],
)
def test_individual_path_field_cannot_hide_behind_aligned_challenges(
    runtime: tuple[_Runtime, Engine, Clock], table: s.Table, field: str
) -> None:
    service, engine, clock = runtime
    old, new = Authenticator(), Authenticator()
    enroll(service, old)
    clock.value += timedelta(seconds=1)
    real_insert = implementation.insert

    def historical_insert(connection: Any, kind: s.Table, row: Any) -> None:
        if kind is table:
            offset = -1 if kind is s.PENDING else 1
            row = s.sealed(
                kind, {**row, field: c.utc_text(clock.value + timedelta(microseconds=offset))}
            )
        real_insert(connection, kind, row)

    # Only fixture construction writes the valid historical field. Hashes are
    # generated before insertion; frozen guards and FK checks remain active.
    with historical_setup(), patch.object(implementation, "insert", historical_insert):
        ceremony = service.issue("ADD_CREDENTIAL")
        ceremony = service.complete(ceremony.challenge_id, old.assertion(ceremony.options, 8))
        assert isinstance(ceremony, Ceremony)
        if table is not s.CONSUMPTION:
            if table is s.CHILD:
                # Child issued_at must not precede pending verified_at in SQL.
                clock.value += timedelta(seconds=1)
            ceremony = service.complete(
                ceremony.challenge_id, new.registration(ceremony.options, 0)
            )
            assert isinstance(ceremony, Ceremony)
    before = snapshot(engine)
    with patch.object(
        implementation, "verify_assertion", wraps=implementation.verify_assertion
    ) as spy:
        with pytest.raises(c.ReviewerError, match="R1_TIME_PROFILE_INCOMPATIBLE"):
            service.complete(ceremony.challenge_id, {})
        assert spy.call_count == 0
    assert all(snapshot(engine).rows(t) == before.rows(t) for t in s.WRITE_TABLES)


@pytest.mark.parametrize("zero", [False, True])
def test_completed_off_grid_history_does_not_poison_new_active_execution(
    runtime: tuple[_Runtime, Engine, Clock], zero: bool
) -> None:
    service, engine, clock = runtime
    clock.value += timedelta(microseconds=123900)
    old = Authenticator()
    with historical_setup():
        enroll(service, old, registration_count=0 if zero else 7, assertion_count=8)
    before = snapshot(engine)
    clock.value += timedelta(seconds=1)
    ceremony = service.issue("REVOKE_CREDENTIAL", target_webauthn_credential_id=old.identity)
    with patch.object(
        implementation, "verify_assertion", wraps=implementation.verify_assertion
    ) as spy:
        assert (
            service.complete(ceremony.challenge_id, old.assertion(ceremony.options, 9)).result
            == "SUCCEEDED"
        )
        assert spy.call_count == 1
    after = snapshot(engine)
    for table in s.WRITE_TABLES:
        for row in before.rows(table):
            assert after.get(table, row[table.key]) == row
    assert not after.active
    with pytest.raises(c.ReviewerError, match="FIRST_ENROLLMENT_PERMANENTLY_CLOSED"):
        service.issue("FIRST_ENROLLMENT")


def restart_probe(mode: str, directory: str) -> None:
    """Manual two-process QA using separate top-level invocations and one disposable DB."""
    root = Path(directory).resolve(strict=True)
    expected = Path(__file__).resolve().parents[2] / "var" / "tmp" / "backend-tests"
    assert root.parent == expected.resolve() and len(root.name) == 32
    assert not root.is_symlink() and not root.is_junction()
    url = "sqlite:///" + (root / "time-profile-restart.sqlite3").as_posix()
    if mode == "seed":
        command.upgrade(
            alembic_config(url), "0007_phase_02_cp3_c2_b2_c_counter_capability_bootstrap"
        )
    engine = create_database_engine(url)
    clock = Clock()
    service = _Runtime(engine, lambda: OWNER, clock)
    try:
        if mode == "seed":
            old = Authenticator()
            enroll(service, old)
            clock.value += timedelta(seconds=1, microseconds=123900)
            with historical_setup():
                service.issue("REVOKE_CREDENTIAL", target_webauthn_credential_id=old.identity)
        else:
            assert mode == "verify"
            clock.value += timedelta(days=1)
            before = snapshot(engine)
            assert before.operation_leaf is not None
            challenge_id = before.operation_leaf["initial_challenge_id"]
            with patch.object(
                implementation, "verify_assertion", wraps=implementation.verify_assertion
            ) as spy:
                with pytest.raises(c.ReviewerError, match="R1_TIME_PROFILE_INCOMPATIBLE"):
                    service.complete(challenge_id, {})
                with pytest.raises(c.ReviewerError, match="R1_TIME_PROFILE_INCOMPATIBLE"):
                    service.issue("FIRST_ENROLLMENT")
                assert spy.call_count == 0
            assert all(snapshot(engine).rows(t) == before.rows(t) for t in s.WRITE_TABLES)
        print(f"restart profile probe: {mode} PASS; pid={os.getpid()}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    restart_probe(sys.argv[1], sys.argv[2])
