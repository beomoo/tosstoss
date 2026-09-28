from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from sqlalchemy import Engine
from tests.backend.conftest import alembic_config
from tests.backend.reviewer_test_support import Authenticator, Clock

from toss_dashboard_api.reviewer import schema as s
from toss_dashboard_api.reviewer.canonical import ReviewerError, decode_base64url, digest, parse_utc
from toss_dashboard_api.reviewer.ledger import Ledger
from toss_dashboard_api.reviewer.runtime import Ceremony, Completed, _Runtime
from toss_dashboard_api.storage.database import create_database_engine

OWNER = digest(b"isolated-test-owner-binding")


@pytest.fixture
def runtime(workspace_tmp_path: Path) -> Iterator[tuple[_Runtime, Engine, Clock]]:
    url = "sqlite:///" + (workspace_tmp_path / "r1.sqlite3").as_posix()
    command.upgrade(alembic_config(url), "0007_phase_02_cp3_c2_b2_c_counter_capability_bootstrap")
    engine = create_database_engine(url)
    clock = Clock()
    try:
        yield _Runtime(engine, lambda: OWNER, clock), engine, clock
    finally:
        engine.dispose()


def snapshot(engine: Engine) -> Ledger:
    with engine.connect() as connection:
        return Ledger(connection, OWNER)


def enroll(
    service: _Runtime,
    authenticator: Authenticator,
    *,
    registration_count: int = 7,
    assertion_count: int = 8,
) -> None:
    creation = service.issue("FIRST_ENROLLMENT")
    result = service.complete(
        creation.challenge_id, authenticator.registration(creation.options, registration_count)
    )
    if registration_count == 0:
        assert isinstance(result, Ceremony)
        result = service.complete(
            result.challenge_id, authenticator.assertion(result.options, assertion_count)
        )
    assert isinstance(result, Completed) and result.result == "SUCCEEDED"


@pytest.mark.parametrize("algorithm", ["ES256", "RS256"])
@pytest.mark.parametrize("registration_count,assertion_count", [(7, 8), (0, 8), (0, 0)])
def test_first_enrollment_actual_crypto(
    runtime: tuple[_Runtime, Engine, Clock],
    algorithm: str,
    registration_count: int,
    assertion_count: int,
) -> None:
    service, engine, _clock = runtime
    authenticator = Authenticator(algorithm)
    enroll(
        service,
        authenticator,
        registration_count=registration_count,
        assertion_count=assertion_count,
    )
    ledger = snapshot(engine)
    assert set(ledger.active) == {authenticator.identity}
    credential = ledger.active[authenticator.identity][0]
    assert credential["counter_capability"] == (
        "NO_USABLE_COUNTER"
        if registration_count == assertion_count == 0
        else "SIGN_COUNT_SUPPORTED"
    )
    assert ledger.counters[authenticator.identity] == (
        None if registration_count == assertion_count == 0 else (7 if registration_count else 8)
    )


@pytest.mark.parametrize("operation", ["ADD_CREDENTIAL", "REPLACE_CREDENTIAL", "REVOKE_CREDENTIAL"])
@pytest.mark.parametrize("registration_count,assertion_count", [(7, 8), (0, 8), (0, 0)])
def test_management_actual_crypto(
    runtime: tuple[_Runtime, Engine, Clock],
    operation: str,
    registration_count: int,
    assertion_count: int,
) -> None:
    service, engine, clock = runtime
    old, new = Authenticator(), Authenticator()
    enroll(service, old)
    clock.value += timedelta(seconds=1)
    intent = (
        {} if operation == "ADD_CREDENTIAL" else {"target_webauthn_credential_id": old.identity}
    )
    challenge = service.issue(operation, **intent)
    result = service.complete(challenge.challenge_id, old.assertion(challenge.options))
    if operation != "REVOKE_CREDENTIAL":
        assert isinstance(result, Ceremony)
        result = service.complete(
            result.challenge_id, new.registration(result.options, registration_count)
        )
        if registration_count == 0:
            assert isinstance(result, Ceremony)
            result = service.complete(
                result.challenge_id, new.assertion(result.options, assertion_count)
            )
    assert isinstance(result, Completed) and result.result == "SUCCEEDED"
    ledger = snapshot(engine)
    assert set(ledger.active) == (
        {old.identity, new.identity}
        if operation == "ADD_CREDENTIAL"
        else ({new.identity} if operation == "REPLACE_CREDENTIAL" else set())
    )
    assert ledger.counters[old.identity] == 8
    if operation == "REVOKE_CREDENTIAL":
        with pytest.raises(ReviewerError, match="FIRST_ENROLLMENT_PERMANENTLY_CLOSED"):
            service.issue("FIRST_ENROLLMENT")
    assert len(ledger.rows(s.OUTCOME)) == 2


