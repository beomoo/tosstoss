"""R1 clock-policy boundaries against the actual frozen 0001-0007 SQLite DB."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from sqlalchemy import Engine
from tests.backend.reviewer_test_support import Authenticator, Clock
from tests.backend.test_reviewer_runtime import OWNER, enroll, runtime, snapshot

from toss_dashboard_api.reviewer import canonical as c
from toss_dashboard_api.reviewer import runtime as implementation
from toss_dashboard_api.reviewer import schema as s
from toss_dashboard_api.reviewer.runtime import Ceremony, _ClockSample, _Runtime

# Explicit fixture re-export, used by pytest rather than by direct calls.
__all__ = ["runtime"]


@pytest.mark.parametrize(
    "text",
    [
        "2026-09-05T00:00:00Z",
        "2026-09-05T00:00:00.000001Z",
        "2026-09-05T00:00:00.123499Z",
        "2026-09-05T00:00:00.123500Z",
        "2026-09-05T00:00:00.123999Z",
        "2026-09-05T00:00:00.124000Z",
        "2026-09-05T00:00:00.999999Z",
        "2026-09-05T23:59:59.999999Z",
        "2026-09-30T23:59:59.999999Z",
        "2026-12-31T23:59:59.999999Z",
        "2028-02-29T23:59:59.999999Z",
    ],
)
def test_private_floor_preserves_common_microsecond_serialization(text: str) -> None:
    raw = c.parse_utc(text)
    sample = _ClockSample.take(lambda: raw)
    assert sample.raw == raw
    assert sample.stored.microsecond == raw.microsecond // 1000 * 1000
    assert timedelta(0) <= raw - sample.stored < timedelta(milliseconds=1)
    assert c.utc_text(raw) == text
    assert c.canonical_json({"at": text}) == ('{"at":"' + text + '"}').encode()
    serialized = c.utc_text(sample.stored)
    assert serialized.endswith("000Z") if sample.stored.microsecond else "." not in serialized


@pytest.mark.parametrize("offset", [123499, 123500, 999999])
@pytest.mark.parametrize(
    "start", ["2026-09-05T00:00:59Z", "2026-09-30T23:59:59Z", "2026-12-31T23:59:59Z"]
)
def test_ordinary_exact_canonical_five_minutes(
    runtime: tuple[_Runtime, Engine, Clock], start: str, offset: int
) -> None:
    service, engine, clock = runtime
    clock.value = c.parse_utc(start) + timedelta(microseconds=offset)
    raw = clock.value
    ceremony = service.issue("FIRST_ENROLLMENT")
    ledger = snapshot(engine)
    challenge = ledger.get(s.CHALLENGE, ceremony.challenge_id)
    issued, expiry = c.parse_utc(challenge["issued_at"]), c.parse_utc(ceremony.expires_at)
    assert expiry - issued == timedelta(minutes=5)
    assert timedelta(minutes=5) - timedelta(milliseconds=1) < expiry - raw <= timedelta(minutes=5)
    assert challenge["issued_at"] == c.utc_text(_ClockSample.take(clock).stored)
    assert ledger.rows(s.OPERATION)[0]["created_at"] == challenge["issued_at"]
    assert ledger.rows(s.PRINCIPAL)[0]["registered_at"] == challenge["issued_at"]
    assert challenge == s.sealed(s.CHALLENGE, challenge)


@pytest.mark.parametrize("delta_us", [-1, 0, 1])
@pytest.mark.parametrize("child", [False, True])
def test_raw_parent_and_child_deadline_boundary(
    runtime: tuple[_Runtime, Engine, Clock], child: bool, delta_us: int
) -> None:
    service, engine, clock = runtime
    clock.value += timedelta(microseconds=123999)
    authenticator = Authenticator()
    parent = service.issue("FIRST_ENROLLMENT")
    ceremony = parent
    if child:
        clock.value += timedelta(seconds=1)
        result = service.complete(
            parent.challenge_id, authenticator.registration(parent.options, 0)
        )
        assert isinstance(result, Ceremony)
        ceremony = result
    before = snapshot(engine)
    clock.value = c.parse_utc(ceremony.expires_at) + timedelta(microseconds=delta_us)
    response = (
        authenticator.assertion(ceremony.options)
        if child
        else authenticator.registration(ceremony.options, 7)
    )
    if delta_us < 0:
        assert service.complete(ceremony.challenge_id, response).result == "SUCCEEDED"
    else:
        with pytest.raises(c.ReviewerError, match="CHALLENGE_EXPIRED"):
            service.complete(ceremony.challenge_id, response)
    after = snapshot(engine)
    outcome = after.rows(s.OUTCOME)[0]
    assert outcome["completed_at"] == c.utc_text(_ClockSample.take(clock).stored)
    assert outcome["terminal_result"] == ("SUCCEEDED" if delta_us < 0 else "EXPIRED")
    assert after.rows(s.CONSUMPTION)[0]["consumed_at"] == outcome["completed_at"]
    if child:
        assert after.rows(s.BOOTSTRAP)[0]["consumed_at"] == outcome["completed_at"]
    if delta_us >= 0:
        for table in (s.CREDENTIAL, s.EVENT, s.AUTHORIZATION):
            assert after.rows(table) == before.rows(table)


@pytest.mark.parametrize("elapsed_us", [0, 1, 1000, 299_999_999, 300_000_000, 300_000_001])
def test_child_issuance_cap_positive_or_expired_parent_no_child(
    runtime: tuple[_Runtime, Engine, Clock], elapsed_us: int
) -> None:
    service, engine, clock = runtime
    authenticator = Authenticator()
    parent = service.issue("FIRST_ENROLLMENT")
    clock.value += timedelta(microseconds=elapsed_us)
    if elapsed_us >= 300_000_000:
        with pytest.raises(c.ReviewerError, match="CHALLENGE_EXPIRED"):
            service.complete(parent.challenge_id, authenticator.registration(parent.options, 0))
        ledger = snapshot(engine)
        assert not ledger.rows(s.PENDING) and not ledger.rows(s.CHILD)
        assert ledger.rows(s.OUTCOME)[0]["terminal_result"] == "EXPIRED"
        assert not ledger.rows(s.CREDENTIAL) and not ledger.rows(s.EVENT)
        return
    child = service.complete(parent.challenge_id, authenticator.registration(parent.options, 0))
    assert isinstance(child, Ceremony)
    ledger = snapshot(engine)
    row = ledger.get(s.CHILD, child.challenge_id)
    issued, expiry = c.parse_utc(row["issued_at"]), c.parse_utc(child.expires_at)
    parent_expiry = c.parse_utc(parent.expires_at)
    assert expiry == min(issued + timedelta(minutes=5), parent_expiry)
    assert timedelta(0) < expiry - issued <= timedelta(minutes=5)
    assert expiry <= parent_expiry
    assert ledger.rows(s.PENDING)[0]["verified_at"] == row["issued_at"]
    assert row == s.sealed(s.CHILD, row)


@pytest.mark.parametrize("child", [False, True])
@pytest.mark.parametrize("delay_point", ["crypto", "preprojection"])
def test_expiry_crossed_during_verification_or_final_state_check(
    runtime: tuple[_Runtime, Engine, Clock],
    monkeypatch: pytest.MonkeyPatch,
    child: bool,
    delay_point: str,
) -> None:
    service, engine, clock = runtime
    authenticator = Authenticator()
    ceremony = service.issue("FIRST_ENROLLMENT")
    if child:
        result = service.complete(
            ceremony.challenge_id, authenticator.registration(ceremony.options, 0)
        )
        assert isinstance(result, Ceremony)
        ceremony = result
    clock.value = c.parse_utc(ceremony.expires_at) - timedelta(microseconds=1)
    if delay_point == "crypto":
        name = "verify_assertion" if child else "verify_registration"
        verifier = getattr(implementation, name)

        def delayed(*args: Any, **kwargs: Any) -> Any:
            facts = verifier(*args, **kwargs)
            assert facts.terminal_result == "SUCCEEDED"
            clock.value = c.parse_utc(ceremony.expires_at)
            return facts

        monkeypatch.setattr(implementation, name, delayed)
    else:
        calls = 0

        def owner() -> str:
            nonlocal calls
            calls += 1
            if calls == 2:  # Inside writer, final target/ledger projection check.
                clock.value = c.parse_utc(ceremony.expires_at)
            return OWNER

        monkeypatch.setattr(service, "_owner", owner)
    response = (
        authenticator.assertion(ceremony.options)
        if child
        else authenticator.registration(ceremony.options, 0)
    )
    with pytest.raises(c.ReviewerError, match="CHALLENGE_EXPIRED"):
        service.complete(ceremony.challenge_id, response)
    ledger = snapshot(engine)
    assert ledger.rows(s.OUTCOME)[0]["terminal_result"] == "EXPIRED"
    for table in (s.CREDENTIAL, s.EVENT, s.AUTHORIZATION):
        assert not ledger.rows(table)
    if not child:
        assert not ledger.rows(s.CHILD) and not ledger.rows(s.PENDING)


def test_same_millisecond_events_have_exact_projection_and_independent_identity(
    runtime: tuple[_Runtime, Engine, Clock],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, engine, clock = runtime
    clock.value += timedelta(microseconds=123499)
    old, new = Authenticator(), Authenticator()
    enroll(service, old)
    challenge = service.issue("REPLACE_CREDENTIAL", target_webauthn_credential_id=old.identity)
    registration = service.complete(challenge.challenge_id, old.assertion(challenge.options))
    assert isinstance(registration, Ceremony)
    child = service.complete(registration.challenge_id, new.registration(registration.options, 0))
    assert isinstance(child, Ceremony)
    calls = 0

    def counted_clock() -> Any:
        nonlocal calls
        calls += 1
        assert calls <= 2  # Receipt, then one final decision/audit sample.
        return clock.value + timedelta(microseconds=calls)

    monkeypatch.setattr(service, "_clock", counted_clock)
    assert service.complete(child.challenge_id, new.assertion(child.options)).result == "SUCCEEDED"
    assert calls == 2
    ledger = snapshot(engine)
    assert set(ledger.active) == {new.identity}
    assert len({row[s.EVENT.key] for row in ledger.rows(s.EVENT)}) == 3
    for table in s.WRITE_TABLES:
        if table.time_column:
            assert {row[table.time_column] for row in ledger.rows(table)} <= {
                "2026-09-05T00:00:00.123000Z"
            }
    with engine.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []


@pytest.mark.parametrize("fraction", [123456, 123900])
@pytest.mark.parametrize("delta_us", [-1, 0, 1])
@pytest.mark.parametrize("child", [False, True])
def test_historical_off_grid_deadline_preservation_and_explicit_conflict(
    runtime: tuple[_Runtime, Engine, Clock],
    monkeypatch: pytest.MonkeyPatch,
    fraction: int,
    delta_us: int,
    child: bool,
) -> None:
    service, engine, clock = runtime
    old, new = Authenticator(), Authenticator()
    enroll(service, old)
    clock.value += timedelta(seconds=1, microseconds=fraction)
    # Build valid pre-policy historical rows through the old high-resolution
    # issuance behavior on this disposable DB; never rewrite an existing row.
    with monkeypatch.context() as patch:
        # Fixture construction predates the approved execution profile. Restore
        # the real boundary before every operation attempt below.
        patch.setattr(implementation, "_require_time_profile", lambda _ledger: None)
        patch.setattr(
            _ClockSample, "take", classmethod(lambda cls, source: cls(source(), source()))
        )
        authorization = service.issue("ADD_CREDENTIAL")
        registration = service.complete(
            authorization.challenge_id, old.assertion(authorization.options)
        )
        assert isinstance(registration, Ceremony)
        ceremony = registration
        if child:
            clock.value += timedelta(seconds=1)
            result = service.complete(
                registration.challenge_id, new.registration(registration.options, 0)
            )
            assert isinstance(result, Ceremony)
            ceremony = result
    before = snapshot(engine)
    clock.value = c.parse_utc(ceremony.expires_at) + timedelta(microseconds=delta_us)
    response = new.assertion(ceremony.options) if child else new.registration(ceremony.options, 0)
    with pytest.raises(c.ReviewerError, match="R1_TIME_PROFILE_INCOMPATIBLE"):
        service.complete(ceremony.challenge_id, response)
    after = snapshot(engine)
    for table in s.WRITE_TABLES:
        for row in before.rows(table):
            assert after.get(table, row[table.key]) == row
        assert after.rows(table) == before.rows(table)
    assert after.rows(s.AUTHENTICATION) == before.rows(s.AUTHENTICATION)
    assert after.counters[old.identity] == before.counters[old.identity] == 8
    for table in (s.CREDENTIAL, s.EVENT, s.AUTHORIZATION):
        assert after.rows(table) == before.rows(table)