@pytest.mark.parametrize("operation", ["ADD_CREDENTIAL", "REPLACE_CREDENTIAL", "REVOKE_CREDENTIAL"])
@pytest.mark.parametrize("fault", ["signature", "equal", "rollback", "origin", "target", "expiry"])
def test_failed_management_consumes_preserves_state_and_counters(
    runtime: tuple[_Runtime, Engine, Clock], operation: str, fault: str
) -> None:
    service, engine, clock = runtime
    authorizer = Authenticator()
    enroll(service, authorizer)
    before = snapshot(engine)
    intent = (
        {}
        if operation == "ADD_CREDENTIAL"
        else {"target_webauthn_credential_id": authorizer.identity}
    )
    challenge = service.issue(operation, **intent)
    response = authorizer.assertion(
        challenge.options,
        count=7 if fault == "equal" else (6 if fault == "rollback" else 9),
        invalid=fault == "signature",
        **({"origin": "http://127.0.0.1:3000"} if fault == "origin" else {}),
    )
    if fault == "target":
        response["target_webauthn_credential_id"] = "untrusted"
    if fault == "expiry":
        clock.value = parse_utc(challenge.expires_at)
    with pytest.raises(ReviewerError) as failure:
        service.complete(challenge.challenge_id, response)
    assert failure.value.code != "REVIEWER_TRANSACTION_FAILED"
    after = snapshot(engine)
    assert after.state_hash == before.state_hash and after.counters == before.counters
    assert len(after.rows(s.CONSUMPTION)) == len(before.rows(s.CONSUMPTION)) + 1
    assert len(after.rows(s.OUTCOME)) == len(before.rows(s.OUTCOME)) + 1
    assert after.rows(s.EVENT) == before.rows(s.EVENT)
    if fault == "signature":
        assert after.rows(s.AUTHENTICATION)[-1]["authentication_result"] == "REJECTED"
        assert after.rows(s.AUTHENTICATION)[-1]["signature_verified"] == 0
    with pytest.raises(ReviewerError, match="CHALLENGE_ALREADY_CONSUMED"):
        service.complete(challenge.challenge_id, response)
    assert len(snapshot(engine).rows(s.CONSUMPTION)) == len(after.rows(s.CONSUMPTION))


@pytest.mark.parametrize("zero", [False, True])
@pytest.mark.parametrize("operation", ["FIRST_ENROLLMENT", "ADD_CREDENTIAL", "REPLACE_CREDENTIAL"])
@pytest.mark.parametrize("expired", [False, True])
def test_failed_registration_and_continuation_preserve_original_operation(
    runtime: tuple[_Runtime, Engine, Clock], zero: bool, operation: str, expired: bool
) -> None:
    service, engine, clock = runtime
    old, new = Authenticator(), Authenticator()
    if operation != "FIRST_ENROLLMENT":
        enroll(service, old)
    intent = (
        {"target_webauthn_credential_id": old.identity} if operation == "REPLACE_CREDENTIAL" else {}
    )
    registration = service.issue(operation, **intent)
    if operation != "FIRST_ENROLLMENT":
        registration = service.complete(
            registration.challenge_id, old.assertion(registration.options, count=11)
        )
        assert isinstance(registration, Ceremony)
    before = snapshot(engine)
    if zero:
        child = service.complete(
            registration.challenge_id, new.registration(registration.options, 0)
        )
        assert isinstance(child, Ceremony)
        assert set(snapshot(engine).active) == set(before.active)
        response = new.assertion(child.options, invalid=True)
        terminal = child
    else:
        response = new.registration(registration.options)
        response["authenticatorAttachment"] = "cross-platform"
        terminal = registration
    if expired:
        clock.value = parse_utc(terminal.expires_at)
    with pytest.raises(ReviewerError) as failure:
        service.complete(terminal.challenge_id, response)
    assert failure.value.code != "REVIEWER_TRANSACTION_FAILED"
    after = snapshot(engine)
    assert after.state_hash == before.state_hash and after.counters == before.counters
    assert after.rows(s.EVENT) == before.rows(s.EVENT)
    assert after.rows(s.AUTHORIZATION) == before.rows(s.AUTHORIZATION)
    outcome = after.find(s.OUTCOME, reviewer_credential_operation_id=registration.operation_id)[0]
    assert outcome["terminal_result"] == (
        "EXPIRED" if expired else ("FAILED_CLOSED" if zero else "REJECTED")
    )
    if operation != "FIRST_ENROLLMENT":
        assert after.counters[old.identity] == 11


def test_failed_first_retry_keeps_principal_and_issues_fresh_unique_32_bytes(
    runtime: tuple[_Runtime, Engine, Clock],
) -> None:
    service, engine, _clock = runtime
    first = service.issue("FIRST_ENROLLMENT")
    principal = snapshot(engine).principal
    with pytest.raises(ReviewerError):
        service.complete(first.challenge_id, {})
    second = service.issue("FIRST_ENROLLMENT")
    assert (
        first.challenge_id != second.challenge_id
        and first.options["challenge"] != second.options["challenge"]
    )
    assert snapshot(engine).principal == principal
    for challenge in snapshot(engine).rows(s.CHALLENGE):
        assert parse_utc(challenge["expires_at"]) - parse_utc(challenge["issued_at"]) == timedelta(
            minutes=5
        )
    assert (
        len(decode_base64url(first.options["challenge"]))
        == len(decode_base64url(second.options["challenge"]))
        == 32
    )


@pytest.mark.parametrize("elapsed", [0, 1, 299, 300, 301])
def test_continuation_exact_parent_expiry_cap_and_no_expired_child(
    runtime: tuple[_Runtime, Engine, Clock], elapsed: int
) -> None:
    service, engine, clock = runtime
    authenticator = Authenticator()
    parent = service.issue("FIRST_ENROLLMENT")
    clock.value += timedelta(seconds=elapsed)
    payload = authenticator.registration(parent.options, 0)
    if elapsed >= 300:
        with pytest.raises(ReviewerError, match="CHALLENGE_EXPIRED"):
            service.complete(parent.challenge_id, payload)
        ledger = snapshot(engine)
        assert ledger.rows(s.PENDING) == ledger.rows(s.CHILD) == []
        assert ledger.rows(s.OUTCOME)[0]["terminal_result"] == "EXPIRED"
    else:
        child = service.complete(parent.challenge_id, payload)
        assert isinstance(child, Ceremony)
        child_row = snapshot(engine).rows(s.CHILD)[0]
        duration = parse_utc(child.expires_at) - parse_utc(child_row["issued_at"])
        assert timedelta(0) < duration <= timedelta(minutes=5)
        assert child.expires_at == parent.expires_at
        assert duration == timedelta(seconds=300 - elapsed)


def test_verification_must_finish_before_expiry(
    runtime: tuple[_Runtime, Engine, Clock], monkeypatch: pytest.MonkeyPatch
) -> None:
    import toss_dashboard_api.reviewer.runtime as implementation

    service, engine, clock = runtime
    authenticator = Authenticator()
    creation = service.issue("FIRST_ENROLLMENT")
    real_verify = implementation.verify_registration

    def verify_then_expire(*args: Any, **kwargs: Any) -> Any:
        facts = real_verify(*args, **kwargs)
        assert facts.terminal_result == "SUCCEEDED"
        clock.value = parse_utc(creation.expires_at)
        return facts

    monkeypatch.setattr(implementation, "verify_registration", verify_then_expire)
    with pytest.raises(ReviewerError, match="CHALLENGE_EXPIRED"):
        service.complete(creation.challenge_id, authenticator.registration(creation.options, 0))
    assert snapshot(engine).rows(s.CHILD) == []
    assert snapshot(engine).rows(s.OUTCOME)[0]["terminal_result"] == "EXPIRED"


def add(service: _Runtime, authorizer: Authenticator, new: Authenticator, count: int) -> None:
    challenge = service.issue("ADD_CREDENTIAL")
    creation = service.complete(
        challenge.challenge_id, authorizer.assertion(challenge.options, count)
    )
    assert isinstance(creation, Ceremony)
    result = service.complete(creation.challenge_id, new.registration(creation.options))
    assert isinstance(result, Completed)


@pytest.mark.parametrize("operation", ["REPLACE_CREDENTIAL", "REVOKE_CREDENTIAL"])
@pytest.mark.parametrize("self_authorized", [False, True])
def test_target_intent_is_not_authorizer_and_unrelated_credential_unchanged(
    runtime: tuple[_Runtime, Engine, Clock], operation: str, self_authorized: bool
) -> None:
    service, engine, _clock = runtime
    first, target, unrelated, replacement = (
        Authenticator(),
        Authenticator(),
        Authenticator(),
        Authenticator(),
    )
    enroll(service, first)
    add(service, first, target, 8)
    add(service, first, unrelated, 9)
    before = snapshot(engine)
    challenge = service.issue(operation, target_webauthn_credential_id=target.identity)
    operation_row = snapshot(engine).get(s.OPERATION, challenge.operation_id)
    assert operation_row["target_credential_id_fingerprint"] == digest(target.credential_id)
    assert {entry["id"] for entry in challenge.options["allowCredentials"]} == set(before.active)
    authorizer = target if self_authorized else first
    result = service.complete(challenge.challenge_id, authorizer.assertion(challenge.options, 12))
    if operation == "REPLACE_CREDENTIAL":
        assert isinstance(result, Ceremony)
        result = service.complete(result.challenge_id, replacement.registration(result.options))
    assert isinstance(result, Completed) and result.result == "SUCCEEDED"
    after = snapshot(engine)
    assert after.active[unrelated.identity] == before.active[unrelated.identity]
    assert after.active[first.identity] == before.active[first.identity]
    assert target.identity not in after.active
    assert len(after.find(s.EVENT, webauthn_credential_id=target.identity)) == 2


@pytest.mark.parametrize("operation", ["ADD_CREDENTIAL", "REPLACE_CREDENTIAL", "REVOKE_CREDENTIAL"])
def test_final_no_counter_revoke_stays_closed(
    runtime: tuple[_Runtime, Engine, Clock], operation: str
) -> None:
    service, engine, _clock = runtime
    authenticator = Authenticator()
    enroll(service, authenticator, registration_count=0, assertion_count=0)
    challenge = service.issue(
        "REVOKE_CREDENTIAL", target_webauthn_credential_id=authenticator.identity
    )
    service.complete(challenge.challenge_id, authenticator.assertion(challenge.options, count=23))
    ledger = snapshot(engine)
    assert not ledger.active
    auth = ledger.rows(s.AUTHENTICATION)[0]
    assert auth["previous_sign_count"] is auth["asserted_sign_count"] is None
    intent = (
        {}
        if operation == "ADD_CREDENTIAL"
        else {"target_webauthn_credential_id": authenticator.identity}
    )
    with pytest.raises(ReviewerError, match="NO_ACTIVE_AUTHORIZER"):
        service.issue(operation, **intent)
    with pytest.raises(ReviewerError, match="FIRST_ENROLLMENT_PERMANENTLY_CLOSED"):
        service.issue("FIRST_ENROLLMENT")


def test_pending_operation_and_untrusted_trust_fields_rejected(
    runtime: tuple[_Runtime, Engine, Clock],
) -> None:
    service, engine, _clock = runtime
    service.issue("FIRST_ENROLLMENT")
    with pytest.raises(ReviewerError, match="OPERATION_ALREADY_PENDING"):
        service.issue("FIRST_ENROLLMENT")
    for field in (
        "principal_content_hash",
        "os_owner_sid_hash",
        "principal_id",
        "payload_json",
        "allowCredentials",
        "expected_credential_state_hash",
        "target_credential_id_fingerprint",
    ):
        with pytest.raises(TypeError):
            service.issue("REPLACE_CREDENTIAL", **{field: "untrusted"})
    assert len(snapshot(engine).rows(s.OPERATION)) == 1


@pytest.mark.parametrize("case", ["fork", "duplicate", "disconnected", "rollback", "valid"])
def test_three_ledger_counter_union_exact_graph(
    runtime: tuple[_Runtime, Engine, Clock], case: str
) -> None:
    service, engine, _clock = runtime
    authorizer, new = Authenticator(), Authenticator()
    enroll(service, authorizer, registration_count=0, assertion_count=4)
    add(service, authorizer, new, 8)
    ledger = snapshot(engine)
    credential = ledger.active[authorizer.identity][0]
    base = ledger.rows(s.AUTHENTICATION)[0]
    # Unit-level third-ledger rows; no issuer disposition runtime is executed.
    issuer = {
        **base,
        "webauthn_credential_id": authorizer.identity,
        "previous_sign_count": 8,
        "asserted_sign_count": 19,
    }
    if case == "fork":
        issuer["previous_sign_count"] = 4
    if case == "duplicate":
        issuer.update(previous_sign_count=4, asserted_sign_count=8)
    if case == "disconnected":
        issuer.update(previous_sign_count=10, asserted_sign_count=19)
    if case == "rollback":
        issuer.update(previous_sign_count=8, asserted_sign_count=7)
    ledger.tables[s.ISSUER_AUTHENTICATION.name]["isolated-unit-edge"] = issuer
    if case == "valid":
        assert ledger._counter(credential) == 19
    else:
        with pytest.raises(ReviewerError, match="REVIEWER_LEDGER_CORRUPT"):
            ledger._counter(credential)


@pytest.mark.parametrize(
    "case",
    [
        "missing_authorization",
        "missing_root",
        "wrong_principal",
        "key_hash",
        "state_hash",
        "root_cycle",
    ],
)
def test_corrupt_persisted_graph_is_never_silently_filtered(
    runtime: tuple[_Runtime, Engine, Clock], case: str
) -> None:
    service, engine, _clock = runtime
    authenticator = Authenticator()
    enroll(service, authenticator)
    # Deliberately damage only this disposable database, leaving migrations and
    # application code unchanged. The runtime must not trust bypassed SQL guards.
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.commit()
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        names = (
            connection.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name IN "
                "('reviewer_webauthn_credentials','reviewer_webauthn_credential_events',"
                "'reviewer_webauthn_credential_event_authorizations',"
                "'reviewer_credential_operation_outcomes')"
            )
            .scalars()
            .all()
        )
        for name in names:
            assert name.replace("_", "").isalnum()
            connection.exec_driver_sql(f'DROP TRIGGER "{name}"')
        statements = {
            "missing_authorization": (
                "DELETE FROM reviewer_webauthn_credential_event_authorizations"
            ),
            "missing_root": "DELETE FROM reviewer_webauthn_credential_events",
            "wrong_principal": (
                "UPDATE reviewer_webauthn_credentials SET reviewer_principal_id='wrong-principal'"
            ),
            "key_hash": "UPDATE reviewer_webauthn_credentials SET public_key_fingerprint=?",
            "state_hash": (
                "UPDATE reviewer_credential_operation_outcomes "
                "SET resulting_credential_state_hash=?"
            ),
            "root_cycle": (
                "UPDATE reviewer_webauthn_credential_events "
                "SET supersedes_credential_event_id=credential_event_id"
            ),
        }
        connection.exec_driver_sql(
            statements[case], (digest(b"incorrect"),) if case in ("key_hash", "state_hash") else ()
        )
        connection.commit()
    with pytest.raises(ReviewerError):
        snapshot(engine)
    with pytest.raises(ReviewerError):
        service.issue("ADD_CREDENTIAL")


def test_terminal_write_failure_rolls_back_all_projection(
    runtime: tuple[_Runtime, Engine, Clock], monkeypatch: pytest.MonkeyPatch
) -> None:
    import toss_dashboard_api.reviewer.runtime as implementation

    service, engine, _clock = runtime
    authenticator = Authenticator()
    creation = service.issue("FIRST_ENROLLMENT")
    real_insert = implementation.insert

    def fail_outcome(connection: Any, table: Any, row: Any) -> None:
        if table is s.OUTCOME:
            raise ReviewerError("INJECTED_DISPOSABLE_STORAGE_FAILURE")
        real_insert(connection, table, row)

    monkeypatch.setattr(implementation, "insert", fail_outcome)
    with pytest.raises(ReviewerError, match="INJECTED_DISPOSABLE_STORAGE_FAILURE"):
        service.complete(creation.challenge_id, authenticator.registration(creation.options))
    ledger = snapshot(engine)
    assert not ledger.active and not ledger.rows(s.CONSUMPTION)
    assert not ledger.rows(s.AUTHORIZATION) and not ledger.rows(s.OUTCOME)


def test_begin_immediate_concurrent_issuance_has_one_winner(
    runtime: tuple[_Runtime, Engine, Clock],
) -> None:
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    service, engine, _clock = runtime
    barrier = Barrier(2)

    def issue() -> str:
        barrier.wait(timeout=10)
        try:
            service.issue("FIRST_ENROLLMENT")
            return "ISSUED"
        except ReviewerError as failure:
            return failure.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _index: issue(), range(2)))
    assert sorted(results) == ["ISSUED", "OPERATION_ALREADY_PENDING"]
    assert len(snapshot(engine).rows(s.OPERATION)) == 1


def test_no_secret_ceremony_material_in_database_or_log(
    runtime: tuple[_Runtime, Engine, Clock], caplog: pytest.LogCaptureFixture
) -> None:
    service, engine, _clock = runtime
    authenticator = Authenticator()
    creation = service.issue("FIRST_ENROLLMENT")
    result = service.complete(
        creation.challenge_id, authenticator.registration(creation.options, 0)
    )
    assert isinstance(result, Ceremony)
    response = authenticator.assertion(result.options)
    service.complete(result.challenge_id, response)
    ledger = snapshot(engine)
    rows = repr(ledger.tables)
    for forbidden in (
        creation.options["challenge"],
        result.options["challenge"],
        response["response"]["signature"],
        authenticator.handle,
    ):
        assert forbidden not in rows and forbidden not in caplog.text
    assert "PRIVATE KEY" not in rows and "S-1-" not in rows
